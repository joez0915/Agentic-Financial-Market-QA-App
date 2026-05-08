import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

# Azure OpenAI Configuration
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT", "https://haozez-0810-resource.cognitiveservices.azure.com/")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2024-12-01-preview")

MODEL_SMALL = "gpt-4o-mini"
MODEL_LARGE = "gpt-4o"
ACTIVE_MODEL = MODEL_SMALL

# Database
DB_PATH = "stocks.db"

# Initialize client
client = AzureOpenAI(
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_API_KEY,
    api_version=AZURE_API_VERSION,
)
