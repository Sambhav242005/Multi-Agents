from dotenv import load_dotenv
import os

# load variables from .env file into environment
load_dotenv()

print("Environment variables loaded successfully.")

# access the value
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")  # Optional custom OpenAI base URL
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default_secret_key_change_me_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# Model Configuration
# Set USE_SINGLE_MODEL=true to use the same model for all agents
# Set USE_SINGLE_MODEL=false to use different models per agent
USE_SINGLE_MODEL = os.getenv("USE_SINGLE_MODEL", "true").lower() == "true"

# Default model used when USE_SINGLE_MODEL=true or as fallback
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "z-ai/glm-4.5-air:free")

# Per-agent model configuration (only used when USE_SINGLE_MODEL=false)
CLARIFIER_MODEL = os.getenv("CLARIFIER_MODEL", DEFAULT_MODEL)
PRODUCT_MODEL = os.getenv("PRODUCT_MODEL", DEFAULT_MODEL)
CUSTOMER_MODEL = os.getenv("CUSTOMER_MODEL", DEFAULT_MODEL)
ENGINEER_MODEL = os.getenv("ENGINEER_MODEL", DEFAULT_MODEL)
RISK_MODEL = os.getenv("RISK_MODEL", DEFAULT_MODEL)
SUMMARIZER_MODEL = os.getenv("SUMMARIZER_MODEL", DEFAULT_MODEL)
PROMPT_GENERATOR_MODEL = os.getenv("PROMPT_GENERATOR_MODEL", DEFAULT_MODEL)
DIAGRAM_MODEL = os.getenv("DIAGRAM_MODEL", DEFAULT_MODEL)
TTS_CONVERTER_MODEL = os.getenv("TTS_CONVERTER_MODEL", DEFAULT_MODEL)

