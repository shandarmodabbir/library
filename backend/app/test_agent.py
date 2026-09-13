from .agent.library_agent import agent

response = agent.run(
    "i want a historical book that's related to roman"
)

print(response)
