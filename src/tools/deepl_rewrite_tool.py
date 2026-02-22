import logging
import os

import requests

DEEPL_FALLBACK_PROMPT = (
    "Rewrite the following academic text to improve clarity and academic tone. "
    "Keep the original meaning. Be concise. Maximum 500 words total. "
    "Return only the rewritten text, no explanations:"
)


async def rewrite_text(text: str) -> str:
    """Rewrite text using DeepL API, with Claude as fallback."""
    api_key = os.getenv("DEEPL_API_KEY", "")
    if api_key:
        try:
            return _rewrite_with_deepl(text, api_key)
        except Exception as e:
            logging.warning(f"DeepL failed ({e}), using Claude fallback")

    logging.info("DeepL unavailable, using Claude fallback")
    return await _rewrite_with_claude(text)


def _rewrite_with_deepl(text: str, api_key: str) -> str:
    response = requests.post(
        "https://api.deepl.com/v2/translate",
        headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
        json={
            "text": [text],
            "target_lang": "EN-US",
            "source_lang": "EN",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["translations"][0]["text"]


async def _rewrite_with_claude(text: str) -> str:
    from claude_code_sdk import ClaudeCodeOptions, query

    prompt = f"{DEEPL_FALLBACK_PROMPT}\n\n{text}"
    result_parts = []

    async for message in query(
        prompt=prompt,
        options=ClaudeCodeOptions(model="claude-haiku-4-5-20251001", max_turns=1),
    ):
        if hasattr(message, "content"):
            for block in message.content:
                if hasattr(block, "text"):
                    result_parts.append(block.text)

    return "".join(result_parts).strip() or text
