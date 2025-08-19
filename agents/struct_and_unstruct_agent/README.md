# RAG Agent (Structured + Unstructured)

## Problem Description
Stock investors often need to combine structured data (e.g., daily prices, quarterly financials, divdends & splits) with unstructured data (e.g., press releases, analyst notes, shareholder letters) to understand market movements and investment opportunities. This project demonstrates a multi-agent RAG system that integrates structured (sql-like) and unstructured (vector-search-based) retrievals to answer queries that span both domains.

## Dataset Description
Structured Data
- Includes information about 4 fictional companies: WWebServices, XBricks, YFlake, and ZSoft
- Data covers the period Jan 1, 2025 – Jan 1, 2026
- Tables include:
    - companies (tickers, names)
    - financials (quarterly metrics)
    - daily_prices (closing prices, daily changes)

Unstructured Data
- Includes press releases, shareholder letters, and analyst notes for the same companies
- Stored in a vector search index for semantic retrieval

## Target Questions
- What was the one-day price change and percent change due to the XBR press release in Q3 2025 and what were the reason behind it?
- Which company had the highest quarter-over-quarter revenue growth in Q3 2025 and what was its stock closing price on the announcement date?
- After WWebServices announced its Q2 2025 earnings on June 30, 2025, by how much did its stock price change compared to the previous trading day?

## Deploying Agent

For local development (IDE) modify databricks.yml from example by adding your targets.

### Approach 1 (Managed MCP Servers)
- Update the data related fields and `warehouse_id` in `configs/config.yaml`.
- Run the `01_IngestionDriver` to create Genie Room and Vector Search Index on your data.
- Use AI Playground Managed MCP Servers to combine Genie and Vector Search Index as tools to an LLM of your choice.
OR
- Update `agent_backend` to 'mcp' in `configs/config.yaml`.
- Add `managed_server_urls` in agents section in `configs/config.yaml`
- Run the `02_AgentDriver` to deploy the mcp agent.


### Approach 2 (Custom Multi-Agent Approach)
- Update the data related fields and `warehouse_id` in `configs/config.yaml`.
- Run the `01_IngestionDriver` to create Genie Space and VS index on your data.
- Update the `genie_space_id` in the config.yaml
- Run the `02_AgentDriver` to deploy the multi-agent supervisor agent.
- Use Review App to test.


### Approach 3 (AI Agents Tiles)
- Update the data related fields and `warehouse_id` in `configs/config.yaml`.
- Run the `01_IngestionDriver` to create Genie Space and VS index on your data.
- Create a KA Assitant from AI Agents tiles using VS Index.
    - Get descriptions and prompts from config.yaml where required.
- Creata a Multi-Agent Supervisor from AI Agent tiles using KA Assistant Endpoint and Genie Space.
    - Get descriptions and prompts from config.yaml where required.


NOTE: Quality depends on metadata, system prompt used as well as the instructions specified in Genie Space. This was tested with without optimizing any of these parameters.

