import json
import mlflow

from typing import Any, List, Optional, Type
from pydantic import BaseModel, Field

from mlflow.entities import Document
from langchain_core.tools import BaseTool
from langchain_core.callbacks.manager import CallbackManagerForToolRun

from databricks.sdk import WorkspaceClient
from databricks.vector_search.client import VectorSearchClient


def create_vector_search_tool(agent_config):
    tool_name = (
        agent_config
        .get("agents")
        .get("unstructured_agent")
        .get("tools")
        .get("vector_search_tool")
        .get("tool_name")
    )
    tool_description = (
        agent_config
        .get("agents")
        .get("unstructured_agent")
        .get("tools")
        .get("vector_search_tool")
        .get("tool_description")
    )
    query_description = (
        agent_config
        .get("agents")
        .get("unstructured_agent")
        .get("tools")
        .get("vector_search_tool")
        .get("tool_arguments")
        .get("query_input_description")
    )

    class VectorSearchRetrieverInput(BaseModel):
        query: str = Field(description=query_description)

    # Note: It's important that every field has type hints. BaseTool is a
    # Pydantic class and not having type hints can lead to unexpected behavior.
    class VectorSearchRetrieverTool(BaseTool):
        name: str = Field(description=tool_name)
        description: str = Field(description=tool_description)
        args_schema: Type[BaseModel] = VectorSearchRetrieverInput
        return_direct: bool = True
        agent_config: mlflow.models.ModelConfig = None
        vs_client: VectorSearchClient = None

        def __init__(self, agent_config, *args, **kwargs):
            super().__init__(
                name=tool_name,
                description=tool_description,
                agent_config=agent_config,
                *args,
                **kwargs,
            )

            try:
                self.vs_client = VectorSearchClient()
            except Exception as e:
                # When running from an IDE via Databricks Connect
                w = WorkspaceClient()
                token = w.tokens.create(
                    comment=f"sdk-temp-token", lifetime_seconds=600
                ).token_value
                self.vs_client = VectorSearchClient(
                    workspace_url=w.config.host,
                    personal_access_token=token
                )

            mlflow.models.set_retriever_schema(
                primary_key=agent_config.get(
                    "vector_search_index_primary_key_column"
                ),
                text_column=agent_config.get(
                    "vector_search_index_text_column"
                ),
                doc_uri=agent_config.get(
                    "vector_search_index_doc_uri_column"
                ),
            )

        @mlflow.trace(span_type="PARSER")
        def parse_vector_search_results(self, vs_results) -> List[Document]:
            column_names = []
            for column in vs_results["manifest"]["columns"]:
                column_names.append(column)

            docs = []
            if vs_results["result"]["row_count"] > 0:
                for item in vs_results["result"]["data_array"]:

                    info = {}
                    for i, field in enumerate(item[0:-1]):
                        info[column_names[i]["name"]] = field

                    if not info["content"].strip():
                        continue

                    docs.append(
                        {
                            "id": info["id"],
                            "doc_uri": info["doc_uri"],
                            "content": info["content"],
                            "score": info["score"],
                            "metadata": info["metadata"]
                        }
                    )

            return docs

        @mlflow.trace(span_type="RETRIEVER")
        def retrieve_facts(self, query: str) -> List[Document]:
            """Retrieve relevant facts from the vector search index."""
            index = self.vs_client.get_index(
                endpoint_name=agent_config.get("vector_endpoint_name"),
                index_name=f"{agent_config.get('catalog_name')}.{agent_config.get('schema_name')}.{agent_config.get('vector_index_table_name')}"
            )
            results = index.similarity_search(
                query_text=query,
                **agent_config.get("vector_search_parameters")
            )

            documents = self.parse_vector_search_results(results)

            return [
                Document(
                    id=doc["id"],
                    page_content=doc["content"],
                    metadata={
                        "score": doc["score"],
                        "doc_uri": doc["doc_uri"],
                    }
                ) for doc in documents
            ]

        def _run(
                self,
                query: str,
                run_manager: Optional[CallbackManagerForToolRun] = None,
            ) -> str:
                results = self.retrieve_facts(query)
                
                response = {}
                for i, fact in enumerate(results):
                    response[f"fact_{i + 1}"] = fact.page_content
                return json.dumps(response, indent=2)

        def __call__(
            self,
            query: str,
            run_manager: Optional[CallbackManagerForToolRun] = None,
        ) -> List[Document]:
            return self._run(query, run_manager)

    return VectorSearchRetrieverTool(agent_config)