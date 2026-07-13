# brain-service

Chat generation/orchestration service for BoopBot. Runs on the AI server (10.8.0.200), colocated with Ollama and Qdrant, reachable from the BoopBot process (on the Oracle VM) only over the WireGuard tunnel.

BoopBot sends a raw message + metadata to `/generate` and gets back either a reply or `null`; everything else (rolling history, lore retrieval/storage, the relevance check for unprompted jump-ins) happens locally on this host.

## One-time setup on the AI server

1. `docker network create brain-net`
2. `docker network connect brain-net <existing-qdrant-container-name>` — attaches the already-running Qdrant container to the network this compose project uses, without touching how it was started.
3. Confirm whether Ollama is bare-metal or containerized on this host:
   - Bare-metal: leave `OLLAMA_BASE_URL=http://host.docker.internal:11434` in `.env` (already the default).
   - Containerized: instead join it to `brain-net` and point `OLLAMA_BASE_URL` at its container name.
4. Pull the models referenced in `.env` (`OLLAMA_MODEL`, `OLLAMA_RELEVANCE_MODEL`, `OLLAMA_EMBED_MODEL`).
5. Copy the bot's persona file to `persona/chatbot_context.txt` (currently lives only on the Oracle VM, untracked — this service will fail to start without it).
6. `cp .env.example .env` and fill in real values, especially `BRAIN_SHARED_SECRET` (must match `BRAIN_SHARED_SECRET` in `BoopBot/.env`).

## Running

```
docker compose up -d --build
```

Binds port 8000 only on the WireGuard interface (`10.8.0.200:8000`), not the public interface.

## Endpoints

- `POST /generate` — main chat + jump-in path.
- `POST /lore/add` / `/lore/addme` / `/lore/list` / `/lore/forget` — manual lore management, backing `!lore` Discord commands.
- `POST /history/clear` — clears a channel's rolling history (backs `!resetchat`).
- `GET /healthz`

All `POST` endpoints require an `X-BoopBot-Secret` header matching `BRAIN_SHARED_SECRET`.

## Verification

```
curl -X POST http://10.8.0.200:8000/generate \
  -H "X-BoopBot-Secret: <secret>" -H "Content-Type: application/json" \
  -d '{"guild_id":1,"channel_id":1,"user_id":1,"user_name":"t","display_name":"t","content":"hello","is_mention":true}'
```

A request with a wrong/missing secret should get `401`.
