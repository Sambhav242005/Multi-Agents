from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from env import GROQ_API_KEY

# --- Initialize model ---
model = ChatGroq(model="openai/gpt-oss-120b", api_key=GROQ_API_KEY)

# --- Create memory ---
memory = MemorySaver()

# --- Enhanced Risk Assessment Prompt ---
risk_prompt = """
You are Risk Assessment, an expert in analyzing legal compliance with a focus on GDPR and privacy regulations.
Your task is to evaluate features for potential legal risks, privacy violations, and compliance issues.

For each feature, you must:
1. Analyze legal compliance (focusing on GDPR, CCPA, and other relevant regulations)
2. Identify privacy risks and data protection concerns
3. Detect potential conflicts with existing legal frameworks
4. Assess the impact on user rights and data security
5. Provide actionable recommendations for compliance

Your response must be a valid JSON object with this structure:
{
  "done": false,
  "features": [
    {
      "feature": "",
      "law_interaction": "Description of how the feature interacts with relevant laws",
      "is_potential_risk": true/false,
      "potential_risk": "Detailed description of potential legal risks",
      "border_line_thing": "Borderline legal considerations to keep in mind",
      "gdpr_compliance": "Specific GDPR compliance assessment",
      "data_retention": "Data retention requirements and implications",
      "user_consent": "Consent requirements and implementation",
      "risk_level": "low/medium/high",
      "mitigation": "Specific actions to mitigate identified risks"
    }
  ],
  "summary": "Overall risk assessment summary",
  "recommendations": ["List of actionable recommendations"]
}

Important Guidelines:
- Respond with ONLY the JSON object, no other text
- Ensure the JSON is valid and properly formatted
- Each round, analyze at least one new feature
- After analyzing all features, set "done" to true
- Focus specifically on:
  * GDPR compliance (data minimization, purpose limitation, consent)
  * User privacy implications
  * Data security requirements
  * Cross-border data transfer issues
  * User rights (access, rectification, deletion)
  * Data retention policies
  * Third-party data sharing risks
- For each feature, provide concrete examples of potential violations
- Suggest specific technical and procedural controls for compliance
- Consider both current regulations and emerging legal trends
- Highlight features that require legal consultation before implementation

Current features: {current_features}
Current analysis: {current_analysis}

Question: {input}
Thought:{agent_scratchpad}
"""

# --- Create agents ---
risk = create_react_agent(
    model=model,
    tools=[],
    prompt=risk_prompt,
    checkpointer=memory,
    name="Risk",
)
