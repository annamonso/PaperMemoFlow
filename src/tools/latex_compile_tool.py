import logging
import shutil
import subprocess
from pathlib import Path


def compile_latex(tex_path: Path) -> bool:
    """Compile a .tex file to PDF using latexmk. Returns True on success."""
    if not shutil.which("latexmk"):
        logging.info("latexmk not installed, skipping PDF compilation")
        return False

    try:
        result = subprocess.run(
            [
                "latexmk",
                "-pdf",
                "-interaction=nonstopmode",
                "-halt-on-error",
                str(tex_path.name),
            ],
            cwd=tex_path.parent,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return True
        logging.error(f"latexmk exited with code {result.returncode}")
        logging.error(result.stderr[-2000:] if result.stderr else "(no stderr)")
        return False
    except subprocess.TimeoutExpired:
        logging.error("LaTeX compilation timed out")
        return False
    except Exception as e:
        logging.error(f"LaTeX compilation error: {e}")
        return False
