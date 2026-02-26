"""
JSON utilities for parsing and repairing LLM responses.

This module provides utilities for extracting and repairing JSON from
potentially malformed text responses from LLMs.
"""

import json
import logging
import re
from typing import Any, Dict, Optional, Tuple, Union

logger = logging.getLogger("die.json_utils")


def extract_json_from_text(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Extract JSON data from text that may contain other content.

    Args:
        text: Text that may contain JSON

    Returns:
        Tuple of (json_data, raw_text) where json_data is the parsed JSON
        and raw_text is the original text
    """
    if not text or not isinstance(text, str):
        return None, text

    # Try to find JSON blocks with various patterns
    json_patterns = [
        r"```json\s*(\{.*?\})\s*```",  # JSON in code blocks
        r"```\s*(\{.*?\})\s*```",  # JSON in generic code blocks
        r"(\{.*?\})",  # Just JSON objects
        r"\[.*?\]",  # JSON arrays
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, text, re.DOTALL | re.MULTILINE)
        for match in matches:
            try:
                json_data = json.loads(match)
                logger.debug(f"Successfully extracted JSON using pattern: {pattern}")
                return json_data, text
            except json.JSONDecodeError:
                continue

    # Try to extract the largest JSON-like structure
    try:
        # Find the first '{' and last '}'
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1 and end > start:
            potential_json = text[start : end + 1]
            json_data = json.loads(potential_json)
            logger.debug("Successfully extracted JSON from text boundaries")
            return json_data, text
    except json.JSONDecodeError:
        pass

    logger.warning("Could not extract valid JSON from text")
    return None, text


def repair_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to repair malformed JSON text.

    Args:
        text: Potentially malformed JSON text

    Returns:
        Parsed JSON data or None if irreparable
    """
    if not text or not isinstance(text, str):
        return None

    # Common JSON repair strategies
    repair_strategies = [
        # Fix missing quotes around keys
        lambda s: re.sub(r"(\w+)(?=\s*:)", r'"\1"', s),
        # Fix single quotes to double quotes
        lambda s: s.replace("'", '"'),
        # Fix trailing commas
        lambda s: re.sub(r",(\s*[}\]])", r"\1", s),
        # Fix escaped quotes
        lambda s: s.replace('\\"', '"'),
        # Remove comments
        lambda s: re.sub(r"//.*?$", "", s, flags=re.MULTILINE),
        # Fix unquoted string values
        lambda s: re.sub(r':\s*([^",\[\]{}]+)(?=\s*[,}])', r': "\1"', s),
    ]

    original_text = text.strip()

    # Try parsing as-is first
    try:
        return json.loads(original_text)
    except json.JSONDecodeError:
        pass

    # Apply repair strategies incrementally
    repaired_text = original_text
    for strategy in repair_strategies:
        try:
            repaired_text = strategy(repaired_text)
            json_data = json.loads(repaired_text)
            logger.info("Successfully repaired JSON")
            return json_data
        except (json.JSONDecodeError, Exception):
            continue

    # Last resort: try to extract just the JSON part
    json_data, _ = extract_json_from_text(repaired_text)
    return json_data


def safe_json_parse(text: str) -> Optional[Union[Dict[str, Any], list]]:
    """
    Safely parse JSON with multiple fallback strategies.

    Args:
        text: Text to parse as JSON

    Returns:
        Parsed JSON data or None if unparseable
    """
    if not text:
        return None

    # Try direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extraction
    json_data, _ = extract_json_from_text(text)
    if json_data:
        return json_data

    # Try repair
    repaired = repair_json(text)
    if repaired:
        return repaired

    logger.error(f"Could not parse JSON from text: {text[:100]}...")
    return None


def validate_json_schema(data: Dict[str, Any], required_fields: list) -> bool:
    """
    Validate that JSON data contains required fields.

    Args:
        data: JSON data to validate
        required_fields: List of required field names

    Returns:
        True if all required fields are present
    """
    if not isinstance(data, dict):
        return False

    for field in required_fields:
        if field not in data:
            logger.warning(f"Missing required field: {field}")
            return False

    return True


def clean_json_string(text: str) -> str:
    """
    Clean a string to make it more likely to parse as valid JSON.

    Args:
        text: Text to clean

    Returns:
        Cleaned text
    """
    if not text:
        return text

    # Remove common prefixes/suffixes
    text = text.strip()

    # Remove markdown code block markers
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)

    # Remove leading/trailing non-JSON characters
    text = text.strip(" \t\n\r")

    return text
