# Dusk Agent Persistent Memory
> **Documentation / How this file works:**
> This file (`DUSK-MEMORY.md`) serves as the long-term, persistent memory for the **Dusk Agent** (the AI Community Manager for loader.land).
> 
> - **Initialization (Waking up):** Every time the `dusk_worker.py` pipeline runs (at scheduled intervals like 02:00, 06:00, 10:00, etc. GMT+8), it reads this exact file and injects the contents into Dusk's system prompt. This gives Dusk context on what happened previously.
> - **Termination (Going to sleep):** Before the agent finishes its run, it is strictly instructed to call the `dusk_update_memory` tool. This tool overwrites or updates this file with its latest findings, statuses, and plans.
> - **Safeguard:** If Dusk completes a run without updating the memory, the system automatically appends a `[System Note]` to the bottom of this file indicating how long the run took.
> - **Size Limit:** The file content is meant to be kept concise (under 6,000 words). The agent is instructed to periodically clean up and delete outdated information.

---

## Memory Status
*This is the start of your memory. Please replace this section and maintain your memory according to the suggested format when you update it using `dusk_update_memory`.*

### Suggested Format:
1. **Status Section**: Today's date, Tweet count, Best performing tweet.
2. **Community Observations**: What trends did you notice on X/Twitter?
3. **Todo List**: What needs to be done next time you wake up?
4. **Strategy Reflection**: What types of tweets work well/poorly? How can we optimize?
