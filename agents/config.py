"""Agent and model configuration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    """Configuration for an OpenRouter model."""

    id: str  # OpenRouter model ID
    label: str  # Human-readable short name
    tier: str  # "weak", "medium", "strong"
    max_tokens: int = 8192
    temperature: float = 0.2
    response_timeout: float = 120.0  # Max seconds to wait for a single LLM response


# Models chosen to show clear capability differences:
# - Weak:   small model, limited reasoning
# - Medium: solid open-source model
# - Strong: top-tier commercial model
# - Additional frontier models for broader comparison
MODELS: dict[str, ModelConfig] = {
    "medium": ModelConfig(
        id="meta-llama/llama-3.3-70b-instruct",
        label="Llama 3.3 70B",
        tier="weak",
        temperature=0.2,
    ),
    "claude-opus": ModelConfig(
        id="anthropic/claude-opus-4.6",
        label="Claude Opus 4.6",
        tier="strong",
        temperature=0.1,
        max_tokens=8192,
        response_timeout=150.0,  # Reasoning model, allow a bit more time
    ),
    "kimi": ModelConfig(
        id="moonshotai/kimi-k2.5",
        label="Kimi K2.5",
        tier="strong",
        temperature=0.1,
        max_tokens=8192,
    ),
    "gpt": ModelConfig(
        id="openai/gpt-5.2-codex",
        label="GPT-5.2 Codex",
        tier="strong",
        temperature=0.1,
        max_tokens=8192,
    ),
    "minimax": ModelConfig(
        id="minimax/minimax-m2.5",
        label="MiniMax M2.5",
        tier="strong",
        temperature=0.1,
        max_tokens=8192,
    ),
    "glm": ModelConfig(
        id="z-ai/glm-5",
        label="GLM 5",
        tier="strong",
        temperature=0.1,
        max_tokens=8192,
    ),
    "claude-sonnet": ModelConfig(
        id="anthropic/claude-sonnet-4.6",
        label="Claude Sonnet 4.6",
        tier="strong",
        temperature=0.1,
        max_tokens=8192,
    ),
    "gemini-3.1": ModelConfig(
        id="google/gemini-3.1-pro-preview",
        label="Gemini 3.1 Pro",
        tier="strong",
        temperature=0.1,
        max_tokens=8192,
    ),
    "deepseek": ModelConfig(
        id="deepseek/deepseek-v3.2",
        label="DeepSeek V3.2",
        tier="strong",
        temperature=0.1,
        max_tokens=8192,
    ),
    "grok": ModelConfig(
        id="x-ai/grok-4.1-fast",
        label="Grok 4.1 Fast",
        tier="strong",
        temperature=0.1,
        max_tokens=8192,
    ),
    "trinity": ModelConfig(
        id="arcee-ai/trinity-large-preview:free",
        label="Trinity Large",
        tier="strong",
        temperature=0.1,
        max_tokens=8192,
    ),
}


def get_model(tier: str) -> ModelConfig:
    """Get model config by tier name."""
    if tier not in MODELS:
        raise ValueError(f"Unknown model tier: {tier}. Choose from: {list(MODELS.keys())}")
    return MODELS[tier]


def list_models() -> list[ModelConfig]:
    """Return all configured models."""
    return list(MODELS.values())
