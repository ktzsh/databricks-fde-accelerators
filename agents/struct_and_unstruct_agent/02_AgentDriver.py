# Databricks notebook source
# COMMAND ----------
# MAGIC %pip install -r requirements.txt
# MAGIC %restart_python

# COMMAND ----------
# MAGIC %reload_ext autoreload
# MAGIC %autoreload 2

# COMMAND ----------
import os
import yaml

config_file_path = os.path.join(os.getcwd(), "configs/config.yaml")
with open(config_file_path, "r") as f:
    config = yaml.safe_load(f)

# COMMAND ----------
from src.agent import agent

try:
    from IPython.display import Image
    display(Image(agent.program.workflow.get_graph().draw_mermaid_png()))
except Exception:
    pass

# COMMAND ----------
from src.agent import agent

input_example = {
    "input": [
        {
            "role": "user",
            "content": "What was the one-day price change and percent change due to the XBR press release in Q3 2025 and what were the reason behind it?"
        }
    ]
}
response = agent.predict(input_example)
print(response.output[-1].content[-1]['text'])

# COMMAND ----------
from src.agent import agent

input_example = {
    "input": [
        {
            "role": "user",
            "content": "What was the one-day price change and percent change due to the XBR press release in Q3 2025 and what were the reason behind it?"
        }
    ]
}
response = agent.predict_stream(input_example)
for event in response:
    print(event)

# COMMAND ----------
import os
import mlflow
from mlflow.models.resources import (
    DatabricksServingEndpoint,
    DatabricksVectorSearchIndex,
    DatabricksGenieSpace,
    DatabricksSQLWarehouse,
    DatabricksTable
)

from src.agent import agent

run_info = None

with open("requirements.txt", "r") as file:
    pip_requirements = [line.strip() for line in file.readlines()]

databricks_resources = [
    DatabricksVectorSearchIndex(
        index_name=f"{config['catalog_name']}.{config['schema_name']}.{config['vector_index_table_name']}"
    ),
    DatabricksServingEndpoint(
        endpoint_name=config.get("llm_endpoint_name")
    ),
    DatabricksServingEndpoint(
        endpoint_name=config.get("embedding_endpoint_name")
    ),
    DatabricksGenieSpace(
        genie_space_id=config.get("agents").get("structured_agent").get("genie_space_id")
    ),
    DatabricksSQLWarehouse(
        warehouse_id=config.get("warehouse_id")
    ),
    *[
        DatabricksTable(
            table_name=f"{config['catalog_name']}.{config['schema_name']}.{data_table}",
        )
        for data_table in ["companies", "financials", "daily_prices"]
    ]
]

# Log the model to MLflow

agent_model_name = f"{config.get('catalog_name')}.{config.get('schema_name')}.{config.get('agent_model_name')}"

mlflow.set_registry_uri("databricks-uc")
with mlflow.start_run() as run:
    run_info = run.info
    logged_chain_info = mlflow.pyfunc.log_model(
        python_model=os.path.join(
            os.getcwd(), f"{agent.__module__.replace('.', '/')}.py"),
        model_config=f"configs/config.yaml",
        name="model",
        input_example=config.get("agent_input_example"),
        registered_model_name=f"{agent_model_name}_{config.get('agent_backend')}",
        resources=databricks_resources,
        extra_pip_requirements=pip_requirements,
        code_paths=[os.path.join(os.getcwd(), "src")]
    )

uc_registered_model_info = mlflow.register_model(
    model_uri=logged_chain_info.model_uri, name=f"{agent_model_name}_{config.get('agent_backend')}"
)

# COMMAND ----------
import os
from databricks import agents

agent_model_name = f"{config.get('catalog_name')}.{config.get('schema_name')}.{config.get('agent_model_name')}"

deployment_info = agents.deploy(
    model_name=f"{agent_model_name}_{config.get('agent_backend')}",
    model_version=uc_registered_model_info.version,
    scale_to_zero=config.get("agent_scale_to_zero"),
    endpoint_name=f"{config.get('agent_endpoint_name_prefix')}"
)
 
print(f"App URL: {deployment_info.review_app_url}")
 