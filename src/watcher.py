#!/usr/bin/env python3
"""
PaperAgent — entrypoint.
Watches ~/PapersInbox/ for new PDFs and processes them automatically.

Usage:
  python src/watcher.py                           # normal watch mode
  python src/watcher.py --dry-run /path/file.pdf  # process a single file
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path

# Make src/ importable regardless of cwd
sys.path.insert(0, str(Path(__file__).parent))

from config import IGNORE_EXTENSIONS, IGNORE_PREFIXES, PAPERS_INBOX, PAPERS_OUTBOX
from latex_writer import fill_template
from pipeline import run_pipeline
from tools.deepl_rewrite_tool import rewrite_text
from tools.latex_compile_tool import compile_latex
from tools.pdf_extract_tool import extract_text


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging() -> None:
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def is_temp_file(path: Path) -> bool:
    return (
        path.suffix.lower() in IGNORE_EXTENSIONS
        or path.name[0] in IGNORE_PREFIXES
    )


def wait_for_complete(path: Path, checks: int = 3, interval: float = 1.0) -> bool:
    """Block until the file size is stable across `checks` consecutive reads."""
    prev_size = -1
    stable = 0
    for _ in range(checks + 2):
        try:
            size = path.stat().st_size
        except OSError:
            return False
        if size > 0 and size == prev_size:
            stable += 1
            if stable >= checks:
                return True
        else:
            stable = 0
        prev_size = size
        time.sleep(interval)
    return False


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

async def process_pdf(pdf_path: Path) -> None:
    """Run the complete pipeline for a single PDF."""
    logging.info(f"New PDF detected: {pdf_path.name}")

    try:
        # 1. Extract text
        text = extract_text(pdf_path)
        word_count = len(text.split())
        logging.info(f"Text extracted: {word_count} words")

        # 2. Summarise & structure via claude-code-sdk
        data = await run_pipeline(text, pdf_path.stem)

        # 3. Rewrite summary with DeepL / Claude for academic polish
        original_summary = data.get("summary", "")
        rewritten_summary = await rewrite_text(original_summary)
        data["summary"] = rewritten_summary

        # 4. Fill LaTeX template
        tex_content = fill_template(data)

        # 5. Write .tex file
        PAPERS_OUTBOX.mkdir(parents=True, exist_ok=True)
        tex_path = PAPERS_OUTBOX / f"{pdf_path.stem}.tex"
        tex_path.write_text(tex_content, encoding="utf-8")
        logging.info(f"LaTeX written: {tex_path}")

        # 6. Compile to PDF (optional — requires latexmk)
        if compile_latex(tex_path):
            logging.info(f"PDF compiled: {tex_path.with_suffix('.pdf')}")

    except Exception as e:
        logging.error(f"Failed to process {pdf_path.name}: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Watcher
# ---------------------------------------------------------------------------

def start_watcher() -> None:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    class _Handler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            path = Path(event.src_path)
            if path.suffix.lower() != ".pdf":
                return
            if is_temp_file(path):
                logging.info(f"Ignored temp file: {path.name}")
                return
            if wait_for_complete(path):
                asyncio.run(process_pdf(path))
            else:
                logging.warning(f"File not stable after timeout: {path.name}")

    PAPERS_INBOX.mkdir(parents=True, exist_ok=True)
    PAPERS_OUTBOX.mkdir(parents=True, exist_ok=True)

    logging.info(f"Watching: {PAPERS_INBOX}")
    logging.info(f"Output:   {PAPERS_OUTBOX}")

    handler = _Handler()
    observer = Observer()
    observer.schedule(handler, str(PAPERS_INBOX), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping watcher...")
        observer.stop()
    observer.join()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _sanitize_env() -> None:
    """Clean os.environ before launching claude-code-sdk subprocesses.

    1. Remove vars with null bytes (cause _fork_exec to crash).
    2. Unset CLAUDECODE so the SDK's nested-session guard doesn't block us
       when PaperAgent is started from inside a Claude Code terminal.
    """
    bad_keys = [k for k, v in os.environ.items() if "\x00" in k or "\x00" in v]
    for k in bad_keys:
        logging.warning(f"Removing env var with null byte: {k!r}")
        del os.environ[k]

    if "CLAUDECODE" in os.environ:
        logging.info("Unsetting CLAUDECODE to allow claude-code-sdk subprocess")
        del os.environ["CLAUDECODE"]


def main() -> None:
    setup_logging()
    _sanitize_env()

    parser = argparse.ArgumentParser(
        description="PaperAgent — Academic PDF processor"
    )
    parser.add_argument(
        "--dry-run",
        metavar="PDF_PATH",
        help="Process a single PDF file without watching the inbox folder",
    )
    args = parser.parse_args()

    if args.dry_run:
        pdf_path = Path(args.dry_run).expanduser().resolve()
        if not pdf_path.exists():
            logging.error(f"File not found: {pdf_path}")
            sys.exit(1)
        if pdf_path.suffix.lower() != ".pdf":
            logging.error(f"Not a PDF file: {pdf_path}")
            sys.exit(1)
        asyncio.run(process_pdf(pdf_path))
    else:
        start_watcher()


if __name__ == "__main__":
    main()
