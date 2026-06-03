"""Build and load the Chroma vector store from World Cup matches."""
import shutil
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from src import config
from src.data_loader import load_world_cup_matches, match_to_document, annotate_world_cup_stages


def build_vector_store() -> Chroma:
    """Build (or rebuild) the Chroma DB from World Cup matches.

    Wipes any existing store on disk first so re-runs don't accumulate duplicates.
    """
    if config.CHROMA_DIR.exists():
        shutil.rmtree(config.CHROMA_DIR)
    df = annotate_world_cup_stages(load_world_cup_matches())
    docs = [
        Document(
            page_content=match_to_document(row, stage=row.get("stage", "")),
            metadata={
                "date": str(row["date"].date()),
                "home_team": row["home_team"],
                "away_team": row["away_team"],
                "home_score": int(row["home_score"]),
                "away_score": int(row["away_score"]),
                "tournament": row["tournament"],
                "stage": row.get("stage", ""),
            },
        )
        for _, row in df.iterrows()
    ]
    embeddings = OpenAIEmbeddings(model=config.EMBED_MODEL)
    store = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=str(config.CHROMA_DIR),
    )
    return store


def load_vector_store() -> Chroma:
    """Load an already-built store (faster than rebuilding)."""
    embeddings = OpenAIEmbeddings(model=config.EMBED_MODEL)
    return Chroma(
        persist_directory=str(config.CHROMA_DIR),
        embedding_function=embeddings,
    )


if __name__ == "__main__":
    store = build_vector_store()
    print(f"Built Chroma at {config.CHROMA_DIR}")
    sample = store.similarity_search("Germany vs Argentina World Cup final", k=3)
    for doc in sample:
        print(doc.page_content)
