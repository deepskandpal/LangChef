"""Model-provider credentials — detection only, never handling.

Nothing in ``core`` ever reads a key's value. This module exists so that the
CLI and the CI guard agree on one list, and so a test can assert that no
credential is present in an environment that must not have one.
"""

import os

VARS: tuple[str, ...] = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "AWS_SECRET_ACCESS_KEY",
    "COHERE_API_KEY",
    "MISTRAL_API_KEY",
    "GROQ_API_KEY",
    "TOGETHER_API_KEY",
)


def present(environ: dict[str, str] | None = None) -> list[str]:
    """Names — never values — of provider credentials set in the environment."""
    env = os.environ if environ is None else environ
    return sorted(name for name in VARS if env.get(name))
