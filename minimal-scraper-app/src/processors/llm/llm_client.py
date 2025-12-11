"""
LLM client abstraction for multiple providers (OpenAI, DeepSeek, etc.).

Provides a unified interface for LLM calls with config-driven provider selection.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from src.common.logging_utils import get_logger

log = get_logger("llm-client")


class LLMClient:
    """Unified LLM client supporting multiple providers."""

    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
        base_url: Optional[str] = None,
    ) -> None:
        """
        Initialize LLM client.

        Args:
            provider: Provider name ('openai', 'deepseek', 'anthropic', etc.)
            model: Model name (e.g., 'gpt-4o-mini', 'deepseek-chat')
            api_key: API key (if None, reads from env)
            max_tokens: Maximum tokens in response
            temperature: Temperature (0.0 = deterministic)
            base_url: Custom base URL (for compatible APIs)
        """
        self.provider = provider.lower()
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.base_url = base_url

        # Get API key
        if api_key:
            self.api_key = api_key
        else:
            key_env = {
                "openai": "OPENAI_API_KEY",
                "deepseek": "DEEPSEEK_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "groq": "GROQ_API_KEY",
            }.get(self.provider, "OPENAI_API_KEY")
            self.api_key = os.getenv(key_env, "")

        if not self.api_key:
            log.warning(
                f"LLM client initialized without API key for provider {self.provider}. "
                "LLM calls will fail."
            )

    def _get_openai_client(self):
        """Get OpenAI client."""
        try:
            from openai import OpenAI  # type: ignore[import]

            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            return OpenAI(**client_kwargs)
        except ImportError:
            raise RuntimeError("openai package not installed. Install with: pip install openai")

    def _get_deepseek_client(self):
        """Get DeepSeek client (OpenAI-compatible)."""
        try:
            from openai import OpenAI  # type: ignore[import]

            return OpenAI(
                api_key=self.api_key,
                base_url=self.base_url or "https://api.deepseek.com",
            )
        except ImportError:
            raise RuntimeError("openai package not installed. Install with: pip install openai")

    def _get_groq_client(self):
        """Get Groq client."""
        try:
            from groq import Groq  # type: ignore[import]
        except ImportError as exc:  # pragma: no cover - optional dependency not installed
            raise RuntimeError("groq package not installed. Install with: pip install groq") from exc

        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        return Groq(**client_kwargs)

    def _get_client(self):
        """Get appropriate client for provider."""
        if self.provider == "openai":
            return self._get_openai_client()
        elif self.provider == "deepseek":
            return self._get_deepseek_client()
        elif self.provider == "groq":
            return self._get_groq_client()
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Complete a prompt and return text response.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Override default max_tokens
            temperature: Override default temperature

        Returns:
            Generated text
        """
        if not self.api_key:
            raise RuntimeError(f"API key not configured for provider {self.provider}")

        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature if temperature is not None else self.temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            log.error("LLM completion failed", extra={"provider": self.provider, "error": str(exc)})
            raise

    def extract_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any] | List[Dict[str, Any]]:
        """
        Extract structured JSON from prompt.

        Args:
            prompt: User prompt with data to extract
            system_prompt: Optional system prompt
            schema: Optional JSON schema (for structured output)

        Returns:
            Parsed JSON (dict or list)
        """
        import json

        # Enhance prompt to request JSON
        json_prompt = f"{prompt}\n\nReturn only valid JSON, no markdown, no explanation."
        if schema:
            json_prompt += f"\n\nSchema: {json.dumps(schema, indent=2)}"

        response = self.complete(json_prompt, system_prompt=system_prompt)
        
        # Try to extract JSON from response
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as exc:
            log.error("Failed to parse LLM JSON response", extra={"response": response[:200]})
            raise ValueError(f"Invalid JSON from LLM: {exc}") from exc


def get_llm_client_from_config(config: Dict[str, Any]) -> Optional[LLMClient]:
    """
    Create LLM client from source config.

    Args:
        config: Source config dict with 'llm' section

    Returns:
        LLMClient instance or None if LLM disabled
    """
    llm_config = config.get("llm", {})
    
    if not llm_config.get("enabled", False):
        return None

    provider = llm_config.get("provider", "openai")
    model = llm_config.get("model", "gpt-4o-mini")
    max_tokens = llm_config.get("max_tokens", 2048)
    temperature = llm_config.get("temperature", 0.0)
    base_url = llm_config.get("base_url")

    return LLMClient(
        provider=provider,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        base_url=base_url,
    )

