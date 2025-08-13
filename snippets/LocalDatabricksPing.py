# Databricks notebook source
# COMMAND ----------
# MAGIC %pip install mlflow

# COMMAND ----------
from mlflow.deployments import get_deploy_client

client = get_deploy_client(f"databricks")
response = client.predict(
    endpoint="databricks-gpt-oss-20b",
    inputs={
        "messages": [
            {"role": "user", "content": "Hello, how are you?"},
        ]
    }
)
print(response)
