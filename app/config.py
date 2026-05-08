import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Standard OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

MODEL_SMALL = "gpt-4o-mini"
MODEL_LARGE = "gpt-4o"
ACTIVE_MODEL = MODEL_SMALL

# Database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "stocks.db")

# Initialize client
client = OpenAI(
    api_key=OPENAI_API_KEY,
)
