import json
import time
import pygame
from typing import Dict, Any, Optional, List
from langchain_core.messages import HumanMessage, BaseMessage

# Import agents and utilities
from src.agents.agent import get_clarifier_agent, get_product_agent
from src.models.agentComp import ClarifierResp, ProductResp
from src.utils.helper import get_user_input, process_agent_response
from src.agents.engineer import get_engineer_agent
from src.agents.customer import get_customer_agent
from src.agents.risk import get_risk_agent
from src.agents.summarizer import get_summarizer_agent
from src.utils.prompt import get_prompt_generator_agent
from src.services.diagram.diagramAgent import generate_mermaid_link
from src.services.tts.tts_summarize import get_tts_converter_agent
from src.services.tts.tts import TextToSpeech, synthesize_text_with_rate_limit
from src.config.model_config import get_model
from src.config.model_limits import get_agent_limit

class ProductConversationManager:
    def __init__(self, thread_id: str = "product_conversation",
                 text_input: Optional[str] = None,
                 image_input: Optional[str] = None,
                 audio_input: Optional[str] = None,
                 model_provider: str = "openai",
                 max_questions: Optional[int] = None,
                 max_features: Optional[int] = None):
        self.config = {"configurable": {"thread_id": thread_id}}
        self.text_input = text_input
        self.image_input = image_input
        self.audio_input = audio_input
        self.model_provider = model_provider
        
        # Resolve limits from config if not provided
        if max_questions is None:
            max_questions = get_agent_limit("clarifier", "max_questions", 5)
        if max_features is None:
            max_features = get_agent_limit("product", "max_features", 5)
            
        self.max_questions = max_questions
        self.max_features = max_features
        
        # Initialize model and agents with agent-specific models
        self.clarifier_agent = get_clarifier_agent(get_model(provider=model_provider, agent_type="clarifier"), max_questions=max_questions)
        self.product_agent = get_product_agent(get_model(provider=model_provider, agent_type="product"), max_features=max_features)
        self.customer_runner = get_customer_agent(get_model(provider=model_provider, agent_type="customer"))
        self.engineer_agent = get_engineer_agent(get_model(provider=model_provider, agent_type="engineer"))
        self.risk_agent = get_risk_agent(get_model(provider=model_provider, agent_type="risk"))
        self.summarizer_agent = get_summarizer_agent(get_model(provider=model_provider, agent_type="summarizer"))
        self.prompt_generator = get_prompt_generator_agent(get_model(provider=model_provider, agent_type="prompt_generator"))
        self.tts_converter = get_tts_converter_agent(get_model(provider=model_provider, agent_type="tts_converter"))

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
        print("DEBUG: Entering generate_enhanced_prompt")
        if not any([self.text_input, self.image_input, self.audio_input]):
            print("DEBUG: No inputs provided, returning default prompt")
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
        print(f"DEBUG: Invoking prompt_generator with inputs: {inputs}")
        try:
            result = self.prompt_generator.invoke(inputs, config=self.config)
            print("DEBUG: prompt_generator invoked successfully")
            return result["messages"][-1].content
        except Exception as e:
            print(f"DEBUG: Error in prompt_generator: {e}")
            raise e

    def run_clarifier_conversation(self, max_rounds: int = 3, max_user_inputs: int = 4,
                                  user_input_callback=None, clarifier_callback=None) -> bool:
        """Run the clarifier conversation loop with enhanced prompt"""
        print("Starting Clarifier conversation...")

        # Generate enhanced prompt if inputs are provided
        print("DEBUG: Calling generate_enhanced_prompt")
        initial_prompt = self.generate_enhanced_prompt()
        print(f"DEBUG: Enhanced prompt generated: {initial_prompt[:50]}...")
        
        initial_message = HumanMessage(
            content=f"Start gathering requirements for a new mobile app based on this: {initial_prompt}. "
                   f"Only ask {self.max_questions} critical questions that require user input."
        )

        # Initial invocation
        print("DEBUG: Invoking clarifier_agent (Round 1)")
        clarifier_result = self.clarifier_agent.invoke({"messages": [initial_message]}, self.config)
        print("DEBUG: clarifier_agent invoked successfully")
        
        self.clarifier_messages = clarifier_result.get("messages", [])
        if not self.clarifier_messages:
            print("Error: Clarifier agent returned no messages")
            return False

        clarifier_response = self.clarifier_messages[-1].content
        usage_metadata = self.clarifier_messages[-1].response_metadata.get("token_usage") if hasattr(self.clarifier_messages[-1], "response_metadata") else None
        print(f"Clarifier (Round 1): {clarifier_response}")

        # Process the response
        clarifier_obj = process_agent_response(clarifier_response, ClarifierResp, usage_metadata)
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
            clarifier_result = self.clarifier_agent.invoke({"messages": self.clarifier_messages}, self.config)
            self.clarifier_messages = clarifier_result.get("messages", [])
            if not self.clarifier_messages:
                print("Error: Clarifier agent returned no messages in subsequent rounds")
                return False

            clarifier_response = self.clarifier_messages[-1].content
            usage_metadata = self.clarifier_messages[-1].response_metadata.get("token_usage") if hasattr(self.clarifier_messages[-1], "response_metadata") else None
            print(f"\nClarifier (Round {round_num+1}): {clarifier_response}")

            clarifier_obj = process_agent_response(clarifier_response, ClarifierResp, usage_metadata)
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
        trigger_message = HumanMessage(content=f"Based on the gathered requirements, please generate the full product specification with at least {self.max_features} features.")
        product_result = self.product_agent.invoke({"messages": self.clarifier_messages + [trigger_message]}, self.config)
        self.product_messages = product_result.get("messages", [])
        if not self.product_messages:
            print("Error: Product agent returned no messages")
            return False

        product_response = self.product_messages[-1].content
        usage_metadata = self.product_messages[-1].response_metadata.get("token_usage") if hasattr(self.product_messages[-1], "response_metadata") else None
        
        from src.utils.token_tracker import token_tracker
        if usage_metadata:
            token_tracker.track_usage(usage_metadata)
            
        print(f"\nProduct Response: {product_response}")

        # Try to parse the response using TOON
        try:
            from src.utils import toon
            # Try TOON parsing first since product agent outputs TOON
            parsed = toon.parse_response(product_response)
            if not parsed:
                # Fallback to JSON
                parsed = json.loads(product_response)
            
            # Convert to ProductResp object
            product_obj = ProductResp(
                name=parsed.get("name", "Unknown Product"),
                description=parsed.get("description", "No description available"),
                features=parsed.get("features", [])
            )
        except Exception as e:
            print(f"Error processing response: {e}")
            print("\nError: Could not parse product response.")
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
                    {"name": "User Profiles", "reason": "Personalization", "goal_oriented": 0.7, "development_time": "1 week", "cost_estimate": 2000.0},
                    {"name": "Social Sharing", "reason": "Engagement", "goal_oriented": 0.6, "development_time": "1 week", "cost_estimate": 1500.0},
                    {"name": "Progress Tracking", "reason": "Motivation", "goal_oriented": 0.9, "development_time": "2 weeks", "cost_estimate": 3000.0},
                    {"name": "Goal Setting", "reason": "User retention", "goal_oriented": 0.8, "development_time": "1 week", "cost_estimate": 2500.0},
                    {"name": "Health Insights", "reason": "Value addition", "goal_oriented": 0.7, "development_time": "2 weeks", "cost_estimate": 4000.0}
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
        customer_result = self.customer_runner.invoke(
            {"messages": [HumanMessage(content=product_response)]},
            self.config
        )
        if not customer_result or not customer_result.get("messages"):
            print("Error: Customer agent returned no result")
            return False
            
        customer_response = customer_result["messages"][-1].content
        usage_metadata = customer_result["messages"][-1].response_metadata.get("token_usage") if hasattr(customer_result["messages"][-1], "response_metadata") else None
        
        from src.utils.token_tracker import token_tracker
        if usage_metadata:
            token_tracker.track_usage(usage_metadata)

        try:
            from src.utils import toon
            # Try TOON parsing first since customer agent outputs TOON
            parsed = toon.parse_response(customer_response)
            if not parsed:
                # Fallback to JSON
                parsed = json.loads(customer_response)
                
            self.final_data["customer"] = parsed
            print(json.dumps(parsed, indent=2))
            return True
        except Exception as e:
            print(f"Error: Failed to parse customer response: {e}")
            return False

    def run_engineer_agent(self) -> bool:
        """Run the engineer agent"""
        print("\nGenerating Engineer response...")
        if not self.final_data.get("customer"):
            print("Error: No customer data available for engineer agent")
            return False

        engineer_result = self.engineer_agent.invoke(
            {"messages": [HumanMessage(content=json.dumps(self.final_data["customer"]))]},
            self.config
        )
        if not engineer_result.get("messages"):
            print("Error: Engineer agent returned no messages")
            return False

        engineer_response = engineer_result["messages"][-1].content
        usage_metadata = engineer_result["messages"][-1].response_metadata.get("token_usage") if hasattr(engineer_result["messages"][-1], "response_metadata") else None
        
        # Use helper to parse (supports JSON and TOON) and track usage
        # We don't have a specific Pydantic model for the full response structure in agentComp.py 
        # that matches the TOON structure exactly (EngineerAnalysis has features list), 
        # but let's try to parse it to a dict first using toon.loads if helper fails or just use helper with a dummy model?
        # Actually, helper.process_agent_response requires a model.
        # Let's just track usage manually and use toon.parse_response directly if needed, 
        # or better, use the helper with the EngineerAnalysis model if it matches.
        
        from src.utils.token_tracker import token_tracker
        if usage_metadata:
            token_tracker.track_usage(usage_metadata)
            
        try:
            from src.utils import toon
            # Try TOON parsing first since we switched to TOON
            parsed = toon.parse_response(engineer_response)
            if not parsed:
                # Fallback to JSON
                parsed = json.loads(engineer_response)
                
            self.final_data["engineer"] = {"analysis": parsed}
            print(json.dumps(parsed, indent=2))
            return True
        except Exception as e:
            print(f"Error: Failed to parse engineer response: {e}")
            return False

    def run_risk_agent(self) -> bool:
        """Run the risk agent"""
        print("\nGenerating Risk response...")
        if not self.final_data.get("engineer"):
            print("Error: No engineer data available for risk agent")
            return False

        risk_result = self.risk_agent.invoke(
            {"messages": [HumanMessage(content=json.dumps(self.final_data["engineer"]))]},
            self.config
        )
        if not risk_result.get("messages"):
            print("Error: Risk agent returned no messages")
            return False

        risk_response = risk_result["messages"][-1].content
        usage_metadata = risk_result["messages"][-1].response_metadata.get("token_usage") if hasattr(risk_result["messages"][-1], "response_metadata") else None
        
        from src.utils.token_tracker import token_tracker
        if usage_metadata:
            token_tracker.track_usage(usage_metadata)

        try:
            from src.utils import toon
            parsed = toon.parse_response(risk_response)
            if not parsed:
                parsed = json.loads(risk_response)
                
            self.final_data["risk"] = {"assessment": parsed}
            print(json.dumps(parsed, indent=2))
            return True
        except Exception as e:
            print(f"Error: Failed to parse risk response: {e}")
            return False

    def run_summarizer_agent(self) -> str:
        """Run the summarizer agent and return summary"""
        print("\nGenerating Final Summary...")
        summary_result = self.summarizer_agent.invoke(
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
        response = self.tts_converter.invoke(
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
            # Note: TTS still uses an external API endpoint (may require specific TTS API key)
            from src.config.env import OPENAI_API_KEY
            
            if not OPENAI_API_KEY:
                print("Warning: No API key available for TTS. Skipping audio generation.")
                return False
                
            tts = TextToSpeech(OPENAI_API_KEY)
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
