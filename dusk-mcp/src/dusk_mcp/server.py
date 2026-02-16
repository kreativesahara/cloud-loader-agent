
import os
import sqlite3
import json
import sys
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timezone

# Ensure project root is in path to import from parent if needed, 
# but here we rely on env vars passed by the worker.

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP
mcp = FastMCP("dusk-tools")

# Configuration from Environment
# In the worker we pass DATA_DIR env var
DATA_DIR_STR = os.environ.get("DATA_DIR", "./data")
DATA_DIR = Path(DATA_DIR_STR)
DB_PATH = DATA_DIR / "cloud_loader.db"
DUSK_MEMORY_PATH = DATA_DIR / "DUSK-MEMORY.md"

# API Keys
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
X_API_KEY = os.environ.get("X_API_KEY")
X_API_SECRET = os.environ.get("X_API_SECRET")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET")
X_BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN")


def get_db_connection():
    # Ensure data dir exists
    if not DB_PATH.parent.exists():
         DB_PATH.parent.mkdir(parents=True, exist_ok=True)
         
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@mcp.tool()
def dusk_read_memory() -> str:
    """Read the current content of Dusk's persistent memory."""
    if not DUSK_MEMORY_PATH.exists():
        return "Memory file does not exist yet."
    return DUSK_MEMORY_PATH.read_text(encoding="utf-8")


@mcp.tool()
def dusk_update_memory(content: str) -> str:
    """Update Dusk's persistent memory. Overwrites existing content."""
    DUSK_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    DUSK_MEMORY_PATH.write_text(content, encoding="utf-8")
    return "Memory updated successfully."


@mcp.tool()
def dusk_get_wake_answers() -> str:
    """Get recent answers from Wake (the user) to Dusk's questions."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check table existence first? 
        # Worker initializes DB via SQLModel so it should be fine.
        # But let's be safe against 'no such table' errors if DB is fresh/empty/broken.
        cmd = "SELECT name FROM sqlite_master WHERE type='table' AND name='duskaskwake'"
        cursor.execute(cmd)
        if not cursor.fetchone():
             return "Database not initialized properly (table duskaskwake missing)."

        # Check if acknowledged_at is NULL (unread)
        cursor.execute(
            "SELECT id, question, answer, answered_at FROM duskaskwake WHERE is_answered = 1 AND acknowledged_at IS NULL ORDER BY answered_at DESC LIMIT 5"
        )
        rows = cursor.fetchall()
        if not rows:
            return "No new answers from Wake."
        
        result = []
        for row in rows:
            result.append(f"ID: {row['id']}\nQ: {row['question']}\nA: {row['answer']}\n(at: {row['answered_at']})")
            # Mark as acknowledged
            cursor.execute("UPDATE duskaskwake SET acknowledged_at = ? WHERE id = ?", (datetime.now(timezone.utc).isoformat(), row['id']))
        
        conn.commit()
        return "\n\n---\n\n".join(result)
    except sqlite3.Error as e:
        return f"Database error: {e}"
    finally:
        conn.close()


@mcp.tool()
def dusk_ask_wake(question: str) -> str:
    """Ask Wake (the user) a question. He will answer later."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "INSERT INTO duskaskwake (question, created_at, is_answered) VALUES (?, ?, 0)",
            (question, now)
        )
        conn.commit()
        return "Question sent to Wake."
    except sqlite3.Error as e:
        return f"Database error: {e}"
    finally:
        conn.close()


@mcp.tool()
def dusk_post_brainstorm(title: str, summary: str, content: str) -> str:
    """Post a brainstorm report or work log to the timeline."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "INSERT INTO brainstormentry (title, summary, content, created_at) VALUES (?, ?, ?, ?)",
            (title, summary, content, now)
        )
        conn.commit()
        return "Brainstorm entry posted."
    except sqlite3.Error as e:
        return f"Database error: {e}"
    finally:
        conn.close()


@mcp.tool()
def dusk_web_search(query: str) -> str:
    """Search the web using Tavily API."""
    if not TAVILY_API_KEY:
        return "Error: TAVILY_API_KEY not set."
    
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(query=query, search_depth="basic")
        return json.dumps(response, indent=2, ensure_ascii=False)
    except ImportError:
        return "Error: tavily-python package not installed."
    except Exception as e:
        return f"Search failed: {e}"


@mcp.tool()
def dusk_read_tweets(query: str = None, count: int = 5) -> str:
    """Read tweets. Uses X_BEARER_TOKEN. 
    If query is 'my_tweets', gets own timeline. 
    Otherwise searches for query."""
    if not X_BEARER_TOKEN:
        return "Error: X_BEARER_TOKEN not set."
    
    try:
        import tweepy
        client = tweepy.Client(bearer_token=X_BEARER_TOKEN)
        
        if query == "my_tweets":
             # Simple search from known user or just search
             # We don't know our own username easily without another API call.
             # Assuming we want to see mentions or from us?
             # Let's just return a placeholder or try to search if we knew the handle.
             # For now, just search generic relevant terms if no query?
             return "My Tweets feature requires authenticated user ID. Use search instead."
        
        # Simple search
        response = client.search_recent_tweets(query=query, max_results=min(count, 10), tweet_fields=["created_at", "public_metrics", "author_id"])
        
        if not response.data:
            return "No tweets found."
            
        result = []
        for tweet in response.data:
            metrics = tweet.public_metrics
            txt = f"[{tweet.created_at}] {tweet.text}\nLikes: {metrics['like_count']} RTs: {metrics['retweet_count']}"
            result.append(txt)
            
        return "\n\n".join(result)
        
    except ImportError:
        return "Error: tweepy package not installed."
    except Exception as e:
        return f"Twitter error: {e}"


@mcp.tool()
def dusk_post_tweet(text: str) -> str:
    """Post a new tweet. Requires Write permission tokens."""
    if not (X_API_KEY and X_API_SECRET and X_ACCESS_TOKEN and X_ACCESS_TOKEN_SECRET):
        return "Error: X API keys (Consumer/Access) not fully set."
        
    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET
        )
        
        response = client.create_tweet(text=text)
        return f"Tweet posted! ID: {response.data['id']}"
        
    except ImportError:
        return "Error: tweepy package not installed."
    except Exception as e:
        return f"Post failed: {e}"

def main():
    mcp.run()

if __name__ == "__main__":
    main()
