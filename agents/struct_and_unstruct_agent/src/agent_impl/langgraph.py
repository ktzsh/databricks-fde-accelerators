import os
import mlflow
import pydantic

from enum import Enum
from typing import (
    Any, Generator, Optional, Sequence, Union, Annotated, List, TypedDict
)
from mlflow.langchain.chat_agent_langgraph import ChatAgentState, ChatAgentToolNode

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    SystemMessage,
)
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from databricks.sdk import WorkspaceClient
from databricks_langchain import ChatDatabricks

from src.utils.genie import get_genie_agent
from src.utils.vector_search import create_vector_search_tool

MAX_ITERATION_MESSAGE = "<name>Response Agent</name> Agent stopped due to max iterations. Please try again with more specific query!"

class AgentState(ChatAgentState):
    next: str
    iterations: int
    
def create_agent_workflow(
    model_config: mlflow.models.ModelConfig
) -> CompiledStateGraph:
    
    llm = ChatDatabricks(
        endpoint=model_config.get("llm_endpoint_name"),
        extra_params=model_config.get("llm_parameters"),
    )
    tools = [
        create_vector_search_tool(model_config)
    ]
    llm_with_tools = llm.bind_tools(tools)

    workers = [
        worker
        for worker in model_config.get("agents").keys()
        if (worker not in ("supervisor",))
    ]
    WorkerOptions = Enum("WorkerOptions", {opt: opt for opt in workers})

    class Router(TypedDict):
        """Agent to route to next. If no agents needed, route to response_agent."""
        observation: str
        action: str
        next: WorkerOptions = pydantic.Field(description="worker to route to next") # type: ignore


    def supervisor_agent_node(state: AgentState):
        if state.get("iterations", 0) > model_config.get("agents_max_iterations"):
            return {"next": "RECURSION_LIMIT"}

        messages = [
            {
                "role": "system",
                "content": model_config.get("agents").get("supervisor").get("system_prompt"),
            },
        ] + state["messages"]

        response = llm.with_structured_output(Router, include_raw=True).invoke(messages)

        return {
            "next": response.get("parsed").get("next"),
            "iterations": state.get("iterations", 0) + 1,
        }

    def unstructured_agent_node(state: AgentState):
        messages = [
            {
                "role": "system",
                "content": model_config.get("agents").get("unstructured_agent").get("system_prompt")
            },
        ] + state["messages"]

        response = llm_with_tools.invoke(messages)

        if response.content:
            response.content = f"<name>Unstructured Agent</name>\n{response.content}"


        return {
            "iterations": state.get("iterations", 0) + 1,
            "messages": [response]
        }
    
    def structured_agent_node(state: AgentState):
        response = get_genie_agent(model_config).invoke({"messages": state["messages"]}).get("messages")

        return {
            "iterations": state.get("iterations", 0) + 1,
            "messages": [
                {
                    "role": "assistant",
                    "content": f"<name>Structured Agent</name>\n{response[0].content} \n\n {response[-1].content}",
                    "name": "structured_agent",
                }
            ]
        }
    
    def response_agent_node(state: AgentState):
        messages = [
            {
                "role": "system",
                "content": model_config.get("agents").get("response_agent").get("system_prompt"),
            },
        ] + state["messages"]

        response = llm.invoke(messages)

        return {
            "iterations": state.get("iterations", 0) + 1,
            "messages": [
                {
                    "role": "assistant",
                    "content": f"<name>Response Agent</name>\n{response.content}",
                    "name": "response_agent",
                }
            ]
        }

    def iteration_limit_node(state: AgentState):
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": MAX_ITERATION_MESSAGE,
                    "name": "unknown",
                }
            ]
        }

    # Define the function that determines which node to go to
    def should_continue(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.get("tool_calls"):
            return "continue"
        else:
            return "done"

    workflow = StateGraph(AgentState)

    workflow.add_node("supervisor", supervisor_agent_node)
    workflow.add_node("structured_agent", structured_agent_node)
    workflow.add_node("unstructured_agent", unstructured_agent_node)
    workflow.add_node("unstructured_agent_tools", ChatAgentToolNode(tools))
    workflow.add_node("response_agent", response_agent_node)
    workflow.add_node("iteration_limit", iteration_limit_node)

    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        lambda x: x["next"],
        {
            **{opt: opt for opt in workers},
            "RECURSION_LIMIT": "iteration_limit"
        },
    )
    workflow.add_edge("structured_agent", "supervisor")
    workflow.add_conditional_edges(
        "unstructured_agent",
        should_continue,
        {
            "continue": "unstructured_agent_tools",
            "done": "supervisor",
        },
    )
    workflow.add_edge("unstructured_agent_tools", 
    "unstructured_agent")
    workflow.add_edge("iteration_limit", END)
    workflow.add_edge("response_agent", END)

    return workflow.compile()


class LangGraphAgent():
    def __init__(self, model_config):
        self.workflow = create_agent_workflow(model_config)

    def predict_stream(self, request):
        for event in self.workflow.stream(request, stream_mode=["updates", "messages"]):
            # print("event", event)
            if event[0] == "updates":
                # Stream response_agent response, send other as updates
                if "response_agent" in event[1]:
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
                    and metadata.get("langgraph_node") == "response_agent" # search internally calls llm so skip those
                    # and message.content
                ):
                    # Skip stream stop messages until last message.
                    # if not message.content:
                    #     if message.response_metadata.get("finish_reason") == "tool_calls":
                    #         continue
                    #     if message.response_metadata.get("finish_reason", None) is None:
                    #         continue
                    #     message.content = "\n"
                    message = message.dict()
                    message["role"] = "assistant"
                    yield ("messages", message)