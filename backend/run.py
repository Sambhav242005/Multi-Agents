import argparse
import uvicorn
import sys
import os

# Add src to python path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

def run_api():
    print("Starting API...")
    uvicorn.run("src.api.api:app", host="0.0.0.0", port=8000, reload=True)

def run_ui():
    print("Starting UI (Gradio)...")
    from src.ui.gradio_app import launch_gradio_ui
    launch_gradio_ui()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run HackWave 2.0 Application")
    parser.add_argument("mode", choices=["api", "ui"], 
                       help="Mode to run: 'api' for FastAPI backend, 'ui' for Gradio web interface (default)")
    
    args = parser.parse_args()
    
    if args.mode == "api":
        run_api()
    elif args.mode == "ui":
        run_ui()

