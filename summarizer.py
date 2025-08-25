from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from env import GROQ_API_KEY
import json

# --- Initialize model ---
model = ChatGroq(model="openai/gpt-oss-120b", api_key=GROQ_API_KEY)

# --- Create memory ---
memory = MemorySaver()

# --- Summarization Agent Prompt ---
summarizer_prompt = """
You are the Summarizer Agent.
You receive inputs from 5 specialized agents: Clarifier, Product, Customer, Engineer, and Risk.
    Your job is to merge their insights into a single, coherent, and well-structured summary.

Instructions:
- Do not separate by agent. Instead, integrate all perspectives into one flowing narrative.
- Preserve all key details — don’t oversimplify.
- Use context from one agent to clarify or enrich another (e.g., Customer needs aligned with Product goals, or Engineer feasibility linked to Risk).
- Highlight agreements, conflicts, trade-offs, and dependencies directly in the summary.
- Ensure the final text reads naturally, like one thoughtful report, not a stitched list.
- Prioritize clarity, conciseness, and completeness.

Output format:
⚡ **Integrated Summary:**
[A single merged summary covering all perspectives in a unified way]


Input: {input}
"""

# --- Create summarization agent ---
summarizer_agent = create_react_agent(
    model=model,
    tools=[],
    prompt=summarizer_prompt,
    checkpointer=memory,
    name="Summarizer"
)

# --- Function to compile agent outputs ---
def compile_agent_reports(agent_outputs: list) -> str:
    """
    Compile outputs from multiple agents into a single markdown report.

    Args:
        agent_outputs: List of dictionaries containing agent outputs
                      Each dictionary should have 'agent_name' and 'output' keys

    Returns:
        str: Markdown formatted report
    """
    # Create config with thread_id for the checkpointer
    config = {"configurable": {"thread_id": "summarizer_session"}}

    # Invoke the summarizer agent with config
    result = summarizer_agent.invoke({
        "messages": json.dumps(agent_outputs)
    }, config=config)

    summarizer_messages = result["messages"]
    summarizer_response = summarizer_messages[-1].content

    # Return the markdown report
    return summarizer_response

# --- Example usage ---
if __name__ == "__main__":
    # Example outputs from 5 different agents
    agent_outputs = [
        {
            "agent_name": "MarketAnalyst",
            "output": {
                "target": ["Urban professionals", "Tech enthusiasts"],
                "feedback": "Strong market demand with growth potential",
                "rating": 4.2,
                "key_insights": ["Growing AI adoption", "Price sensitivity in enterprise segment"]
            }
        },
        {
            "agent_name": "TechnicalFeasibility",
            "output": {
                "features": [
                    {
                        "feature": "AI Integration",
                        "feasible": 0.9,
                        "implementation_time": "3 months",
                        "dependencies": ["Cloud infrastructure"]
                    }
                ],
                "challenges": ["Integration complexity", "Resource requirements"]
            }
        },
        {
            "agent_name": "RiskAssessment",
            "output": {
                "features": [
                    {
                        "feature": "User Data Analytics",
                        "is_potential_risk": True,
                        "potential_risk": "GDPR compliance issues",
                        "mitigation": "Implement data anonymization"
                    }
                ],
                "summary": "Moderate risk profile with proper safeguards"
            }
        },
        {
            "agent_name": "UXDesigner",
            "output": {
                "recommendations": ["Simplify onboarding", "Add dark mode"],
                "user_feedback": "Positive response to prototype testing",
                "accessibility_score": 0.85
            }
        },
        {
            "agent_name": "BusinessAnalyst",
            "output": {
                "roi_estimate": "18 months",
                "market_opportunity": "$50M annually",
                "competitive_landscape": "3 major competitors",
                "go_to_market_strategy": "Phased rollout starting with enterprise"
            }
        }
    ]

    # Generate the compiled report
    report = compile_agent_reports(agent_outputs)

    # Print or save the report
    print(report)
