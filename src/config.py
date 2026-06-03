"""Shared configuration. Edit values here, not in individual files."""
from pathlib import Path
from dotenv import load_dotenv

# Auto-load .env from project root so any module that imports config has the key.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CHROMA_DIR = ROOT_DIR / "chroma_db"

# Dataset files (after downloading martj42 zip into data/)
RESULTS_CSV = DATA_DIR / "results.csv"
GOALSCORERS_CSV = DATA_DIR / "goalscorers.csv"
SHOOTOUTS_CSV = DATA_DIR / "shootouts.csv"

# Data source (cite this in the README)
DATA_SOURCE_URL = "https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017"
DATA_SOURCE_NAME = "martj42 / International Football Results 1872 to Present"

# Models
LLM_MODEL = "gpt-4o-mini"          # cheap default for development
LLM_MODEL_HEAVY = "gpt-4o"         # use for the agent reasoning step
EMBED_MODEL = "text-embedding-3-small"
TEMPERATURE = 0.0

# Prediction settings
RECENT_FORM_WINDOW = 5             # last N matches for form calculation
H2H_MIN_MATCHES = 1                # minimum head to head matches required
