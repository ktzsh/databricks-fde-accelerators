import os
import mlflow
import asyncio
import nest_asyncio

nest_asyncio.apply()

from enum import Enum
from typing import (
    Any, Generator, Optional, Sequence, Union, Annotated, List, TypedDict
)
from mlflow.langchain.chat_agent_langgraph import ChatAgentState, ChatAgentToolNode

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
)
from langchain_core.runnables import RunnableConfig, RunnableLambda

from langgraph.prebuilt.tool_node import ToolNode
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from databricks.sdk import WorkspaceClient
from databricks_langchain import ChatDatabricks

from src.utils.mcp import create_mcp_tools

MAX_ITERATION_MESSAGE = "Agent stopped due to max iterations. Please try again with more specific query!"

class AgentState(ChatAgentState):
    iterations: int
    
def create_agent_workflow(
    model_config: mlflow.models.ModelConfig
) -> CompiledStateGraph:
    workspace_client = WorkspaceClient()

    host = workspace_client.config.host
    tools = asyncio.run(create_mcp_tools(
        ws=workspace_client,
        managed_server_urls=[
            f"{host}{url_suffix}" for url_suffix in model_config.get("agents").get("mcp_agent").get("managed_server_urls")
        ],
        custom_server_urls=[
            f"{host}{url_suffix}" for url_suffix in model_config.get("agents").get("mcp_agent").get("custom_server_urls")
        ]
    ))
    
    llm = ChatDatabricks(
        endpoint=model_config.get("llm_endpoint_name"),
        extra_params=model_config.get("llm_parameters"),
    )
    llm_with_tools = llm.bind_tools(tools)  # Bind tools to the model

    system_prompt = model_config.get("agents").get("mcp_agent").get("system_prompt")

    # Function to check if agent should continue or finish based on last message
    def should_continue(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        # If function (tool) calls are present, continue; otherwise, end
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "continue"
        if isinstance(last_message, dict) and last_message.get("tool_calls"):
            return "continue"
        else:
            return "end"

    # Preprocess: optionally prepend a system prompt to the conversation history
    if system_prompt:
        preprocessor = RunnableLambda(
            lambda state: [{"role": "system", "content": system_prompt}] + state["messages"]
        )
    else:
        preprocessor = RunnableLambda(lambda state: state["messages"])

    model_runnable = preprocessor | llm_with_tools  # Chain the preprocessor and the model

    # The function to invoke the model within the workflow
    def call_model(
        state: AgentState,
        config: RunnableConfig,
    ):
        response = model_runnable.invoke(state, config)
        return {"messages": [response]}

    workflow = StateGraph(AgentState)  # Create the agent's state machine

    workflow.add_node("mcp_agent", RunnableLambda(call_model))  # Agent node (LLM)
    workflow.add_node("tools", ChatAgentToolNode(tools))             # Tools node

    workflow.set_entry_point("mcp_agent")  # Start at agent node
    workflow.add_conditional_edges(
        "mcp_agent",
        should_continue,
        {
            "continue": "tools",  # If the model requests a tool call, move to tools node
            "end": END,           # Otherwise, end the workflow
        },
    )
    workflow.add_edge("tools", "mcp_agent")  # After tools are called, return to agent node

    # Compile and return the tool-calling agent workflow
    return workflow.compile()


class LangGraphAgent():
    def __init__(self, model_config):
        self.workflow = create_agent_workflow(model_config)

    def predict_stream(self, request):
        for event in self.workflow.stream(request, stream_mode=["updates", "messages"]):
            # print("event", event)
            if event[0] == "updates":
                # Stream mcp_agent response, send other as updates
                if "mcp_agent" in event[1]:
                    continue
                for node_data in event[1].values():
                    for message in node_data.get("messages", []):
                        if isinstance(message, dict):
                            yield ("updates", message)
                        else:
                            yield ("updates", message.dict())
            if event[0] == "messages":
                message, metadata = event[1][0], event[1][1]
                if (
                    isinstance(message, AIMessageChunk)
                    and not message.tool_call_chunks
                    and not message.tool_calls
                    and metadata.get("langgraph_node") == "mcp_agent" # search internally calls llm so skip those
                    # and message.content
                ):
                    message = message.dict()
                    message["role"] = "assistant"
                    yield ("messages", message)