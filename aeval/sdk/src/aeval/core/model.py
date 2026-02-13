"""Abstract Model interface for aeval."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ModelInfo:
    """Metadata about a model."""

    name: str
    family: str = ""
    parameter_size: str = ""
    quantization: str = ""
    multimodal: bool = False
    digest: str = ""


@dataclass
class GenerateResponse:
    """Response from a model generation call."""

    text: str
    model: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0
    metadata: dict = field(default_factory=dict)


class Model(ABC):
    """Abstract base class for model adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Model identifier."""
        ...

    @property
    @abstractmethod
    def info(self) -> ModelInfo:
        """Model metadata."""
        ...

    @abstractmethod
    def generate(
        self,
        prompts: list[str] | str,
        *,
        system: str | None = None,
        images: list[str | list[str]] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> list[GenerateResponse]:
        """Generate chat completions for one or more prompts.

        Args:
            prompts: Single prompt string or list of prompt strings.
            system: Optional system message.
            images: Optional images (file paths or base64) for multimodal models.
                    If list of lists, each inner list corresponds to a prompt.
            temperature: Sampling temperature (0.0 = deterministic).
            max_tokens: Maximum tokens to generate.

        Returns:
            List of GenerateResponse objects, one per prompt.
        """
        ...

    @abstractmethod
    def complete(
        self,
        prompts: list[str] | str,
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> list[GenerateResponse]:
        """Generate raw completions (non-chat) for one or more prompts.

        Args:
            prompts: Single prompt string or list of prompt strings.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            List of GenerateResponse objects, one per prompt.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the model backend is reachable and healthy."""
        ...

    @classmethod
    def from_ollama(cls, model_name: str, **kwargs) -> Model:
        """Create an Ollama model adapter.

        Args:
            model_name: Ollama model name (e.g., "llama3", "brain-analyst-ft").
            **kwargs: Additional config (host, timeout, keep_alive).
        """
        from aeval.adapters.ollama import OllamaModel

        return OllamaModel(model_name=model_name, **kwargs)
