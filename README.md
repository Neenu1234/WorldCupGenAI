# WorldCupGenAI

A LangChain powered conversational chatbot for World Cup history, team statistics, match predictions, and goal by goal match breakdowns. Built for the World Cup GenAI Hackathon, Track 1.

## Architecture

```
User question
     |
     v
ReAct Agent (gpt-4o)
  + ConversationBufferMemory (chat history)
  + UserPreferences memory (favorite teams, era focus)
     |
     +--> Tool 1: WorldCupRAG     (Chroma + OpenAI embeddings on match docs)
     +--> Tool 2: MatchPredictor  (pandas head to head + recent form + LLM)
     +--> Tool 3: TeamStats       (pandas filters on results.csv + shootouts.csv)
     +--> Tool 4: MatchGoals      (goal by goal lookup from goalscorers.csv)
     |
     v
Final Answer (with evidence + limitations)
     |
     v
Streamlit chat UI (live reasoning trace + 5 chart types + suggested-question sidebar)
```

## Tools

| Tool | Purpose | Input | Output |
|---|---|---|---|
| WorldCupRAG | RAG over historical World Cup matches | natural language question | answer + retrieved match docs |
| MatchPredictor | Predict outcome between two teams | "TeamA vs TeamB" | preview + predicted outcome + limitations |
| TeamStats | Structured stats lookup for one team | team name | titles, win rate, top scorers |
| MatchGoals | Goal by goal breakdown of one historical match | "TeamA vs TeamB YYYY" | scorer list + minutes + own goals/penalties |

## Prompts

- **Agent prompt:** custom ReAct template in `src/agent.py`. Forces the Thought / Action / Observation format and routes between the four tools based on question type.
- **RAG prompt:** strict "answer only from context" template in `src/tools/rag_tool.py`.
- **Prediction prompt:** structured features (head to head + recent form) passed to the LLM, with explicit instructions to cite results and avoid invention.

## Scope Guardrails

Two layers stop the chatbot from responding to off-topic questions.

1. **Agent-level refusal:** the ReAct prompt declares an explicit scope (football, World Cup, team stats, match predictions, historical goals). For any question outside that scope (weather, programming, news, personal advice, etc.) the agent goes straight to a polite refusal **without calling any tool**. This saves cost (no tool runs) and keeps answers honest.

2. **UI-level chart suppression:** the Streamlit app inspects every agent response for refusal patterns ("outside the scope", "I cannot", "I'm unable", etc.). If the agent refused, **no chart is rendered**, no matter which fallback rule would normally fire. This stops irrelevant visuals from appearing when the bot has just said it cannot answer.

The two layers are independent on purpose: even if the agent slips and tries to answer something off-topic, the UI guard still suppresses the chart. Belt and suspenders.

## Memory

Two persistent memory layers per session:

1. **`ConversationBufferMemory`** (`memory_key='chat_history'`) wired into the AgentExecutor. Enables follow ups like "and Brazil?" after asking about Germany.

2. **`UserPreferences`** (`src/preferences.py`) auto-detects and persists at least two user preferences across the session:
   - `favorite_teams`: list of one or more teams the user follows. Detected from natural phrasings in either direction:
     - **Phrase first:** "I'm a Brazil fan", "I support Germany", "my favorite team is Italy"
     - **Team first:** "Brazil is my favorite team", "Brazil and Argentina are my favorite teams"
   - `era_focus`: detected from decades ("1990s", "2010s") or era phrases ("modern era", "classic era")

   Preferences are injected into the agent's input prompt as a header so answers stay personalized. The sidebar shows the live preference state. When the user has 2+ favorite teams and asks a vague question, the UI falls back to a head-to-head chart between the first two favorite teams.

## Data Source

### Source

- **Dataset:** martj42, *International Football Results from 1872 to Present*
- **URL:** https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017
- **License:** Kaggle dataset license (see linked page)
- **Why we chose it:** 136K+ downloads, actively maintained, covers all international football matches in one place. The `tournament` column lets us filter for `FIFA World Cup` matches when we need just the World Cup subset, while keeping the full international history for head to head + recent form features.

### Files used

| File | Rows | Purpose |
|---|---|---|
| `results.csv` | ~49K | Every international match: date, home team, away team, scores, tournament, venue |
| `goalscorers.csv` | ~44K | Every individual goal: scorer, minute, own goal flag, penalty flag |
| `shootouts.csv` | ~675 | Penalty shootout winners (used to resolve tied finals like Italy 2006 and Argentina 2022) |

### How we downloaded the data

The dataset was downloaded once as a zip from Kaggle, unzipped, and the three CSVs placed in `data/`. No API key is required for download. Teammates clone the repo and the CSVs come with it (about 7 MB).

### How we parsed it

`src/data_loader.py`:

1. **`load_results()`** reads `results.csv` with `pandas.read_csv`, then:
   - Asserts required columns exist (`date`, `home_team`, `away_team`, `home_score`, `away_score`, `tournament`, `city`, `country`, `neutral`)
   - Parses `date` with `pd.to_datetime(..., errors='coerce')` and drops rows where it fails
   - Coerces score columns to numeric and drops rows where either score is NaN
   - Returns a clean DataFrame ready for downstream tools

2. **`load_world_cup_matches()`** filters the above to `tournament == "FIFA World Cup"` for the RAG store.

3. **`load_goalscorers()`** reads `goalscorers.csv` for the `MatchGoals` tool and the top scorers chart.

4. **`annotate_world_cup_stages()`** uses a per year sort heuristic to label each World Cup match as Final / Third Place Playoff / Semi-final, so the RAG retrieval can distinguish finals from group stage matches.

5. **`match_to_document()`** converts each match row into a natural language sentence (e.g. "On 2014-07-13, Germany played Argentina at neutral venue during the 2014 FIFA World Cup (Final). Final score: Germany 1, Argentina 0.") for embedding.

### How we cached the data

- The CSVs are committed to `data/` so the repo is fully self contained.
- After the first call to `build_vector_store()`, the Chroma vector store (964 embedded World Cup matches) is persisted to `chroma_db/` on disk. Subsequent runs call `load_vector_store()` and read instantly without re-embedding.
- The pandas DataFrames are loaded fresh per process but are tiny in memory, so no further caching is needed.

### How we validated the data

- **Schema check** in `data_loader.py`: missing required columns raise `ValueError` immediately.
- **Type coercion**: dates and scores are coerced with `errors='coerce'`, and rows with unparseable values are dropped (so we never crash on bad data downstream).
- **Sanity check**: after loading we print row count, date range, and tournament counts so we can spot obvious corruption (notebook section 1 shows this).
- **Penalty shootout cross-reference**: `_wc_titles()` in `tools/stats_tool.py` cross-references `shootouts.csv` to correctly attribute the 4 historical World Cup finals that were decided on penalties.

## Setup

```bash
# 1. Clone and create venv
git clone https://github.com/Neenu1234/WorldCupGenAI.git
cd WorldCupGenAI
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Set your OpenAI key
echo "OPENAI_API_KEY=sk-..." > .env

# 3. Build the Chroma vector store (once, ~2 minutes, ~$0.20 in OpenAI embedding fees)
python -m src.vector_store

# 4. Launch the Streamlit chat UI
streamlit run src/app.py
```

## Example Queries

- "Who won the 2014 World Cup final and what was the score?"
- "How many World Cup titles does Brazil have?"
- "Germany vs Argentina"
- "Show goals from Germany vs Brazil 2014"  (the famous 7-1)
- "Who has won the most World Cup titles?"
- "I'm a Brazil fan, predict Brazil vs Argentina"  (demonstrates preference memory)

## Limitations

- Dataset ends at the most recent maintainer update; current squad composition, injuries, transfers, and live match data are not modeled.
- Predictions are based only on historical results and recent form, not tactical or fitness data.
- Player level metadata (xG, positions, heatmaps) is not in this dataset. StatsBomb integration remains a planned stretch goal.
- Goal scorer records depend on tournament organisers reporting; older matches may have incomplete scorer data.
