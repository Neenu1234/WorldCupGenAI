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


AGENT_PROMPT = PromptTemplate.from_template(
    """You are WorldCupGPT. Answer the user's question by calling exactly ONE tool.

Tools available:
{tools}

Tool routing:
- Use WorldCupRAG for history, finals, scores.
- Use TeamStats for titles, win rate, top scorers of one team.
- Use MatchPredictor for "TeamA vs TeamB" prediction.

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
                "Answers natural language questions about World Cup history, "
                "matches, scores, and tournaments. Input: a question string."
            ),
        ),
        Tool(
            name="MatchPredictor",
            func=predict_match,
            description=(
                "Predicts the outcome of a match between two national teams. "
                "Input format must be exactly: 'TeamA vs TeamB'."
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
        max_iterations=3,
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
