"""Check local Markdown link targets; external sources are recorded in the docs."""

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    failures = []
    for source in [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]:
        for target in re.findall(r"\]\(([^)]+)\)", source.read_text()):
            url = urlsplit(target)
            if url.scheme or not url.path:
                continue
            if not (source.parent / unquote(url.path)).exists():
                failures.append(f"{source.relative_to(ROOT)}: {target}")
    if failures:
        raise SystemExit("\n".join(failures))
    print("All local documentation links resolve.")


if __name__ == "__main__":
    main()
