from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import uuid
import time
from typing import Dict, Any, List, Optional

app = FastAPI(title="Product Conversation API")

# In-memory storage for conversation states
conversation_states: Dict[str, Dict[str, Any]] = {}

# Pydantic models for request/response
class TextInput(BaseModel):
    text_input: str
    image_input: Optional[str] = None
    audio_input: Optional[str] = None

class StartConversationRequest(TextInput):
    pass

class ContinueClarifierRequest(BaseModel):
    thread_id: str
    answers: List[str]

class RunWorkflowRequest(BaseModel):
    thread_id: str

class RunWorkflowStreamRequest(TextInput):
    pass

# Helper functions
def generate_thread_id() -> str:
    return str(uuid.uuid4())

def get_conversation_state(thread_id: str) -> Dict[str, Any]:
    if thread_id not in conversation_states:
        raise HTTPException(status_code=404, detail="Thread not found")
    return conversation_states[thread_id]

def update_conversation_state(thread_id: str, state: Dict[str, Any]) -> None:
    conversation_states[thread_id] = state

# API Endpoints
@app.post("/start_conversation")
async def start_conversation(request: StartConversationRequest):
    """Start a new clarifier conversation"""
    thread_id = generate_thread_id()

    # Initialize the state with simplified data structure
    state = {
        "thread_id": thread_id,
        "text_input": request.text_input,
        "image_input": request.image_input,
        "audio_input": request.audio_input,
        "clarifier_done": False,
        "current_round": 0,
        "workflow_done": False,
        "messages": [],
        "final_data": {}
    }

    # Add initial clarifier message
    state["messages"].append({
        "role": "assistant",
        "content": json.dumps({
            "resp": [
                {"question": "What is your primary goal with this product?", "answer": None},
                {"question": "Who is your target audience?", "answer": None}
            ],
            "done": False
        })
    })

    state["current_round"] = 1
    update_conversation_state(thread_id, state)

    return {
        "type": "start",
        "thread_id": thread_id
    }

@app.post("/continue_clarifier")
async def continue_clarifier(request: ContinueClarifierRequest):
    """Continue the clarifier conversation with user answers"""
    state = get_conversation_state(request.thread_id)

    if state.get("clarifier_done", False):
        return {
            "type": "end",
            "clarifier_done": True,
            "current_round": state["current_round"]
        }

    try:
        # Get the last clarifier message
        last_message = state["messages"][-1]
        clarifier_data = json.loads(last_message["content"])

        # Update with user answers
        if "resp" in clarifier_data:
            questions = clarifier_data["resp"]
            for i, question in enumerate(questions):
                if i < len(request.answers) and not question.get("answer"):
                    question["answer"] = request.answers[i]

            # Add user response
            state["messages"].append({
                "role": "user",
                "content": f"User answered: {request.answers}"
            })

            # Generate next clarifier response
            if state["current_round"] < 3:  # Limit to 3 rounds for demo
                next_questions = [
                    {"question": f"Follow-up question {state['current_round'] + 1}?", "answer": None}
                ]

                state["messages"].append({
                    "role": "assistant",
                    "content": json.dumps({
                        "resp": next_questions,
                        "done": False
                    })
                })

                state["current_round"] += 1
                state["clarifier_done"] = False
            else:
                # Mark clarifier as done
                state["messages"].append({
                    "role": "assistant",
                    "content": json.dumps({
                        "resp": [],
                        "done": True
                    })
                })

                state["clarifier_done"] = True
                state["final_data"]["clarifier"] = clarifier_data

        update_conversation_state(request.thread_id, state)

        return {
            "type": "continue",
            "thread_id": request.thread_id,
            "content": state["messages"][-1]["content"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error continuing clarifier: {str(e)}")

@app.get("/get_state/{thread_id}")
async def get_state(thread_id: str):
    """Get the current state of the conversation"""
    state = get_conversation_state(thread_id)

    # Extract the relevant state information
    response_state = {
        "thread_id": thread_id,
        "state": state["final_data"],
        "clarifier_done": state.get("clarifier_done", False),
        "current_round": state.get("current_round", 0)
    }

    return response_state

@app.post("/run_workflow")
async def run_workflow(request: RunWorkflowRequest):
    """Run the workflow for a given thread_id"""
    state = get_conversation_state(request.thread_id)

    # Check if clarifier is done
    if not state.get("clarifier_done", False):
        raise HTTPException(status_code=400, detail="Clarifier conversation not completed")

    # Run the workflow in the background
    background_tasks = BackgroundTasks()
    background_tasks.add_task(run_workflow_background, request.thread_id)

    return {
        "status": "workflow_started",
        "thread_id": request.thread_id
    }

async def run_workflow_background(thread_id: str):
    """Run the workflow in the background"""
    state = get_conversation_state(thread_id)

    try:
        # Simulate running the workflow steps
        state["final_data"]["product"] = {"name": "Sample Product", "features": ["Feature 1", "Feature 2"]}
        state["final_data"]["diagram_url"] = "https://example.com/diagram.png"

        state["final_data"]["customer"] = {"segment": "Enterprise", "needs": ["Need 1", "Need 2"]}

        state["final_data"]["engineer"] = {"feasibility": "High", "timeline": "6 months"}

        state["final_data"]["risk"] = {"level": "Medium", "mitigations": ["Mitigation 1", "Mitigation 2"]}

        # Generate final summary
        summary = "This is a summary of the product analysis."
        state["final_data"]["summary"] = summary

        # Convert summary to speech (simulated)
        state["final_data"]["tts_file"] = "https://example.com/speech.mp3"

        # Update state to mark workflow as done
        state["workflow_done"] = True
        update_conversation_state(thread_id, state)
    except Exception as e:
        print(f"Error running workflow: {str(e)}")
        state["workflow_error"] = str(e)
        update_conversation_state(thread_id, state)

@app.get("/get_result/{thread_id}")
async def get_result(thread_id: str):
    """Get the final result of the workflow"""
    state = get_conversation_state(thread_id)

    if not state.get("workflow_done", False):
        if "workflow_error" in state:
            raise HTTPException(status_code=500, detail=f"Workflow failed: {state['workflow_error']}")
        raise HTTPException(status_code=404, detail="Workflow result not available yet")

    # Return the final data
    result = {
        **state["final_data"],
        "summary": state["final_data"].get("summary", "")
    }

    return result

@app.post("/run_workflow_stream")
async def run_workflow_stream(request: RunWorkflowStreamRequest):
    """Run the entire workflow in one go and stream the results"""
    thread_id = generate_thread_id()

    # Initialize the state
    state = {
        "thread_id": thread_id,
        "text_input": request.text_input,
        "image_input": request.image_input,
        "audio_input": request.audio_input,
        "clarifier_done": True,
        "current_round": 1,
        "workflow_done": False,
        "messages": [],
        "final_data": {}
    }

    update_conversation_state(thread_id, state)

    async def generate_stream():
        try:
            # Step 1: Start
            yield json.dumps({
                "step": "start",
                "status": "success",
                "data": {
                    "thread_id": thread_id,
                    "timestamp": time.time()
                },
                "thread_id": thread_id,
                "timestamp": time.time()
            }) + "\n"

            # Step 2: Run clarifier (simulated)
            clarifier_data = {
                "resp": [
                    {"question": "What is your primary goal with this product?", "answer": "Goal"},
                    {"question": "Who is your target audience?", "answer": "Audience"}
                ],
                "done": True
            }

            state["final_data"]["clarifier"] = clarifier_data

            yield json.dumps({
                "step": "clarifier",
                "status": "success",
                "data": clarifier_data,
                "error": None,
                "thread_id": thread_id,
                "timestamp": time.time()
            }) + "\n"

            # Step 3: Run product agent
            state["final_data"]["product"] = {"name": "Sample Product", "features": ["Feature 1", "Feature 2"]}
            state["final_data"]["diagram_url"] = "https://example.com/diagram.png"

            yield json.dumps({
                "step": "product",
                "status": "success",
                "data": {
                    "product": state["final_data"]["product"],
                    "diagram_url": state["final_data"]["diagram_url"]
                },
                "error": None,
                "thread_id": thread_id,
                "timestamp": time.time()
            }) + "\n"

            # Step 4: Run customer agent
            state["final_data"]["customer"] = {"segment": "Enterprise", "needs": ["Need 1", "Need 2"]}

            yield json.dumps({
                "step": "customer",
                "status": "success",
                "data": state["final_data"]["customer"],
                "error": None,
                "thread_id": thread_id,
                "timestamp": time.time()
            }) + "\n"

            # Step 5: Run engineer agent
            state["final_data"]["engineer"] = {"feasibility": "High", "timeline": "6 months"}

            yield json.dumps({
                "step": "engineer",
                "status": "success",
                "data": state["final_data"]["engineer"],
                "error": None,
                "thread_id": thread_id,
                "timestamp": time.time()
            }) + "\n"

            # Step 6: Run risk agent
            state["final_data"]["risk"] = {"level": "Medium", "mitigations": ["Mitigation 1", "Mitigation 2"]}

            yield json.dumps({
                "step": "risk",
                "status": "success",
                "data": state["final_data"]["risk"],
                "error": None,
                "thread_id": thread_id,
                "timestamp": time.time()
            }) + "\n"

            # Step 7: Generate summary
            summary = "This is a summary of the product analysis."
            state["final_data"]["summary"] = summary

            yield json.dumps({
                "step": "summary",
                "status": "success",
                "data": {"summary": summary},
                "error": None,
                "thread_id": thread_id,
                "timestamp": time.time()
            }) + "\n"

            # Step 8: Convert to speech
            state["final_data"]["tts_file"] = "https://example.com/speech.mp3"

            yield json.dumps({
                "step": "tts",
                "status": "success",
                "data": {"tts_file": state["final_data"]["tts_file"]},
                "error": None,
                "thread_id": thread_id,
                "timestamp": time.time()
            }) + "\n"

            # Final result
            result = {
                **state["final_data"],
                "summary": summary
            }

            yield json.dumps(result) + "\n"

            # Update state to mark workflow as done
            state["workflow_done"] = True
            update_conversation_state(thread_id, state)
        except Exception as e:
            yield json.dumps({
                "step": "error",
                "status": "error",
                "error": str(e),
                "thread_id": thread_id,
                "timestamp": time.time()
            }) + "\n"

    return StreamingResponse(
        generate_stream(),
        media_type="application/json"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
