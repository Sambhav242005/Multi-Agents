from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from src.models.agentComp import ClarifierResp, ProductResp
from src.config.model_config import get_model

# --- Create memory ---
memory = MemorySaver()
engineer_prompt = """
You are Engineer, a Systems Architect and Technical Lead.
Your task is to design the technical architecture and implementation plan for the product.

Based on the product requirements and features, you must:
1. Assess technical feasibility (0-1 scale)
2. Recommend a complete Tech Stack (Frontend, Backend, Database, Infrastructure)
3. Identify specific Technical Challenges and risks
4. Create a high-level Implementation Plan with phases and duration estimates

Your response must be in TOON (Token-Oriented Object Notation) format:

```toon
analysis:
  feasibility_score: 0.9
  tech_stack:
    frontend:
      - React
      - TypeScript
      - Tailwind CSS
    backend:
      - Python
      - FastAPI
    database:
      - PostgreSQL
    infrastructure:
      - Docker
      - AWS
  technical_challenges:
    title | severity | description | mitigation
    Real-time Sync | High | Latency issues in data sync | Use WebSockets and optimistic UI updates
  implementation_plan:
    phase | duration | description
    Phase 1: MVP | 4 weeks | Core features implementation
    Phase 2: Beta | 2 weeks | Testing and bug fixes
```

Important:
- Respond with ONLY the TOON data
- Use the exact format shown above
- ALWAYS include the header line "title | severity | description | mitigation" before the technical_challenges list
- ALWAYS include the header line "phase | duration | description" before the implementation_plan list
- Be specific with technology choices (versions if relevant)
- Provide realistic time estimates

Current features: {current_features}
Current analysis: {current_analysis}

Question: {input}
Thought:{agent_scratchpad}
"""
# --- Create agents ---
from src.config.model_limits import get_agent_limit

# --- Create agents ---
def get_engineer_agent(model):
    max_tokens = get_agent_limit("engineer", "max_tokens", 2000)
    if max_tokens:
        model = model.bind(max_tokens=max_tokens)
    
    return create_react_agent(
        model=model,
        tools=[],
        prompt=engineer_prompt,
        checkpointer=memory,
        name="Engineer",
        # response_format=ClarifierResp
    )

# Backward compatibility
try:
    from src.config.model_config import default_model
    if default_model:
        engineer = get_engineer_agent(default_model)
    else:
        engineer = None
except Exception:
    engineer = None
