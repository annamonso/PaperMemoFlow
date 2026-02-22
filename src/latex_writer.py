import re
from pathlib import Path

# LaTeX template — do NOT modify
LATEX_TEMPLATE = r"""\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{setspace}
\usepackage{hyperref}
\usepackage{times}
\usepackage{setspace}
\usepackage{xurl}
\usepackage{float}
\singlespacing

\begin{document}
\begin{center}
    {\LARGE \textbf{TITULO_PAPER}} \\[2ex]
    \normalsize
\end{center}

\begin{center}
    {\textbf{Anna Monsó Rodriguez}} \\[2ex]
    \normalsize
\end{center}

\section*{Paper Summary}
SUMMARY_TEXT

\section*{Contributions}
\begin{itemize}
CONTRIBUTIONS_ITEMS
\end{itemize}

\section*{Limitations}
\begin{itemize}
LIMITATIONS_ITEMS
\end{itemize}

\section*{One Question to Discuss}
QUESTION_TEXT

\vspace{2\baselineskip}
\textit{Note:} I used \href{https://www.deepl.com/es/write}{www.deepl.com} to improve the quality of my text.
\end{document}
"""

# Characters to escape in user-generated content (order matters: backslash first)
_ESCAPE_MAP = {
    "\\": r"\textbackslash{}",
    "%":  r"\%",
    "$":  r"\$",
    "#":  r"\#",
    "_":  r"\_",
    "{":  r"\{",
    "}":  r"\}",
    "~":  r"\textasciitilde{}",
    "^":  r"\textasciicircum{}",
    "&":  r"\&",
}

# Single-pass regex: matches any special char
_ESCAPE_RE = re.compile(r'([\\%$#_{}~^&])')


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters in user-supplied text."""
    return _ESCAPE_RE.sub(lambda m: _ESCAPE_MAP[m.group(0)], text)


def fill_template(data: dict) -> str:
    """Fill the LaTeX template with structured data. Returns complete .tex string."""
    title = escape_latex(data["title"])
    summary = escape_latex(data["summary"])

    contributions_lines = []
    for item in data["contributions"]:
        label = escape_latex(item["label"])
        text = escape_latex(item["text"])
        contributions_lines.append(f"    \\item \\textbf{{{label}:}} {text}")
    contributions = "\n".join(contributions_lines)

    limitations_lines = []
    for item in data["limitations"]:
        label = escape_latex(item["label"])
        text = escape_latex(item["text"])
        limitations_lines.append(f"    \\item \\textbf{{{label}:}} {text}")
    limitations = "\n".join(limitations_lines)

    question = escape_latex(data["question"])

    tex = LATEX_TEMPLATE
    tex = tex.replace("TITULO_PAPER", title)
    tex = tex.replace("SUMMARY_TEXT", summary)
    tex = tex.replace("CONTRIBUTIONS_ITEMS", contributions)
    tex = tex.replace("LIMITATIONS_ITEMS", limitations)
    tex = tex.replace("QUESTION_TEXT", question)
    return tex
