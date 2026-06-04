# WorldCupGenAI — Project Walkthrough

A plain-language guide to what we built, why, and how. Read this before presenting. Each section maps to one slide in `WorldCupGenAI_Slides.pptx`.

---

## Slide 1 — What is this project?

**The one-line answer:** A chatbot for World Cup questions that uses LangChain to pick the right tool for each question.

**The fuller version:** WorldCupGPT is a conversational AI assistant built for the Track 1 hackathon. You type a question (like "Who won the 2014 World Cup?" or "Germany vs France"), and the chatbot picks the right tool to answer, returns the answer with evidence, and even draws a chart automatically.

**Key things to know:**
- Built with LangChain (the same framework from our M5 and M6 labs)
- Uses OpenAI's gpt-4o as the reasoning model
- Has a Streamlit chat UI that you launch with one command
- Code lives at github.com/Neenu1234/WorldCupGenAI

---

## Slide 2 — The problem we solved

**What Track 1 asked for:**

Track 1 wants a chatbot that handles three different types of questions about the World Cup:
1. **History questions** like "Who won 1986?" or "What was the score of the 2018 final?"
2. **Team statistics** like "How many titles does Brazil have?" or "Who is England's top scorer?"
3. **Match predictions** like "Germany vs France" or "Who would win Spain vs Italy?"

**Why this is hard:**

These three questions need three different kinds of computation:
- History needs **semantic search** (find the right past match by meaning, not exact words)
- Stats need **structured filtering** (run pandas code on a CSV)
- Predictions need **historical analysis + reasoning** (look at past matches + recent form + ask the LLM to predict)

**Our angle:** Instead of one big RAG chain (which most teams will do), we built a **ReAct agent** that can pick between **four specialized tools**. Each tool handles one type of question. The agent is the brain that decides which tool to use.

---

## Slide 3 — Architecture (how it all fits together)

**The flow, in plain English:**

1. **You type a question** in the Streamlit chat
2. **The ReAct agent reads it** and thinks: "Which tool should I call?"
3. **Memory is loaded in parallel** — both the past conversation AND your saved preferences
4. **The agent picks ONE tool** and calls it
5. **The tool returns three things:** an answer, the evidence it used, and an explicit limitations note
6. **The Streamlit UI shows the answer**, plus a relevant chart, plus the agent's full reasoning trace on the right side

**Why a ReAct agent and not a simple chain?**

A "chain" runs the same steps every time. An "agent" looks at the question and decides what to do. Since our chatbot handles 4 different kinds of questions, an agent is the right choice. We chose **ReAct** specifically because it writes its thinking out in a clean format (Thought → Action → Observation → Final Answer) that we can show to users for transparency.

**The 4 building blocks of our architecture:**

1. **ReAct Agent** (the brain) — built with `create_react_agent` + `AgentExecutor` from langchain_classic
2. **Two memory layers** — chat history + user preferences
3. **Four tools** — each one a Python function the agent can call
4. **Streamlit UI** — the chat window with a sidebar and reasoning panel

---

## Slide 4 — Data (what we used and why)

**The dataset we picked:**

martj42 "International Football Results 1872 to Present" on Kaggle.

**Why this one:**
- Most popular football dataset on Kaggle (136K+ downloads)
- Actively maintained, goes up to today
- Has every international match, not just World Cup ones
- One source covers BOTH the history Q&A AND the prediction features

**What's in it (3 CSV files):**

| File | What it has | What we use it for |
|---|---|---|
| `results.csv` | Every international match (49K+ rows) | History RAG + prediction features |
| `goalscorers.csv` | Every individual goal scored | Top scorers + goal timelines |
| `shootouts.csv` | Penalty shootout winners | Fix tied World Cup finals |

**The 4 things we did to the data (this matches the rubric's 20% Data Sourcing box):**

1. **Cited the source** — README has the exact Kaggle URL
2. **Cached it locally** — CSVs are committed to `data/` in the repo so teammates and judges don't need a Kaggle account
3. **Validated the schema** — `src/data_loader.py` asserts that required columns exist, parses dates, drops bad rows
4. **Cross-referenced** — `shootouts.csv` is used to correctly attribute titles when finals ended in a draw (like Italy 2006 and Argentina 2022)

**Key code file:** `src/data_loader.py` — this is where ingestion + validation happens.

---

## Slide 5 — The 4 Tools (the heart of the project)

Each tool is a Python function the agent can call. Every tool returns the same shape: `answer + evidence + limitations`. This standard interface is defined in `src/tools/base.py` as the `ToolOutput` dataclass.

### Tool 1: WorldCupRAG (the history search tool)

**What it does:** Searches our Chroma vector database for the most relevant past World Cup matches, then asks the LLM to answer using only those matches.

**When the agent calls it:** Any question about past matches, finals, or scores.

**Example:** User asks "Who won the 2014 World Cup final?" → tool retrieves the 12 most similar match documents → returns answer plus the matches as evidence.

**File:** `src/tools/rag_tool.py`

### Tool 2: MatchPredictor (the prediction tool)

**What it does:** Takes two team names, pulls their head to head history and recent form (last 5 matches) from pandas, feeds it all to the LLM, and gets back a match preview with a predicted score.

**When the agent calls it:** Questions in the format "TeamA vs TeamB".

**Example:** User asks "Germany vs France" → tool computes 10 most recent meetings + each team's last 5 matches → LLM writes a 4-6 sentence preview + final prediction.

**File:** `src/tools/prediction_tool.py`

### Tool 3: TeamStats (the stats lookup tool)

**What it does:** Computes structured stats for one team using pandas — total matches, win rate, World Cup titles (including penalty shootout wins), and top all-time scorers.

**When the agent calls it:** Questions about a single team's record.

**Example:** User asks "How many titles does Italy have?" → returns 4 titles (1934, 1938, 1982, **2006**). That 2006 is the one most other teams will miss because the final was 1-1 with Italy winning on penalties.

**File:** `src/tools/stats_tool.py`

### Tool 4: MatchGoals (the goal-by-goal tool)

**What it does:** Looks up every individual goal in one specific historical match. Shows the scorer, minute, and flags for own goals or penalties.

**When the agent calls it:** Questions about goals in a specific match (year required).

**Example:** User asks "Show goals from Germany vs Brazil 2014" → returns all 8 goals of the famous 7-1 thrashing in chronological order.

**File:** `src/tools/goals_tool.py`

### How the agent picks which tool

The agent reads each tool's **description** (which we wrote into `src/agent.py`). The LLM looks at the question, looks at the descriptions, and picks the one that fits. This is why writing good tool descriptions is the single highest-leverage thing in any agent project.

---

## Slide 6 — Live Demo (5 clicks)

This is the longest section of the presentation. Five clicks demonstrate the full system.

### Click 1: "Who won the 2014 World Cup final?"

- **Tool called:** WorldCupRAG
- **What to point out:** The cited match documents as evidence, and the limitations note at the end

### Click 2: Type "im a brazil and france fan, can i get their history"

- **What happens:** The preferences detector saves BOTH Brazil AND France
- **What to point out:**
  - Sidebar updates: "Favorite teams: Brazil, France"
  - Because user has 2 favorite teams, the UI shows a head to head bar chart between them
  - This is the multi-team preferences feature we added

### Click 3: "How many World Cup titles does Brazil have?"

- **Tool called:** TeamStats
- **What to point out:** 5 titles with years cited. The penalty shootout handling means we got the right count.

### Click 4: "Show goals from Germany vs Brazil 2014"

- **Tool called:** MatchGoals
- **What to point out:** Goal timeline chart appears below the text answer. This is the famous 7-1.

### Click 5: 🎲 Surprise me button

- **What happens:** Random query fires from a curated list
- **What to point out:** Polished UX touch, ready-made for users who don't know what to ask

---

## Slide 7 — Innovation (what makes us different)

The 10% Innovation rubric box asks for "creative features beyond the base requirements." Here is what we added.

### 1. Live agent reasoning panel
A side panel in the Streamlit UI shows the agent's Thought → Action → Observation trace in real time. This is what the rubric calls an "explainability overlay." Most teams will hide this; we show it.

### 2. 5 chart types, auto-rendered by query intent
- Head to head bar chart (all time + last 10 grouped) → for "X vs Y" questions
- World Cup titles ranking → for "most winning" questions
- Top scorers chart → only when the question is actually about scorers
- Team record chart (wins / draws / losses) → for "record", "win rate", "stats" questions
- Goal timeline → for "show goals from X vs Y year" questions

### 3. Multi-team UserPreferences memory
The chatbot remembers your favorite teams (you can have more than one) and your favorite era. It detects them from natural phrasings like "I'm a Brazil fan" OR the reverse "Brazil is my favorite team."

### 4. Penalty shootout handling
Most teams will miss Italy 2006 and Argentina 2022 because their finals were tied 1-1 and 3-3 respectively. We cross-reference `shootouts.csv` to correctly attribute those titles.

### 5. Polished sidebar UX
- Categorized sample questions (History, Team stats, Predictions, Match goals)
- Surprise me button for random queries
- Reset preferences button
- Clear chat button

---

## Slide 8 — Reflections and what's next

### What worked

- **ReAct agent routed cleanly** between the 4 tools when descriptions were specific
- **Tool descriptions are the highest-leverage prompt** — vague descriptions cause wrong tool selection
- **Streamlit + sidebar buttons** made the demo flow effortless and reduced typing during the live demo
- **Caching the Chroma store** made re-runs instant after the first build
- **Per-tool limitations** satisfied the grounded reasoning rubric out of the box

### What we'd add next

- **StatsBomb event data** for shot maps and pressure events
- **Multi-team comparison** (3+ teams side by side, not just head to head)
- **Live match data API** for 2026 fixtures and recent results
- **Cross-era predictions** like "1970 Brazil vs 2022 Argentina"
- **PDF export** of match reports

### Biggest lesson

An agent's behavior depends much more on what WE write (the tool descriptions and the ReAct prompt) than on the LLM itself. The model is the engine, but the prompts and tool descriptions are the steering wheel.

---

## Quick reference: key files in the repo

| File | What's in it |
|---|---|
| `notebooks/WorldCup_Hackathon.ipynb` | The full pipeline end to end with executed outputs |
| `src/data_loader.py` | Data ingestion + schema validation |
| `src/vector_store.py` | Builds and loads the Chroma vector DB |
| `src/tools/rag_tool.py` | WorldCupRAG tool |
| `src/tools/prediction_tool.py` | MatchPredictor tool |
| `src/tools/stats_tool.py` | TeamStats tool (with penalty shootout handling) |
| `src/tools/goals_tool.py` | MatchGoals tool |
| `src/tools/base.py` | Common ToolOutput dataclass |
| `src/agent.py` | ReAct agent assembly with custom prompt |
| `src/preferences.py` | UserPreferences memory with multi-team detection |
| `src/visuals.py` | Chart helpers + query parsers |
| `src/app.py` | Streamlit chat UI |
| `src/config.py` | Shared paths and model names |
| `README.md` | Project documentation for the repo page |

---

## Quick reference: rubric coverage

| Rubric box | Weight | Where it's covered |
|---|---|---|
| LangChain Architecture | 40% | Agent + 4 tools + 2 memory layers + custom prompts |
| Data Sourcing | 20% | README data section + `data_loader.py` validation |
| Grounded Reasoning | 20% | Every tool returns evidence + limitations |
| Innovation | 10% | Reasoning panel + 5 chart types + multi-team prefs + Surprise me |
| Presentation | 10% | This script + the slide deck |
