# boop-brain

Chat generation/orchestration service for BoopBot. Runs on the AI server (10.8.0.200), colocated with Ollama and Qdrant, reachable from the BoopBot process (on the Oracle VM) only over the WireGuard tunnel.

BoopBot sends a raw message + metadata to `/generate` and gets back either a reply or `null`; everything else (rolling history, lore retrieval/storage, the relevance check for unprompted jump-ins, model routing, tool calling, and image handling) happens locally on this host.

## One-time setup on the AI server

1. `docker network create boop-brain`
2. `docker network connect --alias qdrant boop-brain <existing-qdrant-container-name>` — attaches the already-running Qdrant container to the network this compose project uses (without touching how it was started) and gives it the network alias `qdrant`, so it resolves under that name regardless of its actual container name. `QDRANT_HOST=qdrant` in `.env` relies on this alias.
3. Confirm whether Ollama is bare-metal or containerized on this host:
   - Bare-metal: leave `OLLAMA_BASE_URL=http://host.docker.internal:11434` in `.env` (already the default).
   - Containerized: instead join it to `boop-brain` and point `OLLAMA_BASE_URL` at its container name.
4. Pull the models referenced in `.env` (`OLLAMA_MODEL`, `OLLAMA_RELEVANCE_MODEL`, `OLLAMA_EMBED_MODEL`, `OLLAMA_SMART_MODEL`) — the embed model is needed for mem0/Qdrant lore search, and the smart model needs both vision and tool-calling support (see [Model routing & tools](#model-routing--tools) below).
5. Copy the bot's persona file to `persona/chatbot_context.txt` (currently lives only on the Oracle VM, untracked — this service will fail to start without it).
6. `cp .env.example .env` and fill in real values, especially `BRAIN_SHARED_SECRET` (must match `BRAIN_SHARED_SECRET` in `BoopBot/.env`), `QDRANT_EMBED_DIMS` (must match `OLLAMA_EMBED_MODEL`'s actual output dimension, or Qdrant inserts will fail), and `BRAVE_API_KEY` (get one at Brave's search API portal — required for the `search_web` tool to work at all; without it, search silently fails per-request rather than blocking startup).
7. **Explicitly set `OLLAMA_SMART_MODEL`** to a vision+tools-capable model (e.g. `qwen3-vl:8b`) — if left unset it silently falls back to `OLLAMA_MODEL`, which likely has no vision support, so escalated image requests would fail to actually "see" anything with no obvious error.

## Running

```
docker compose up -d --build
```

Binds port 8000 only on the WireGuard interface (`10.8.0.200:8000`), not the public interface.

## Endpoints

- `POST /generate` — main chat + jump-in path. Routes each request to either the fast model or the smart model (see below) and returns a reply, or `null` if gate 2 declined a jump-in.
- `POST /lore/add` / `/lore/addme` / `/lore/list` / `/lore/forget` — manual lore management, backing `!lore` Discord commands.
- `POST /history/clear` — clears a channel's rolling history (backs `!resetchat`).
- `GET /healthz`

All `POST` endpoints require an `X-BoopBot-Secret` header matching `BRAIN_SHARED_SECRET`.

## Model routing & tools

Every `/generate` call is classified by `app/heuristics.py` before generating — pure regex, no extra model call, so the common case stays fast:

| Signal | Detected by |
|---|---|
| Image attached | `image_urls` non-empty (bot sends Discord CDN URLs; this service downloads + base64-encodes them itself, right before calling Ollama — see `app/images.py`) |
| A link in the message | URL regex |
| Question/search-like phrasing | keyword list — "what is", "who is", "search for", "look up", etc. |

- **No signal** → `OLLAMA_MODEL` (fast default, e.g. `llama3.2:3b`), plain generation, same as today.
- **Any signal** → `OLLAMA_SMART_MODEL` (e.g. `qwen3-vl:8b`) via `app/tool_loop.py`, which gives the model two tools it can choose to invoke (or not — providing the schema doesn't force use):
  - `search_web` — live web search via the Brave Search API (`app/brave_search.py`, needs `BRAVE_API_KEY`).
  - `fetch_url` — fetches and reads a specific webpage's text content (`app/web_fetch.py`, BeautifulSoup-based, truncated to `FETCH_URL_MAX_CHARS`).

  The loop runs up to `TOOL_MAX_ROUNDS` rounds of tool-call → execute → feed result back, then forces a final plain-text answer if it hasn't converged. Tool-call/tool-result exchanges are **never** written to Redis history — only the original message and the final reply get stored, so they don't bloat future prompts (fast-path included).

Expect the smart path to be noticeably slower than the fast path — it's a bigger "thinking" model, each tool round is a full model round-trip plus real external HTTP latency, and worst case is several model calls plus a few external calls in one request. Watch the `[route] channel=... escalate=...` log line to see how often escalation is actually firing.

## Verification

```
curl -X POST http://10.8.0.200:8000/generate \
  -H "X-BoopBot-Secret: <secret>" -H "Content-Type: application/json" \
  -d '{"guild_id":1,"channel_id":1,"user_id":1,"user_name":"t","display_name":"t","content":"hello","is_mention":true}'
```

A request with a wrong/missing secret should get `401`.

To exercise model routing and tools directly:
```
# should log escalate=None and stay on the fast model
curl -X POST http://10.8.0.200:8000/generate -H "X-BoopBot-Secret: <secret>" -H "Content-Type: application/json" \
  -d '{"guild_id":1,"channel_id":1,"user_id":1,"user_name":"t","display_name":"t","content":"hello","is_mention":true,"image_urls":[]}'

# should log escalate=question and may invoke search_web
curl -X POST http://10.8.0.200:8000/generate -H "X-BoopBot-Secret: <secret>" -H "Content-Type: application/json" \
  -d '{"guild_id":1,"channel_id":1,"user_id":1,"user_name":"t","display_name":"t","content":"what is the capital of France","is_mention":true,"image_urls":[]}'

# should log escalate=url and may invoke fetch_url
curl -X POST http://10.8.0.200:8000/generate -H "X-BoopBot-Secret: <secret>" -H "Content-Type: application/json" \
  -d '{"guild_id":1,"channel_id":1,"user_id":1,"user_name":"t","display_name":"t","content":"summarize https://en.wikipedia.org/wiki/Discord","is_mention":true,"image_urls":[]}'
```
Watch `docker logs boopbot-brain -f` for the `[route]` line and confirm `ollama ps` shows the expected model(s) loaded.
