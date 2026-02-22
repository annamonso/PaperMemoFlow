# PaperAgent

Automated academic PDF processor. Watches a folder for new PDFs and generates structured LaTeX summaries using Claude.

## What it does

1. Detects new PDFs in `~/PapersInbox/`
2. Extracts text (PyMuPDF → pdfminer.six fallback)
3. Summarises and structures the content via **claude-code-sdk** (Claude Opus)
4. Rewrites the summary with **DeepL** (or Claude Haiku as fallback)
5. Fills a LaTeX template and saves a `.tex` file to `~/PapersOut/`
6. Compiles to PDF with `latexmk` if available

## Requirements

- Python 3.11+
- `claude` CLI installed and authenticated (`npm install -g @anthropic-ai/claude-code`)
- `ANTHROPIC_API_KEY` set in your environment
- `latexmk` (optional, for PDF compilation)

## Installation

```bash
cd ~/PaperAgent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Normal mode (watch inbox folder)

```bash
python src/watcher.py
```

The agent will watch `~/PapersInbox/` and process every new PDF automatically.

### Dry-run mode (process a single file)

```bash
python src/watcher.py --dry-run /path/to/paper.pdf
```

Processes the given PDF immediately without starting the folder watcher.

## Configuration

All settings can be overridden via environment variables:

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(required)* | Your Anthropic API key |
| `DEEPL_API_KEY` | *(optional)* | DeepL API key for text rewriting |
| `PAPERS_INBOX` | `~/PapersInbox` | Folder to watch for new PDFs |
| `PAPERS_OUTBOX` | `~/PapersOut` | Folder where `.tex` / `.pdf` files are saved |

### Setting DEEPL_API_KEY (optional)

```bash
export DEEPL_API_KEY="your-deepl-api-key"
python src/watcher.py
```

Without a DeepL key the system falls back to Claude Haiku for text rewriting — output quality is still high.

### Changing inbox / outbox folders

```bash
export PAPERS_INBOX="/Users/anna/Documents/Papers"
export PAPERS_OUTBOX="/Users/anna/Documents/Summaries"
python src/watcher.py
```

## Output format

For each PDF `paper.pdf` the agent writes `~/PapersOut/paper.tex` (and `paper.pdf` if latexmk is installed) containing:

- **Title** — detected from the paper or derived from the filename
- **Paper Summary** — 1–2 paragraphs, ≤ 150 words
- **Contributions** — 2–4 bullet points
- **Limitations** — 1–3 bullet points
- **One Question to Discuss** — a single debatable question

## Log format

```
[2026-02-21 10:23:01] [INFO] New PDF detected: paper.pdf
[2026-02-21 10:23:04] [INFO] Text extracted: 4823 words
[2026-02-21 10:23:09] [INFO] Summary generated
[2026-02-21 10:23:11] [INFO] DeepL unavailable, using Claude fallback
[2026-02-21 10:23:14] [INFO] LaTeX written: ~/PapersOut/paper.tex
```
