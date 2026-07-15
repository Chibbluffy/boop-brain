import asyncio

from . import config, history, summarize


async def _summarize_channel_if_idle(channel_id: int) -> None:
    ttl = await history.get_ttl(channel_id)
    if ttl < 0:
        return  # no history right now
    if ttl > config.IDLE_SUMMARY_THRESHOLD_SECONDS:
        return  # still active enough, not close to expiring yet
    if await history.is_summarized(channel_id):
        return  # already handled this idle period

    guild_id = await history.get_channel_guild(channel_id)
    if guild_id is None:
        print(f"[idle_sweep] channel {channel_id}: no guild mapping, skipping")
        return

    conversation = await history.get_recent(channel_id)
    try:
        summary = await summarize.summarize_conversation(conversation)
        if summary:
            await summarize.store_summary(guild_id, summary)
            print(f"[idle_sweep] channel {channel_id}: stored summary ({len(summary)} chars)")
        else:
            print(f"[idle_sweep] channel {channel_id}: nothing to summarize")
    except Exception as e:
        print(f"[idle_sweep] channel {channel_id}: summarization failed: {e}")
        return  # don't mark summarized if it failed — retry on the next sweep

    await history.mark_summarized(channel_id, ttl_seconds=ttl)


async def sweep_once() -> None:
    for channel_id in await history.list_channel_ids():
        await _summarize_channel_if_idle(channel_id)


async def run_idle_sweep_loop() -> None:
    while True:
        try:
            await sweep_once()
        except Exception as e:
            print(f"[idle_sweep] sweep failed: {e}")
        await asyncio.sleep(config.IDLE_SWEEP_INTERVAL_SECONDS)
