# website/scripts/bank_agent_runtime.py

from wayflowcore.agentspec import AgentSpecLoader as WayFlowLoader
from wayflowcore.agent import Agent as RuntimeAgent
from wayflowcore.executors.executionstatus import UserMessageRequestStatus
from pyagentspec.agent import Agent
from pyagentspec.serialization import AgentSpecSerializer

from twols import (
    resolve_customer,
    get_customer_profile,
    list_transactions,
    summarize_customer_spend,
    resolve_customer_tool,
    get_customer_profile_tool,
    list_transactions_tool,
    summarize_customer_spend_tool,
)
from llm_config import llm_config

system_prompt = """
You are a Financial Crime Assistant Agent for a Swiss bank.
You review clients for AML relevant transactions in compliance with FINMA
and Swiss regulations.

You have access to the tool resolve_customer_tool,
            get_customer_profile_tool,
            list_transactions_tool,
            summarize_customer_spend_tool.
"""

agent_config = Agent(
    name="Financial Crime Assistant Agent",
    description="Agent equipped with tools to assist with fraudulent financial incidents",
    llm_config=llm_config,
    tools=[
        resolve_customer_tool,
        get_customer_profile_tool,
        list_transactions_tool,
        summarize_customer_spend_tool,
    ],
    system_prompt=system_prompt,
)

serialized_agent = AgentSpecSerializer().to_json(agent_config)

tool_registry = {
    "resolve_customer": resolve_customer,
    "get_customer_profile": get_customer_profile,
    "list_transactions": list_transactions,
    "summarize_customer_spend": summarize_customer_spend,
}

agent: RuntimeAgent = WayFlowLoader(tool_registry=tool_registry).load_json(
    serialized_agent
)

conversation = agent.start_conversation()


def step(user_input: str) -> str:
    conversation.append_user_message(user_input)
    status = conversation.execute()
    assistant_reply = conversation.get_last_message()
    return assistant_reply.content if assistant_reply else ""
