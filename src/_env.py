"""
Loads .env from the project root exactly once per process, before anything
reads os.environ for an API key. Imported (not run standalone) by every
module that touches os.environ.get("...API_KEY") - gemini_client.py,
openai_compat_client.py, llm_router.py - so it doesn't matter which one a
script imports first, or what the current working directory is (README
has commands run from both the project root and from src/).

Uses an explicit path via __file__ rather than dotenv's own directory
search, so this works the same way no matter where the process was
launched from.

.env itself is never committed - see .gitignore. .env.example documents
the variable names with no values.
"""
import os

from dotenv import load_dotenv

_DOTENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_DOTENV_PATH)
