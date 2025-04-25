"""
Exceptions for the OpenAI Assistant Client module.
"""

class AssistantClientError(Exception):
    """Base exception for the assistant client module."""
    pass


class ConfigError(AssistantClientError):
    """Error related to configuration issues."""
    pass


class AssistantError(AssistantClientError):
    """Error related to assistant operations."""
    pass


class ThreadError(AssistantClientError):
    """Error related to thread operations."""
    pass


class RunError(AssistantClientError):
    """Error related to run operations."""
    pass 