import os
import json
import base64
import tempfile
import io
import sounddevice as sd
import soundfile as sf
import numpy as np
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from src.config.env import OPENAI_API_KEY, OPENAI_API_BASE

# --- Initialize OpenAI client ---
openai_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

# --- Create memory ---
memory = MemorySaver()

# --- Audio recording functionality ---
def record_audio(duration=5, samplerate=16000):
    """Record audio from microphone and return as bytes.
    Args:
        duration: Recording duration in seconds
        samplerate: Sample rate for recording
    Returns:
        Audio data as bytes in WAV format
    """
    print(f"Recording audio for {duration} seconds...")
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='float32')
    sd.wait()  # Wait until recording is finished
    # Create a BytesIO object to hold the WAV data
    buffer = io.BytesIO()
    sf.write(buffer, recording, samplerate, format='WAV')
    buffer.seek(0)  # Rewind the buffer to the beginning
    audio_bytes = buffer.read()
    print("Recording complete")
    return audio_bytes

# --- Helper function to encode image to base64 ---
def encode_image(image_path):
    """Encode an image file to base64 string.
    Args:
        image_path: Path to the image file
    Returns:
        Base64 encoded string of the image
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# --- Helper function to determine MIME type from file extension ---
def get_mime_type(file_path):
    """Determine MIME type from file extension.
    Args:
        file_path: Path to the file
    Returns:
        MIME type string
    """
    ext = os.path.splitext(file_path)[1].lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp'
    }
    return mime_types.get(ext, 'image/jpeg')  # Default to jpeg if not found

# --- Define tools for processing different input types ---
@tool
def analyze_image(image_input: str) -> str:
    """Analyze an image using OpenAI's vision model.
    Args:
        image_input: Either a URL of the image or a local file path to the image.
    Returns:
        JSON string describing the image content.
    """
    try:
        # Check if input is a URL or local file path
        if image_input.startswith('http'):
            # It's a URL
            image_content = {
                "type": "image_url",
                "image_url": {
                    "url": image_input
                }
            }
        else:
            # It's a local file path
            if not os.path.exists(image_input):
                return json.dumps({"error": f"Image file not found: {image_input}"})

            # Encode image to base64
            base64_image = encode_image(image_input)
            mime_type = get_mime_type(image_input)
            data_url = f"data:{mime_type};base64,{base64_image}"

            image_content = {
                "type": "image_url",
                "image_url": {
                    "url": data_url
                }
            }

        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this image and extract key information about requirements, features, design elements, and user interface components. Respond in JSON format."
                        },
                        image_content
                    ]
                }
            ],
            temperature=0.2,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        return completion.choices[0].message.content
    except Exception as e:
        return json.dumps({"error": f"Image analysis failed: {str(e)}"})

@tool
def transcribe_audio(audio_input: str) -> str:
    """Transcribe audio file to text using OpenAI's Whisper model.
    Args:
        audio_input: Either a file path to an audio file or "RECORD" to record new audio.
    Returns:
        Transcribed text from the audio.
    """
    try:
        if audio_input.upper() == "RECORD":
            # Record audio and get bytes
            audio_bytes = record_audio()
            # Create a file-like object from bytes
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "recorded_audio.wav"
            transcription = openai_client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
            )
        else:
            # Use provided file path
            with open(audio_input, "rb") as file:
                transcription = openai_client.audio.transcriptions.create(
                    file=file,
                    model="whisper-1",
                )
        return transcription.text
    except Exception as e:
        return f"Audio transcription failed: {str(e)}"

@tool
def process_text(text_input: str) -> str:
    """Process text input to extract key requirements.
    Args:
        text_input: Raw text input from user.
    Returns:
        Structured summary of key points from the text.
    """
    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Extract and structure key requirements, features, and constraints from the user's text input. Respond in JSON format."
                },
                {
                    "role": "user",
                    "content": text_input
                }
            ],
            temperature=0.2,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        return completion.choices[0].message.content
    except Exception as e:
        return json.dumps({"error": f"Text processing failed: {str(e)}"})

# --- Create the prompt generation agent ---
def get_prompt_generator_agent(model):
    return create_react_agent(
        model=model,
        tools=[analyze_image, transcribe_audio, process_text],
        prompt="""
You are a Prompt Generation Specialist.
Your task is to convert image, audio, and text inputs into a comprehensive,
well-structured prompt that clearly defines requirements for a product or system and definition of the product.
Your workflow:
1. Use the appropriate tools to process each input type:
   - For images: use analyze_image tool with either a URL or local file path
   - For audio: use transcribe_audio tool with either a file path or "RECORD" to record new audio
   - For text: use process_text tool with the raw text
2. Analyze the outputs from all tools to identify:
   - Core requirements and features
   - User needs and pain points
   - Technical constraints or preferences
   - Design elements or UI components
3. Synthesize all information into a single, detailed prompt that:
   - Clearly states the primary purpose and goals
   - Lists all key features and functionalities
   - Describes user requirements and constraints
   - Includes relevant design elements from images
   - Incorporates specific details from audio and text
   - Is structured logically for easy understanding

Provide your final output as a comprehensive prompt text. Do not wrap it in JSON.
Just provide the text directly as your Final Answer.
Combine information from all input types into a cohesive prompt.
Prioritize requirements that appear in multiple sources.
Include specific details mentioned in any input.
""",
        checkpointer=memory,
        name="PromptGenerator",
    )
# Backward compatibility
try:
    from src.config.model_config import default_model
    if default_model:
        prompt_generator = get_prompt_generator_agent(default_model)
    else:
        prompt_generator = None
except Exception:
    prompt_generator = None

# --- Example usage ---
if __name__ == "__main__":
    # Example inputs (in a real scenario, these would be actual files)
    # For URL image:
    # image_input = "https://upload.wikimedia.org/wikipedia/commons/d/da/SF_From_Marin_Highlands3.jpg"
    # For local file image:
    image_input = "/path/to/your/local/image.jpg"  # Replace with actual path

    audio_input = "RECORD"  # This will trigger audio recording
    text_input = "Create a mobile app for fitness tracking with step counting, calorie monitoring, and sleep analysis. Include social features for challenges with friends."

    # Create inputs dictionary
    inputs = {
        "messages": [
            ("user", f"Please process these inputs to generate a comprehensive prompt:\n"
                    f"Image: {'URL' if image_input.startswith('http') else 'Local file'}: {image_input}\n"
                    f"Audio: {'Record new audio' if audio_input == 'RECORD' else f'File: {audio_input}'}\n"
                    f"Text: {text_input}"
            )
        ]
    }

    # Create config with thread_id for the checkpointer
    config = {"configurable": {"thread_id": "1"}}

    # Generate the enhanced prompt
    result = prompt_generator.invoke(inputs, config=config)
    print(result["messages"][-1].content)

