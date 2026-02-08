from typing import Dict, Type

from implementations.llms.base_provider import BaseLLMProvider
from implementations.llms.openai_provider import OpenAIProvider
from implementations.llms.together_provider import TogetherProvider

PROVIDERS: Dict[str, Type[BaseLLMProvider]] = {
    "openai": OpenAIProvider,
    "together": TogetherProvider,
}


def get_llm_provider(provider_name: str, **kwargs) -> BaseLLMProvider:
    """
    Get an instance of an LLM provider.

    Args:
        provider_name: The name of the provider (e.g., 'openai', 'together').
        **kwargs: Arguments to pass to the provider constructor.

    Returns:
        An instance of the requested LLM provider.

    Raises:
        ValueError: If the provider is not supported.
    """
    provider_class = PROVIDERS.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unsupported LLM provider: {provider_name}")

    return provider_class(**kwargs)
