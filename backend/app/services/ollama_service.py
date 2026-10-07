"""
Ollama Service.
Handles HTTP communication with the local Ollama LLM server.
Completely decoupled from Manim and any rendering logic.
"""
import logging
from typing import Optional, Dict, Any, Union
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Base exception for Ollama service errors."""
    pass


class OllamaConnectionError(OllamaError):
    """Raised when connecting to Ollama server fails."""
    pass


class OllamaTimeoutError(OllamaError):
    """Raised when Ollama request times out."""
    pass


class OllamaResponseError(OllamaError):
    """Raised when Ollama returns an empty or invalid response."""
    pass


class OllamaService:
    """
    Clean client service for local Ollama LLM execution.
    Communicates via the Ollama HTTP REST API (/api/generate, /api/tags).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT

    def is_available(self, check_model: bool = True) -> bool:
        """
        Check if the local Ollama server is running and optionally verify
        that the configured model is installed.
        Does not raise exceptions; returns False on failure.
        """
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                if resp.status_code != 200:
                    return False

                if check_model:
                    data = resp.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    # Match exact model name or prefix (e.g. "qwen2.5:3b" or "qwen2.5:3b:latest")
                    model_found = any(
                        self.model == m or m.startswith(f"{self.model}:") or self.model in m
                        for m in models
                    )
                    return model_found

                return True
        except Exception as e:
            logger.debug(f"[LLM] Ollama health probe failed: {e}")
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        format: Optional[Union[str, Dict[str, Any]]] = None,
        temperature: float = 0.2,
        timeout: Optional[float] = None,
    ) -> str:
        """
        Send a generation request to the Ollama server.

        :param prompt: User or instruction prompt.
        :param system_prompt: Optional system persona and constraints.
        :param format: "json" or a JSON schema dictionary for structured output.
        :param temperature: Sampling temperature (default: 0.2).
        :param timeout: Request timeout in seconds (default: settings.OLLAMA_TIMEOUT).
        :return: Generated text response string.
        """
        req_timeout = timeout or self.timeout
        endpoint = f"{self.base_url}/api/generate"

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if system_prompt:
            payload["system"] = system_prompt

        if format is not None:
            payload["format"] = format

        logger.info(f"[LLM] Connecting to Ollama at {self.base_url}")
        logger.info(f"[LLM] Model: {self.model}")

        try:
            with httpx.Client(timeout=req_timeout) as client:
                response = client.post(endpoint, json=payload)
        except httpx.ConnectError as e:
            err_msg = (
                f"Failed to connect to Ollama at {self.base_url}. "
                "Ensure Ollama is running ('ollama serve')."
            )
            logger.warning(f"[LLM] {err_msg}: {e}")
            raise OllamaConnectionError(err_msg) from e
        except httpx.TimeoutException as e:
            err_msg = f"Ollama request timed out after {req_timeout}s for model '{self.model}'."
            logger.warning(f"[LLM] {err_msg}")
            raise OllamaTimeoutError(err_msg) from e
        except httpx.RequestError as e:
            err_msg = f"Network error during Ollama request: {str(e)}"
            logger.warning(f"[LLM] {err_msg}")
            raise OllamaConnectionError(err_msg) from e

        if response.status_code != 200:
            err_msg = f"Ollama API returned HTTP {response.status_code}: {response.text}"
            logger.warning(f"[LLM] {err_msg}")
            raise OllamaResponseError(err_msg)

        try:
            data = response.json()
        except Exception as e:
            err_msg = f"Ollama response was not valid JSON: {response.text[:200]}"
            logger.warning(f"[LLM] {err_msg}")
            raise OllamaResponseError(err_msg) from e

        generated_text = data.get("response", "")
        if not generated_text or not generated_text.strip():
            err_msg = "Ollama returned an empty response string."
            logger.warning(f"[LLM] {err_msg}")
            raise OllamaResponseError(err_msg)

        logger.info("[LLM] Response received")
        return generated_text.strip()


# Global default instance
ollama_service = OllamaService()
