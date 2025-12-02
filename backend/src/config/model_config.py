from langchain_openai import ChatOpenAI
from src.config.env import (
    OPENAI_API_KEY, 
    OPENAI_API_BASE,
    USE_SINGLE_MODEL,
    DEFAULT_MODEL,
    CLARIFIER_MODEL,
    PRODUCT_MODEL,
    CUSTOMER_MODEL,
    ENGINEER_MODEL,
    RISK_MODEL,
    SUMMARIZER_MODEL,
    PROMPT_GENERATOR_MODEL,
    DIAGRAM_MODEL,
    TTS_CONVERTER_MODEL
)

def get_model(temperature: float = 0.1, model_name: str = None, provider: str = "openai", base_url: str = None, agent_type: str = None):
    """
    Returns a configured Chat model instance based on provider.
    
    Args:
        temperature: Model temperature (0.0-1.0)
        model_name: Specific model name to use (overrides agent-specific config)
        provider: Provider to use ("openai")
        base_url: Optional custom OpenAI API base URL
        agent_type: Type of agent (e.g., "clarifier", "product", "customer", etc.)
                   Used to select agent-specific model when USE_SINGLE_MODEL=false
    """
    if provider == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")
        
        # Use provided base_url, or fall back to environment variable
        api_base = base_url or OPENAI_API_BASE
        
        # Determine which model to use
        if model_name:
            # Explicitly provided model takes precedence
            selected_model = model_name
        elif USE_SINGLE_MODEL:
            # Use single model for all agents
            selected_model = DEFAULT_MODEL
        elif agent_type:
            # Use agent-specific model
            agent_models = {
                "clarifier": CLARIFIER_MODEL,
                "product": PRODUCT_MODEL,
                "customer": CUSTOMER_MODEL,
                "engineer": ENGINEER_MODEL,
                "risk": RISK_MODEL,
                "summarizer": SUMMARIZER_MODEL,
                "prompt_generator": PROMPT_GENERATOR_MODEL,
                "diagram": DIAGRAM_MODEL,
                "tts_converter": TTS_CONVERTER_MODEL,
            }
            selected_model = agent_models.get(agent_type, DEFAULT_MODEL)
        else:
            # Fallback to default
            selected_model = DEFAULT_MODEL
        
        return ChatOpenAI(
            model=selected_model,
            api_key=OPENAI_API_KEY,
            base_url=api_base,
        )
    else:
        raise ValueError(f"Provider '{provider}' is not supported. Use 'openai'.")

# Default model instance for general use (defaults to OpenAI)
try:
    default_model = get_model()
except Exception:
    default_model = None

