"""
LLM Client Utilities for Diet Insight Engine

This module provides utilities for creating and managing LLM clients,
with support for OpenRouter (DeepSeek) as primary and OpenAI as fallback.
Includes LangSmith tracing for observability and full Hydra integration.
"""

import logging
import os

from dotenv import load_dotenv

# Load environment variables from .env at import time
load_dotenv()
from typing import Any, Dict, Optional, Union

from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.tracers import LangChainTracer
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# Import LangSmith wrapper for full tracing
try:
    from langsmith import wrappers as langsmith_wrappers

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False

from diet.utils.config_manager import get_config_manager


class LLMClientManager:
    """Manages LLM clients with fallback and tracing capabilities."""

    def __init__(self, config_override: Optional[Dict[str, Any]] = None):
        from omegaconf import DictConfig, OmegaConf

        config_manager = get_config_manager()
        if config_override is not None:
            if not isinstance(config_override, DictConfig):
                self.config = OmegaConf.create(config_override)
            else:
                self.config = config_override
        else:
            self.config = config_manager.config
        self.settings = config_manager.settings
        self.logger = logging.getLogger("die.llm_client")

        # Get LLM configurations from Hydra config
        self.openrouter_config = config_manager.get_llm_config("openrouter")
        self.openai_config = config_manager.get_llm_config("openai")
        self.langsmith_config = config_manager.get_api_config("langsmith")

        # Setup LangSmith tracing if configured
        self.callback_manager = self._setup_tracing()

        # Initialize clients
        self._primary_client = None
        self._fallback_client = None

        # Cache for different client configurations
        self._client_cache = {}

    def _setup_tracing(self) -> Optional[CallbackManager]:
        """Setup LangSmith tracing if configured."""
        try:
            if (
                self.langsmith_config.get("tracing_enabled", False)
                and self.settings.langchain_api_key
                and self.settings.langchain_project
            ):

                # Configure LangSmith environment
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
                os.environ["LANGCHAIN_API_KEY"] = self.settings.langchain_api_key
                os.environ["LANGCHAIN_PROJECT"] = self.settings.langchain_project
                os.environ["LANGCHAIN_ENDPOINT"] = self.settings.langchain_endpoint

                tracer = LangChainTracer(project_name=self.settings.langchain_project)
                callback_manager = CallbackManager([tracer])

                self.logger.info("✅ LangSmith tracing enabled")
                return callback_manager
            else:
                self.logger.info(
                    "LangSmith tracing not configured - missing credentials or disabled"
                )
                return None

        except Exception as e:
            self.logger.warning(f"Failed to setup LangSmith tracing: {e}")
            return None

    def get_primary_client(self, model_override: Optional[str] = None) -> BaseChatModel:
        """Get the primary LLM client (OpenRouter/DeepSeek)."""
        cache_key = f"primary_{model_override or 'default'}"

        if cache_key not in self._client_cache:
            if self.settings.openrouter_api_key:
                self._client_cache[cache_key] = self._create_openrouter_client(model_override)
            else:
                self.logger.warning(
                    "OpenRouter API key not available, using OpenAI as primary client"
                )
                if self.settings.openai_api_key:
                    self._client_cache[cache_key] = self._create_openai_client(model_override)
                else:
                    raise ValueError("No API keys available for LLM clients")

        return self._client_cache[cache_key]

    def get_fallback_client(self, model_override: Optional[str] = None) -> Optional[BaseChatModel]:
        """Get the fallback LLM client (OpenAI)."""
        cache_key = f"fallback_{model_override or 'default'}"

        if cache_key not in self._client_cache and self.settings.openai_api_key:
            self._client_cache[cache_key] = self._create_openai_client(
                model_override, is_fallback=True
            )

        return self._client_cache.get(cache_key)

    def _create_openrouter_client(self, model_override: Optional[str] = None) -> ChatOpenAI:
        """Create OpenRouter client for DeepSeek."""
        if not self.settings.openrouter_api_key:
            raise ValueError("OpenRouter API key is required")

        try:
            # Use model override or config model or fallback to settings
            model = (
                model_override
                or self.openrouter_config.get("model")
                or self.settings.openrouter_model
            )

            # Prepare extra headers for OpenRouter
            extra_headers = self.openrouter_config.get("extra_headers", {})
            if not extra_headers.get("HTTP-Referer"):
                extra_headers["HTTP-Referer"] = "https://syntropyhealth.ai"
            if not extra_headers.get("X-Title"):
                extra_headers["X-Title"] = "SyntropyHealth Diet Insight Engine"

            from pydantic import SecretStr

            client = ChatOpenAI(
                model=model,
                api_key=(
                    SecretStr(self.settings.openrouter_api_key)
                    if self.settings.openrouter_api_key
                    else None
                ),
                base_url=self.openrouter_config.get("base_url", self.settings.openrouter_base_url),
                temperature=self.openrouter_config.get("temperature", 0.1),
                max_tokens=self.openrouter_config.get("max_tokens", 4000),
                timeout=self.openrouter_config.get("request_timeout", 60),
                max_retries=self.openrouter_config.get("max_retries", 3),
                model_kwargs={
                    "extra_headers": extra_headers,
                },
                streaming=True,
            )

            # Apply LangSmith wrapper for full tracing if available
            if LANGSMITH_AVAILABLE and self.callback_manager:
                try:
                    client = langsmith_wrappers.wrap_openai(client)
                    self.logger.debug("Applied LangSmith wrapper to OpenRouter client")
                except Exception as e:
                    self.logger.warning(f"Failed to apply LangSmith wrapper: {e}")

            self.logger.info(f"✅ OpenRouter client created with model: {model}")
            return client

        except Exception as e:
            self.logger.error(f"Failed to create OpenRouter client: {e}")
            raise

    def _create_openai_client(
        self, model_override: Optional[str] = None, is_fallback: bool = False
    ) -> ChatOpenAI:
        """Create OpenAI fallback client."""
        try:
            # Use model override or config model or fallback
            if model_override:
                model = model_override
            elif is_fallback and self.openai_config.get("fallback", {}).get("model"):
                model = self.openai_config["fallback"]["model"]
            else:
                model = self.openai_config.get("model", "gpt-4")

            from pydantic import SecretStr

            client = ChatOpenAI(
                model=model,
                api_key=(
                    SecretStr(self.settings.openai_api_key)
                    if self.settings.openai_api_key
                    else None
                ),
                temperature=self.openai_config.get("temperature", 0.1),
                max_tokens=self.openai_config.get("max_tokens", 4000),
                timeout=self.openai_config.get("request_timeout", 60),
                max_retries=self.openai_config.get("max_retries", 3),
                streaming=True,
            )

            # Apply LangSmith wrapper for full tracing if available
            if LANGSMITH_AVAILABLE and self.callback_manager:
                try:
                    client = langsmith_wrappers.wrap_openai(client)
                    self.logger.debug("Applied LangSmith wrapper to OpenAI client")
                except Exception as e:
                    self.logger.warning(f"Failed to apply LangSmith wrapper: {e}")

            client_type = "fallback" if is_fallback else "primary"
            self.logger.info(f"✅ OpenAI {client_type} client created with model: {model}")
            return client

        except Exception as e:
            self.logger.error(f"Failed to create OpenAI client: {e}")
            raise

    def get_client(
        self, use_fallback: bool = False, model_override: Optional[str] = None
    ) -> BaseChatModel:
        """
        Get an LLM client with fallback capability.

        Args:
            use_fallback: If True, use fallback client directly
            model_override: Optional model name to override config

        Returns:
            BaseChatModel: LLM client instance
        """
        if use_fallback:
            fallback = self.get_fallback_client(model_override)
            if fallback:
                return fallback
            else:
                self.logger.warning("Fallback client not available, using primary client")
                return self.get_primary_client(model_override)
        else:
            return self.get_primary_client(model_override)

    def invoke_with_fallback(self, messages: list, max_attempts: int = 2, **kwargs) -> str:
        """
        Invoke LLM with automatic fallback on failure.

        Args:
            messages: List of messages to send
            max_attempts: Maximum number of attempts (primary + fallback)
            **kwargs: Additional arguments for the LLM

        Returns:
            str: Response content
        """
        last_error = None

        for attempt in range(max_attempts):
            try:
                use_fallback = attempt > 0
                client = self.get_client(use_fallback=use_fallback)

                client_name = "fallback" if use_fallback else "primary"
                self.logger.debug(f"Attempt {attempt + 1}: Using {client_name} client")

                response = client.invoke(messages, **kwargs)

                self.logger.info(f"✅ LLM call successful with {client_name} client")

                # Handle different response types
                if hasattr(response, "content"):
                    return str(response.content)
                else:
                    return str(response)

            except Exception as e:
                last_error = e
                client_name = "fallback" if use_fallback else "primary"
                self.logger.warning(f"LLM call failed with {client_name} client: {e}")

                if attempt == max_attempts - 1:
                    self.logger.error(f"All LLM attempts failed. Last error: {e}")
                    raise e
                else:
                    self.logger.info(f"Retrying with next client...")

        # This shouldn't be reached, but just in case
        raise last_error or Exception("Unknown error in LLM invocation")


# Global instance
_llm_manager = None


def get_llm_manager(config_override: Optional[Dict[str, Any]] = None) -> LLMClientManager:
    """Get global LLM manager instance."""
    global _llm_manager
    if _llm_manager is None or config_override is not None:
        _llm_manager = LLMClientManager(config_override)
    return _llm_manager


def get_llm_client(
    use_fallback: bool = False,
    model_override: Optional[str] = None,
    config_override: Optional[Dict[str, Any]] = None,
) -> BaseChatModel:
    """Get LLM client with fallback capability."""
    manager = get_llm_manager(config_override)
    return manager.get_client(use_fallback=use_fallback, model_override=model_override)


def invoke_llm_with_fallback(
    messages: list, config_override: Optional[Dict[str, Any]] = None, **kwargs
) -> str:
    """Invoke LLM with automatic fallback."""
    manager = get_llm_manager(config_override)
    return manager.invoke_with_fallback(messages, **kwargs)


def create_llm_client_from_config(
    config: Dict[str, Any], step_name: Optional[str] = None
) -> BaseChatModel:
    """
    Create an LLM client from a specific configuration.

    This is useful for LangGraph nodes that need specific model configurations
    for different steps in the pipeline.

    Args:
        config: Configuration dictionary for the client
        step_name: Optional step name for logging

    Returns:
        Configured LLM client
    """
    manager = get_llm_manager(config)

    # Determine if we should use fallback based on config
    use_fallback = config.get("use_fallback", False)
    model_override = config.get("model_override")

    if step_name:
        logger = logging.getLogger("die.llm_client")
        logger.info(f"Creating LLM client for step: {step_name}")

    return manager.get_client(use_fallback=use_fallback, model_override=model_override)
