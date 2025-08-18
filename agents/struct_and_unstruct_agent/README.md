# RAG Agent (Structured + Unstructured)

- Structured data includes information about imaginary listed companies, their quaterly financial metrics and daily prices (few dates) from period Jan 1 2025 to Jan 1 2026.
- The Unstructured data includes information from press releases, shareholder letters and analyst notes.

## Target Questions
- What was the one-day price change and percent change due to the XBR press release in Q3 2025 and what were the reason behind it?
- Which company had the highest quarter-over-quarter revenue growth in Q3 2025 and what was its stock closing price on the announcement date?
- After WWebServices announced its Q2 2025 earnings on June 30, 2025, by how much did its stock price change compared to the previous trading day?

## Deploying Agent

### Approach 1 (Managed MCP Servers)
- Update the data related fields and `warehouse_id` in `config.yaml`.
- Run the `01_IngestionDriver` to create Genie Room and Vector Search Index on your data.
- Use AI Playground Managed MCP Servers to combine Genie and Vector Search Index as tools to an LLM of your choice.
- Export Notebook (Currently not supported from AI Playground).


### Approach 2 (Custom Multi-Agent Approach)
- Update the data related fields and `warehouse_id` in `config.yaml`.
- Run the `01_IngestionDriver` to create Genie Space and VS index on your data.
- Update the `genie_space_id` in the config.yaml
- Run the `02_AgentDriver` to deploy the multi-agent supervisor agent.
- Use Review App to test.


### Approach 3 (AI Agents Tiles)
- Update the data related fields and `warehouse_id` in `config.yaml`.
- Run the `01_IngestionDriver` to create Genie Space and VS index on your data.
- Create a KA Assitant from AI Agents tiles using VS Index.
    - Get descriptions and prompts from config.yaml where required.
- Creata a Multi-Agent Supervisor from AI Agent tiles using KA Assistant Endpoint and Genie Space.
    - Get descriptions and prompts from config.yaml where required.


NOTE: Quality depends on metadata, system prompt used as well as the instructions specified in Genie Space. This was tested with without optimizing any of these parameters.

