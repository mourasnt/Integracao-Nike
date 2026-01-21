#!/usr/bin/env python3
"""Simple Alembic migrations linter.

Checks:
- revision id length <= 32
- docstring 'Revises:' (if present) matches down_revision variable
- down_revision points to an existing revision id in the folder (unless None)
- duplicate revision ids
- heuristic: repeated add_column on same table+column across files (warn)

Exit code non-zero on errors.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / 'alembic' / 'versions'

REV_RE = re.compile(r"^revision\s*=\s*['\"]([^'\"]+)['\"]", re.I | re.M)
DOWN_REV_RE = re.compile(r"^down_revision\s*=\s*['\"]([^'\"]*)['\"]", re.I | re.M)
DOC_REV_RE = re.compile(r"^Revision ID:\s*(.+)$", re.I | re.M)
DOC_REVISES_RE = re.compile(r"^Revises:\s*(.+)$", re.I | re.M)
ADD_COL_RE = re.compile(r"op\.add_column\(\s*['\"](?P<table>[^'\"]+)['\"]\s*,\s*sa\.Column\(\s*['\"](?P<col>[^'\"]+)['\"]", re.I)


def main() -> int:
    files = sorted(VERSIONS.glob('*.py'))
    if not files:
        print('No alembic versions found under', VERSIONS)
        return 0

    revisions = {}
    errors = []
    warnings = []
    add_column_occurrences = {}

    for f in files:
        txt = f.read_text(encoding='utf-8')
        m_rev = REV_RE.search(txt)
        m_down = DOWN_REV_RE.search(txt)

        revision = m_rev.group(1).strip() if m_rev else None
        down_revision = m_down.group(1).strip() if m_down and m_down.group(1) else None

        # docstring checks
        doc_m = DOC_REVISES_RE.search(txt)
        if doc_m:
            doc_revises = doc_m.group(1).strip()
            # normalize empty
            if doc_revises and down_revision and doc_revises != down_revision:
                warnings.append(f"File {f.name}: doc 'Revises: {doc_revises}' != down_revision var '{down_revision}'")

        if not revision:
            errors.append(f"File {f.name}: missing revision id")
            continue

        if revision in revisions:
            errors.append(f"Duplicate revision id {revision} found in {f.name} and {revisions[revision]}")
        revisions[revision] = f.name

        if len(revision) > 32:
            errors.append(f"Revision id too long ({len(revision)} > 32): {revision} in {f.name}")

        if down_revision:
            # leave existence check for next pass
            pass

        # find add_column occurrences
        for m in ADD_COL_RE.finditer(txt):
            table = m.group('table')
            col = m.group('col')
            key = (table, col)
            add_column_occurrences.setdefault(key, []).append(f.name)

    # check down_revision existence
    for f in files:
        txt = f.read_text(encoding='utf-8')
        m_rev = REV_RE.search(txt)
        m_down = DOWN_REV_RE.search(txt)
        rev = m_rev.group(1).strip() if m_rev else None
        down = m_down.group(1).strip() if m_down and m_down.group(1) else None
        if down and down not in revisions:
            warnings.append(f"File {f.name}: down_revision '{down}' does not match any revision id in versions/ (maybe it's a filename or typo)")

    # repeated add_column heuristic
    for (table, col), files_list in add_column_occurrences.items():
        if len(files_list) > 1:
            warnings.append(f"Column {col} on table {table} added in multiple migrations: {files_list}")

    # print results
    if errors:
        print('\nERRORS:')
        for e in errors:
            print(' -', e)
    if warnings:
        print('\nWARNINGS:')
        for w in warnings:
            print(' -', w)

    if errors:
        print('\nRun `python scripts/check_alembic.py --debug` for more info')
        return 2
    if warnings:
        print('\nFound warnings. Consider reviewing migrations.')
        return 1

    print('Alembic checks passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
