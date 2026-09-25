"""PreToolUse guard: blocks Bob's writes to protected paths, decide.py, git push and secrets.

Exit 2 blocks the tool call; exit 0 allows it. Fails closed: on any internal error the
call is blocked if the raw payload mentions a protected path or a secret, else allowed.
Every decision is appended to audit/<handle>/hook_events.jsonl (repo-relative paths only).
Honest limit: a shell can always find another way to write a file; CI is the
authoritative control, this guard is the fast one.

Standard library only; Python 3.8+.
Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import os
import re
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

PROTECTED = re.compile(
    r"^(workbook|harness|golden|decisions|tools|manual|build|audit|\.bob|\.github|\.git)(/|$)"
    r"|^(AGENTS\.md|\.bobignore|sheetshift\.json|Makefile|ATTRIBUTION\.md|PROVENANCE\.md)$"
    r"|^docs/CONTRACT\.md$"
    r"|^reports/[^/]+\.(json|jsonl|html)$"
    r"|^tests/test_(harness_selfcheck|no_env)\.py$"
    r"|^service/sheetshift_ho3/data/verify_sample_[^/]*$"
    r"|\.xls[xm]$")
RAW_PROTECTED = re.compile(
    r"(^|[\s\"'=:/\\(])(workbook|harness|golden|decisions|tools|manual|build|audit|\.bob|\.github)[/\\]"
    r"|(^|[\s\"'=:/\\(])reports[/\\][^/\\\s\"']+\.(json|jsonl|html)\b"
    r"|AGENTS\.md|\.bobignore|sheetshift\.json|Makefile|CONTRACT\.md|\.xls[xm]\b|decide\.py")
SECRET = re.compile(r"BOB_API_KEY|-----BEGIN [A-Z ]*PRIVATE KEY"
                    r"|(?i:api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,})")
CMD_BLOCK = [
    (re.compile(r"decide\.py|decisions/"), "decisions are made by people"),
    (re.compile(r"\bgit\s+push\b"), "git push is done by people"),
    (re.compile(r"(python[\d.]*\s+-c|open\(|Path\().*"
                r"(workbook|harness|golden|decisions|tools|\.bob|\.github)/", re.S),
     "inline Python touching a protected path"),
]
EDIT_TOOLS = ("write_file", "apply_diff", "search_and_replace", "insert_content")
WRAPPERS = ("sudo", "env", "nohup", "time", "command", "exec", "builtin", "nice")
DEST_ONLY = ("cp", "install", "ln", "rsync", "scp")
ALL_ARGS = ("mv", "rm", "rmdir", "unlink", "touch", "truncate", "chmod", "chown", "tee",
            "shred", "mkdir")
GIT_WRITES = ("rm", "mv", "checkout", "restore", "apply")
SEPARATOR_CHARS = set("();|&\n")


class Blocked(Exception):
    """Raised with (reason, rel_path) when the call must be blocked."""


def protected(rel):
    """True if a repo-relative path is protected (or is Bob's global config)."""
    if rel == ".." or rel.startswith("../"):
        return "/.bob/" in rel + "/"
    return bool(PROTECTED.search(rel))


def check_path(p, base=None):
    """Raise Blocked if p resolves to a protected path; return its repo-relative form."""
    rel = C.rel_path(p, base)
    if protected(rel):
        raise Blocked("protected path", rel)
    return rel


def tokenize(cmd):
    """shlex tokens with shell punctuation split out; newlines act as separators."""
    lex = shlex.shlex(cmd, posix=True, punctuation_chars="();<>|&\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    return list(lex)


def split_commands(tokens):
    """Yield (argv, redirect_targets) for each simple command."""
    argv, targets, i = [], [], 0
    while i < len(tokens):
        t = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if t and set(t) <= SEPARATOR_CHARS:
            yield argv, targets
            argv, targets = [], []
        elif t and ">" in t and set(t) <= set("<>|&"):
            if t.endswith(">&") and nxt is not None and (nxt.isdigit() or nxt == "-"):
                pass  # fd duplication such as 2>&1
            elif nxt is not None:
                targets.append(nxt)
            i += 1
        elif t in ("<", "<<", "<<<"):
            i += 1  # input redirection: nothing is written
        else:
            argv.append(t)
        i += 1
    yield argv, targets


def strip_prefix(argv):
    """Drop leading VAR=value assignments and wrappers such as sudo or env."""
    while argv and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", argv[0])
                    or os.path.basename(argv[0]) in WRAPPERS):
        argv = argv[1:]
    return argv


def write_targets(argv):
    """Paths a simple command writes to, as far as argv shows."""
    if not argv:
        return []
    prog = os.path.basename(argv[0])
    args = argv[1:]
    plain = [a for a in args if not a.startswith("-")]
    if prog in DEST_ONLY:
        for j, a in enumerate(args):
            if a in ("-t", "--target-directory") and j + 1 < len(args):
                return [args[j + 1]]
            if a.startswith("--target-directory="):
                return [a.split("=", 1)[1]]
        return plain[-1:]
    if prog in ALL_ARGS:
        return plain
    if prog in ("sed", "perl") and any(re.match(r"^-[A-Za-z]*i", a) or a.startswith("--in-place")
                                       for a in args):
        return plain
    if prog == "dd":
        return [a[3:] for a in args if a.startswith("of=")]
    if prog == "git":
        rest, skip = [], False
        for a in args:
            if skip:
                skip = False
            elif a in ("-C", "-c", "--git-dir", "--work-tree", "--namespace"):
                skip = True
            elif not a.startswith("-"):
                rest.append(a)
        if rest and rest[0] == "push":
            raise Blocked("git push is done by people", None)
        if rest and rest[0] in GIT_WRITES:
            return rest[1:]
    return []


def check_command(cmd, base):
    """Raise Blocked for a protected write, decide.py, git push or inline Python on protected paths."""
    for rx, why in CMD_BLOCK:
        if rx.search(cmd):
            raise Blocked(why, None)
    for argv, targets in split_commands(tokenize(cmd)):
        argv = strip_prefix(argv)
        for t in targets:
            check_path(t, base)
        if argv and argv[0] == "cd" and len(argv) > 1:
            base = os.path.join(base, os.path.expanduser(argv[1]))
            continue
        for t in write_targets(argv):
            check_path(t, base)


def has_secret(raw, obj=None):
    """True if the raw payload, its unescaped form, or any string value holds a secret."""
    texts = [raw, raw.replace('\\"', '"')]
    stack = [obj]
    while stack:
        o = stack.pop()
        if isinstance(o, str):
            texts.append(o)
        elif isinstance(o, dict):
            stack.extend(o.values())
        elif isinstance(o, list):
            stack.extend(o)
    return any(SECRET.search(t) for t in texts)


def decide(payload):
    """Return (decision, reason, rel_path) for one PreToolUse payload."""
    if has_secret(payload.raw, payload.input):
        return "block", "secret in tool input", None
    base = os.getcwd()
    cwd = payload.input.get("cwd")
    if isinstance(cwd, str) and cwd.strip():
        base = os.path.join(base, cwd)
    try:
        rels = [check_path(p, base) for p in C.find_paths(payload.input)]
        command = payload.input.get("command") or payload.input.get("cmd")
        if isinstance(command, str):
            check_command(command, base)
        elif payload.tool in EDIT_TOOLS and not rels:
            raise ValueError("edit tool without a path field")
    except Blocked as b:
        return "block", b.args[0], b.args[1]
    return "allow", "", (rels[0] if rels else None)


def main():
    raw, who, rel = "", None, None
    try:
        raw = C.read_stdin(sys.stdin)
        who = C.handle()
        payload = C.Payload(raw)
        decision, reason, rel = decide(payload)
        C.append_jsonl(C.audit_path("hook_events.jsonl", who), {
            "ts": C.now(), "handle": who, "event": payload.event or "PreToolUse",
            "tool": payload.tool, "rel_path": C.loggable(rel), "decision": decision,
            "reason": reason})
        C.log_payload_keys(payload, who)
    except Exception as e:  # fail closed on anything that looks dangerous
        bad = bool(RAW_PROTECTED.search(raw) or has_secret(raw))
        decision, reason = ("block" if bad else "allow"), "guard_error: %s" % type(e).__name__
        try:
            C.append_jsonl(C.audit_path("hook_events.jsonl", who or "unknown"), {
                "ts": C.now(), "handle": who or "unknown", "event": "guard_error", "tool": None,
                "rel_path": None, "decision": decision, "reason": reason})
        except Exception:
            pass
    if decision == "block":
        where = (" (%s)" % C.loggable(rel)) if rel else ""
        sys.stderr.write("SheetShift guard blocked this call: %s%s\n" % (reason, where))
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
