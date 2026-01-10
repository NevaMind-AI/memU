import logging
import os

from memu.llm.openai_sdk import OpenAISDKClient

logger = logging.getLogger(__name__)


class GeminiClient(OpenAISDKClient):
    """
    Gemini LLM client using Google's OpenAI-compatible API.

    Requires GEMINI_API_KEY environment variable if not provided explicitly.
    Base URL defaults to https://generativelanguage.googleapis.com/v1beta/openai/
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        chat_model: str = "gemini-2.0-flash-exp",
        embed_model: str = "text-embedding-004",
        embed_batch_size: int = 1,
    ):
        # Set defaults specific to Gemini if not provided
        if not base_url or base_url == "https://api.openai.com/v1":
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"

        if not api_key or api_key == "OPENAI_API_KEY":
            api_key = os.environ.get("GEMINI_API_KEY")

        if not api_key:
            logger.warning("GEMINI_API_KEY not found. Gemini calls may fail.")

        super().__init__(
            base_url=base_url,
            api_key=api_key or "",
            chat_model=chat_model,
            embed_model=embed_model,
            embed_batch_size=embed_batch_size,
        )

    # Gemini's OpenAI compatible endpoint should handle summarize, vision, and embed
    # via the parent OpenAISDKClient methods.
    # We can override here if we find specific discrepancies.
