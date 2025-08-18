from databricks_langchain.genie import GenieAgent

def get_genie_agent(model_config):
    # TODO Does not effectively handle conversation history, just dumps them in user message
    genie_agent = GenieAgent(
        genie_space_id=model_config.get("agents").get("structured_agent").get("genie_space_id"),
        genie_agent_name="structured_agent",
        description=model_config.get("agents").get("structured_agent").get("genie_agent_description"),
        include_context=True
    )
    return genie_agent
