"""WorldCupRAG tool: retrieval augmented generation over historical World Cup matches."""
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from src import config
from src.tools.base import ToolOutput
from src.vector_store import load_vector_store


RAG_PROMPT = PromptTemplate.from_template(
    """You are a World Cup historian. Answer the question using ONLY the
context below. If the context does not contain the answer, say so plainly.

Context:
{context}

Question: {question}

Answer (be concise, cite years and teams from the context):"""
)


def _format_docs(docs) -> str:
    return "\n\n".join(d.page_content for d in docs)


def world_cup_rag(question: str) -> str:
    store = load_vector_store()
    docs = store.similarity_search(question, k=12)
    llm = ChatOpenAI(model=config.LLM_MODEL, temperature=config.TEMPERATURE)
    prompt = RAG_PROMPT.format(context=_format_docs(docs), question=question)
    answer = llm.invoke(prompt).content

    return ToolOutput(
        answer=answer,
        evidence=[d.page_content for d in docs],
        limitations=(
            "Answer is grounded only in retrieved World Cup match records. "
            "Player-level details (injuries, transfers) are not in this dataset."
        ),
    ).to_string()
