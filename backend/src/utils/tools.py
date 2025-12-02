from src.agents.agent import clarifier

config = {"configurable": {"thread_id": "product_conversation"}}
response = clarifier.invoke({"messages": ["create a product who is like e commerce but for api"]},config=config)


print(response)
