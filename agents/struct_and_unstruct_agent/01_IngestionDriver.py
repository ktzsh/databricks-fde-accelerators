# Databricks notebook source
# COMMAND ----------
# MAGIC %pip install mlflow pandas pdfplumber databricks-vectorsearch
# MAGIC %restart_python

# COMMAND ----------
import os
import yaml

config_file_path = os.path.join(os.getcwd(), "configs/config.yaml")
with open(config_file_path, "r") as f:
    config = yaml.safe_load(f)

# COMMAND ----------
# Prepare the catalog, schema, and volume before transfering data
spark.sql(
    f"CREATE SCHEMA IF NOT EXISTS {config['catalog_name']}.{config['schema_name']}"
)
spark.sql(
    f"CREATE VOLUME IF NOT EXISTS {config['catalog_name']}.{config['schema_name']}.{config['volume_name']}"
)

# COMMAND ----------
import os
import json
import pandas as pd

from pathlib import Path

data_dir = Path(os.getcwd()) / ".." / ".." /  "artifacts" / "data" / "structured"

with open(f"{data_dir}/metadata.json", "r") as f:
    metadata = json.load(f)

all_tables = []
for csv_file in data_dir.glob("*.csv"):
    table_name = f"{config['catalog_name']}.{config['schema_name']}.{csv_file.stem}" 

    print(f"Processing {csv_file.name} -> table `{table_name}`")
    df = pd.read_csv(csv_file)
    (
        spark.createDataFrame(df)
        .write
        .format("delta")
        .mode("overwrite")
        .saveAsTable(table_name)
    )

    all_tables.append(table_name)

    # add metadata to the spark table column description and table description
    spark.sql(f"""
        ALTER TABLE {table_name}
        SET TBLPROPERTIES (
            'comment' = '{metadata[csv_file.stem]["description"]}'
        )
    """)
    for column, description in metadata[csv_file.stem]["columns"].items():
        spark.sql(f"""
            ALTER TABLE {table_name}
            ALTER COLUMN `{column}` COMMENT '{description}'
        """)

# COMMAND ----------
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# TODO Unofficial, Unpublished API
# TODO Running multiple times will create multiple genie spaces
try:
    w.api_client.do(
        method="POST",
        path="/api/2.0/data-rooms",
        body={
            "display_name": "Personal Finance Demo",
            "warehouse_id": config["warehouse_id"],
            "table_identifiers": all_tables,
            "run_as_type": "VIEWER"
        }
    )
except Exception as e:
    print(f"Error creating data room: {e}")

# COMMAND ----------
import os
import json
import pandas as pd

from pathlib import Path

data_dir = Path(os.getcwd()) / ".." / ".." / "artifacts" / "data" / "unstructured"

pdf_files = []
for pdf_file in data_dir.glob("*.pdf"):
    with open(pdf_file, "rb") as f:
        pdf_content = f.read()
    pdf_files.append(
        {
            "content": pdf_content,
            "name": pdf_file.name,
            "path": str(pdf_file),
            "size": len(pdf_content),
        }
    )

# creaste a DataFrame from the list of dictionaries
df = pd.DataFrame(pdf_files)
display(df)

# COMMAND ----------
import io
import uuid
import pdfplumber

from pyspark.sql.functions import udf, explode, col
from pyspark.sql.types import ArrayType, StringType, StructType, StructField

try:
# For IDE / VSCode users using serverless, ensure pdfplumber is installed in the Databricks cluster
# https://docs.databricks.com/aws/en/dev-tools/databricks-connect/python/udf#udfs-with-dependencies
    from databricks.connect import DatabricksSession, DatabricksEnv
    env = DatabricksEnv().withDependencies("pdfplumber")
    spark = DatabricksSession.builder.withEnvironment(env).getOrCreate()
    print(f"Running in a local environment")
except Exception as e:
    print(f"Running in a Databricks environment")

def extract_chunks_from_pdf(pdf_bytes, chunk_size=1024):
    if pdf_bytes is None:
        return []
    
    try:
        # Read PDF from bytes
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        
        # Remove extra spaces/newlines
        full_text = " ".join(full_text.split())

        # Calculate step size for overlap (1/3 overlap means step = chunk_size - chunk_size/3)
        overlap = chunk_size * 2 // 3
        step = chunk_size - overlap

        # Create overlapping chunks
        chunks = []
        for i, start in enumerate(range(0, len(full_text), step)):
            chunk_text = full_text[start:start + chunk_size]
            if chunk_text:
                metadata = {
                    "chunk_index": i,
                    "source": "pdf_document"
                }
                chunks.append(
                    {"content": chunk_text, "metadata": str(metadata)}
                )
        
        return chunks
    
    except Exception as e:
        # Optional: log or return empty if parsing fails
        return ["Error parsing PDF: " + str(e)]

# Schema for array of structs
chunk_schema = ArrayType(
    StructType([
        StructField("content", StringType(), True),
        StructField("metadata", StringType(), True)
    ])
)
# Register UDF
extract_chunks_udf = udf(extract_chunks_from_pdf, chunk_schema)
generate_uuid = udf(lambda: str(uuid.uuid4()), StringType())

(
    spark.createDataFrame(pdf_files)
    .withColumn("chunks", explode(extract_chunks_udf("content")))
    .withColumn("id", generate_uuid())
    .select(
        col("id").alias("id"),
        col("name").alias("doc_name"),
        col("path").alias("doc_uri"),
        col("size").alias("size"),
        col("chunks.content").alias("content"),
        col("chunks.metadata").alias("metadata")
    )
    .write
    .format("delta")
    .mode("overwrite")
    .saveAsTable(
        f"{config['catalog_name']}.{config['schema_name']}.{config['processed_chunks_table_name']}"
    )
)

# Enable Change Data Feed (CDF) if not already enabled
cdf_check = spark.sql(f"""
    SHOW TBLPROPERTIES {config['catalog_name']}.{config['schema_name']}.{config['processed_chunks_table_name']}
""")
cdf_enabled = any(
    row['key'] == 'delta.enableChangeDataFeed' and row['value'] == 'true'
    for row in cdf_check.collect()
)
if not cdf_enabled:
    spark.sql(f"""
        ALTER TABLE {config['catalog_name']}.{config['schema_name']}.{config['processed_chunks_table_name']}
        SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
    """)

# COMMAND ----------
from databricks.vector_search.client import VectorSearchClient
from databricks.sdk import WorkspaceClient

# Initialize the Vector Search client
client = VectorSearchClient()
try:
    client = VectorSearchClient()
except Exception as e:
    # When running from an IDE via Databricks Connect
    w = WorkspaceClient()
    token = w.tokens.create(
        comment=f"sdk-temp-token", lifetime_seconds=600
    ).token_value
    client = VectorSearchClient(
        workspace_url=w.config.host,
        personal_access_token=token
    )

def endpoint_exists(client, endpoint_name):
    """Check if a vector search endpoint exists."""
    return endpoint_name in [
        ep["name"] for ep in client.list_endpoints().get("endpoints", [])
    ]

def index_exists(client, endpont_name, index_name):
    try:
        index = client.get_index(endpont_name, index_name)
    except Exception as e:
        if "RESOURCE_DOES_NOT_EXIST" in str(e):
            return False, None
        raise e
    return True, index

# Create a standard endpoint
try:
    if not endpoint_exists(client, config["vector_endpoint_name"]):
        client.create_endpoint_and_wait(
            name=config["vector_endpoint_name"],
            endpoint_type="STANDARD"
        )

    index_exists_bool, index = index_exists(
        client, 
        config["vector_endpoint_name"],
        f"{config['catalog_name']}.{config['schema_name']}.{config['vector_index_table_name']}"
    )
    if not index_exists_bool:
        index = client.create_delta_sync_index_and_wait(
            endpoint_name=config["vector_endpoint_name"],
            source_table_name=f"{config['catalog_name']}.{config['schema_name']}.{config['processed_chunks_table_name']}",
            index_name=f"{config['catalog_name']}.{config['schema_name']}.{config['vector_index_table_name']}",
            pipeline_type="TRIGGERED",  # or "CONTINUOUS"
            primary_key="id",
            embedding_source_column="content",
            embedding_model_endpoint_name=config["embedding_endpoint_name"],
        )
        print(f"Vector index created successfully: {index.name}")
    else:
        index.sync()
        print(f"Vector index synced successfully: {index.name}")
except Exception as e:
    print(f"Error creating vector index: {e}")
    # Handle the error as needed, e.g., log it or raise an exception

# COMMAND ----------
