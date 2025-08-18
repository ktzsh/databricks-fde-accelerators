# Databricks notebook source
# MAGIC %pip install databricks-langchain

# COMMAND ----------

import base64

from databricks_langchain import ChatDatabricks

with open("../artifacts/databricks.png", "rb") as image_file:
    binary_data = image_file.read()
    image_data = base64.b64encode(binary_data).decode('utf-8')

messages = [
    {
        "role": "system",
        "content": "You are a helpful assistant."
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "What is this image about?"
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_data}"}
            }
        ]
    }
]

# TODO enable guardrails on these
llm = ChatDatabricks(endpoint="databricks-llama-4-maverick")

print(llm.invoke(messages).content)