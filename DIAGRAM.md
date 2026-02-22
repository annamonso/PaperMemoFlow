# PaperAgent — Pipeline Diagram

## Flow

```
  PapersInbox/
       │
       │  new .pdf detected (watchdog)
       ▼
  ┌──────────────────┐
  │  Stability Check │  3 size checks × 1s — ignores .tmp, .part, ~ files
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │   PDF Extract    │  PyMuPDF  →  pdfminer.six (fallback)
  │  pdf_extract_    │  strip null bytes from text
  │    tool.py       │
  └────────┬─────────┘
           │
           │  word count?
           ├───────────────────────────────────────┐
           │ > 3 000 words                          │ ≤ 3 000 words
           ▼                                       │
  ┌──────────────────┐                             │
  │  Split in chunks │  3 000 words + 200 overlap  │
  └────────┬─────────┘                             │
           │                                       │
           │  each chunk (sequential)              │
           ▼                                       │
  ┌──────────────────────────────┐                 │
  │  🤖 Claude Haiku             │                 │
  │  claude-haiku-4-5-20251001   │                 │
  │                              │                 │
  │  "Summarise this portion     │                 │
  │   of the paper..."           │                 │
  │                              │                 │
  │  → plain text summary        │                 │
  └────────┬─────────────────────┘                 │
           │  all chunk summaries                  │
           │  joined                               │
           ▼                                       │
  ┌──────────────────────────────┐                 │
  │  🤖 Claude Opus              │◄────────────────┘
  │  claude-opus-4-5             │
  │                              │
  │                              │
  │  "Analyse this paper         │
  │   and return JSON..."        │
  │                              │
  │  → structured JSON:          │
  │    title                     │
  │    summary                   │
  │    contributions [ ]         │
  │    limitations   [ ]         │
  │    question                  │
  └────────┬─────────────────────┘
           │
           ▼
  ┌──────────────────────────────┐
  │     Rewrite / Polish         │
  │   deepl_rewrite_tool.py      │
  │                              │
  │   DEEPL_API_KEY set?         │
  │   ├── yes → DeepL API        │
  │   └── no  → 🤖 Claude Haiku  │  same prompt, academic tone rewrite
  └────────┬─────────────────────┘
           │
           ▼
  ┌──────────────────────────────┐
  │     LaTeX Writer             │
  │     latex_writer.py          │
  │                              │
  │  fill template placeholders  │
  │  escape special chars        │
  │  → zhang21r.tex              │
  └────────┬─────────────────────┘
           │
           ▼
  ┌──────────────────────────────┐
  │     LaTeX Compile (optional) │
  │     latex_compile_tool.py    │
  │                              │
  │  latexmk installed?          │
  │  ├── yes → zhang21r.pdf      │
  │  └── no  → skip, .tex kept   │
  └────────┬─────────────────────┘
           │
           ▼
       PapersOut/
```

---

## Where Claude is used

| Step | Model | Role |
|---|---|---|
| Chunk summarisation | **Claude Haiku** | Cheap, fast — one call per chunk |
| Full summary / consolidation | **Claude Opus** | Best quality — one call total |
| DeepL fallback rewrite | **Claude Haiku** | Academic tone polish |

> All calls go through **claude-code-sdk**, which spawns the `claude` CLI under the hood and uses your Claude Code Pro account — no separate API key needed.

---

## File map

```
watcher.py          ← entrypoint, watchdog loop, --dry-run
│
├── pdf_extract_tool.py     ← PyMuPDF / pdfminer
│
├── pipeline.py             ← chunking + Claude Haiku + Claude Opus
│
├── deepl_rewrite_tool.py   ← DeepL / Claude Haiku fallback
│
├── latex_writer.py         ← template fill + LaTeX escaping
│
└── latex_compile_tool.py   ← latexmk wrapper
```
