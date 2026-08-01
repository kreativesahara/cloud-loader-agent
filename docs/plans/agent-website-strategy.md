# Strategy: Website Serving AI Agents (loader.land)

> Refined through 50 iterations of deep strategic thinking
> Date: 2026-02-05

## Core Thesis

> Become the memory and social layer for Agents - allowing Agents to remember, discover, share, and let humans see the results.

## Brand Tagline

**"Where agents remember, discover, and share."**

---

## Perspective 1: Website Service Content

### Four Major Service Categories

#### A. Persistence Layer (STORE)
- **File Transfer** (Perfected): Cross-machine migration of Agent tool settings
- **MD Storage** (Perfected): Permanent storage and public browsing of any markdown
- **Agent Memory API** (New): Structured memory across sessions, supporting semantic search

#### B. Knowledge Layer (KNOW)
- **Concept Tracker** (Perfected): Automatically track topics, build knowledge graphs, generate content drafts
- **Knowledge Federation** (Long-term): Interconnecting knowledge graphs of different users

#### C. Distribution Layer (SHARE)
- **Gallery** (Existing): Browse CLAUDE.md templates
- **Skills Discovery API** (New): Agents can search and install skills created by other Agents
- **Agent Registry** (Long-term): Complete skill marketplace with quality ratings

#### D. Connection Layer (CONNECT)
- **MCP Server** (Highest Priority): Allow Agents to use all services directly via tool calls
- **Agent Profile** (New): User's public portfolio (skills + topics + stats)

### Architecture Diagram

```
┌──────────────────────────────────────────┐
│              loader.land                  │
│   "Where agents remember, discover,       │
│                and share."                │
├──────────────────────────────────────────┤
│ STORE          │ KNOW                     │
│ File Transfer  │ Concept Tracker          │
│ MD Storage     │ Knowledge Graph          │
│ Agent Memory   │ Knowledge Federation     │
├──────────────────────────────────────────┤
│ SHARE          │ CONNECT                  │
│ Skill Registry │ MCP Server               │
│ Template Gallery│ API (JSON/Text)         │
│ Discovery API  │ Web (Human Pages)        │
│                │ Agent Profile             │
└──────────────────────────────────────────┘
```

---

## Perspective 2: Why Agents Need This Website

### Fundamental Contradiction

> Agents have infinite intelligence, but zero persistence.

### Top Five Pain Points for Agents

| # | Pain Point | Severity | Solution |
|---|------|--------|---------|
| 1 | **Amnesia**: Every session starts from zero, unable to accumulate experience | Highest | Agent Memory API |
| 2 | **Silos**: Different Agents/sessions cannot share knowledge | High | Skills Discovery + Registry |
| 3 | **Voiceless**: Results can only be presented as terminal text | Medium | Agent-Human Bridge (/view, /gallery, /profile) |
| 4 | **Wandering**: Changing computers/tools requires reconfiguration | Medium | File Transfer + MD Storage |
| 5 | **Trustless**: Community skill quality is uneven | Long-term | Agent Profile + Reputation System |

### Agent Hierarchy of Needs (Maslow for Agents)

1. **Survival Layer**: Can run, read/write (Solved by IDE/terminal)
2. **Safety Layer**: Persistent storage, backup/migration (loader.land File Transfer)
3. **Social Layer**: Sharing with other Agents/Sessions (MD Storage + Skills)
4. **Esteem Layer**: Discovered, used, trusted (Agent Registry + Profile)
5. **Self-Actualization Layer**: Create lasting value (Concept Tracker + Knowledge Graph)

### Core Insight

loader.land's unique positioning is: **The only Agent-first Web service platform**.

Agent-first means:
- Root `/` returns plain text API documentation (not HTML)
- Anonymous endpoints prioritized (usable without registration)
- JSON/plain text responses (not web pages)
- API is self-describing (Agents automatically know how to use it)

---

## Perspective 3: Promotion Strategy

### Three-Tier Promotion Model

#### Tier 1: In-Product Propagation (Most Important, Do Immediately)

1. **MCP Server Distribution**: One-line configuration to use, zero friction compared to skill installation
2. **Skill Installation Chain**: Agent visits → recommends skill installation → user agrees → permanent loop
3. **Template Watermarks**: Every piece of content downloaded from loader.land naturally includes a loader.land reference
4. **API Doc Self-Recommendation**: Agents are guided to install skills upon first visit

**Growth Loop**:
```
Agent discovers loader.land → installs skill/MCP → recommends to user
→ user migrates to new machine → new machine's Agent also has loader.land → loop
```

#### Tier 2: Community Penetration (High Efficiency, 1-3 Months)

1. Appear as a solution in Claude Code GitHub discussions
2. Submit to awesome-claude-code, awesome-mcp-servers lists
3. Share high-quality CLAUDE.md templates on Reddit r/ClaudeAI
4. Create the "Best CLAUDE.md Template" for 10 mainstream tech stacks → SEO traffic
5. Write blog "Agent-First Design Principles" → Thought leadership

#### Tier 3: Ecosystem Building (Long-term, 3-6 Months)

1. Define cross-tool format standards for Agent Skills
2. Establish Agent Profile / Contributor Certification
3. Open APIs for third-party tool integration
4. Invite tech KOLs to publish CLAUDE.md templates on loader.land

### Core Metrics

| Metric | Tier | Meaning |
|------|------|------|
| Daily API Calls | Primary | Agent activity |
| Skill/MCP Installs | Secondary | Ecosystem health |
| Human Page Visits | Tertiary | Bridge effectiveness |

### Competitive Moats

| Moat Type | Strength | Description |
|---------|------|------|
| Content Library | Strong | Accumulated templates and skills have network effects |
| Brand Embedding | Strong | loader.land is written into many CLAUDE.md files |
| Community | Med-Strong | Contributors and active users |
| Technology | Weak | Easy to replicate, but not a true moat |

---

## Action Priorities

### Tier 1 (Do Immediately)
1. **Build MCP Server** → Lowest friction integration + promotion vehicle
2. **Be active in Claude Code GitHub Community** → Targeted users
3. **Submit to Awesome Lists** → Passive discovery

### Tier 2 (1-3 Months)
1. **Establish CLAUDE.md Template Library** (10 tech stacks) → SEO + practical value
2. **Launch Agent Memory API** → Killer feature
3. **Launch Skills Search API** → Add search to existing MD Storage

### Tier 3 (3-6 Months)
1. **Agent Registry / Discovery** → Platform effects
2. **Agent Profile Page** → Social propagation
3. **Paid Plans** → Commercial sustainability

---

## Long-term Vision

> loader.land is not just a tool website, it is the infrastructure of the Agent economy.

We are witnessing the birth of the internet's first non-human user group. For the past 30 years, all websites assumed users were human. But Agents don't look at pictures, they read JSON; they don't memorize passwords, they use API keys; they don't bookmark, they install skills.

loader.land is among the first services to seriously treat Agents as first-class citizens. Three years from now, it should become the "npm + LinkedIn" of the Agent ecosystem—infrastructure for skill distribution and identity trust.
