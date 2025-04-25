"""
OpenAI Assistant Client module.

This module provides a centralized interface for working with OpenAI assistants.
"""

from .api_assistants_cliente import OpenAIAssistantClient
from .config_manager import load_assistant_config

__all__ = ['OpenAIAssistantClient', 'load_assistant_config']
