"""Static check of the Bob pack: modes, hooks settings, skills, commands, AGENTS.md.

One invalid fileRegex can stop .bob/custom_modes.yaml from loading, so this runs in CI:
- every mode has the documented fields, a valid unique slug and known tool groups;
- every fileRegex compiles and avoids Python-only syntax that JavaScript would reject;
- each Bob task's output paths match its mode's edit regex (plan section 4.2 table), and
  no protected path matches any mode's edit regex;
- .bob/settings.json uses only documented hook keys, and each hook script exists;
- every skill has `name` and `description` front matter; command names start with `shift-`
  (or are `sheetshift`) and do not clash with mode slugs; AGENTS.md is 60 lines or fewer.

Usage: python3 tools/check_modes.py   (exit 0 = all checks pass). Dev dependency: pyyaml.
Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import glob
import json
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOB = os.path.join(ROOT, ".bob")

MODE_KEYS = {"slug", "name", "description", "roleDefinition", "whenToUse",
             "customInstructions", "groups", "allowedSubagents"}
REQUIRED = ("slug", "name", "roleDefinition", "groups")
GROUPS = {"read", "edit", "execute", "mcp", "skill", "workflow", "todo", "subtask",
          "subagent", "mode"}
BUILTIN = {"agent", "plan", "ask"}
SLUG = re.compile(r"^[A-Za-z0-9-]+$")
NOT_JS = re.compile(r"\(\?P|\(\?#|\(\?>|\\[AZz]|\(\?[aiLmsux]+\)|[*+?}]\+")

# Plan section 4.2: which mode each task runs in, and files that task writes.
TASKS = {
    "T02": ("sheet-translator", ["service/sheetshift_ho3/__init__.py", "service/sheetshift_ho3/xlsem.py",
                                 "service/sheetshift_ho3/tables.py",
                                 "service/sheetshift_ho3/data/rate_tables.json",
                                 "tests/test_xlsem.py", "tests/test_tables.py"]),
    "T03": ("sheet-translator", ["service/sheetshift_ho3/units/__init__.py",
                                 "service/sheetshift_ho3/units/u1_base.py",
                                 "service/sheetshift_ho3/units/u2_aop.py",
                                 "service/sheetshift_ho3/units/u3_credits_hurricane.py",
                                 "service/sheetshift_ho3/units/u4_term_fees.py",
                                 "service/sheetshift_ho3/rater.py", "tests/test_u1.py",
                                 "tests/test_u4.py", "tests/test_rater_order.py"]),
    "T04": ("sheet-translator", ["service/sheetshift_ho3/api.py", "tests/test_api.py"]),
    "T07": ("sheet-translator", ["service/sheetshift_ho3/OUT_OF_SCOPE.json",
                                 "service/sheetshift_ho3/units/u2_aop.py", "tests/test_decisions.py"]),
    "T05": ("sheet-triage", ["service/sheetshift_ho3/units/u3_credits_hurricane.py",
                             "tests/test_u3.py", "reports/notes/triage_1.md",
                             "docs/anomalies/D-001.md"]),
    "T06": ("sheet-analyst", ["docs/anomalies/D-001.md", "docs/anomalies/D-003.md"]),
    "T12": ("sheet-analyst", ["docs/notes/flag_gaps.md"]),
    "T09": ("sheet-verifier", ["docs/bob_run_summary.html", "docs/architecture.md",
                               "docs/how_it_works.md", "reports/notes/run_1.md"]),
}
# Paths no custom mode may edit (the guard blocks them too).
PROTECTED = ["harness/run.py", "harness/tests/test_x.py", "tools/decide.py",
             "tools/tests/test_guard.py", "workbook/example_mutual_ho3_rater.xlsx",
             "golden/oracle_meta.json", "decisions/decisions.jsonl", ".bob/custom_modes.yaml",
             ".bob/hooks/guard.py", ".github/workflows/verify.yml", "AGENTS.md", "sheetshift.json",
             "Makefile", "build/graph.json", "reports/certificate.json", "reports/certificate.html",
             "service/sheetshift_ho3/data/verify_sample_2026.json.gz", "public/trace.html"]
HOOK_EVENTS = {"SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"}


def edit_regexes(mode):
    """The compiled fileRegex of each edit group in a mode ('.*' for an unrestricted edit)."""
    out = []
    for g in mode.get("groups", []):
        if g == "edit":
            out.append(re.compile(".*"))
        elif isinstance(g, list) and g and g[0] == "edit":
            opts = g[1] if len(g) > 1 and isinstance(g[1], dict) else {}
            try:
                out.append(re.compile(opts.get("fileRegex", ".*")))
            except re.error:
                pass  # reported by check_modes
    return out


def check_modes(errors):
    """Validate .bob/custom_modes.yaml; return {slug: mode}."""
    with open(os.path.join(BOB, "custom_modes.yaml"), encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    modes = (doc or {}).get("customModes")
    if not isinstance(modes, list) or not modes:
        errors.append("custom_modes.yaml: customModes must be a non-empty list")
        return {}
    by_slug = {}
    for i, m in enumerate(modes):
        where = "mode #%d (%s)" % (i + 1, m.get("slug"))
        for k in REQUIRED:
            if not m.get(k):
                errors.append("%s: missing %s" % (where, k))
        for k in sorted(set(m) - MODE_KEYS):
            errors.append("%s: unknown key %s" % (where, k))
        slug = str(m.get("slug", ""))
        if not SLUG.match(slug):
            errors.append("%s: slug must use letters, numbers and hyphens" % where)
        if slug in by_slug or slug in BUILTIN:
            errors.append("%s: duplicate or built-in slug" % where)
        by_slug[slug] = m
        for g in m.get("groups", []):
            name = g[0] if isinstance(g, list) and g else g
            if name not in GROUPS:
                errors.append("%s: unknown group %r" % (where, name))
            if isinstance(g, list):
                rx = (g[1] if len(g) > 1 and isinstance(g[1], dict) else {}).get("fileRegex")
                if rx is None:
                    continue
                try:
                    re.compile(rx)
                except re.error as e:
                    errors.append("%s: fileRegex does not compile: %s" % (where, e))
                if NOT_JS.search(rx):
                    errors.append("%s: fileRegex uses syntax JavaScript rejects: %s" % (where, rx))
    return by_slug


def check_tasks(modes, errors):
    """Each task's outputs match its mode; no protected path matches any mode."""
    for task, (slug, paths) in sorted(TASKS.items()):
        if slug not in modes:
            errors.append("%s: mode %s is not defined" % (task, slug))
            continue
        rxs = edit_regexes(modes[slug])
        for p in paths:
            if not any(rx.search(p) for rx in rxs):
                errors.append("%s: %s does not match any edit regex of %s" % (task, p, slug))
    for slug, m in sorted(modes.items()):
        for p in PROTECTED:
            if any(rx.search(p) for rx in edit_regexes(m)):
                errors.append("protected path %s is editable in mode %s" % (p, slug))
    for d in glob.glob(os.path.join(BOB, "rules-*")):
        slug = os.path.basename(d)[len("rules-"):]
        if slug not in modes and slug not in BUILTIN:
            errors.append("%s: no mode with slug %s" % (os.path.relpath(d, ROOT), slug))


def check_settings(errors):
    """Hooks JSON uses only documented keys; matchers compile; scripts exist."""
    with open(os.path.join(BOB, "settings.json"), encoding="utf-8") as f:
        doc = json.load(f)
    for k in set(doc) - {"hooks"}:
        errors.append("settings.json: unexpected top-level key %s" % k)
    for event, entries in doc.get("hooks", {}).items():
        if event not in HOOK_EVENTS:
            errors.append("settings.json: unknown hook event %s" % event)
        for e in entries:
            for k in set(e) - {"matcher", "hooks"}:
                errors.append("settings.json %s: unknown key %s" % (event, k))
            try:
                re.compile(e.get("matcher", ""))
            except re.error as err:
                errors.append("settings.json %s: matcher does not compile: %s" % (event, err))
            for h in e.get("hooks", []):
                for k in set(h) - {"type", "command", "timeout"}:
                    errors.append("settings.json %s: unknown hook key %s" % (event, k))
                if h.get("type") != "command":
                    errors.append("settings.json %s: type must be command" % event)
                script = h.get("command", "").split()[-1]
                if not os.path.isfile(os.path.join(ROOT, script)):
                    errors.append("settings.json %s: missing script %s" % (event, script))


def front_matter(path):
    """The YAML front matter of a markdown file, or {}."""
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def check_pack(modes, errors):
    """Skills, commands and AGENTS.md."""
    skills = glob.glob(os.path.join(BOB, "skills", "*", "SKILL.md"))
    if not skills:
        errors.append("no skills found")
    for p in skills:
        fm = front_matter(p)
        if not fm.get("name") or not fm.get("description"):
            errors.append("%s: needs name and description" % os.path.relpath(p, ROOT))
    for p in glob.glob(os.path.join(BOB, "commands", "*.md")):
        name = os.path.basename(p)[:-3]
        if not (name == "sheetshift" or name.startswith("shift-")) or name in modes:
            errors.append("command %s: must be sheetshift or shift-* and not a mode slug" % name)
    with open(os.path.join(ROOT, "AGENTS.md"), encoding="utf-8") as f:
        n = len(f.read().splitlines())
    if n > 60:
        errors.append("AGENTS.md has %d lines (limit 60)" % n)


def main():
    errors = []
    modes = check_modes(errors)
    check_tasks(modes, errors)
    check_settings(errors)
    check_pack(modes, errors)
    for e in errors:
        print("FAIL " + e)
    print("check_modes: %d modes, %d tasks, %d protected samples; %s"
          % (len(modes), len(TASKS), len(PROTECTED), "OK" if not errors else "%d errors" % len(errors)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
