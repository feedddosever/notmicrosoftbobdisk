"""Shared helpers for the SheetShift Bob hooks: payload parsing, repo paths, audit logs.

Standard library only; Python 3.8+. Accepts both payload shapes
{event, tool, input} and {hook_event_name, tool_name, tool_input}.
Audit records hold repo-relative paths only, never file contents or absolute paths.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import datetime
import json
import os
import re
import subprocess
import tempfile

ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
REPORTS = os.path.join(ROOT, "reports")
SMOKE_LAST = os.path.join(REPORTS, "smoke_last.json")
PATH_KEYS = ("path", "file_path", "filePath", "target_file", "file", "destination")
OUTSIDE = "<outside-repo>"
_HANDLE_OK = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


def now():
    """UTC timestamp, second precision."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def handle():
    """Member handle from `git config sheetshift.handle`; 'unknown' if unset or odd."""
    try:
        out = subprocess.run(["git", "config", "--get", "sheetshift.handle"], cwd=ROOT,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=3)
        h = out.stdout.decode("utf-8", "replace").strip()
    except Exception:
        h = ""
    return h if _HANDLE_OK.match(h) else "unknown"


class Payload(object):
    """One hook invocation: raw stdin text plus the normalised fields."""

    def __init__(self, raw):
        self.raw = raw
        data = json.loads(raw) if raw.strip() else {}
        if not isinstance(data, dict):
            raise ValueError("payload is not a JSON object")
        self.data = data
        self.event = data.get("event") or data.get("hook_event_name") or ""
        self.tool = data.get("tool") or data.get("tool_name") or ""
        tin = data["input"] if "input" in data else data.get("tool_input")
        if isinstance(tin, str):
            try:
                tin = json.loads(tin)
            except ValueError:
                tin = {"command": tin} if self.tool == "execute_command" else {}
        self.input = tin if isinstance(tin, dict) else {}
        self.session_id = str(data.get("session_id") or "")


def read_stdin(stream):
    """Read stdin as text, tolerating bad bytes."""
    data = stream.buffer.read() if hasattr(stream, "buffer") else stream.read()
    return data.decode("utf-8", "replace") if isinstance(data, bytes) else data


def find_paths(obj, depth=0):
    """All string values stored under path-like keys, searched recursively."""
    found = []
    if depth > 6:
        return found
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in PATH_KEYS and isinstance(v, str) and v.strip():
                found.append(v)
            elif isinstance(v, (dict, list)):
                found.extend(find_paths(v, depth + 1))
    elif isinstance(obj, list):
        for v in obj:
            found.extend(find_paths(v, depth + 1))
    return found


def rel_path(p, base=None):
    """Repo-relative, forward-slash form of p after resolving symlinks ('../..' if outside)."""
    p = p.strip().strip("'\"").replace("\\", "/")
    p = os.path.expanduser(p)
    if not os.path.isabs(p):
        p = os.path.join(base or os.getcwd(), p)
    real = os.path.realpath(p)
    try:
        rel = os.path.relpath(real, ROOT)
    except ValueError:  # another drive on Windows
        return "../" + real.replace("\\", "/")
    return rel.replace("\\", "/")


def loggable(rel):
    """What may go into an audit record: repo-relative paths only."""
    if rel is None:
        return None
    return OUTSIDE if (rel == ".." or rel.startswith("../")) else rel


def append_jsonl(path, record):
    """Append one JSON line with a single O_APPEND write (safe for parallel subagents)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    line = (json.dumps(record, sort_keys=False, ensure_ascii=True) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)


def write_json_atomic(path, obj):
    """Write JSON through a temp file and os.replace, so readers never see half a file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1, sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def audit_path(name, who=None):
    """audit/<handle>/<name>."""
    return os.path.join(ROOT, "audit", who or handle(), name)


def log_payload_keys(payload, who=None):
    """Record the payload's key names (never values) per event, to confirm field names."""
    path = audit_path("hook_payload_sample.json", who)
    try:
        with open(path, encoding="utf-8") as f:
            sample = json.load(f)
    except Exception:
        sample = {}
    entry = {"top_keys": sorted(payload.data.keys()), "tool": payload.tool or None,
             "input_keys": sorted(payload.input.keys())}
    key = payload.event or "unknown"
    if sample.get(key) != entry:
        sample[key] = entry
        write_json_atomic(path, sample)


def read_json(path):
    """Parsed JSON, or None if the file is missing or unreadable."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def smoke_summary():
    """Short text for reports/smoke_last.json, e.g. 'smoke U2 200/200 equal'."""
    d = read_json(SMOKE_LAST)
    if not isinstance(d, dict):
        return "smoke: not run yet"
    status = str(d.get("status", "")).lower()
    if isinstance(d.get("line"), str) and d["line"].strip():  # the harness writes its own line
        return d["line"].strip()
    if status == "pending":
        missing = [re.sub(r".*\b[uU]([1-4]).*", r"U\1", str(m)) for m in d.get("missing", [])]
        return "smoke: pending (%s not yet written)" % ", ".join(missing or ["units"])
    if status == "error":
        return "smoke: error (%s)" % str(d.get("reason") or d.get("error") or "see reports/smoke_last.json")[:50]
    unit = d.get("unit") or d.get("units") or "all"
    if isinstance(unit, list):
        unit = ",".join(str(u) for u in unit)
    for a, b in (("rows_equal", "rows"), ("rows_equal", "n"), ("equal", "n"),
                 ("equal", "total"), ("cells_equal", "cells_compared")):
        if isinstance(d.get(a), int) and isinstance(d.get(b), int):
            return "smoke %s %d/%d equal" % (unit, d[a], d[b])
    return "smoke %s %s" % (unit, status or "done")


def pending_decisions():
    """IDs of decision-queue items still PENDING (reports/decision_queue.json)."""
    d = read_json(os.path.join(REPORTS, "decision_queue.json"))
    items = d.get("items", []) if isinstance(d, dict) else (d or [])
    return [str(i.get("id")) for i in items
            if isinstance(i, dict) and str(i.get("status", "")).upper().startswith("PENDING")]


def open_groups():
    """Mismatch groups not yet decided or escalated (reports/mismatches.json)."""
    d = read_json(os.path.join(REPORTS, "mismatches.json"))
    if isinstance(d, dict):
        groups = d.get("groups") or (d.get("original") or {}).get("groups") or []
    else:
        groups = d or []
    return [g for g in groups
            if isinstance(g, dict) and g.get("class") not in ("decided", "escalated")]
