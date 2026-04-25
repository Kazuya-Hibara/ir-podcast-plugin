"""HTML → plain text fallback for ir-document-analyzer.

Used when the `defuddle` skill is not installed. NotebookLM rejects raw
iXBRL HTML uploads (400 Bad Request); this strips tags + XBRL metadata
and emits readable text suitable for `notebooklm source add --type file`.

Usage:
    python3 scripts/html_to_md.py <input.html> [<output.txt>]
    python3 scripts/html_to_md.py <input.html> > <output.txt>
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

try:
    from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
except ImportError:
    sys.stderr.write(
        "ERROR: beautifulsoup4 not installed.\n"
        "  Run: pip install beautifulsoup4\n"
        "  (or install the `defuddle` skill for higher-fidelity output)\n"
    )
    sys.exit(1)

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


def html_to_text(html_bytes: bytes) -> str:
    soup = BeautifulSoup(html_bytes, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def main() -> int:
    if len(sys.argv) < 2:
        sys.stderr.write(__doc__)
        return 1
    src = Path(sys.argv[1])
    if not src.exists():
        sys.stderr.write(f"ERROR: input not found: {src}\n")
        return 1
    text = html_to_text(src.read_bytes())
    if len(sys.argv) >= 3:
        Path(sys.argv[2]).write_text(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
