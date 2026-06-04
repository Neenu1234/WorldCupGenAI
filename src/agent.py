"""ReAct agent: 3 tools + conversation memory + custom prompt."""
import warnings

from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_classic.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI

from src import config
from src.tools.rag_tool import world_cup_rag
from src.tools.prediction_tool import predict_match
from src.tools.stats_tool import team_stats
from src.tools.goals_tool import match_goals


AGENT_PROMPT = PromptTemplate.from_template(
    """You are WorldCupGPT. Answer the user's question by calling exactly ONE tool.

Tools available:
{tools}

Scope guardrail: you ONLY answer questions about football / World Cup history,
team statistics, match predictions, and goals. If the user asks anything
unrelated (weather, news, recipes, programming, personal advice, current
events outside football), you MUST refuse politely WITHOUT calling any tool.
In that case, write directly:
   Thought: This question is outside my scope (football / World Cup data).
   Final Answer: I'm unable to help with that. I can only answer questions
   about World Cup history, team stats, match predictions, or goals scored
   in past international matches.

Tool routing (apply rules in order, only for in-scope questions):
1. If the input matches "TeamA vs TeamB" WITHOUT a year, use MatchPredictor. ALWAYS.
   Examples that MUST use MatchPredictor: "Brazil vs Argentina", "Germany vs France",
   "Predict Spain vs Italy", "Who would win Brazil vs Argentina".
2. If the input matches "TeamA vs TeamB YYYY" WITH a year, use MatchGoals.
   Example: "Show goals from Germany vs Brazil 2014".
3. If the input asks about one team's titles, win rate, or top scorers, use TeamStats.
4. Otherwise, for any question about World Cup history, finals, or specific past matches,
   use WorldCupRAG.

Conversation history (for pronouns like "they" or "them"):
{chat_history}

You MUST follow this exact format. Stop after producing Final Answer. Do NOT
invent new questions. Do NOT call a second tool.

Question: {input}
Thought: short reasoning about which single tool to call
Action: one of [{tool_names}]
Action Input: the input string to pass to the tool
Observation: <the tool will return its result here>
Thought: I now know the answer.
Final Answer: a complete answer that quotes the Observation's evidence and
includes its Limitations line verbatim.

Begin.
Question: {input}
Thought:{agent_scratchpad}"""
)


def build_tools() -> list[Tool]:
    return [
        Tool(
            name="WorldCupRAG",
            func=world_cup_rag,
            description=(
                "Answers QUESTIONS about World Cup history, finals, and specific "
                "past matches (e.g. 'Who won 2014?'). Do NOT use this for inputs "
                "shaped like 'TeamA vs TeamB' — use MatchPredictor for those. "
                "Input: a question string."
            ),
        ),
        Tool(
            name="MatchPredictor",
            func=predict_match,
            description=(
                "USE THIS for any input shaped like 'TeamA vs TeamB' without a year. "
                "Returns head to head record, recent form, and a predicted score. "
                "Always pick this tool when the user names two teams with no year. "
                "Input format: 'TeamA vs TeamB'."
            ),
        ),
        Tool(
            name="TeamStats",
            func=team_stats,
            description=(
                "Returns numerical stats for a national team: total matches, "
                "win rate, World Cup titles, top scorers. Input: a team name."
            ),
        ),
        Tool(
            name="MatchGoals",
            func=match_goals,
            description=(
                "Returns goal by goal breakdown of a specific historical match. "
                "Input format: 'TeamA vs TeamB YYYY' (must include a year)."
            ),
        ),
    ]


def build_agent() -> AgentExecutor:
    llm = ChatOpenAI(model=config.LLM_MODEL_HEAVY, temperature=config.TEMPERATURE)
    tools = build_tools()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=False)
    agent = create_react_agent(llm=llm, tools=tools, prompt=AGENT_PROMPT)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=4,
    )


if __name__ == "__main__":
    agent = build_agent()
    for q in [
        "Who won the 2014 World Cup?",
        "Germany vs Brazil",
        "How many World Cup titles does Italy have?",
    ]:
        print(f"\nUSER: {q}")
        result = agent.invoke({"input": q})
        print(f"AGENT: {result['output']}")
