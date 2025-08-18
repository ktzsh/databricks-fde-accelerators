import os
import json
import mlflow

from uuid import uuid4
from typing import Any, Callable, Generator, Optional, Dict

from databricks.sdk import WorkspaceClient
from mlflow.entities import SpanType
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)

from src.agent_impl.langgraph import LangGraphAgent

mlflow.langchain.autolog()


class ToolCallingAgent(ResponsesAgent):
    """
    Class representing a tool-calling Agent
    """

    def __init__(self, model_config: mlflow.models.ModelConfig):
        if model_config.get("agent_backend") == "langgraph":
            self.program = LangGraphAgent(model_config)
        elif model_config.get("agent_backend") == "dspy":
            raise NotImplementedError
        else:
            raise NotImplementedError("Unsupported backend type")

    def convert_to_chat_completion_format(self, message: dict[str, Any]) -> dict[str, Any]:
        """Convert from Responses API to be compatible with a ChatCompletions LLM endpoint"""
        msg_type = message.get("type", None)
        if msg_type == "function_call":
            return [
                {
                    "role": "assistant",
                    "content": "tool call",
                    "tool_calls": [
                        {
                            "id": message["call_id"],
                            "type": "function",
                            "function": {
                                "arguments": message["arguments"],
                                "name": message["name"],
                            },
                        }
                    ],
                }
            ]
        elif msg_type == "message" and isinstance(message["content"], list):
            return [
                {"role": message["role"], "content": content["text"]}
                for content in message["content"]
            ]
        elif msg_type == "function_call_output":
            return [
                {
                    "role": "tool",
                    "content": message["output"],
                    "tool_call_id": message["call_id"],
                }
            ]
        compatible_keys = ["role", "content", "name", "tool_calls", "tool_call_id"]
        if not message.get("content") and message.get("tool_calls"):
            message["content"] = "tool call"
        filtered = {k: v for k, v in message.items() if k in compatible_keys}
        return [filtered] if filtered else []

    def prepare_messages_for_llm(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter out message fields that are not compatible with LLM message formats and convert from Responses API to ChatCompletion compatible"""
        chat_msgs = []
        for msg in messages:
            chat_msgs.extend(self.convert_to_chat_completion_format(msg))
        return chat_msgs

    @mlflow.trace(span_type=SpanType.PARSER)
    def _langchain_to_responses(self, message: dict[str, Any]) -> dict[str, Any]:
        role = message["role"]
        if role == "assistant":
            if tool_calls := message.get("tool_calls"):
                output_items = []
                if message.get("content", "").strip():
                    output_items.append(
                        self.create_text_output_item(
                            text=message["content"],
                            id=message.get("id") or str(uuid4()),
                        )
                    )
                for tool_call in tool_calls:
                    output_items.append(
                        self.create_function_call_item(
                            id=message.get("id") or str(uuid4()),
                            call_id=tool_call["id"],
                            name=tool_call["function"]["name"],
                            arguments=json.dumps(tool_call["function"]["arguments"]),
                        )
                    )
                return output_items
            else:
                return [
                    self.create_text_output_item(
                        text=message["content"],
                        id=message.get("id") or str(uuid4()),
                    )
                ]
        elif role == "tool":
            return [
                self.create_function_call_output_item(
                    call_id=message["tool_call_id"],
                    output=message["content"],
                )
            ]
        elif role == "human":
            return [message]
        
    @mlflow.trace(span_type=SpanType.AGENT)
    def _langchain_predict_stream(
            self, inputs: Dict[str, Any]
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        for event_type, event in self.program.predict_stream(inputs):
            if event_type == "updates":
                for item in self._langchain_to_responses(event):
                    yield ResponsesAgentStreamEvent(
                        type="response.output_item.done",
                        item=item
                    )
            elif event_type == "messages":
                yield ResponsesAgentStreamEvent(
                    **self.create_text_delta(delta=event["content"], item_id=event["id"]),
                )

    @mlflow.trace(span_type=SpanType.AGENT)
    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        inputs = {
            "messages": self.prepare_messages_for_llm([i.model_dump() for i in request.input]),
        }
        for event in self._langchain_predict_stream(inputs):
            yield event
    
    @mlflow.trace(span_type=SpanType.AGENT)
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        outputs = []
        stream_encountered = False
        # TODO Combine stream
        for event in self.predict_stream(request):
            if event.type == "response.output_item.done":
                outputs.append(event.item)
                stream_encountered = False
            elif event.type == "response.output_text.delta":
                if not stream_encountered:
                    outputs.append(
                        self.create_text_output_item(
                            text=event.delta,
                            id=event.item_id or str(uuid4()),
                        )
                    )
                    stream_encountered = True
                else:
                    outputs[-1]["content"][-1]["text"] += event.delta
        return ResponsesAgentResponse(output=outputs, custom_outputs=request.custom_inputs)
        

# specify config path
model_config = mlflow.models.ModelConfig(
    development_config=f"{os.getcwd()}/configs/config.yaml"
)

# Log the model using MLflow
agent = ToolCallingAgent(model_config=model_config)
mlflow.models.set_model(agent)