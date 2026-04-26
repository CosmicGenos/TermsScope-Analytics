from __future__ import annotations

# Maps model name prefixes to tiktoken encoding names.
# Claude and Gemini have no native tiktoken encoding; cl100k_base is the
# closest approximation for token-budget purposes.
_MODEL_TOKENIZER_MAP: dict[str, str] = {
    "gpt-4o":          "o200k_base",
    "gpt-4o-mini":     "o200k_base",
    "gpt-4-turbo":     "cl100k_base",
    "gpt-4":           "cl100k_base",
    "gpt-3.5-turbo":   "cl100k_base",
    "claude-opus-4":   "cl100k_base",
    "claude-sonnet-4": "cl100k_base",
    "claude-haiku-4":  "cl100k_base",
    "claude-3":        "cl100k_base",
    "gemini-2.0":      "cl100k_base",
    "gemini-1.5":      "cl100k_base",
    "gemini-1.0":      "cl100k_base",
}


def get_tokenizer_for_model(model: str) -> str:
    """Return the tiktoken encoding name that best matches the given LLM model.

    Uses prefix matching so partial model IDs (e.g. "gpt-4o-mini-2024-07-18")
    are handled correctly.  Falls back to cl100k_base for unknown models.
    """
    model_lower = (model or "").lower()
    for prefix, encoding in _MODEL_TOKENIZER_MAP.items():
        if model_lower.startswith(prefix):
            return encoding
    return "cl100k_base"
