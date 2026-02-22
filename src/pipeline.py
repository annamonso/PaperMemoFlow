import asyncio
import json
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import CHUNK_MODEL, CHUNK_OVERLAP, CHUNK_SIZE, MAIN_MODEL


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _query_claude(prompt: str, model: str, retries: int = 3) -> str:
    """Run a single-turn Claude query and return the full text response.

    Retries automatically on rate-limit events (the installed SDK version
    surfaces these as MessageParseError instead of handling them internally).
    """
    from claude_code_sdk import ClaudeCodeOptions, query

    for attempt in range(retries):
        try:
            parts = []
            async for message in query(
                prompt=prompt,
                options=ClaudeCodeOptions(model=model, max_turns=1),
            ):
                if hasattr(message, "content"):
                    for block in message.content:
                        if hasattr(block, "text"):
                            parts.append(block.text)
            return "".join(parts).strip()

        except Exception as e:
            is_rate_limit = "rate_limit" in str(e).lower()
            if is_rate_limit and attempt < retries - 1:
                wait = 60 * (attempt + 1)
                logging.warning(
                    f"Rate limited — waiting {wait}s before retry "
                    f"{attempt + 2}/{retries}..."
                )
                await asyncio.sleep(wait)
            else:
                raise

    return ""


def _extract_json(text: str) -> dict:
    """Extract a JSON object from Claude's response (handles markdown fences)."""
    # Strip common markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find the outermost {...} block
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from Claude response:\n{text[:400]}")


def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i : i + CHUNK_SIZE]
        chunks.append(" ".join(chunk_words))
        if i + CHUNK_SIZE >= len(words):
            break
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_JSON_SCHEMA = """\
{
  "title": "string",
  "summary": "string (1-2 paragraphs, max 150 words)",
  "contributions": [{"label": "string", "text": "string"}],
  "limitations": [{"label": "string", "text": "string"}],
  "question": "string"
}"""

_JSON_RULES = """\
Rules:
- contributions: 2 to 4 items
- limitations: 1 to 3 items
- Total words across summary + contributions + limitations + question: max 500
- Return ONLY valid JSON — no markdown, no code fences, no explanations"""


def _build_summary_prompt(text: str, filename: str) -> str:
    return f"""You are an academic paper summarizer.

Analyze the following paper and return a structured JSON summary with this exact schema:
{_JSON_SCHEMA}

The "title" should be the actual paper title if detectable, otherwise use "{filename}".
{_JSON_RULES}

Paper text:
{text}"""


def _build_chunk_prompt(chunk: str, chunk_num: int, total: int) -> str:
    return f"""Summarize portion {chunk_num}/{total} of an academic paper.
Extract the main points, any contributions mentioned, and any limitations mentioned.
Return a concise paragraph of at most 100 words.
Return ONLY the summary text, no labels or JSON.

Text:
{chunk}"""


def _build_consolidation_prompt(summaries: str, filename: str) -> str:
    return f"""You are an academic paper summarizer.
The following are partial summaries of consecutive chunks from a long academic paper.

Consolidate them into a single structured JSON summary with this exact schema:
{_JSON_SCHEMA}

The "title" should be the actual paper title if detectable, otherwise use "{filename}".
{_JSON_RULES}

Partial summaries:
{summaries}"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_pipeline(text: str, filename: str) -> dict:
    """
    Process extracted PDF text and return a structured dict:
        {title, summary, contributions, limitations, question}
    Uses MAIN_MODEL for the final pass and CHUNK_MODEL for intermediate chunks.
    """
    word_count = len(text.split())

    if word_count > CHUNK_SIZE:
        logging.info(f"Text exceeds {CHUNK_SIZE} words ({word_count}), chunking...")
        chunks = _chunk_text(text)
        logging.info(f"Split into {len(chunks)} chunks")

        # Summarise each chunk sequentially to avoid rate limits
        chunk_summaries = []
        for i, c in enumerate(chunks):
            logging.info(f"Summarising chunk {i + 1}/{len(chunks)}...")
            summary = await _query_claude(
                _build_chunk_prompt(c, i + 1, len(chunks)), CHUNK_MODEL
            )
            chunk_summaries.append(summary)

        consolidated = "\n\n".join(chunk_summaries)
        logging.info("Consolidating chunk summaries with main model...")
        response = await _query_claude(
            _build_consolidation_prompt(consolidated, filename), MAIN_MODEL
        )
    else:
        response = await _query_claude(_build_summary_prompt(text, filename), MAIN_MODEL)

    logging.info("Summary generated")
    data = _extract_json(response)
    return data
