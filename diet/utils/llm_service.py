"""
Integrated LLM Service for Diet Insight Engine

This module provides LangGraph-compatible step execution with LLM calls,
integrating with Hydra configuration and the existing LLM client infrastructure.
"""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, TypeVar, Union

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel

from diet.models.shared import IntermediateStep, PipelineState, StepStatus
from diet.utils.config_manager import get_config_manager

from .llm_client import get_llm_manager

# Type variable for generic model parsing
T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger("die.llm_service")


class LLMStepExecutor:
    """Executes LLM-based pipeline steps with error handling and state management."""

    def __init__(self, config: Optional[Any] = None, project_name: str = "diet-insight-engine"):
        """Initialize with optional config override and project name for tracing."""
        from omegaconf import DictConfig, OmegaConf

        config_manager = get_config_manager()
        # Always convert config to DictConfig for dot-access and OmegaConf compatibility
        if config is not None:
            if isinstance(config, DictConfig):
                self.config = config
            elif isinstance(config, dict):
                self.config = OmegaConf.create(config)
            elif isinstance(config, str):
                # If config is a string, it's likely a config group name or invalid YAML
                logger.warning(f"LLMStepExecutor received string config ('{config}'). Using default config instead.")
                self.config = config_manager.config
            else:
                raise ValueError("Unsupported config type for LLMStepExecutor")
        else:
            self.config = config_manager.config
        self.llm_manager = get_llm_manager()
        self.logger = logging.getLogger("die.llm_service.executor")
        self.project_name = project_name

        # Set up LangSmith tracing if enabled in config
        self._setup_langsmith_tracing()

    def _setup_langsmith_tracing(self):
        """Set up LangSmith tracing for LLM calls."""
        try:
            import os

            # Check if LangSmith is enabled in config
            # OmegaConf DictConfig supports .get, but fallback to getattr for compatibility
            # Always use getattr for OmegaConf DictConfig or fallback to dict .get
            if isinstance(self.config, dict):
                langsmith_config = self.config.get("langsmith", {})
            else:
                # OmegaConf DictConfig: use getattr, never .get for string keys
                langsmith_config = getattr(self.config, "langsmith", {})
            if langsmith_config.get("enabled", False):
                # Set environment variables for LangSmith
                api_key = langsmith_config.get("api_key") or os.getenv("LANGCHAIN_API_KEY")
                if api_key:
                    os.environ["LANGCHAIN_TRACING_V2"] = "true"
                    os.environ["LANGCHAIN_API_KEY"] = api_key
                    os.environ["LANGCHAIN_PROJECT"] = f"{self.project_name}-pipeline"

                    self.logger.info(
                        "LangSmith tracing enabled for project: %s-pipeline", self.project_name
                    )
                else:
                    self.logger.warning("LangSmith enabled in config but no API key found")
            else:
                self.logger.debug("LangSmith tracing disabled in config")

        except ImportError:
            self.logger.warning("LangSmith not installed, tracing disabled")
        except (KeyError, AttributeError, ValueError, TypeError) as e:
            self.logger.error("Failed to setup LangSmith tracing: %s", e)

    async def execute_step(
        self,
        state: Optional[PipelineState],
        step_name: str,
        prompt_template: str,
        input_variables: Dict[str, Any],
        parser: Optional[PydanticOutputParser[T]] = None,
        system_prompt: Optional[str] = None,
        dependencies: Optional[Dict[str, str]] = None,
        use_fallback: bool = False,
        **llm_kwargs,
    ) -> Optional[Union[T, Dict[str, Any], str]]:
        """
        Execute an LLM-based step with comprehensive error handling.

        Args:
            state: Pipeline state to track step execution
            step_name: Name of the step being executed
            prompt_template: Template string for the prompt
            input_variables: Variables to substitute in the template
            parser: Optional Pydantic parser for structured output
            system_prompt: Optional system prompt
            dependencies: Optional dependencies to check before execution
            use_fallback: Whether to use fallback LLM client
            **llm_kwargs: Additional arguments for LLM invocation

        Returns:
            Parsed result or None if failed
        """
        # Create and track step
        step = IntermediateStep(
            step_name=step_name,
            status=StepStatus.RUNNING,
            start_time=datetime.now(),
            input_data=input_variables.copy(),
        )

        if state:
            state.intermediate_steps.append(step)

        try:
            # Check dependencies
            if dependencies and state:
                for dep_name, error_msg in dependencies.items():
                    if not getattr(state, dep_name, None):
                        step.fail(error_msg)
                        if state:
                            state.error = error_msg
                        return None

            # Get system prompt from config if not provided
            if not system_prompt:
                system_prompt = self._get_system_prompt()

            # Create and format prompt
            prompt = PromptTemplate(
                template=prompt_template, input_variables=list(input_variables.keys())
            )

            # Add format instructions if parser provided
            if parser:
                input_variables = input_variables.copy()
                input_variables["format_instructions"] = parser.get_format_instructions()

            formatted_prompt = prompt.format(**input_variables)

            # Prepare messages
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=formatted_prompt))

            # Execute LLM call with fallback
            try:
                # Log input for debugging
                self.logger.info("Executing LLM step: %s", step_name)
                self.logger.debug("Input variables: %s", input_variables)
                self.logger.debug("Formatted prompt: %s", formatted_prompt)

                response_content = self.llm_manager.invoke_with_fallback(
                    messages=messages, max_attempts=2 if not use_fallback else 1, **llm_kwargs
                )

                # Log output for debugging
                self.logger.debug("LLM response: %s", response_content)

            except Exception as llm_error:
                self.logger.error("LLM call failed for step %s: %s", step_name, llm_error)
                step.fail(f"LLM call failed: {str(llm_error)}")
                return None

            # Parse response if parser provided
            if parser:
                result = await self._parse_response(response_content, parser, step, state)
            else:
                result = response_content
                # Store raw output in context
                if state:
                    if step_name not in state.context:
                        state.context[step_name] = []
                    state.context[step_name].append(response_content)

            # Complete step
            step.complete(
                output_data={"result_type": type(result).__name__, "has_content": bool(result)}
            )

            self.logger.info("Step %s completed successfully", step_name)
            return result

        except (KeyError, AttributeError, ValueError, TypeError) as e:
            self.logger.error("Error in step %s: %s", step_name, str(e))
            self.logger.error(traceback.format_exc())
            step.fail(str(e))
            if state:
                state.error = f"Error in {step_name}: {str(e)}"
            return None

    async def _parse_response(
        self,
        response_content: str,
        parser: PydanticOutputParser[T],
        step: IntermediateStep,
        state: Optional[PipelineState],
    ) -> Optional[T]:
        """Parse LLM response with fallback strategies."""
        try:
            # First attempt: direct parsing
            result = parser.parse(response_content)
            self.logger.debug("Successfully parsed response on first attempt")
            return result

        except (KeyError, AttributeError, ValueError, TypeError) as parse_error:
            self.logger.warning("Direct parsing failed: %s", parse_error)
            self.logger.debug("Raw output: %s", response_content)

            # Fallback: JSON extraction and repair
            try:
                from diet.utils.json_utils import extract_json_from_text, repair_json

                json_data, raw_text = extract_json_from_text(response_content)

                # Store raw text in context
                if state and raw_text:
                    step_name = step.step_name
                    if step_name not in state.context:
                        state.context[step_name] = []
                    state.context[step_name].append(raw_text)

                if json_data:
                    # Try creating model from extracted JSON
                    model_class = parser.pydantic_object
                    result = model_class(**json_data)
                    self.logger.info(
                        "Successfully created %s from extracted JSON", model_class.__name__
                    )
                    return result
                else:
                    # Try JSON repair
                    repaired_json = repair_json(response_content)
                    if repaired_json:
                        model_class = parser.pydantic_object
                        result = model_class(**repaired_json)
                        self.logger.info(
                            "Successfully created %s from repaired JSON", model_class.__name__
                        )
                        return result

            except (KeyError, AttributeError, ValueError, TypeError) as extraction_error:
                self.logger.error("JSON extraction/repair failed: %s", extraction_error)

            # Final fallback: return None and log error
            error_msg = f"All parsing attempts failed. Original error: {parse_error}"
            self.logger.error(error_msg)
            step.error = error_msg
            return None

    def _get_system_prompt(self) -> str:
        """Get system prompt from configuration."""
        try:
            # Try to get from prompts config
            if type(self.config) is dict:
                prompts_config = self.config.get("prompts", {})
            else:
                prompts_config = getattr(self.config, "prompts", {})
            if isinstance(prompts_config, dict):
                return prompts_config.get("system", "")
            return ""
        except (KeyError, AttributeError, ValueError, TypeError):
            return ""


# Singleton instance
_step_executor = None


def get_step_executor(
    config: Optional[Dict[str, Any]] = None, project_name: str = "diet-insight-engine"
) -> LLMStepExecutor:
    """Get or create singleton step executor instance."""
    global _step_executor
    from omegaconf import DictConfig
    def is_valid_config(cfg):
        return isinstance(cfg, (DictConfig, dict))

    # If config is a string, log and use default
    if isinstance(config, str):
        import logging
        logger = logging.getLogger("die.llm_service.executor")
        logger.warning(f"get_step_executor received string config ('{config}'). Using default config instead.")
        config = None

    # If singleton is missing or has an invalid config, re-create
    if (
        _step_executor is None
        or config is not None
        or not hasattr(_step_executor, "config")
        or not is_valid_config(_step_executor.config)
    ):
        _step_executor = LLMStepExecutor(config, project_name)
    return _step_executor


async def execute_llm_step(
    state: Optional[PipelineState],
    step_name: str,
    prompt_template: str,
    input_variables: Dict[str, Any],
    parser: Optional[PydanticOutputParser[T]] = None,
    system_prompt: Optional[str] = None,
    dependencies: Optional[Dict[str, str]] = None,
    use_fallback: bool = False,
    project_name: str = "diet-insight-engine",
    **llm_kwargs,
) -> Optional[Union[T, Dict[str, Any], str]]:
    """
    Convenience function to execute an LLM step.

    This is the main entry point for LangGraph nodes that need to make LLM calls. It takes prompts, input strings, pydantic parsers, and return structured data in the form of a pydantic model type variable
    """
    executor = get_step_executor(project_name=project_name)
    return await executor.execute_step(
        state=state,
        step_name=step_name,
        prompt_template=prompt_template,
        input_variables=input_variables,
        parser=parser,
        system_prompt=system_prompt,
        dependencies=dependencies,
        use_fallback=use_fallback,
        **llm_kwargs,
    )
