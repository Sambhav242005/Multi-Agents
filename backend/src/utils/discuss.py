import json
from langchain_core.messages import HumanMessage
from agent import clarifier, product
from agentComp import ClarifierResp, ProductResp
from helper import get_user_input, process_agent_response
from engineer import engineer
from customer import customer
from risk import risk
from summarizer import summarizer_agent

# --- Configuration ---
config = {"configurable": {"thread_id": "product_conversation"}}

# --- Collect all outputs here ---
final_data = {
    "clarifier": None,
    "product": None,
    "customer": None,
    "engineer": None,
    "risk": None
}

# --- Start Clarifier conversation ---
print("Starting Clarifier conversation...")
initial_message = HumanMessage(
    content="Start gathering requirements for a new mobile app. Only ask 3-5 critical questions that require user input."
)

clarifier_result = clarifier.invoke({"messages": [initial_message]}, config)
clarifier_messages = clarifier_result["messages"]
clarifier_response = clarifier_messages[-1].content
print(f"Clarifier (Round 1): {clarifier_response}")

clarifier_obj = process_agent_response(clarifier_response, ClarifierResp)
if clarifier_obj:
    final_data["clarifier"] = clarifier_obj.model_dump()
    print(json.dumps(final_data["clarifier"], indent=2))

# --- Collect user inputs ---
user_inputs_collected = 0
max_user_inputs = 4
rounds = 5

for i in range(1, rounds):
    if clarifier_obj and clarifier_obj.done:
        print(f"Clarifier finished after {i} rounds")
        break

    user_inputs_needed = False
    if clarifier_obj:
        for req in clarifier_obj.resp:
            if not req.answer and user_inputs_collected < max_user_inputs:
                user_answer = get_user_input(req.question)
                req.answer = user_answer
                user_inputs_collected += 1
                user_inputs_needed = True

                clarifier_messages.append(
                    HumanMessage(content=f"User answered: '{req.question}' -> '{user_answer}'")
                )

                print(f"\nUser inputs collected: {user_inputs_collected}/{max_user_inputs}")

    clarifier_result = clarifier.invoke({"messages": clarifier_messages}, config)
    clarifier_messages = clarifier_result["messages"]
    clarifier_response = clarifier_messages[-1].content
    print(f"\nClarifier (Round {i+1}): {clarifier_response}")

    clarifier_obj = process_agent_response(clarifier_response, ClarifierResp)
    if clarifier_obj:
        final_data["clarifier"] = clarifier_obj.model_dump()
        print(json.dumps(final_data["clarifier"], indent=2))

# --- Product agent ---
print("\nGenerating Product response...")
product_result = product.invoke({"messages": clarifier_messages}, config)
product_messages = product_result["messages"]
product_response = product_messages[-1].content
print(f"\nProduct Response: {product_response}")

product_obj = process_agent_response(product_response, ProductResp)
if product_obj:
    final_data["product"] = product_obj.model_dump()
    print(json.dumps(final_data["product"], indent=2))

    if len(product_obj.features) < 5:
        print("\nRetrying Product with explicit instruction for at least 5 features...")
        retry_message = HumanMessage(content="Generate a product response with at least 5 features based on our conversation.")
        product_result = product.invoke({"messages": product_messages + [retry_message]}, config)
        product_messages = product_result["messages"]
        product_response = product_messages[-1].content
        product_obj = process_agent_response(product_response, ProductResp)
        if product_obj:
            final_data["product"] = product_obj.model_dump()
            print(json.dumps(final_data["product"], indent=2))
else:
    print("\nError: Could not parse product response.")

# --- Customer agent ---
print("\nGenerating Customer response...")
customer_result = customer(product_response)
final_data["customer"] = json.loads(customer_result)
print(customer_result)

# --- Engineer agent ---
print("\nGenerating Engineer response...")
engineer_result = engineer.invoke(
    {"messages": [HumanMessage(content=json.dumps(customer_result))]},
    config
)
engineer_response = engineer_result["messages"][-1].content
final_data["engineer"] = {"analysis":json.loads(engineer_response)}
print(engineer_response)

# --- Risk agent ---
print("\nGenerating Risk response...")
risk_result = risk.invoke(
    {"messages": [HumanMessage(content=engineer_response)]},
    config
)
risk_response = risk_result["messages"][-1].content
final_data["risk"] = {"assessment":json.loads(risk_response)}
print(risk_response)

# --- Final merged JSON ---
print("\n✅ Final Merged JSON:")
print(json.dumps(final_data, indent=2))

# --- Summarizer agent ---
print("\nGenerating Final Summary...")
summary_result = summarizer_agent.invoke(
    {"messages": [HumanMessage(content=json.dumps(final_data, indent=2))]},
    config
)
summary = summary_result["messages"][-1].content
print(f"\n📌 Final Summary:\n{summary}")
