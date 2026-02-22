import os
from pathlib import Path

# Project root (two levels up from src/config.py)
_PROJECT_ROOT = Path(__file__).parent.parent

# Directories (overridable via env vars; default = inside the project folder)
PAPERS_INBOX = Path(os.getenv("PAPERS_INBOX", str(_PROJECT_ROOT / "PapersInbox")))
PAPERS_OUTBOX = Path(os.getenv("PAPERS_OUTBOX", str(_PROJECT_ROOT / "PapersOut")))

# DeepL
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")
DEEPL_API_URL = "https://api.deepl.com/v2/translate"

# Models
MAIN_MODEL = "claude-opus-4-5"
CHUNK_MODEL = "claude-haiku-4-5-20251001"

# Chunking
CHUNK_SIZE = 3000   # words
CHUNK_OVERLAP = 200  # words

# File ignore rules
IGNORE_EXTENSIONS = {".crdownload", ".part", ".tmp"}
IGNORE_PREFIXES = {".", "~"}
