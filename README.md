# WorldCupGenAI

A LangChain powered conversational chatbot for World Cup history, team statistics, and match predictions. Built for the World Cup GenAI Hackathon, Track 1.

## Architecture

```
User question
     |
     v
ReAct Agent (gpt-4o) + ConversationBufferMemory
     |
     +--> Tool 1: WorldCupRAG   (Chroma + OpenAI embeddings on match docs)
     +--> Tool 2: MatchPredictor (pandas head to head + recent form + LLM)
     +--> Tool 3: TeamStats      (pandas filters on results.csv)
     |
     v
Final Answer (with evidence + limitations)
     |
     v
Streamlit chat UI (with live reasoning trace)
```

## Tools

| Tool | Purpose | Input | Output |
|---|---|---|---|
| WorldCupRAG | RAG over historical World Cup matches | natural language question | answer + retrieved match docs |
| MatchPredictor | Predict outcome between two teams | "TeamA vs TeamB" | preview + predicted outcome + limitations |
| TeamStats | Structured stats lookup | team name | titles, win rate, top scorers |

## Prompts

- **Agent prompt:** custom ReAct template (`src/agent.py`). Forces the Thought / Action / Observation format and routes between tools based on question type.
- **RAG prompt:** strict "answer only from context" template (`src/tools/rag_tool.py`).
- **Prediction prompt:** structured features (head to head + recent form) passed to the LLM, with explicit instructions to cite results and avoid invention.

## Memory

`ConversationBufferMemory` (memory_key=`chat_history`) wired into the AgentExecutor. Enables follow-up questions like "and Brazil?" after asking about Germany.

## Data Source

- **Dataset:** martj42 — International Football Results 1872 to Present
- **URL:** https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017
- **Files used:** `results.csv` (~47K matches), `goalscorers.csv`, `shootouts.csv`
- **License:** see Kaggle page

### Caching

The dataset is downloaded once into `data/` and cached locally. The notebook reads from disk only, so judges can re run offline (no API needed beyond OpenAI).

### Validation

`src/data_loader.py` enforces a schema check: required columns must exist, dates must parse, scores must be numeric. Rows that fail validation are dropped.

## Setup

```bash
# 1. Create venv and install deps
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Set your OpenAI key
echo "OPENAI_API_KEY=sk-..." > .env

# 3. Download dataset from Kaggle and unzip into data/
#    Expected files: data/results.csv, data/goalscorers.csv, data/shootouts.csv

# 4. Build the vector store (once)
python -m src.vector_store

# 5. Launch the Streamlit UI
streamlit run src/app.py
```

## Example Queries

- "Who won the 2014 World Cup final and what was the score?"
- "How many World Cup titles does Brazil have?"
- "Germany vs Argentina"
- "Tell me about Italy's World Cup history"
- "Who is England's all time top scorer?"

## Limitations

- Dataset ends at most recent maintainer update; current squad composition, injuries, transfers not modeled.
- Predictions are based on historical results and recent form only.
- Player level metadata (xG, positions) not in this dataset. StatsBomb integration is a planned stretch goal.

