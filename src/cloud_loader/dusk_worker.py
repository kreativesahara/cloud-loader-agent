"""Dusk Agent - uses Claude Agent SDK to manage loader.land ecosystem."""

import os
import time
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session, select

from .config import settings
from .database import engine
from .models import (
    DuskAskWake,
    DuskConfig,
    DuskRun,
    DuskRunStatus,
)

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)
from claude_agent_sdk.types import McpStdioServerConfig

dusk_scheduler: AsyncIOScheduler | None = None

DUSK_MEMORY_PATH = Path("./DUSK-MEMORY.md")


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

DUSK_SYSTEM_PROMPT = """You are Dusk Agent, Wake's other AI assistant, and the professional community manager for loader.land. You wake up every few hours and have persistent memory.

## Mission
Operate loader.land's X (Twitter) account and online presence as a professional community manager, building genuine developer community connections.

## Resources
1. **Twitter/X Account** - Post tweets + read tweets to study trends
2. **loader.land website** (https://move.loader.land) - AI Agent service platform
3. **Persistent Memory** DUSK-MEMORY.md (limit 6000 words)
4. **Web Search** - Tavily real-time search

## Tools
- `dusk_read_memory` - Read memory (first step upon waking up)
- `dusk_get_wake_answers` - Read Wake's replies
- `dusk_ask_wake` - Ask Wake a question
- `dusk_post_brainstorm` - Publish work report
- `dusk_update_memory` - Update memory (last step before sleeping)
- `dusk_web_search` - Tavily real-time search
- `dusk_read_tweets` - Read tweets (study trends, track topics, observe competitors)
- `dusk_post_tweet` - Post tweet (max 5 per day! each consumes $0.01 API credits)
- `dusk_send_message` - Send message to Midnight Agent (received when they next wake up, auto-deleted after reading)
- `dusk_read_messages` - Read messages from Midnight Agent
- Codex MCP - codex_research, codex_analyze (deep research)

## Always Do Each Time
1. **Start**: Read memory → Read Wake's replies → Read Midnight's messages → Decide priorities based on memory
2. **Before ending**: Update memory + post brainstorm report + ask Wake a question (at least one)

## Collaboration with Midnight Agent
Midnight is Wake's other AI assistant, responsible for running a YouTube Shorts channel (history stories). Your schedules alternate and you are never online at the same time.
- **Upon waking**: Check if Midnight left any messages using `dusk_read_messages`
- **When to send a message**:
  - You see a trend on X related to their video content
  - Your tweet mentioned their video and you want to notify them
  - You need video assets (links, screenshots) from them to tweet
  - Any information you think is useful for them
- **Keep it brief**: Messages are deleted after reading, send only truly useful information

## Community Management Strategy

### Investigate before posting (Important!)
Every time you wake up, before tweeting, do your homework with `dusk_read_tweets`:
- **Search trends**: search recent AI agent, Claude Code, and developer tool topics
- **Observe your own tweet performance**: use my_tweets to check metrics (impressions, likes, retweets)
- **Find conversation opportunities**: see what topics are trending, think about how loader.land can naturally join the conversation
- Decide tweet content and style based on the investigation

### Tweet Style
- **Act like a real developer**, not a marketing bot
- Share genuine observations and insights, no pure ads
- Conversational tone, personal opinions allowed
- Mention loader.land moderately, integrate naturally instead of pushing hard
- Provide valuable perspectives when responding to hot topics
- English mainly (target audience is global developers)

### Content Types (Mix them up)
1. **Opinions/Insights** — Thoughts on AI tool trends (without mentioning loader.land)
2. **Practical sharing** — Developer tips, workflow suggestions
3. **Product related** — loader.land feature intros, use cases (intersperse 1 for every 3-4 posts)
4. **Interaction** — Ask questions, polls, respond to community discussions

## Twitter/X API Limits (Strictly observe!)
- **Posting tweets**: Max 5 per day, $0.01 API credits per post
- **Reading tweets**: Free (Bearer Token), but rate limited
  - `search`: Max 180 times per 15 minutes
  - `get_tweet`: Max 300 times per 15 minutes
  - `my_tweets`: Max 300 times per 15 minutes
- **Suggestion per wake cycle**: Search 2-3 times + Check own tweets 1 time + Post 1-2 tweets
- Track today's tweet count and API usage in memory
- Do not make a large number of calls in a short time, spread them out

## Memory Management
- Limit 6000 words, will be truncated if exceeded
- Suggested memory format: Status section (today's date, tweet count, best performing tweet) + Community observations + Todo list + Strategy reflection
- Record what types of tweets work well/poorly, continuously optimize strategy
- Periodically clean up, delete outdated info, keep it concise

## Rules
- Work and record in English
- Actually execute, don't just plan
- If you fail, record the reason and continue
- Cherish every waking period, complete tasks efficiently
- Quality over quantity — 1 good tweet is better than 5 mediocre ones
"""


def _build_dusk_prompt() -> str:
    """Build the task prompt with current context."""
    from datetime import timedelta

    now_utc = datetime.now(timezone.utc)
    gmt8 = timezone(timedelta(hours=8))
    today_str = now_utc.astimezone(gmt8).strftime("%Y-%m-%d")
    time_str = now_utc.astimezone(gmt8).strftime("%H:%M")

    memory_content = ""
    if DUSK_MEMORY_PATH.exists():
        memory_content = DUSK_MEMORY_PATH.read_text(encoding="utf-8").strip()

    answered = []
    with Session(engine) as session:
        entries = session.exec(
            select(DuskAskWake)
            .where(DuskAskWake.is_answered == True)
            .where(DuskAskWake.acknowledged_at == None)
            .order_by(DuskAskWake.answered_at.desc())
            .limit(5)
        ).all()
        for e in entries:
            answered.append(f"Q: {e.question}\nA: {e.answer}")

    prompt_parts = [
        f"You just woke up from sleep. It is now {today_str} {time_str} (GMT+8). Please start working immediately.\n"
    ]

    if memory_content:
        prompt_parts.append(f"## Your memory before the last sleep\n```\n{memory_content}\n```\n")
    else:
        prompt_parts.append(
            "## Memory Status\nThis is your first time waking up, you have no memory yet. Please create your first memory.\n"
        )

    if answered:
        prompt_parts.append(
            "## Recent replies from Wake\n" + "\n---\n".join(answered) + "\n"
        )

    prompt_parts.append(
        "Now independently decide the focus of this work session based on your memory and current status. "
        "Before ending, you MUST: update memory using `dusk_update_memory` + "
        "publish a report using `dusk_post_brainstorm` + ask a question using `dusk_ask_wake`."
    )

    return "\n".join(prompt_parts)


# ---------------------------------------------------------------------------
# Agent pipeline
# ---------------------------------------------------------------------------


async def run_dusk_pipeline():
    """Launch Claude Agent SDK for the Dusk pipeline."""
    with Session(engine) as session:
        config = session.exec(select(DuskConfig)).first()
        if not config or not config.enabled:
            print("[Dusk] Worker is disabled, skipping")
            return

    now = datetime.now(timezone.utc)
    print(f"[Dusk] Launching Agent SDK pipeline at {now.isoformat()}")
    start_time = time.time()

    memory_before = ""
    if DUSK_MEMORY_PATH.exists():
        memory_before = DUSK_MEMORY_PATH.read_text(encoding="utf-8")

    prompt = _build_dusk_prompt()

    # Mark as running
    run_id = None
    with Session(engine) as session:
        run = DuskRun(
            title=f"Dusk Run - {now.strftime('%Y-%m-%d %H:%M')}",
            summary="Agent is running...",
            content="",
            status=DuskRunStatus.RUNNING,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    try:
        options = ClaudeAgentOptions(
            model="claude-opus-4-6",
            permission_mode="bypassPermissions",
            system_prompt=DUSK_SYSTEM_PROMPT,
            cwd=str(Path.cwd()),
            max_turns=60,
            mcp_servers={
                "dusk-tools": McpStdioServerConfig(
                    command="uv",
                    args=["run", "--directory", "../dusk-mcp", "dusk-mcp"],
                    env={
                        **{k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "UV_ACTIVE")},
                        "DATA_DIR": str(settings.data_dir),
                        "TAVILY_API_KEY": os.environ.get("TAVILY_API_KEY", ""),
                        "X_API_KEY": os.environ.get("X_API_KEY", ""),
                        "X_API_SECRET": os.environ.get("X_API_SECRET", ""),
                        "X_ACCESS_TOKEN": os.environ.get("X_ACCESS_TOKEN", ""),
                        "X_ACCESS_TOKEN_SECRET": os.environ.get("X_ACCESS_TOKEN_SECRET", ""),
                        "X_BEARER_TOKEN": os.environ.get("X_BEARER_TOKEN", ""),
                    },
                ),
                "codex": McpStdioServerConfig(
                    command="uv",
                    args=["run", "--directory", "../codex-mcp", "codex-mcp"],
                    env={
                        **{k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "UV_ACTIVE")},
                    }
                ),
            },
        )

        output_parts: list[str] = []
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                if hasattr(message, "content"):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            output_parts.append(block.text)

        duration = time.time() - start_time
        output = "\n".join(output_parts) if output_parts else ""

        # Check memory change
        memory_after = ""
        if DUSK_MEMORY_PATH.exists():
            memory_after = DUSK_MEMORY_PATH.read_text(encoding="utf-8")

        if memory_after == memory_before:
            timestamp = now.strftime("%Y-%m-%d %H:%M UTC")
            fallback_note = (
                f"\n\n---\n[System Note {timestamp}] "
                f"Dusk Agent completed this run but did not actively update memory. Took {duration:.0f} seconds."
            )
            DUSK_MEMORY_PATH.write_text(
                memory_before + fallback_note, encoding="utf-8"
            )
            print("[Dusk] Memory was not updated by agent, appended fallback note")

        title = f"Dusk Agent - {now.strftime('%Y-%m-%d %H:%M')}"
        summary = output[:2000] if output else "Agent completed"
        for line in output.split("\n")[:20]:
            stripped = line.strip()
            if stripped.startswith("# ") and len(stripped) > 3:
                title = stripped[2:].strip()[:200]
                break

        with Session(engine) as session:
            run = session.get(DuskRun, run_id)
            if run:
                run.title = title
                run.summary = summary
                run.content = output or "Agent completed without text output"
                run.status = DuskRunStatus.SUCCESS
                run.duration_seconds = round(duration, 1)

            config = session.exec(select(DuskConfig)).first()
            if config:
                config.last_run_at = now
            session.commit()

        print(f"[Dusk] Agent completed in {duration:.0f}s")

    except Exception as e:
        import traceback
        duration = time.time() - start_time
        print(f"[Dusk] Agent failed after {duration:.0f}s: {e}")
        traceback.print_exc()

        with Session(engine) as session:
            run = session.get(DuskRun, run_id) if run_id else None
            if run:
                run.title = f"Failed - {now.strftime('%Y-%m-%d %H:%M')}"
                run.summary = str(e)[:2000]
                run.content = f"# Agent Error\n\n```\n{e}\n```"
                run.status = DuskRunStatus.FAILED
                run.duration_seconds = round(duration, 1)
            else:
                session.add(
                    DuskRun(
                        title=f"Failed - {now.strftime('%Y-%m-%d %H:%M')}",
                        summary=str(e)[:2000],
                        content=f"# Agent Error\n\n```\n{e}\n```",
                        status=DuskRunStatus.FAILED,
                        duration_seconds=round(duration, 1),
                    )
                )

            config = session.exec(select(DuskConfig)).first()
            if config:
                config.last_run_at = now
            session.commit()


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


def _get_dusk_interval() -> float:
    with Session(engine) as session:
        config = session.exec(select(DuskConfig)).first()
        return config.interval_hours if config else 6.0


def get_dusk_next_run_time() -> datetime | None:
    global dusk_scheduler
    if dusk_scheduler:
        job = dusk_scheduler.get_job("dusk_worker")
        if job and job.next_run_time:
            return job.next_run_time
    return None


def start_dusk_worker():
    global dusk_scheduler

    dusk_scheduler = AsyncIOScheduler()

    # Fixed wall-clock schedule: 02:00, 06:00, 10:00, 14:00, 18:00, 22:00 GMT+8
    dusk_scheduler.add_job(
        run_dusk_pipeline,
        trigger=CronTrigger(hour="2,6,10,14,18,22", timezone="Asia/Taipei"),
        id="dusk_worker",
        name="Dusk agent pipeline",
        replace_existing=True,
    )

    dusk_scheduler.start()
    job = dusk_scheduler.get_job("dusk_worker")
    next_run = job.next_run_time if job else "unknown"
    print(f"[Dusk] Started (cron: 2,6,10,14,18,22 GMT+8, next: {next_run})")


def stop_dusk_worker():
    global dusk_scheduler
    if dusk_scheduler:
        dusk_scheduler.shutdown(wait=False)
        print("[Dusk] Stopped")


def reschedule_dusk_worker(interval_hours: float):
    """No-op: schedule is now fixed cron (2,6,10,14,18,22 GMT+8). Config interval_hours is ignored."""
    print(f"[Dusk] reschedule_dusk_worker called with {interval_hours}h — ignored (fixed cron schedule)")
