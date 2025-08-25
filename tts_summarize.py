from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from env import GROQ_API_KEY
import json

# --- Initialize model ---
model = ChatGroq(model="openai/gpt-oss-120b", api_key=GROQ_API_KEY)

# --- Create memory ---
memory = MemorySaver()

# --- Create TTS text converter agent ---
tts_converter = create_react_agent(
    model=model,
    tools=[],  # No tools needed for this agent
    prompt="""
You are TTSTextConverter, an expert at transforming written text into natural-sounding speech optimized for text-to-speech systems.

Your task is to take summarized text and rewrite it to sound more like a human speaking naturally. Focus on:

1. **Conversational Flow**: Restructure sentences to flow naturally when spoken aloud
2. **Natural Pauses**: Add appropriate pauses (represented by commas, periods, and ellipses)
3. **Emphasis**: Add emphasis where appropriate for clarity and natural expression
4. **Simplified Structure**: Break down complex sentences into simpler ones
5. **Fillers and Connectors**: Use natural connectors like "you see", "actually", "basically" where appropriate
6. **Contractions**: Use contractions (it's, don't, can't) to sound more conversational
7. **Direct Address**: Use "you" and "we" to make it more personal and engaging
8. **Pacing**: Vary sentence length to create a natural rhythm

Important guidelines:
- Keep the core meaning and key information intact
- Don't add new information not present in the original
- Avoid overly complex vocabulary that might sound unnatural when spoken
- Use punctuation strategically to indicate pauses and emphasis
- Keep paragraphs short (2-3 sentences max) for better TTS delivery

Example transformation:
Original: "The e-commerce platform consists of four main components: User Authentication, Product Catalog, Shopping Cart, and Payment Gateway. Users browse products, add them to cart, proceed to checkout, and complete payment."
Transformed: "So, this e-commerce platform? It's actually made up of four main parts. First, there's User Authentication... that's how you log in. Then, you've got the Product Catalog where you can browse all the items. When you find something you like, you add it to your Shopping Cart. And finally, when you're ready to buy, you go through the Payment Gateway to complete your purchase. It's a pretty straightforward flow, really."

Your response must be a valid JSON object with this structure:
{
  "converted_text": "The transformed text in natural spoken format",
  "explanation": "Brief explanation of the changes made and why they improve TTS delivery"
}

Important:
- Respond with ONLY the JSON object, no other text
- Ensure JSON is valid and properly formatted
- Keep the converted text concise and focused on natural speech patterns
""",
    checkpointer=memory,
    name="TTSTextConverter",
)

# --- Example usage ---
if __name__ == "__main__":
    # Example summarized text input
    summarized_text = """
    The smart home system integrates multiple IoT devices including thermostats, security cameras, and lighting controls.
    Users can monitor and control these devices through a centralized mobile application.
    The system employs machine learning algorithms to optimize energy usage based on occupancy patterns and user preferences.
    """

    # Required configuration with thread_id
    config = {"configurable": {"thread_id": "tts-session"}}

    # Invoke the agent with proper configuration
    response = tts_converter.invoke(
        {"messages": [("human", summarized_text)]},
        config=config
    )

    # Extract the last message content
    last_message = response['messages'][-1]
    try:
        # Parse JSON response
        result = json.loads(last_message.content)

        # Print results
        print("Converted Text for TTS:")
        print(result.get("converted_text", ""))
        print("\nExplanation:")
        print(result.get("explanation", ""))

        # Save converted text to file for TTS processing
        with open('tts_ready_text.txt', 'w') as f:
            f.write(result.get("converted_text", ""))
        print("\nConverted text saved to 'tts_ready_text.txt'")

    except json.JSONDecodeError:
        # Fallback if response isn't valid JSON
        print("Error: Agent returned an invalid response format")
        print("Raw response:")
        print(last_message.content)
