"""Import a Bob IDE task export into bob_sessions/ as evidence (hackathon rules: Bob task evidence).

usage: python3 tools/import_bob_export.py <bob-task-<id>-<date>.json> --task T01 --desc plan
                                          [--status done] [--handle m1] [--index] [--force]

Bob IDE's Export button (task header) saves one JSON file per task: {version, exportedAt,
workspace, tasks: [{task, messages}]}. The file holds the workspace's absolute path many times,
so it is never committed as saved (`bob-task-*.json` is git-ignored). This tool:
- scrubs the raw text, keeping Bob's formatting: home paths (any case, JSON-escaped, forward-slash
  or URL-encoded) become <home>, email addresses other than noreply ones become <email>, and
  Bob's context-cache key (which secret scanners mistake for an API key) becomes
  <context cache key>; the result must still parse and must pass the checks in
  tools/check_evidence.py;
- writes bob_sessions/<team>_task<NN>_<desc>_<handle>_history.json (refuses to overwrite
  without --force);
- prints what the export records: modes, cost, subagents, files Bob edited, failed or blocked
  tool calls, and the INDEX.md row built from them;
- with --index, adds or replaces the task's INDEX.md row, but only when the matching
  _summary.png screenshot is already in bob_sessions/ (check_evidence needs one PNG per row).
  A replaced row keeps its Commit and Gauge values if a person filled them in.
The raw export is left where it is.

Standard library only; Python 3.8+.
Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools import check_evidence as EV  # noqa: E402

EDIT_TOOLS = ("write_file", "apply_diff", "insert_content", "search_and_replace", "office_edit")
SPAWN_TOOLS = ("spawn_subagent", "start_subtask")
GUARD_PREFIX = "SheetShift guard blocked"
# Bob's context-window cache key, "<task id>|<mode>|<hash>|<hash>|<hash>": not a secret, but
# gitleaks' generic-api-key rule reads it as one, and the evidence-folder scan runs default rules.
CACHE_KEY_RE = re.compile(r'("key"\s*:\s*")[0-9a-f]{32}\|[^"]*(")')
KEEP_IF_SET = ("commit", "gauge_before", "gauge_after")


# ---------------------------------------------------------------- scrub
def scrub(text):
    """(scrubbed text, home paths replaced, emails replaced, cache keys replaced).

    Emails are found in the decoded JSON strings (check_evidence.found_emails), then replaced in
    the raw text: matching the raw text directly would read a decorator line in Bob's code right
    after an escaped newline as an address, and replacing it would break the escape. Raises
    ValueError if the text is not JSON."""
    text, n_home = EV.HOME_RE.subn("<home>", text)
    text, n_key = CACHE_KEY_RE.subn(r"\1<context cache key>\2", text)
    json.loads(text)
    n_mail = 0
    for e in EV.found_emails("export.json", text):
        n_mail += text.count(e)
        text = text.replace(e, "<email>")
    return text, n_home, n_mail, n_key


def load_export(text):
    data = json.loads(text)
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list) or not data["tasks"]:
        raise ValueError("not a Bob task export (expected {version, tasks: [...]})")
    if "version" not in data:
        raise ValueError("not a Bob task export (no version field)")
    return data


# ---------------------------------------------------------------- summary
def _data(msg):
    return msg.get("data") or {}


def _text(content):
    """A tool result's text: a string, or the text parts of a list of content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


def summarize(export):
    """What the export records, for the INDEX row. Costs are Bob's own task cost fields."""
    tasks = export["tasks"]
    main = next((t for t in tasks if not (t.get("task") or {}).get("parentId")), tasks[0])
    children = [t for t in tasks if t is not main]
    modes, calls, results = [], {}, {}
    for t in tasks:
        for m in t.get("messages") or []:
            d = _data(m)
            mode = (d.get("_meta") or {}).get("mode")
            mode_id = mode.get("id") if isinstance(mode, dict) else mode
            if m.get("role") == "user" and mode_id and mode_id not in modes:
                modes.append(mode_id)
            for tc in d.get("toolCalls") or []:
                calls[tc.get("id")] = tc
            usage = d.get("toolUsage") or {}
            sig = usage.get("signature") or {}
            if m.get("role") == "tool" and sig.get("id"):
                results[sig["id"]] = {"error": bool(sig.get("isError")), "text": _text(d.get("content"))}
    env_mode = ((main.get("task") or {}).get("env") or {}).get("modeId")
    if env_mode and env_mode not in modes:
        modes.append(env_mode)

    files, spawns, failed, blocked, by_tool = [], 0, 0, 0, {}
    for cid, tc in calls.items():
        name = tc.get("name") or "?"
        by_tool[name] = by_tool.get(name, 0) + 1
        res = results.get(cid, {})
        if res.get("error"):
            failed += 1
            blocked += res.get("text", "").startswith(GUARD_PREFIX)
        if name in SPAWN_TOOLS:
            spawns += 1
        args = tc.get("arguments") or {}
        path = args.get("path") or args.get("file_path")
        if name in EDIT_TOOLS and path and cid in results and not res.get("error"):
            path = path.replace("\\", "/")
            if path.startswith("./"):
                path = path[2:]
            if path not in files:
                files.append(path)

    def cost(t):
        c = ((t.get("task") or {}).get("costs") or {}).get("cost")
        return float(c) if isinstance(c, (int, float)) else None

    mt = main.get("task") or {}
    return {
        "task_id": mt.get("id"),
        "title": (mt.get("title") or mt.get("firstMessage") or "").strip(),
        "status": mt.get("status"),
        "modes": modes,
        "cost": cost(main),
        "child_costs": [c for c in (cost(t) for t in children) if c is not None],
        "subagents": max(spawns, len(children)),
        "files": sorted(files),
        "failed": failed,
        "blocked": blocked,
        "tool_calls": dict(sorted(by_tool.items())),
    }


def files_cell(files, blocked):
    """'none', a single path, or folders with counts: 'service/sheetshift_ho3/units/ (8)'."""
    if files:
        groups = {}
        for p in files:
            groups.setdefault(os.path.dirname(p) or ".", []).append(p)
        parts = [g[0] if len(g) == 1 else "%s/ (%d)" % (d, len(g)) for d, g in sorted(groups.items())]
        cell = ", ".join(parts)
    else:
        cell = "none"
    if blocked:
        cell += "; %d call%s blocked by the guard" % (blocked, "" if blocked == 1 else "s")
    return cell


def cost_cell(s):
    if s["cost"] is None:
        return ""
    cell = "task cost %.2f" % s["cost"]
    if s["child_costs"]:
        cell += " (+%.2f in %d subagent task%s)" % (sum(s["child_costs"]), len(s["child_costs"]),
                                                     "" if len(s["child_costs"]) == 1 else "s")
    return cell


# ---------------------------------------------------------------- INDEX.md
def build_row(task, handle, s, screenshot, export_name, status):
    return {"task": task, "member": handle, "mode": ", ".join(s["modes"]), "subagents": str(s["subagents"]),
            "files_changed": files_cell(s["files"], s["blocked"]), "commit": "", "gauge_before": "",
            "gauge_after": cost_cell(s), "screenshot": screenshot, "export": export_name, "status": status}


def row_line(row):
    keys = [EV._key(c) for c in EV.INDEX_COLUMNS]
    return "| " + " | ".join(row.get(k) or "–" for k in keys) + " |"


def upsert_row(index_path, row):
    """Add the row, or replace the row for the same task (keeping Commit/Gauge values a person set)."""
    with open(index_path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    for old in EV.parse_index(index_path):
        if (old.get("task") or "").upper() == row["task"]:
            for k in KEEP_IF_SET:
                if old.get(k) and not (k == "gauge_after" and old[k].startswith("task cost")):
                    row[k] = old[k]
    new = row_line(row)
    pat = re.compile(r"^\|\s*%s\s*\|" % re.escape(row["task"]), re.I)
    hits = [i for i, l in enumerate(lines) if pat.match(l)]
    if hits:
        lines[hits[0]] = new
        for i in reversed(hits[1:]):
            del lines[i]
    else:
        # Insert in task order (tasks may run out of order, e.g. T04 before T03).
        task_row = re.compile(r"^\|\s*(T\d{2})\s*\|", re.I)
        rows_at = [(i, m.group(1).upper()) for i, m in ((i, task_row.match(l)) for i, l in enumerate(lines)) if m]
        after = [i for i, t in rows_at if t < row["task"]]
        if after:
            at = max(after) + 1
        elif rows_at:
            at = rows_at[0][0]
        else:
            at = max(i for i, l in enumerate(lines) if l.startswith("|")) + 1
        lines.insert(at, new)
    with open(index_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    return new


# ---------------------------------------------------------------- main
def read_roster(sessions):
    path = os.path.join(sessions, "roster.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv=None, sessions=None):
    ap = argparse.ArgumentParser(description="Import a Bob IDE task export into bob_sessions/")
    ap.add_argument("export", help="the bob-task-<id>-<date>.json file saved by Bob IDE's Export button")
    ap.add_argument("--task", required=True, help="task number from docs/bob_prompts.md, e.g. T01")
    ap.add_argument("--desc", required=True, help="short name, lowercase letters, digits and underscores")
    ap.add_argument("--status", default="done", choices=["done", "aborted", "re-run", "fallback"])
    ap.add_argument("--handle", help="member handle (default: the only roster member)")
    ap.add_argument("--index", action="store_true", help="add or replace the task's INDEX.md row")
    ap.add_argument("--force", action="store_true", help="overwrite an existing export")
    a = ap.parse_args(argv)
    sessions = sessions or EV.SESSIONS

    task = a.task.upper()
    if not re.match(r"^T\d{2}$", task):
        ap.error("--task must look like T01")
    if not re.match(r"^[a-z0-9_]+$", a.desc):
        ap.error("--desc must be lowercase letters, digits and underscores")
    ros = read_roster(sessions)
    team = ros.get("team_slug")
    handles = [m.get("handle") for m in ros.get("members", []) if isinstance(m, dict)]
    if not team:
        ap.error("bob_sessions/roster.json has no team_slug")
    handle = a.handle or (handles[0] if len(handles) == 1 else None)
    if handle not in handles:
        ap.error("--handle must be one of %s" % ", ".join(handles))

    with open(a.export, encoding="utf-8") as f:
        raw = f.read()
    try:
        load_export(raw)
        text, n_home, n_mail, n_key = scrub(raw)
        export = load_export(text)
    except ValueError as e:
        print("ERROR: %s: %s" % (a.export, e), file=sys.stderr)
        return 1
    if EV.HOME_RE.search(text):
        print("ERROR: a home path survived the scrub; not writing", file=sys.stderr)
        return 1

    stem = "%s_task%s_%s_%s" % (team, task[1:], a.desc, handle)
    export_name, shot = stem + "_history.json", stem + "_summary.png"
    out = os.path.join(sessions, export_name)
    if os.path.exists(out) and not a.force:
        print("ERROR: %s exists; pass --force to replace it" % out, file=sys.stderr)
        return 1
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write(text)

    s = summarize(export)
    row = build_row(task, handle, s, shot, export_name, a.status)
    print("wrote bob_sessions/%s (scrubbed: %d home paths, %d emails, %d cache keys)" % (
        export_name, n_home, n_mail, n_key))
    print("Bob task %s: %s" % (s["task_id"], s["title"][:100]))
    print("  modes: %s | %s | subagents: %d" % (", ".join(s["modes"]) or "?", cost_cell(s) or "no cost field",
                                                 s["subagents"]))
    print("  tool calls: %s" % ", ".join("%s %d" % kv for kv in s["tool_calls"].items()))
    print("  failed: %d (blocked by the guard: %d)" % (s["failed"], s["blocked"]))
    print("  files edited: %s" % (", ".join(s["files"]) or "none"))
    if a.index:
        if os.path.exists(os.path.join(sessions, shot)):
            print("INDEX.md: " + upsert_row(os.path.join(sessions, "INDEX.md"), row))
        else:
            print("warning: bob_sessions/%s is missing, so INDEX.md was not changed. Row to add:" % shot)
            print(row_line(row))
    else:
        print("INDEX.md row: " + row_line(row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
