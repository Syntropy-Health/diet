"""
Hydra Configuration Manager

This module provides utilities for managing Hydra configurations across
the Diet Insight Engine and Amazon Store Agent pipelines.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import hydra
from hydra import compose, initialize_config_dir
from hydra.core.global_hydra import GlobalHydra
from omegaconf import DictConfig, OmegaConf


class ConfigManager:
    """Manages Hydra configuration for the entire pipeline."""

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the configuration manager.

        Args:
            config_dir: Path to configuration directory. If None, uses default.
        """
        if config_dir is None:
            # Use the config directory at the project root (diet-insight-engine/config)
            config_dir = str(Path(__file__).parent.parent.parent / "config")

        self.config_dir = Path(config_dir).absolute()
        self._config: Optional[DictConfig] = None
        self._initialized = False

    def initialize(self, config_name: str = "config") -> None:
        """Initialize Hydra with the specified configuration."""
        if not self._initialized:
            # Clear any existing Hydra instance
            GlobalHydra.instance().clear()

            # Initialize with our config directory
            initialize_config_dir(config_dir=str(self.config_dir), version_base=None)
            self._initialized = True

        # Compose the configuration
        self._config = compose(config_name=config_name)

    @property
    def config(self) -> DictConfig:
        """Get the current configuration as an OmegaConf object."""
        if self._config is None:
            self.initialize()
        # Ensure config is always an OmegaConf DictConfig
        if not isinstance(self._config, DictConfig):
            self._config = OmegaConf.create(self._config)
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        return OmegaConf.select(self.config, key, default=default)

    def get_diet_insight_config(self) -> DictConfig:
        """Get Diet Insight Engine specific configuration."""
        return self.config.diet

    def get_amazon_store_config(self) -> DictConfig:
        """Get Amazon Store Agent specific configuration."""
        return self.config.amazon_store_agent

    def get_prompts_config(self) -> DictConfig:
        """Get prompts configuration from llm.prompts."""
        return self.config.llm.prompts

    def get_prompt_template(self, component: str, prompt_type: str) -> str:
        """
        Get a specific prompt template from llm.prompts.<prompt_type> (flat) or llm.prompts.<component>.<prompt_type> (nested).

        Args:
            component: Component name (e.g., 'symptom_diet_solver')
            prompt_type: Prompt type (e.g., 'journal_parsing')

        Returns:
            Prompt template string
        """
        prompts = self.get_prompts_config()
        # For symptom_diet_solver, use flat structure
        if component == "symptom_diet_solver":
            if prompt_type in prompts:
                return prompts[prompt_type]
        # Fallback to nested structure for other components
        if component in prompts and prompt_type in prompts[component]:
            return prompts[component][prompt_type]
        return ""

    def format_prompt(self, component: str, prompt_type: str, **kwargs) -> str:
        """
        Format a prompt template with the provided arguments.

        Args:
            component: Component name
            prompt_type: Prompt type
            **kwargs: Template variables

        Returns:
            Formatted prompt string
        """
        template = self.get_prompt_template(component, prompt_type)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing template variable {e} for {component}.{prompt_type}")

    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values."""
        if self._config is None:
            self.initialize()

        # Merge updates into existing config
        update_config = OmegaConf.create(updates)
        self._config = OmegaConf.merge(self._config, update_config)

    def save_config(self, path: str) -> None:
        """Save current configuration to a file."""
        if self._config is None:
            raise ValueError("No configuration loaded")

        OmegaConf.save(self._config, path)

    def load_config_from_file(self, path: str) -> DictConfig:
        """Load configuration from a specific file."""
        return OmegaConf.load(path)

    def validate_config(self) -> bool:
        """Validate the current configuration."""
        try:
            # Check if basic configuration exists
            if self._config is None:
                self.initialize()

            # Validate environment variables are set
            env_vars = ["OPENAI_API_KEY"]
            for var in env_vars:
                if not os.getenv(var):
                    print(f"Warning: Missing environment variable: {var}")

            return True

        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False

    def get_model_config(self, component: str, model_type: str = "default") -> Dict[str, Any]:
        """
        Get model configuration for a specific component.

        Args:
            component: Component name ('diet' or 'amazon_store_agent')
            model_type: Model type (e.g., 'journal_parser', 'search_engine')

        Returns:
            Model configuration dictionary
        """
        if component == "diet":
            base_config = self.get_diet_insight_config()
            if model_type in base_config:
                return OmegaConf.to_container(base_config[model_type], resolve=True)
        elif component == "amazon_store_agent":
            base_config = self.get_amazon_store_config()
            if model_type in base_config:
                return OmegaConf.to_container(base_config[model_type], resolve=True)

        # Fallback to global model settings
        return OmegaConf.to_container(self.config.models, resolve=True)

    def get_llm_config(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Get LLM configuration for a specific provider or default.

        Args:
            provider: Provider name ('openrouter', 'openai', etc.) or None for default

        Returns:
            LLM configuration dictionary
        """
        llm_config = self.config.get("llm", {})

        if provider and provider in llm_config:
            return OmegaConf.to_container(llm_config[provider], resolve=True)

        # Return default LLM config
        return OmegaConf.to_container(llm_config, resolve=True)

    def get_api_config(self, api_name: str) -> Dict[str, Any]:
        """
        Get API configuration for services like LangSmith.

        Args:
            api_name: API service name ('langsmith', etc.)

        Returns:
            API configuration dictionary
        """
        api_config = self.config.get("api", {})

        if api_name in api_config:
            return OmegaConf.to_container(api_config[api_name], resolve=True)

        return {}

    @property
    def settings(self) -> "ConfigSettings":
        """Get settings wrapper for easy access to common config values."""
        return ConfigSettings(self)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._initialized:
            GlobalHydra.instance().clear()
            self._initialized = False


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


class ConfigSettings:
    """Settings wrapper for easy access to common configuration values."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

    @property
    def openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from environment."""
        return os.getenv("OPENAI_API_KEY")

    @property
    def openrouter_api_key(self) -> Optional[str]:
        """Get OpenRouter API key from environment."""
        return os.getenv("OPENROUTER_API_KEY")

    @property
    def langchain_api_key(self) -> Optional[str]:
        """Get LangChain API key from environment."""
        return os.getenv("LANGCHAIN_API_KEY")

    @property
    def langchain_project(self) -> str:
        """Get LangChain project name."""
        return os.getenv(
            "LANGCHAIN_PROJECT",
            self.config_manager.get_api_config("langsmith").get("project", "diet-insight-engine"),
        )

    @property
    def langchain_endpoint(self) -> str:
        """Get LangChain endpoint."""
        return os.getenv(
            "LANGCHAIN_ENDPOINT",
            self.config_manager.get_api_config("langsmith").get(
                "endpoint", "https://api.smith.langchain.com"
            ),
        )

    @property
    def openrouter_model(self) -> str:
        """Get default OpenRouter model."""
        return self.config_manager.get_llm_config("openrouter").get(
            "model", "deepseek/deepseek-chat"
        )

    @property
    def openrouter_base_url(self) -> str:
        """Get OpenRouter base URL."""
        return self.config_manager.get_llm_config("openrouter").get(
            "base_url", "https://openrouter.ai/api/v1"
        )

    @property
    def openai_model(self) -> str:
        """Get default OpenAI model."""
        return self.config_manager.get_llm_config("openai").get("model", "gpt-4")

    @property
    def default_provider(self) -> str:
        """Get default LLM provider."""
        return self.config_manager.get_llm_config().get("provider", "openrouter")


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> DictConfig:
    """Get the current configuration."""
    return get_config_manager().config


def get_prompt_template(component: str, prompt_type: str) -> str:
    """Get a prompt template."""
    return get_config_manager().get_prompt_template(component, prompt_type)


def format_prompt(component: str, prompt_type: str, **kwargs) -> str:
    """Format a prompt template."""
    return get_config_manager().format_prompt(component, prompt_type, **kwargs)
