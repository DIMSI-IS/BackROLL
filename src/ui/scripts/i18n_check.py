"""Checks the texts of the pages: python src/ui/scripts/i18n_check.py

- every file src/i18n/pages/<area>.en.json has its <area>.fr.json with the same keys and the same {placeholders};
- every key used as $t('pages.<area>.<key>') or t('pages...') in the sources exists in English.
"""

import json
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
PAGES = SRC / "i18n" / "pages"
USED = re.compile(r"""\bt\(\s*['"`](pages\.[A-Za-z0-9_.\-]+)['"`]""")
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def flatten(value, prefix=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from flatten(item, f"{prefix}{key}.")
    else:
        yield prefix.rstrip("."), value


def main() -> int:
    problems = []
    english = {}
    for path in sorted(PAGES.glob("*.en.json")):
        area = path.name.removesuffix(".en.json")
        french_path = PAGES / f"{area}.fr.json"
        en = dict(flatten(json.loads(path.read_text(encoding="utf-8"))))
        english.update({f"pages.{area}.{key}": value for key, value in en.items()})
        if not french_path.exists():
            problems.append(f"{area}: {french_path.name} is missing")
            continue
        fr = dict(flatten(json.loads(french_path.read_text(encoding="utf-8"))))
        for key in sorted(en.keys() - fr.keys()):
            problems.append(f"{area}: “{key}” is not translated to French")
        for key in sorted(fr.keys() - en.keys()):
            problems.append(f"{area}: “{key}” is in French only")
        for key in en.keys() & fr.keys():
            if set(PLACEHOLDER.findall(str(en[key]))) != set(PLACEHOLDER.findall(str(fr[key]))):
                problems.append(f"{area}: “{key}” has different {{placeholders}} in French")
            if not str(fr[key]).strip():
                problems.append(f"{area}: “{key}” is empty in French")
    for path in sorted(PAGES.glob("*.fr.json")):
        if not (PAGES / path.name.replace(".fr.json", ".en.json")).exists():
            problems.append(f"{path.name} has no English file")

    for source in list(SRC.rglob("*.vue")) + list(SRC.rglob("*.js")) + list(SRC.rglob("*.ts")):
        if PAGES in source.parents:
            continue
        for key in USED.findall(source.read_text(encoding="utf-8", errors="ignore")):
            if key not in english:
                problems.append(f"{source.relative_to(SRC)}: unknown key {key}")

    for problem in problems:
        print(problem)
    print(f"{len(english)} English texts, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
