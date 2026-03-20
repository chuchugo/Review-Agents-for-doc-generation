from __future__ import annotations

import re
from typing import Dict, List


def split_markdown_sections(text: str, *, max_sections: int | None = None) -> List[Dict[str, str]]:
    """
    Lightweight markdown section splitter.

    Strategy:
    - Split on headings that start at line beginning: `# ...` through `###### ...`.
    - If no headings are found, return the full text as a single "section".
    """
    if not text.strip():
        return [{"title": "Empty document", "text": ""}]

    heading_re = re.compile(r"^(#{1,6})\s+(.+?)\s*$", flags=re.MULTILINE)
    matches = list(heading_re.finditer(text))
    if not matches:
        return [{"title": "Full document", "text": text}]

    sections: List[Dict[str, str]] = []
    for idx, m in enumerate(matches):
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        title = m.group(2).strip()
        body = text[start:end].strip()
        if body:
            sections.append({"title": title, "text": body})
        else:
            # Still keep empty sections so outputs have stable traceability.
            sections.append({"title": title, "text": ""})

        if max_sections is not None and len(sections) >= max_sections:
            break

    return sections

