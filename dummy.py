import json
import time
import uuid
from typing import Dict, Any, Optional, List

class MockProductConversationManager:
    """Mock version of ProductConversationManager with dummy data"""

    def __init__(self, thread_id: str = "mock_conversation",
                 text_input: Optional[str] = None,
                 image_input: Optional[str] = None,
                 audio_input: Optional[str] = None):
        self.thread_id = thread_id
        self.text_input = text_input
        self.image_input = image_input
        self.audio_input = audio_input
        self.final_data: Dict[str, Any] = {
            "clarifier": None,
            "product": None,
            "customer": None,
            "engineer": None,
            "risk": None,
            "diagram_url": None,
            "tts_file": None
        }

        # Mock data for each agent
        self.mock_clarifier_data = {
            "done": True,
            "resp": [
                {
                    "question": "What platforms should the app support?",
                    "answer": "iOS and Android"
                },
                {
                    "question": "What is the primary target audience?",
                    "answer": "Fitness enthusiasts aged 18-45"
                },
                {
                    "question": "Should the app include social features?",
                    "answer": "Yes, basic sharing capabilities"
                }
            ]
        }

        self.mock_product_data = {
            "name": "FitTrack Pro",
            "description": "A comprehensive fitness tracking application that monitors physical activity, nutrition, and sleep patterns to help users achieve their health goals.",
            "features": [
                {
                    "name": "Activity Tracking",
                    "description": "Automatically tracks steps, distance, calories burned, and active minutes throughout the day."
                },
                {
                    "name": "Workout Plans",
                    "description": "Provides personalized workout routines based on user fitness level and goals."
                },
                {
                    "name": "Nutrition Logging",
                    "description": "Allows users to log meals and track calorie intake with a comprehensive food database."
                },
                {
                    "name": "Sleep Analysis",
                    "description": "Monitors sleep patterns and provides insights to improve sleep quality."
                },
                {
                    "name": "Progress Reports",
                    "description": "Generates detailed reports on fitness progress with visual charts and trends."
                }
            ]
        }

        self.mock_customer_data = {
            "demographics": {
                "age_range": "18-45",
                "gender": "All",
                "income_level": "Middle to High",
                "tech_savviness": "High"
            },
            "needs": [
                "Easy-to-use interface",
                "Comprehensive tracking",
                "Personalized insights",
                "Motivation through achievements"
            ],
            "pain_points": [
                "Too many apps needed for different tracking",
                "Complex interfaces in existing apps",
                "Lack of personalized recommendations"
            ],
            "expectations": [
                "Seamless user experience",
                "Accurate tracking",
                "Actionable insights",
                "Privacy protection"
            ]
        }

        self.mock_engineer_data = {
            "technical_feasibility": "High",
            "required_technologies": [
                "React Native for cross-platform development",
                "Firebase for backend services",
                "HealthKit and Google Fit API integration",
                "Machine learning for personalized recommendations"
            ],
            "development_timeline": "6-8 months",
            "resource_requirements": {
                "team_size": "5-7 members",
                "budget": "$150,000-$200,000",
                "infrastructure": "Cloud-based servers, CI/CD pipeline"
            },
            "potential_challenges": [
                "Accurate integration with multiple device sensors",
                "Battery optimization for background tracking",
                "Data synchronization across platforms"
            ]
        }

        self.mock_risk_data = {
            "technical_risks": [
                {
                    "risk": "Data synchronization issues",
                    "probability": "Medium",
                    "impact": "High",
                    "mitigation": "Implement robust conflict resolution strategies"
                },
                {
                    "risk": "Performance bottlenecks",
                    "probability": "Medium",
                    "impact": "Medium",
                    "mitigation": "Optimize database queries and implement caching"
                }
            ],
            "market_risks": [
                {
                    "risk": "Competition from established fitness apps",
                    "probability": "High",
                    "impact": "High",
                    "mitigation": "Focus on unique features and superior user experience"
                },
                {
                    "risk": "Changing user preferences",
                    "probability": "Medium",
                    "impact": "Medium",
                    "mitigation": "Implement agile development to quickly adapt to feedback"
                }
            ],
            "operational_risks": [
                {
                    "risk": "Data privacy concerns",
                    "probability": "Medium",
                    "impact": "High",
                    "mitigation": "Implement strong encryption and transparent privacy policies"
                }
            ]
        }

        self.mock_summary = (
            "FitTrack Pro is a comprehensive fitness tracking application designed for fitness enthusiasts aged 18-45. "
            "The app will be available on both iOS and Android platforms and will feature activity tracking, "
            "workout plans, nutrition logging, sleep analysis, and progress reports. The technical analysis indicates "
            "high feasibility with a development timeline of 6-8 months and a budget of $150,000-$200,000. "
            "Key risks include competition from established apps and data privacy concerns, which can be mitigated "
            "through focused differentiation and strong security measures."
        )

        self.mock_diagram_url = "https://mermaid.ink/img/eyJjb2RlIjoic2VxdWVuY2VEaWFncmFtXG4gICAgcGFydGljaXBhbnQgVXNlciBhcyBZXG4gICAgcGFydGljaXBhbnQgQXBwIGFcyBBXG4gICAgcGFydGljaXBhbnQgU2VydmVyIGFcyBTXG4gICAgXG4gICAgVVMgPj4-IEE6IE9wZW4gYXBwXG4gICAgQSAtPj4gUzogTG9naW4gcmVxdWVzdFxuICAgIFMgLT4-IFM6IFZlcmlmeSBjcmVkZW50aWFsc1xuICAgIFMgLT4-IEE6IFNlc3Npb24gdG9rZW5cbiAgICBBIC0-PiBVOiBTaG93IGRhc2hib2FyZCIsIm1lcm1haWQiOnsidGhlbWUiOiJkZWZhdWx0In19"

        self.mock_tts_file = "mock_podcast.mp3"

    def run_clarifier_conversation(self, max_rounds: int = 5, max_user_inputs: int = 4,
                                  user_input_callback=None, clarifier_callback=None) -> bool:
        """Mock clarifier conversation"""
        print("Mock: Starting Clarifier conversation...")

        # Simulate processing time
        time.sleep(0.5)

        # Store mock clarifier data
        self.final_data["clarifier"] = self.mock_clarifier_data

        # If a callback is provided, simulate the questions
        if clarifier_callback:
            for req in self.mock_clarifier_data["resp"]:
                clarifier_callback(req["question"])

        print("Mock: Clarifier conversation completed")
        return True

    def run_product_agent(self) -> bool:
        """Mock product agent"""
        print("Mock: Generating Product response...")

        # Simulate processing time
        time.sleep(0.7)

        # Store mock product data
        self.final_data["product"] = self.mock_product_data
        self.final_data["diagram_url"] = self.mock_diagram_url

        print("Mock: Product response generated")
        return True

    def run_customer_agent(self) -> bool:
        """Mock customer agent"""
        print("Mock: Generating Customer response...")

        # Simulate processing time
        time.sleep(0.6)

        # Store mock customer data
        self.final_data["customer"] = self.mock_customer_data

        print("Mock: Customer response generated")
        return True

    def run_engineer_agent(self) -> bool:
        """Mock engineer agent"""
        print("Mock: Generating Engineer response...")

        # Simulate processing time
        time.sleep(0.8)

        # Store mock engineer data
        self.final_data["engineer"] = self.mock_engineer_data

        print("Mock: Engineer response generated")
        return True

    def run_risk_agent(self) -> bool:
        """Mock risk agent"""
        print("Mock: Generating Risk response...")

        # Simulate processing time
        time.sleep(0.5)

        # Store mock risk data
        self.final_data["risk"] = self.mock_risk_data

        print("Mock: Risk response generated")
        return True

    def run_summarizer_agent(self) -> str:
        """Mock summarizer agent"""
        print("Mock: Generating Final Summary...")

        # Simulate processing time
        time.sleep(0.4)

        print(f"Mock: Final Summary: {self.mock_summary}")
        return self.mock_summary

    def convert_summary_to_speech(self, summary: str, output_file: str = "podcast.mp3") -> bool:
        """Mock TTS conversion"""
        print("Mock: Converting summary to speech...")

        # Simulate processing time
        time.sleep(0.3)

        # Store mock TTS file
        self.final_data["tts_file"] = self.mock_tts_file

        print(f"Mock: Audio saved to: {self.mock_tts_file}")
        print("Mock: Audio playback completed")
        return True

    def run_full_workflow(self, user_input_callback=None, clarifier_callback=None,
                         generate_audio: bool = True, progress_callback=None) -> Dict[str, Any]:
        """Execute the entire mock workflow"""
        try:
            # Step 1: Run clarifier conversation
            if progress_callback:
                progress_callback("Running clarifier conversation...")
            self.run_clarifier_conversation(
                user_input_callback=user_input_callback,
                clarifier_callback=clarifier_callback
            )

            # Step 2: Run product agent
            if progress_callback:
                progress_callback("Generating product specifications...")
            self.run_product_agent()

            # Step 3: Run customer agent
            if progress_callback:
                progress_callback("Analyzing customer perspective...")
            self.run_customer_agent()

            # Step 4: Run engineer agent
            if progress_callback:
                progress_callback("Evaluating technical feasibility...")
            self.run_engineer_agent()

            # Step 5: Run risk agent
            if progress_callback:
                progress_callback("Assessing potential risks...")
            self.run_risk_agent()

            # Step 6: Generate final summary
            if progress_callback:
                progress_callback("Creating final summary...")
            summary = self.run_summarizer_agent()

            # Step 7: Convert summary to speech
            if generate_audio:
                if progress_callback:
                    progress_callback("Generating audio summary...")
                self.convert_summary_to_speech(summary)

            # Create result dictionary
            result = {
                **self.final_data,
                "summary": summary
            }

            if progress_callback:
                progress_callback("Workflow completed successfully!")

            return result
        except Exception as e:
            print(f"Error during mock workflow execution: {str(e)}")
            return {"error": str(e)}

# Mock API using the MockProductConversationManager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

app = FastAPI(title="Mock Product Conversation API", version="1.0.0")

# In-memory storage for conversation sessions
conversation_sessions: Dict[str, MockProductConversationManager] = {}

# Request/Response Models (same as in the real API)
class StartConversationRequest(BaseModel):
    text_input: Optional[str] = None
    image_input: Optional[str] = None
    audio_input: Optional[str] = None

class StartConversationResponse(BaseModel):
    session_id: str
    clarifier_questions: List[Dict[str, Any]]
    status: str

class ClarifyRequest(BaseModel):
    session_id: str
    answers: List[Dict[str, str]]  # [{"question": "question text", "answer": "answer text"}]

class ClarifyResponse(BaseModel):
    session_id: str
    clarifier_questions: List[Dict[str, Any]]
    status: str

class GenerateProductRequest(BaseModel):
    session_id: str

class GenerateProductResponse(BaseModel):
    session_id: str
    product_data: Dict[str, Any]
    diagram_url: Optional[str] = None
    status: str

class CompleteWorkflowRequest(BaseModel):
    session_id: str
    generate_audio: bool = True

class CompleteWorkflowResponse(BaseModel):
    session_id: str
    final_data: Dict[str, Any]
    summary: str
    tts_file: Optional[str] = None
    status: str

# Helper function to get or create a conversation manager
def get_conversation_manager(session_id: str) -> MockProductConversationManager:
    if session_id not in conversation_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return conversation_sessions[session_id]

# Endpoint 1: Start a new conversation
@app.post("/start-conversation", response_model=StartConversationResponse)
async def start_conversation(request: StartConversationRequest):
    """Start a new conversation session and run the initial clarifier."""
    try:
        # Generate a unique session ID
        session_id = str(uuid.uuid4())

        # Create a new conversation manager
        conversation_manager = MockProductConversationManager(
            thread_id=session_id,
            text_input=request.text_input,
            image_input=request.image_input,
            audio_input=request.audio_input
        )

        # Store the conversation manager
        conversation_sessions[session_id] = conversation_manager

        # Define a callback to collect clarifier questions
        clarifier_questions = []

        def clarifier_callback(question):
            clarifier_questions.append({"question": question, "answer": None})
            return None  # We're not providing answers yet

        # Run the clarifier conversation
        success = conversation_manager.run_clarifier_conversation(
            max_rounds=1,  # Just one round to get initial questions
            clarifier_callback=clarifier_callback
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to start clarifier conversation")

        return StartConversationResponse(
            session_id=session_id,
            clarifier_questions=clarifier_questions,
            status="clarification_needed"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting conversation: {str(e)}")

# Endpoint 2: Provide answers to clarifier questions
@app.post("/clarify", response_model=ClarifyResponse)
async def clarify(request: ClarifyRequest):
    """Provide answers to clarifier questions and get follow-up questions if needed."""
    try:
        # Get the conversation manager
        conversation_manager = get_conversation_manager(request.session_id)

        # Define a callback to provide answers
        answers_dict = {item["question"]: item["answer"] for item in request.answers}

        def user_input_callback(question):
            return answers_dict.get(question, "")

        # Define a callback to collect clarifier questions
        clarifier_questions = []

        def clarifier_callback(question):
            clarifier_questions.append({"question": question, "answer": None})
            return None  # We're not providing answers in this callback

        # Continue the clarifier conversation
        success = conversation_manager.run_clarifier_conversation(
            user_input_callback=user_input_callback,
            clarifier_callback=clarifier_callback
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to continue clarifier conversation")

        # Check if clarification is done
        clarifier_data = conversation_manager.final_data.get("clarifier", {})
        is_done = clarifier_data.get("done", False)

        return ClarifyResponse(
            session_id=request.session_id,
            clarifier_questions=clarifier_questions,
            status="clarification_complete" if is_done else "more_clarification_needed"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during clarification: {str(e)}")

# Endpoint 3: Generate product specifications
@app.post("/generate-product", response_model=GenerateProductResponse)
async def generate_product(request: GenerateProductRequest):
    """Generate product specifications based on the clarified requirements."""
    try:
        # Get the conversation manager
        conversation_manager = get_conversation_manager(request.session_id)

        # Run the product agent
        success = conversation_manager.run_product_agent()

        if not success:
            raise HTTPException(status_code=500, detail="Failed to generate product specifications")

        # Get the product data and diagram URL
        product_data = conversation_manager.final_data.get("product", {})
        diagram_url = conversation_manager.final_data.get("diagram_url")

        return GenerateProductResponse(
            session_id=request.session_id,
            product_data=product_data,
            diagram_url=diagram_url,
            status="product_generated"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating product: {str(e)}")

# Endpoint 4: Complete the workflow and get final summary
@app.post("/complete-workflow", response_model=CompleteWorkflowResponse)
async def complete_workflow(request: CompleteWorkflowRequest, background_tasks: BackgroundTasks):
    """Complete the remaining workflow steps and generate the final summary."""
    try:
        # Get the conversation manager
        conversation_manager = get_conversation_manager(request.session_id)

        # Define a progress callback
        progress_messages = []

        def progress_callback(message):
            progress_messages.append(message)
            print(f"Progress: {message}")

        # Run the full workflow
        result = conversation_manager.run_full_workflow(
            generate_audio=request.generate_audio,
            progress_callback=progress_callback
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        # Clean up the session after a delay
        def cleanup_session():
            import time
            time.sleep(300)  # Wait for 5 minutes
            if request.session_id in conversation_sessions:
                del conversation_sessions[request.session_id]
                print(f"Cleaned up session: {request.session_id}")

        background_tasks.add_task(cleanup_session)

        return CompleteWorkflowResponse(
            session_id=request.session_id,
            final_data={
                "customer": result.get("customer"),
                "engineer": result.get("engineer"),
                "risk": result.get("risk"),
                "diagram_url": result.get("diagram_url")
            },
            summary=result.get("summary", ""),
            tts_file=result.get("tts_file"),
            status="workflow_complete"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error completing workflow: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
