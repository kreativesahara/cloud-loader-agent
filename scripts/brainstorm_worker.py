#!/usr/bin/env python3
"""
Brainstorm Worker - Daily strategy generation pipeline.

Pipeline:
  1. Read yesterday's brainstorm from SQLite
  2. GPT-4.1: summarize yesterday + generate targeted search queries
  3. Tavily: research using GPT-generated queries
  4. Claude CLI: deep strategy analysis with summary + research
  5. Save to SQLite → visible on /agent-brainstorm

Runs at 20:00 UTC daily via systemd timer.
Usage: uv run python scripts/brainstorm_worker.py
"""

import subprocess
import sys
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from sqlmodel import Session, SQLModel, create_engine, select
from cloud_loader.config import settings
from cloud_loader.models import BrainstormEntry

engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


def get_yesterday_entry() -> str | None:
    """Get yesterday's brainstorm raw content from DB."""
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    with Session(engine) as session:
        entry = session.exec(
            select(BrainstormEntry)
            .where(BrainstormEntry.created_at >= start)
            .where(BrainstormEntry.created_at < end)
            .order_by(BrainstormEntry.created_at.desc())
        ).first()

        if entry:
            return entry.content
    return None




def summarize_with_claude(yesterday_content: str) -> dict:
    """Use Claude to summarize yesterday's brainstorm and generate search queries.

    Returns:
        {
            "summary": "...",
            "queries": ["search query 1", "search query 2", "search query 3"]
        }
    """
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    print("[Worker] Calling Claude for summary + search queries...")

    # For JSON output, Claude works best when told to return ONLY JSON and when prefilled with {
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        system=(
            "You are a research assistant. You will receive yesterday's strategy analysis regarding a 'Website serving AI agents'.\n"
            "Please output JSON, including:\n"
            "1. summary: 3-5 sentences in English summarizing yesterday's core insights and key strategic directions.\n"
            "2. queries: 3 English search queries to investigate directions that should be explored deeper today. "
            "The search queries should be specific, timely, and target points mentioned in yesterday's strategy that need more data.\n\n"
            "Output ONLY JSON, no other text."
        ),
        messages=[
            {
                "role": "user",
                "content": yesterday_content,
            },
            {
                "role": "assistant",
                "content": "{"
            }
        ],
    )

    text = "{" + message.content[0].text
    try:
        result = json.loads(text)
        summary = result.get("summary", "")
        queries = result.get("queries", [])
        if not isinstance(queries, list):
            queries = []
        print(f"[Worker] Claude summary: {len(summary)} chars, {len(queries)} queries")
        for q in queries:
            print(f"[Worker]   → {q}")
        return {"summary": summary, "queries": queries[:5]}
    except json.JSONDecodeError:
        print(f"[Worker] Claude output not valid JSON: {text[:200]}")
        return {"summary": text[:500], "queries": []}


def research_with_tavily(queries: list[str]) -> str:
    """Research using Tavily with the given search queries."""
    if not settings.tavily_api_key:
        print("[Worker] No Tavily API key, skipping research")
        return ""
    if not queries:
        print("[Worker] No search queries, using defaults")
        queries = [
            "AI coding agents services platform 2026",
            "Claude Code Codex AI agent tools infrastructure",
        ]

    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)

    all_results = []
    for query in queries:
        try:
            print(f"[Worker] Tavily search: {query}")
            response = client.search(
                query=query,
                max_results=5,
                include_answer=True,
                include_raw_content=False,
            )
            if response.get("answer"):
                all_results.append(
                    f"**Search: {query}**\nAnswer: {response['answer']}\n"
                )
            for item in response.get("results", [])[:3]:
                all_results.append(
                    f"- [{item.get('title', '')}]({item.get('url', '')}): "
                    f"{item.get('content', '')[:200]}"
                )
        except Exception as e:
            print(f"[Worker] Tavily error for '{query}': {e}")

    if all_results:
        return "## Today's Market Research\n\n" + "\n".join(all_results)
    return ""


def build_prompt(yesterday_summary: str | None, research: str) -> str:
    """Build the final prompt for Claude CLI."""
    sections = [
        "You are a strategy consultant. Your task is to deeply think about the concept of a 'Website serving agents (Claude Code / Codex / OpenClaw)'.\n"
        "This website is currently called Cloud-Loader (loader.land), offering File Transfer, MD Storage, and Loader Tracker services."
    ]

    if research:
        sections.append(
            "\nHere are today's market research results. Please refer to this latest information to formulate strategy:\n\n"
            f"{research}"
        )

    if yesterday_summary:
        sections.append(
            "\nHere is a summary of yesterday's strategy. Please build upon this, do not repeat the same points, and provide new insights:\n\n"
            f"{yesterday_summary}"
        )

    sections.append(
        "\n---\n\n"
        "Please deeply analyze from the following three perspectives and propose concrete actionable strategies:\n\n"
        "1. **Website Service Content**: What services should this website provide to AI agents? What features are urgently needed by agents? "
        "Which existing services can be enhanced? What key features are missing?\n"
        "2. **Why agents need this website**: What pain points do agents encounter in their daily work? "
        "How does this website solve them? What unique value does it have compared to other services?\n"
        "3. **Promotion Strategy**: How to let more agent users know about this website? "
        "How to build an agent ecosystem? Specific promotional channels and methods?\n\n"
        "Please answer in English. The first line of your answer must be a # Title (a one-sentence summary of today's core insights), "
        "the second line should be a 2-3 sentence summary. Then follows the detailed analysis. Each perspective must have concrete, actionable suggestions, do not be vague."
    )

    return "\n".join(sections)


def run_claude(prompt: str) -> str:
    """Run Claude CLI and return the text output."""
    print("[Worker] Starting Claude CLI...")

    result = subprocess.run(
        [
            "claude",
            "--dangerously-skip-permissions",
            "-p",
            prompt,
            "--output-format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=1800,
        cwd=str(project_root),
    )

    if result.returncode != 0:
        print(f"[Worker] Claude CLI error (code {result.returncode}):")
        print(f"[Worker] stderr: {result.stderr[:500]}")
        raise RuntimeError(f"Claude CLI failed with code {result.returncode}")

    try:
        data = json.loads(result.stdout)
        if isinstance(data, dict) and "result" in data:
            return data["result"]
        if isinstance(data, dict) and "content" in data:
            content = data["content"]
            if isinstance(content, list):
                return "\n".join(
                    block.get("text", "") for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                )
            return str(content)
        return result.stdout
    except json.JSONDecodeError:
        return result.stdout


def parse_output(output: str) -> dict:
    """Parse Claude's markdown output into title, summary, content."""
    lines = output.strip().split("\n")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title = f"Agent Service Website Strategy - {today}"
    content_start = 0

    for i, line in enumerate(lines[:10]):
        stripped = line.strip()
        if stripped.startswith("# ") and len(stripped) > 3:
            title = stripped[2:].strip()[:200]
            content_start = i + 1
            break

    summary_lines = []
    for line in lines[content_start:content_start + 10]:
        stripped = line.strip()
        if not stripped:
            if summary_lines:
                break
            continue
        if stripped.startswith("#"):
            break
        summary_lines.append(stripped)

    summary = " ".join(summary_lines)[:1000] if summary_lines else output[:500]

    return {"title": title, "summary": summary, "content": output}


def save_entry(data: dict) -> int:
    """Save the brainstorm entry to the database."""
    SQLModel.metadata.create_all(engine)

    entry = BrainstormEntry(
        title=data["title"][:200],
        summary=data["summary"][:1000],
        content=data["content"],
        concept="Website serving agents",
    )

    with Session(engine) as session:
        session.add(entry)
        session.commit()
        session.refresh(entry)
        print(f"[Worker] Saved entry #{entry.id}: {entry.title}")
        return entry.id


def main():
    """Main worker pipeline."""
    print(
        f"[Worker] Brainstorm worker started at "
        f"{datetime.now(timezone.utc).isoformat()}"
    )

    # Step 1: Read yesterday's content
    print("[Worker] Step 1: Reading yesterday's brainstorm...")
    yesterday_content = get_yesterday_entry()

    # Step 2: Claude summarizes + generates search queries
    yesterday_summary = None
    search_queries = []

    if yesterday_content:

        print("[Worker] Step 2: Claude summarizing + generating queries...")
        claude_result = summarize_with_claude(yesterday_content)
        yesterday_summary = claude_result["summary"]
        search_queries = claude_result["queries"]
    else:
        print("[Worker] No yesterday entry, using default queries")
        search_queries = [
            "AI coding agents services platform 2026",
            "Claude Code Codex AI agent tools marketplace",
            "AI agent infrastructure services developer tools",
        ]

    # Step 3: Tavily research with GPT-generated queries
    print("[Worker] Step 3: Tavily research...")
    research = research_with_tavily(search_queries)
    print(f"[Worker] Research: {len(research)} chars")

    # Step 4: Claude CLI deep analysis
    prompt = build_prompt(yesterday_summary, research)
    print(f"[Worker] Step 4: Claude CLI (prompt: {len(prompt)} chars)...")
    output = run_claude(prompt)
    print(f"[Worker] Claude output: {len(output)} chars")

    # Step 5: Parse and save
    data = parse_output(output)
    entry_id = save_entry(data)

    print(
        f"[Worker] Done! Entry #{entry_id} saved. "
        f"View at: {settings.base_url}/agent-brainstorm"
    )


if __name__ == "__main__":
    main()
