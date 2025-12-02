"""
Product Conversation Manager - Gradio UI
A modern web-based interface for processing product information through conversation workflows.
"""

import gradio as gr
import json
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from queue import Queue
import threading

# Import your existing classes
from src.ui.controller import ProductConversationManager


class GradioUIManager:
    """Manager for the Gradio UI state and workflow execution."""
    
    def __init__(self):
        self.manager: Optional[ProductConversationManager] = None
        self.workflow_thread: Optional[threading.Thread] = None
        self.clarifier_queue = Queue()
        self.user_response_queue = Queue()
        self.is_running = False
        self.current_result = {}
        self.logs = []
        self.clarifier_history = []
        self.waiting_for_response = False
        
    def log(self, message: str):
        """Add a log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        return "\n".join(self.logs)
    
    def clear_logs(self):
        """Clear all logs."""
        self.logs = []
        return ""
    
    def add_clarifier_message(self, sender: str, message: str):
        """Add a message to clarifier history."""
        self.clarifier_history.append(f"{sender}: {message}")
        return "\n\n".join(self.clarifier_history)
    
    def clear_clarifier_history(self):
        """Clear clarifier conversation history."""
        self.clarifier_history = []
        return ""
    
    def run_workflow(self, text_input: str, image_input, audio_input, generate_audio: bool):
        """Run the workflow in a background thread."""
        if self.is_running:
            return "⚠️ Workflow is already running!", "", "", "", "", "", ""
        
        # Validation
        if not text_input and not image_input and not audio_input:
            return "⚠️ Please provide at least one input (text, image, or audio).", "", "", "", "", "", ""
        
        # Clear previous results
        self.current_result = {}
        self.clear_logs()
        self.clear_clarifier_history()
        
        # Get image path if uploaded
        image_path = image_input if image_input else None
        
        # Get audio path if uploaded
        audio_path = audio_input if audio_input else None
        
        # Initialize manager with inputs
        self.manager = ProductConversationManager(
            text_input=text_input if text_input else None,
            image_input=image_path,
            audio_input=audio_path
        )
        
        self.is_running = True
        self.log("Starting workflow...")
        
        # Define callbacks
        def user_input_callback(question):
            self.log(f"User input required: {question}")
            # For now, return empty string (will be handled by clarifier)
            return ""
        
        def clarifier_callback(question):
            self.log(f"Clarifier question: {question}")
            self.add_clarifier_message("Clarifier", question)
            self.waiting_for_response = True
            # Wait for user response
            response = self.user_response_queue.get()
            self.add_clarifier_message("You", response)
            self.waiting_for_response = False
            return response
        
        def progress_callback(message):
            self.log(message)
        
        # Run workflow in background
        def workflow_thread():
            try:
                result = self.manager.run_full_workflow(
                    user_input_callback=user_input_callback,
                    clarifier_callback=clarifier_callback,
                    generate_audio=generate_audio,
                    progress_callback=progress_callback
                )
                self.current_result = result
                self.is_running = False
                self.log("✅ Workflow completed successfully!")
            except Exception as e:
                self.current_result = {"error": str(e)}
                self.is_running = False
                self.log(f"❌ Error: {str(e)}")
        
        self.workflow_thread = threading.Thread(target=workflow_thread, daemon=True)
        self.workflow_thread.start()
        
        return "🚀 Workflow started! Check the Logs tab for progress.", "", "", "", "", "", ""
    
    def send_clarifier_response(self, response: str):
        """Send user response to clarifier."""
        if not response.strip():
            return "⚠️ Please enter a response.", ""
        
        if not self.waiting_for_response:
            return "⚠️ No question pending.", ""
        
        self.user_response_queue.put(response)
        return "✅ Response sent!", ""
    
    def get_current_state(self):
        """Get current workflow state for UI updates."""
        summary = self.current_result.get("summary", "Waiting for workflow to complete...")
        diagram_url = self.current_result.get("diagram_url", "")
        tts_file = self.current_result.get("tts_file", "")
        json_output = json.dumps(self.current_result, indent=2) if self.current_result else "{}"
        
        return (
            "\n".join(self.logs),
            "\n\n".join(self.clarifier_history),
            summary,
            diagram_url,
            tts_file,
            json_output
        )


# Global UI manager instance
ui_manager = GradioUIManager()


def create_gradio_interface():
    """Create and configure the Gradio interface."""
    
    with gr.Blocks(title="Product Conversation Manager", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            """
            # 🎯 Product Conversation Manager
            
            Process product information through multi-agent conversation workflows.
            Provide text, image, or audio input to get comprehensive product analysis.
            """
        )
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📝 Input")
                
                text_input = gr.Textbox(
                    label="Text Input",
                    placeholder="Enter product description or requirements...",
                    lines=5
                )
                
                image_input = gr.Image(
                    label="Image Input (optional)",
                    type="filepath"
                )
                
                audio_input = gr.Audio(
                    label="Audio Input (optional)",
                    type="filepath"
                )
                
                generate_audio = gr.Checkbox(
                    label="Generate Audio Summary",
                    value=True
                )
                
                with gr.Row():
                    run_btn = gr.Button("🚀 Run Workflow", variant="primary", size="lg")
                    reset_btn = gr.Button("🔄 Reset", size="lg")
                
                status_box = gr.Textbox(
                    label="Status",
                    interactive=False,
                    lines=2
                )
            
            with gr.Column(scale=2):
                gr.Markdown("### 📊 Results")
                
                with gr.Tabs() as tabs:
                    with gr.Tab("💬 Clarifier"):
                        clarifier_display = gr.Textbox(
                            label="Clarifier Conversation",
                            lines=15,
                            interactive=False
                        )
                        with gr.Row():
                            clarifier_response = gr.Textbox(
                                label="Your Response",
                                placeholder="Type your response to clarifier questions here...",
                                scale=4
                            )
                            send_btn = gr.Button("Send", variant="primary", scale=1)
                        
                        clarifier_status = gr.Textbox(
                            label="Response Status",
                            interactive=False,
                            lines=1
                        )
                    
                    with gr.Tab("📋 Summary"):
                        summary_display = gr.Textbox(
                            label="Product Summary",
                            lines=20,
                            interactive=False
                        )
                    
                    with gr.Tab("📝 Logs"):
                        logs_display = gr.Textbox(
                            label="Agent Logs",
                            lines=20,
                            interactive=False
                        )
                    
                    with gr.Tab("📊 Diagram"):
                        diagram_url_display = gr.Textbox(
                            label="Diagram URL",
                            interactive=False
                        )
                        diagram_link = gr.Markdown("")
                    
                    with gr.Tab("🔊 Audio"):
                        audio_display = gr.Audio(
                            label="Generated Audio Summary",
                            interactive=False
                        )
                        audio_file_path = gr.Textbox(
                            label="Audio File Path",
                            interactive=False
                        )
                    
                    with gr.Tab("📄 Full JSON"):
                        json_display = gr.Code(
                            label="Complete Workflow Output",
                            language="json",
                            lines=20
                        )
        
        # Auto-update function for polling workflow status
        def update_ui_state():
            """Update UI with current workflow state."""
            logs, clarifier, summary, diagram_url, tts_file, json_output = ui_manager.get_current_state()
            
            # Update diagram link markdown
            diagram_md = ""
            if diagram_url:
                diagram_md = f"[🔗 Open Diagram in Browser]({diagram_url})"
            
            return (
                logs,
                clarifier,
                summary,
                diagram_url,
                diagram_md,
                tts_file if tts_file and os.path.exists(tts_file) else None,
                tts_file,
                json_output
            )
        
        # Event handlers
        def run_workflow_handler(text, image, audio, gen_audio):
            status = ui_manager.run_workflow(text, image, audio, gen_audio)
            return status
        
        def reset_handler():
            ui_manager.clear_logs()
            ui_manager.clear_clarifier_history()
            ui_manager.current_result = {}
            return (
                "",  # text_input
                None,  # image_input
                None,  # audio_input
                "✅ Inputs reset",  # status
                "",  # logs
                "",  # clarifier
                "",  # summary
                "",  # diagram_url
                "",  # diagram_link
                None,  # audio_display
                "",  # audio_file_path
                "{}"  # json
            )
        
        def send_response_handler(response):
            status, cleared_input = ui_manager.send_clarifier_response(response)
            return status, cleared_input
        
        # Connect event handlers
        run_btn.click(
            fn=run_workflow_handler,
            inputs=[text_input, image_input, audio_input, generate_audio],
            outputs=[status_box]
        )
        
        reset_btn.click(
            fn=reset_handler,
            outputs=[
                text_input,
                image_input,
                audio_input,
                status_box,
                logs_display,
                clarifier_display,
                summary_display,
                diagram_url_display,
                diagram_link,
                audio_display,
                audio_file_path,
                json_display
            ]
        )
        
        send_btn.click(
            fn=send_response_handler,
            inputs=[clarifier_response],
            outputs=[clarifier_status, clarifier_response]
        )
        
        clarifier_response.submit(
            fn=send_response_handler,
            inputs=[clarifier_response],
            outputs=[clarifier_status, clarifier_response]
        )
        
        # Auto-refresh every 2 seconds to update workflow progress
        timer = gr.Timer(2)
        timer.tick(
            fn=update_ui_state,
            outputs=[
                logs_display,
                clarifier_display,
                summary_display,
                diagram_url_display,
                diagram_link,
                audio_display,
                audio_file_path,
                json_display
            ]
        )
        
        # Initial load
        demo.load(
            fn=update_ui_state,
            outputs=[
                logs_display,
                clarifier_display,
                summary_display,
                diagram_url_display,
                diagram_link,
                audio_display,
                audio_file_path,
                json_display
            ]
        )
    
    return demo


def launch_gradio_ui(share=False, server_port=7860):
    """Launch the Gradio interface."""
    demo = create_gradio_interface()
    demo.launch(share=share, server_port=server_port)


if __name__ == "__main__":
    launch_gradio_ui()
