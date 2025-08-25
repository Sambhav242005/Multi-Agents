import json
import time
import pygame
from typing import Dict, Any, Optional, List
from langchain_core.messages import HumanMessage, BaseMessage
from env import GROQ_API_KEY

# Import agents and utilities
from agent import clarifier, product
from agentComp import ClarifierResp, ProductResp
from helper import get_user_input, process_agent_response
from engineer import engineer
from customer import customer
from risk import risk
from summarizer import summarizer_agent
from prompt import prompt_generator
from diagramAgent import generate_mermaid_link
from tts_summarize import tts_converter
from tts import TextToSpeech, synthesize_text_with_rate_limit

class ProductConversationManager:
    def __init__(self, thread_id: str = "product_conversation",
                 text_input: Optional[str] = None,
                 image_input: Optional[str] = None,
                 audio_input: Optional[str] = None):
        self.config = {"configurable": {"thread_id": thread_id}}
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
        self.clarifier_messages: List[BaseMessage] = []
        self.product_messages: List[BaseMessage] = []
        self._clear_intermediate_data()

    def _clear_intermediate_data(self) -> None:
        """Clear intermediate data to free memory"""
        self.clarifier_messages.clear()
        self.product_messages.clear()

    def generate_enhanced_prompt(self) -> str:
        """Generate an enhanced prompt using multiple input modalities"""
        if not any([self.text_input, self.image_input, self.audio_input]):
            return "Create a mobile app for fitness tracking with step counting, calorie monitoring, and sleep analysis."

        inputs = {
            "messages": [
                ("user", f"Process these inputs to generate a comprehensive prompt:\n"
                        f"Image: {'URL' if self.image_input and self.image_input.startswith('http') else 'Local file'}: {self.image_input}\n"
                        f"Audio: {'Record new audio' if self.audio_input == 'RECORD' else f'File: {self.audio_input}'}\n"
                        f"Text: {self.text_input}"
                )
            ]
        }
        result = prompt_generator.invoke(inputs, config=self.config)
        return result["messages"][-1].content

    def run_clarifier_conversation(self, max_rounds: int = 5, max_user_inputs: int = 4,
                                  user_input_callback=None, clarifier_callback=None) -> bool:
        """Run the clarifier conversation loop with enhanced prompt"""
        print("Starting Clarifier conversation...")

        # Generate enhanced prompt if inputs are provided
        initial_prompt = self.generate_enhanced_prompt()
        initial_message = HumanMessage(
            content=f"Start gathering requirements for a new mobile app based on this: {initial_prompt}. "
                   "Only ask 3-5 critical questions that require user input."
        )

        # Initial invocation
        clarifier_result = clarifier.invoke({"messages": [initial_message]}, self.config)
        self.clarifier_messages = clarifier_result.get("messages", [])
        if not self.clarifier_messages:
            print("Error: Clarifier agent returned no messages")
            return False

        clarifier_response = self.clarifier_messages[-1].content
        print(f"Clarifier (Round 1): {clarifier_response}")

        # Process the response
        clarifier_obj = process_agent_response(clarifier_response, ClarifierResp)
        if clarifier_obj:
            self.final_data["clarifier"] = clarifier_obj.model_dump()
            print(json.dumps(self.final_data["clarifier"], indent=2))

        # Conversation loop
        user_inputs_collected = 0
        for round_num in range(1, max_rounds):
            if clarifier_obj and clarifier_obj.done:
                print(f"Clarifier finished after {round_num} rounds")
                break

            user_inputs_needed = False
            if clarifier_obj:
                for req in clarifier_obj.resp:
                    if not req.answer and user_inputs_collected < max_user_inputs:
                        # Get user answer using the appropriate callback
                        if clarifier_callback:
                            user_answer = clarifier_callback(req.question)
                        elif user_input_callback:
                            user_answer = user_input_callback(req.question)
                        else:
                            user_answer = get_user_input(req.question)

                        req.answer = user_answer
                        user_inputs_collected += 1
                        user_inputs_needed = True
                        self.clarifier_messages.append(
                            HumanMessage(content=f"User answered: '{req.question}' -> '{user_answer}'")
                        )
                        print(f"\nUser inputs collected: {user_inputs_collected}/{max_user_inputs}")

            # Continue conversation
            clarifier_result = clarifier.invoke({"messages": self.clarifier_messages}, self.config)
            self.clarifier_messages = clarifier_result.get("messages", [])
            if not self.clarifier_messages:
                print("Error: Clarifier agent returned no messages in subsequent rounds")
                return False

            clarifier_response = self.clarifier_messages[-1].content
            print(f"\nClarifier (Round {round_num+1}): {clarifier_response}")

            clarifier_obj = process_agent_response(clarifier_response, ClarifierResp)
            if clarifier_obj:
                self.final_data["clarifier"] = clarifier_obj.model_dump()
                print(json.dumps(self.final_data["clarifier"], indent=2))

        return True

    def run_product_agent(self) -> bool:
        """Run the product agent with retry logic and diagram generation"""
        print("\nGenerating Product response...")
        if not self.clarifier_messages:
            print("Error: No clarifier messages available for product agent")
            return False

        # Initial invocation
        product_result = product.invoke({"messages": self.clarifier_messages}, self.config)
        self.product_messages = product_result.get("messages", [])
        if not self.product_messages:
            print("Error: Product agent returned no messages")
            return False

        product_response = self.product_messages[-1].content
        print(f"\nProduct Response: {product_response}")

        # Try to parse the response as ProductResp
        try:
            product_obj = process_agent_response(product_response, ProductResp)
        except Exception as e:
            print(f"Error processing response: {e}")
            # If parsing fails, try to extract JSON from the response
            try:
                # Look for JSON in the response
                json_start = product_response.find('{')
                json_end = product_response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = product_response[json_start:json_end]
                    product_data = json.loads(json_str)
                    # Create a ProductResp object from the extracted data
                    product_obj = ProductResp(
                        name=product_data.get("name", "Unknown Product"),
                        description=product_data.get("description", "No description available"),
                        features=product_data.get("features", [])
                    )
                else:
                    raise ValueError("No JSON found in response")
            except Exception as e2:
                print(f"Error extracting JSON: {e2}")
                print("\nRetrying with more explicit instructions...")
                # Retry with even more explicit instructions
                retry_message = HumanMessage(
                    content="Please generate a product response in valid JSON format with these exact fields:\n"
                    "{\n"
                    '  "name": "Product Name",\n'
                    '  "description": "Detailed product description",\n'
                    '  "features": [\n'
                    '    {"name": "Feature 1", "description": "Description of feature 1"},\n'
                    '    {"name": "Feature 2", "description": "Description of feature 2"},\n'
                    '    ...\n'
                    '  ]\n'
                    "}\n\n"
                    "Make sure to include at least 5 features. Do not include any questions or other text."
                )
                product_result = product.invoke(
                    {"messages": self.product_messages + [retry_message]},
                    self.config
                )
                self.product_messages = product_result.get("messages", [])
                if not self.product_messages:
                    print("Error: Product agent retry returned no messages")
                    return False
                product_response = self.product_messages[-1].content
                print(f"\nProduct Response (retry): {product_response}")
                try:
                    product_obj = process_agent_response(product_response, ProductResp)
                except Exception as e3:
                    print(f"Error in retry: {e3}")
                    print("\nError: Could not parse product response after retry.")
                    return False

        if product_obj:
            self.final_data["product"] = product_obj.model_dump()
            print(json.dumps(self.final_data["product"], indent=2))

            # Generate diagram from product data with error handling
            try:
                product_json = json.dumps(self.final_data["product"], indent=2)
                # Use the new generate_mermaid_link function with open_in_browser=False
                diagram_url = generate_mermaid_link(product_json, open_in_browser=False)
                if diagram_url:
                    self.final_data["diagram_url"] = diagram_url
                    print(f"\nGenerated diagram URL: {diagram_url}")
                else:
                    print("\nWarning: Could not generate diagram URL")
                    self.final_data["diagram_url"] = None
            except Exception as e:
                print(f"\nError generating diagram: {e}")
                self.final_data["diagram_url"] = None
                print("Continuing without diagram...")

            # Ensure we have at least 5 features
            if len(product_obj.features) < 5:
                print("\nAdding more features to meet the minimum requirement...")
                # Create a new features list with at least 5 features
                base_features = product_obj.features.copy()
                additional_features = [
                    {"name": "User Profiles", "description": "Create and customize personal user profiles with avatars and preferences."},
                    {"name": "Social Sharing", "description": "Share achievements and progress on social media platforms."},
                    {"name": "Progress Tracking", "description": "Visualize progress with charts and graphs over time."},
                    {"name": "Goal Setting", "description": "Set and track personal fitness goals with reminders."},
                    {"name": "Health Insights", "description": "Receive personalized health insights based on tracked data."}
                ]

                # Add additional features until we have at least 5
                while len(base_features) < 5 and additional_features:
                    base_features.append(additional_features.pop(0))

                # Update the product object
                product_obj.features = base_features
                self.final_data["product"] = product_obj.model_dump()
                print(json.dumps(self.final_data["product"], indent=2))
        else:
            print("\nError: Could not parse product response.")
            return False

        return True

    def run_customer_agent(self) -> bool:
        """Run the customer agent"""
        print("\nGenerating Customer response...")
        if not self.product_messages:
            print("Error: No product messages available for customer agent")
            return False

        product_response = self.product_messages[-1].content
        customer_result = customer(product_response)
        if not customer_result:
            print("Error: Customer agent returned no result")
            return False

        try:
            self.final_data["customer"] = json.loads(customer_result)
            print(customer_result)
            return True
        except json.JSONDecodeError:
            print("Error: Failed to parse customer response as JSON")
            return False

    def run_engineer_agent(self) -> bool:
        """Run the engineer agent"""
        print("\nGenerating Engineer response...")
        if not self.final_data.get("customer"):
            print("Error: No customer data available for engineer agent")
            return False

        engineer_result = engineer.invoke(
            {"messages": [HumanMessage(content=json.dumps(self.final_data["customer"]))]},
            self.config
        )
        if not engineer_result.get("messages"):
            print("Error: Engineer agent returned no messages")
            return False

        engineer_response = engineer_result["messages"][-1].content
        try:
            self.final_data["engineer"] = {"analysis": json.loads(engineer_response)}
            print(engineer_response)
            return True
        except json.JSONDecodeError:
            print("Error: Failed to parse engineer response as JSON")
            return False

    def run_risk_agent(self) -> bool:
        """Run the risk agent"""
        print("\nGenerating Risk response...")
        if not self.final_data.get("engineer"):
            print("Error: No engineer data available for risk agent")
            return False

        risk_result = risk.invoke(
            {"messages": [HumanMessage(content=json.dumps(self.final_data["engineer"]))]},
            self.config
        )
        if not risk_result.get("messages"):
            print("Error: Risk agent returned no messages")
            return False

        risk_response = risk_result["messages"][-1].content
        try:
            self.final_data["risk"] = {"assessment": json.loads(risk_response)}
            print(risk_response)
            return True
        except json.JSONDecodeError:
            print("Error: Failed to parse risk response as JSON")
            return False

    def run_summarizer_agent(self) -> str:
        """Run the summarizer agent and return summary"""
        print("\nGenerating Final Summary...")
        summary_result = summarizer_agent.invoke(
            {"messages": [HumanMessage(content=json.dumps(self.final_data, indent=2))]},
            self.config
        )
        if not summary_result.get("messages"):
            print("Error: Summarizer agent returned no messages")
            return ""

        summary = summary_result["messages"][-1].content
        print(f"\n📌 Final Summary:\n{summary}")
        return summary

    def convert_summary_to_speech(self, summary: str, output_file: str = "podcast.mp3") -> bool:
        """Convert summary to speech using TTS"""
        print("\nConverting summary to speech...")
        if not summary:
            print("Error: No summary available for TTS conversion")
            return False

        # Convert summary to TTS-ready format
        response = tts_converter.invoke(
            {"messages": [("human", summary)]},
            config=self.config
        )
        if not response.get("messages"):
            print("Error: TTS converter returned no messages")
            return False

        last_message = response['messages'][-1]
        try:
            result = json.loads(last_message.content)
            tts_text = result.get("converted_text", summary)
            print("TTS Text:", tts_text)

            # Synthesize speech
            tts = TextToSpeech(GROQ_API_KEY)
            out_file = synthesize_text_with_rate_limit(tts, tts_text, out_path=output_file)
            self.final_data["tts_file"] = out_file
            print(f"Audio saved to: {out_file}")

            # Play audio
            try:
                pygame.mixer.init()
                pygame.mixer.music.load(out_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(1)
                print("Audio playback completed")
            except Exception as e:
                print(f"Playback failed: {e}")
            return True
        except json.JSONDecodeError:
            print("Error: Invalid TTS response format")
            print("Raw response:", last_message.content)
            return False

    # In refinedModelClass.py, update the run_full_workflow method

    # refinedModelClass.py - Update the run_full_workflow method

    def run_full_workflow(self, user_input_callback=None, clarifier_callback=None, generate_audio: bool = True, progress_callback=None) -> Dict[str, Any]:
        """Execute the entire conversation workflow"""
        try:
            # Step 1: Run clarifier conversation
            if progress_callback:
                progress_callback("Running clarifier conversation...")
            if not self.run_clarifier_conversation(
                user_input_callback=user_input_callback,
                clarifier_callback=clarifier_callback
            ):
                print("Clarifier conversation failed. Aborting workflow.")
                return {"error": "Clarifier conversation failed"}

            # Step 2: Run product agent
            if progress_callback:
                progress_callback("Generating product specifications...")
            if not self.run_product_agent():
                print("Product agent failed. Aborting workflow.")
                return {"error": "Product agent failed"}

            # Step 3: Run customer agent
            if progress_callback:
                progress_callback("Analyzing customer perspective...")
            if not self.run_customer_agent():
                print("Customer agent failed. Aborting workflow.")
                return {"error": "Customer agent failed"}

            # Step 4: Run engineer agent
            if progress_callback:
                progress_callback("Evaluating technical feasibility...")
            if not self.run_engineer_agent():
                print("Engineer agent failed. Aborting workflow.")
                return {"error": "Engineer agent failed"}

            # Step 5: Run risk agent
            if progress_callback:
                progress_callback("Assessing potential risks...")
            if not self.run_risk_agent():
                print("Risk agent failed. Aborting workflow.")
                return {"error": "Risk agent failed"}

            # Step 6: Generate final summary
            if progress_callback:
                progress_callback("Creating final summary...")
            summary = self.run_summarizer_agent()

            # Step 7: Convert summary to speech
            if generate_audio:
                if progress_callback:
                    progress_callback("Generating audio summary...")
                if not self.convert_summary_to_speech(summary):
                    print("TTS conversion failed. Continuing without audio.")

            # Create result dictionary
            result = {
                **self.final_data,
                "summary": summary
            }

            if progress_callback:
                progress_callback("Workflow completed successfully!")

            return result
        except Exception as e:
            print(f"Error during workflow execution: {str(e)}")
            return {"error": str(e)}
        finally:
            # Ensure memory cleanup
            self._clear_intermediate_data()
