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
- `POST /lore/add` / `/lore/addme` / `/lore/list` / `/lore/forget` — manual lore management, backing `!lore` Discord commands. Admin gating for `!lore add` happens bot-side before this is ever called; `/lore/forget` additionally trusts a bot-supplied `is_admin` flag to refuse deleting guild-scoped entries for non-admins (personal entries are always deletable by their own owner). Guild-scoped adds (here and via auto-extraction) use a custom extraction prompt (`mem0_client._GUILD_EXTRACTION_PROMPT`) — by default mem0 treats `agent_id`-without-`user_id` as "facts about the agent itself," which is backwards for what we use `agent_id` for (shared guild knowledge, not facts about the bot), so this overrides that bias explicitly.
- `POST /lore/guild/list` / `/lore/user/list` / `/lore/update` / `/lore/delete` — used by the boop.fish website's admin Lore settings page (not Discord). Unlike `/lore/list`, these return one scope at a time (no guild+user mixing) and operate on exact `memory_id` UUIDs rather than Discord's short-id-prefix scheme — the short-id resolution in `app/lore_ids.py` exists purely for Discord's manual-typing constraint and isn't needed here. These endpoints trust the caller to have already enforced its own permissions (the website gates its entire Lore section to admins before ever calling here), so there's no `is_admin` flag on this side.
- `POST /lore/guild/scan_duplicates` — finds likely-duplicate guild lore pairs (`app/dedup.py`): for each entry, a semantic-search pass finds near neighbors, then each candidate pair is confirmed by an LLM yes/no call on `OLLAMA_SMART_MODEL`. Returns confirmed pairs for a human to review and delete via `/lore/delete` — this only *finds* duplicates, it never deletes or merges anything itself.
- `POST /lore/summarize_transcript` — summarizes an arbitrary pre-built `{name, content}` message transcript into guild lore, backing `!lore summarize`. The bot fetches the actual Discord channel history itself and sends the reconstructed transcript here — this endpoint has no idea what a "channel" even is, it just summarizes whatever text it's handed. See [Conversation summaries](#conversation-summaries) below.
- `POST /history/clear` — clears a channel's rolling history (backs `!resetchat`).
- `GET /healthz`

All `POST` endpoints require an `X-BoopBot-Secret` header matching `BRAIN_SHARED_SECRET`.

## Model routing & tools

Every `/generate` call is classified by `app/heuristics.py` before generating — pure regex, no extra model call, so the common case stays fast:

| Signal | Detected by |
|---|---|
| Image attached | `image_urls` non-empty (bot sends Discord CDN URLs; this service downloads + base64-encodes them itself, right before calling Ollama — see `app/images.py`) |
| A link in the message | URL regex |
| Explicit search intent | either a search verb ("search up/for", "look up", "find out", "check on", etc.) **or** a recency word ("latest", "newest", "today's", "recently", etc.) — the recency check exists because enumerating every possible search verb in natural English is a losing battle; "the latest X" needs a real lookup no matter how it's phrased (`heuristics.SEARCH_RE`) |
| Other question-like phrasing | keyword list — "what is", "who is", "ping", etc. (`heuristics.QUESTION_RE`) |

- **No signal** → `OLLAMA_MODEL` (fast default, e.g. `llama3.2:3b`), plain generation, same as today.
- **Any signal** → `OLLAMA_SMART_MODEL` (e.g. `qwen3-vl:8b`) via `app/tool_loop.py`, which gives the model two tools it can choose to invoke:
  - `search_web` — live web search via the Brave Search API (`app/brave_search.py`, needs `BRAVE_API_KEY`).
  - `fetch_url` — fetches and reads a specific webpage's text content (`app/web_fetch.py`, BeautifulSoup-based, truncated to `FETCH_URL_MAX_CHARS`).

  For the **"search"** reason specifically, `main.py` does **not** leave this to the model's discretion — it calls `search_web` itself and injects the results directly into the prompt before generating. This is deliberate: Ollama's tool-calling has no `tool_choice`-style way to *require* a call, and the model has been observed narrating a fake search ("I've looked it up... it's X") without ever actually invoking the tool. Pre-fetching for explicit search requests guarantees real results are in context regardless of whether the model also chooses to call the tool itself (e.g. to follow up with `fetch_url` on a specific result).

  The loop runs up to `TOOL_MAX_ROUNDS` rounds of tool-call → execute → feed result back, then forces a final plain-text answer if it hasn't converged. Tool-call/tool-result exchanges are **never** written to Redis history — only the original message and the final reply get stored, so they don't bloat future prompts (fast-path included).

Expect the smart path to be noticeably slower than the fast path — it's a bigger "thinking" model, each tool round is a full model round-trip plus real external HTTP latency, and worst case is several model calls plus a few external calls in one request. Watch the `[route] channel=... escalate=...` log line to see how often escalation is actually firing.

## Conversation summaries

Per-exchange auto-extraction (`_extract_and_store` in `main.py`) only ever sees one message + one reply at a time, so it can only ever produce small atomic facts — it can't capture "what a whole conversation was actually about." `app/summarize.py` adds a second, separate kind of memory for that, fed by two different data sources depending on trigger:

- **Automatic** (`app/idle_sweep.py`, a background loop started on FastAPI startup): checks every `IDLE_SWEEP_INTERVAL_SECONDS` whether any channel's *rolling bot-conversation cache* (Redis, populated only by messages that went through `/generate`) is close to expiring (`IDLE_SUMMARY_THRESHOLD_SECONDS` remaining). If so, summarizes that history before it disappears and marks the channel "already summarized" (a Redis key with its own TTL) so the same idle period doesn't get repeatedly summarized on every sweep. This only ever sees channels BoopBot has actually been talked to in, since it's reading our own Redis cache, not real Discord history.
- **Manual** (`!lore summarize` → `POST /lore/summarize_transcript`): the bot instead reads the *actual Discord channel* directly (`channel.history()`), finds the most recent contiguous burst of activity (stopping at the first gap of silence, capped at a max lookback so it never accidentally pulls in days of history), and sends that reconstructed transcript to `boop-brain` — which has no idea it came from Discord at all, it just summarizes whatever `{name, content}` list it's handed. This means the manual path works in **any** channel, including ones BoopBot has never participated in, unlike the automatic path above.
- Both paths store summaries the same way — `mem0_client.add(..., infer=False, metadata={"type": "summary"})`. `infer=False` skips mem0's own extraction/dedup LLM reasoning entirely, since we've already decided what the summary says ourselves; this also means summaries aren't affected by whatever issue is (still, as of this writing) causing atomic per-exchange extraction to under-report ("nothing extracted from this exchange").
- Summaries are retrieved exactly like any other guild lore entry — same semantic search, same top-K slots — no separate retrieval path. The `metadata={"type": "summary"}` tag exists for future filtering/debugging, not because retrieval treats them differently today.
- The automatic path requires `history.set_channel_guild` to have run at least once for a channel (it's called on every `/generate`) — the idle-sweep needs to know which guild a channel belongs to, since Redis history keys are only keyed by `channel_id`. The manual path doesn't need this at all, since the bot already knows the guild from Discord context.

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
