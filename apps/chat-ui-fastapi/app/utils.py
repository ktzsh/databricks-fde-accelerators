from fastapi import HTTPException, status, Request
from typing import Dict
import os

class UserInfo:
    def __init__(self, user_id: str, email: str, name: str):
        self.user_id = user_id
        self.email = email
        self.name = name

def get_current_user_from_headers(request: Request) -> UserInfo:
    """
    Return a default user for anonymous access.
    No authentication required.
    """
    return UserInfo(
        user_id="anonymous_user",
        email="anonymous@example.com",
        name="Anonymous User"
    )

def get_env_variable(var_name: str, default_value: str = "") -> str:
    """
    Get environment variable value.
    """
    return os.getenv(var_name, default_value)

def get_agent_name() -> str:
    """
    Get the agent name from environment variables.
    """
    return get_env_variable("AGENT_NAME", "MyAgent")
