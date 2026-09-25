"""PreToolUse guard: blocks Bob's writes to protected paths, decide.py, git push and secrets.

Exit 2 blocks the tool call; exit 0 allows it. The hook has no tool matcher: every tool is
checked except the ones that cannot write a workspace file (_common.never_writes: Bob's read tools
such as read_file, office_read, grep and glob, and path-less tools). Fails closed: if the payload cannot be parsed
or decided, the call is blocked when the raw text mentions a protected path together with a
write-like word (or holds a secret), else allowed. Every decision is appended to
audit/<handle>/hook_events.jsonl (repo-relative paths only); a logging failure never changes
the decision. Shell commands are checked in POSIX, PowerShell and cmd forms; backslash path
separators are normalised first.
Honest limit: this guard is best-effort (a shell can always find another way to write a file);
CI (tools/check_protected.py) is the enforcing control, this guard is the fast one.

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
    r"|^(AGENTS\.md|\.bobignore|sheetshift\.json|Makefile|ATTRIBUTION\.md|PROVENANCE\.md"
    r"|\.gitleaks\.toml|\.gitattributes)$"
    r"|^docs/CONTRACT\.md$"
    r"|^reports/[^/]+\.(json|jsonl|html)$"
    r"|^tests/test_(harness_selfcheck|no_env)\.py$"
    r"|^service/sheetshift_ho3/data/verify_sample_[^/]*$"
    r"|\.xls[xm]$", re.I)  # case-insensitive: macOS and Windows file systems ignore case
_NOT_PATH_CHAR = r"(?<![A-Za-z0-9_.-])"
PROTECTED_DIR = (r"(workbook|harness|golden|decisions|tools|manual|build|audit|\.bob|\.github)")
PROTECTED_WORD = re.compile(_NOT_PATH_CHAR + PROTECTED_DIR + r"(?![A-Za-z0-9_.-])", re.I)
RAW_PROTECTED = re.compile(
    _NOT_PATH_CHAR + PROTECTED_DIR + r"[/\\]"
    r"|" + _NOT_PATH_CHAR + r"reports[/\\][^/\\\s\"'<>]+\.(json|jsonl|html)\b"
    r"|AGENTS\.md|\.bobignore|sheetshift\.json|Makefile|CONTRACT\.md|\.gitleaks\.toml|\.xls[xm]\b|decide\.py",
    re.I)
SECRET = re.compile(r"BOB_API_KEY|-----BEGIN [A-Z ]*PRIVATE KEY"
                    r"|(?i:api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,})")
# Calls in inline Python (python -c, heredocs) that write, move or delete files.
PY_WRITE = re.compile(r"open\([^)]*(,\s*|mode\s*=\s*)['\"][rb]*[wax]|\.write(_text|_bytes)?\(|shutil\."
                      r"|\bos\.(rename|replace|remove|unlink|rmdir|makedirs|mkdir)\b|\.(unlink|rename|touch|mkdir)\(")
CMD_BLOCK = [
    (re.compile(r"decide\.py|tools[./]decide\b", re.I), "decisions are made by people"),
    (re.compile(r"\bgit\s+push\b"), "git push is done by people"),
]
EDIT_TOOLS = ("write_file", "apply_diff", "search_and_replace", "insert_content", "office_edit")
EDIT_LIKE = re.compile(r"write|edit|diff|replace|insert|patch|create|delete|remove|move|rename|append", re.I)
WRAPPERS = ("sudo", "env", "nohup", "time", "command", "exec", "builtin", "nice")
SHELLS = ("bash", "sh", "zsh", "dash", "ksh", "pwsh", "powershell", "cmd")
# POSIX and Windows (PowerShell, cmd) writers. DEST_ONLY writes only its last argument.
DEST_ONLY = ("cp", "install", "ln", "rsync", "scp", "copy-item", "cpi", "copy", "xcopy")
ALL_ARGS = ("mv", "rm", "rmdir", "unlink", "touch", "truncate", "chmod", "chown", "tee",
            "shred", "mkdir", "move-item", "mi", "move", "robocopy", "remove-item", "ri", "del",
            "erase", "rd", "set-content", "sc", "add-content", "ac", "out-file", "new-item", "ni",
            "clear-content", "rename-item", "ren", "patch")
PS_PATH_PARAMS = ("-path", "-literalpath", "-destination", "-filepath", "-target")
WIN_WRITE_VERB = re.compile(
    r"(^|[;&|(\n])\s*(copy-item|cpi|xcopy|robocopy|move-item|remove-item|set-content|add-content|out-file|"
    r"new-item|clear-content|rename-item|copy|move|del|erase|ren)(\.exe)?(?=\s)", re.I)
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


def prog_name(arg):
    """'C:/x/Copy-Item.exe' -> 'copy-item'."""
    name = os.path.basename(arg.replace("\\", "/")).lower()
    return name[:-4] if name.endswith(".exe") else name


def write_targets(argv):
    """Paths a simple command writes to, as far as argv shows."""
    if not argv:
        return []
    prog = prog_name(argv[0])
    args = argv[1:]
    plain = [a for a in args if not a.startswith("-")]
    params = []
    for j, a in enumerate(args):
        low = a.lower()
        if low in PS_PATH_PARAMS and j + 1 < len(args):
            params.append(args[j + 1])
        elif low.split(":", 1)[0] in PS_PATH_PARAMS and ":" in low:
            params.append(a.split(":", 1)[1])
    if prog in DEST_ONLY:
        for j, a in enumerate(args):
            if a in ("-t", "--target-directory") and j + 1 < len(args):
                return [args[j + 1]]
            if a.startswith("--target-directory="):
                return [a.split("=", 1)[1]]
        dest = [args[j + 1] for j, a in enumerate(args)
                if a.lower() in ("-destination", "-target") and j + 1 < len(args)]
        return dest or (plain[-1:] + params)
    if prog in ALL_ARGS:
        return plain + params
    if prog in ("sed", "perl") and any(re.match(r"^-[A-Za-z]*i", a) or a.startswith("--in-place")
                                       for a in args):
        return plain
    if prog == "find" and any(a in ("-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint") for a in args):
        return plain
    if prog == "dd":
        return [a[3:] for a in args if a.startswith("of=")]
    if prog == "git":
        rest, skip, cdir = [], None, None
        for a in args:
            if skip:
                if skip == "-C":
                    cdir = a
                skip = None
            elif a in ("-C", "-c", "--git-dir", "--work-tree", "--namespace"):
                skip = a
            elif not a.startswith("-"):
                rest.append(a)
        if rest and rest[0] == "push":
            raise Blocked("git push is done by people", None)
        if rest and rest[0] in GIT_WRITES:
            return [os.path.join(cdir, t) if cdir else t for t in rest[1:]]
    return []


def normalise(cmd):
    """Backslashes that separate path parts become '/', so `harness\\x.py` is seen as a path
    (the same on every platform; escapes before whitespace, quotes and shell punctuation stay)."""
    return re.sub(r"\\(?![\s\"';&|()<>])", "/", cmd)


def raw_command_checks(cmd):
    """Text-level backstops that do not depend on tokenising the command."""
    for m in re.finditer(r">{1,2}\|?\s*(\S+)", cmd):  # a redirect straight into a protected path
        if RAW_PROTECTED.search(" " + m.group(1)):
            raise Blocked("redirect into a protected path", None)
    if re.search(r"\bpython[\d.]*\b", cmd, re.I) and PY_WRITE.search(cmd) \
            and re.search(_NOT_PATH_CHAR + PROTECTED_DIR + r"/", cmd, re.I):
        raise Blocked("inline Python writing a protected path", None)


def check_command(cmd, base, depth=0):
    """Raise Blocked for a protected write, decide.py, git push or inline Python writing protected paths."""
    cmd = normalise(cmd)
    for rx, why in CMD_BLOCK:
        if rx.search(cmd):
            raise Blocked(why, None)
    raw_command_checks(cmd)
    try:
        tokens = tokenize(cmd)
    except ValueError:  # unbalanced quotes (e.g. an apostrophe in a heredoc): text checks decide
        if WIN_WRITE_VERB.search(cmd) and RAW_PROTECTED.search(cmd):
            raise Blocked("write command naming a protected path", None)
        if re.search(r"(^|[;&|(\n])\s*(sudo\s+)?(rm|mv|cp|tee|touch|truncate|sed\s+-i|chmod|ln|install)\b", cmd) \
                and RAW_PROTECTED.search(cmd):
            raise Blocked("write command naming a protected path", None)
        return
    for argv, targets in split_commands(tokens):
        argv = strip_prefix(argv)
        for t in targets:
            check_path(t, base)
        if not argv:
            continue
        prog = prog_name(argv[0])
        if prog in ("cd", "pushd", "set-location", "sl", "chdir") and len(argv) > 1:
            base = os.path.join(base, os.path.expanduser(argv[-1]))
            continue
        if prog in SHELLS and depth < 3:
            for j, a in enumerate(argv[1:-1], 1):
                if a.lower() in ("-c", "/c", "-command"):
                    check_command(argv[j + 1], base, depth + 1)
        if prog == "xargs":
            inner = [a for a in argv[1:] if not a.startswith("-")]
            if inner and (write_targets(inner + ["x"]) or prog_name(inner[0]) in ALL_ARGS + DEST_ONLY) \
                    and (RAW_PROTECTED.search(cmd) or PROTECTED_WORD.search(cmd)):
                raise Blocked("xargs writer on a protected path", None)
        if prog == "patch" and RAW_PROTECTED.search(cmd):
            raise Blocked("patch naming a protected path", None)
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
    if C.never_writes(payload.tool):
        return "allow", "tool writes no workspace file", None
    base = os.getcwd()
    cwd = payload.input.get("cwd")
    if isinstance(cwd, str) and cwd.strip():
        base = os.path.join(base, cwd)
    try:
        rels = [check_path(p, base) for p in C.find_paths(payload.input)]
        command = payload.input.get("command") or payload.input.get("cmd")
        if isinstance(command, str):
            check_command(command, base)
        elif not rels and (payload.tool in EDIT_TOOLS or EDIT_LIKE.search(payload.tool or "")):
            raise ValueError("edit tool without a path field")
    except Blocked as b:
        return "block", b.args[0], b.args[1]
    return "allow", "", (rels[0] if rels else None)


RAW_WRITE = re.compile(r">|write|edit|diff|replace|insert|content|command|\b(rm|mv|cp|del|move|copy)\b", re.I)


def main():
    raw, who, rel, payload = "", None, None, None
    try:
        raw = C.read_stdin(sys.stdin)
        payload = C.Payload(raw)
        decision, reason, rel = decide(payload)
    except Exception as e:  # fail closed on anything that looks dangerous
        bad = bool((RAW_PROTECTED.search(raw) and RAW_WRITE.search(raw)) or has_secret(raw))
        decision, reason = ("block" if bad else "allow"), "guard_error: %s" % type(e).__name__
    # Logging never changes the decision computed above.
    try:
        who = C.handle()
        C.append_jsonl(C.audit_path("hook_events.jsonl", who), {
            "ts": C.now(), "handle": who,
            "event": (payload.event or "PreToolUse") if payload else "guard_error",
            "tool": payload.tool if payload else None, "rel_path": C.loggable(rel),
            "decision": decision, "reason": reason})
        if payload:
            C.log_payload_keys(payload, who)
    except Exception:
        pass
    if decision == "block":
        where = (" (%s)" % C.loggable(rel)) if rel else ""
        sys.stderr.write("SheetShift guard blocked this call: %s%s\n" % (reason, where))
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
