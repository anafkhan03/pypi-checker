#!/usr/bin/env python3
"""Check every line of a requirements.txt against PyPI (JSON API).

Usage: python check_requirements.py [requirements.txt]
"""
import json
import re
import sys
import urllib.error
import urllib.request

LINE_RE = re.compile(
    r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)"   # package name
    r"(?:\[[^\]]*\])?"                    # optional extras
    r"\s*(?:(==|===)\s*([^\s;,#]+))?"     # optional pinned version
)


def fetch_json(url):
    """Return parsed JSON, or None if PyPI answers 404."""
    req = urllib.request.Request(url, headers={"User-Agent": "req-checker/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def parse_requirements(path):
    entries = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.split("#", 1)[0].strip()
            if not line or line.startswith("-"):  # blank, comment, pip option
                continue
            m = LINE_RE.match(line)
            if m:
                entries.append((m.group(1), m.group(3)))
    return entries


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "requirements.txt"
    entries = parse_requirements(path)

    missing_packages = []
    missing_versions = []
    oldest = None  # (upload_time, "name==version(year)")

    for name, version in entries:
        if fetch_json(f"https://pypi.org/pypi/{name}/json") is None:
            missing_packages.append(name)
            continue
        if not version:
            continue  # not pinned, nothing more to verify
        data = fetch_json(f"https://pypi.org/pypi/{name}/{version}/json")
        if data is None:
            missing_versions.append(f"{name}=={version}")
            continue
        files = data.get("urls") or []
        if not files:
            continue
        upload = files[0]["upload_time"]  # e.g. 2021-03-04T12:34:56
        if oldest is None or upload < oldest[0]:
            oldest = (upload, f"{name}=={version}({upload[:4]})")

    print(f"Dependencies checked: {len(entries)}")
    print(f"Packages not on PyPI: {', '.join(missing_packages) or 'none'}")
    print(f"Version not on PyPI: {', '.join(missing_versions) or 'none'}")
    print(f"Oldest pinned release: {oldest[1] if oldest else 'n/a'}")


if __name__ == "__main__":
    main()
