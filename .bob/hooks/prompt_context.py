"""UserPromptSubmit hook: print one status line (<= 120 chars) into Bob's context.

Example: "SheetShift: smoke U2 200/200 equal; decisions pending: D-001, D-002".
Wrapped so it can never block a prompt: any error prints nothing and exits 0.

Standard library only; Python 3.8+.
Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import os
import sys

MAX_CHARS = 120


def line():
    """The status line from reports/smoke_last.json and reports/decision_queue.json."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _common as C
    pending = C.pending_decisions()
    tail = ("; decisions pending: " + ", ".join(pending)) if pending else ""
    head = "SheetShift: " + C.smoke_summary()
    room = MAX_CHARS - len(tail)
    if len(head) > room:  # shorten the smoke part first, so decisions stay visible
        head = head[:max(room - 3, 20)] + "..."
    text = head + tail
    return text if len(text) <= MAX_CHARS else text[:MAX_CHARS - 3] + "..."


def log_keys():
    """Record this event's payload key names (never values) for the T00 probe."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import _common as C
        C.log_payload_keys(C.Payload(C.read_stdin(sys.stdin)))
    except Exception:
        pass


def main():
    try:
        log_keys()
        print(line())
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
