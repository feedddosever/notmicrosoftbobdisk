"""SessionStart hook: print open mismatch groups, pending decisions and the Python version.

The printed lines are added to Bob's context once per session. There is no coin line,
because hooks cannot read the gauge. Always exits 0.

Standard library only; Python 3.8+.
Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import os
import sys


def lines():
    """Up to five short status lines."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _common as C
    v = sys.version_info
    out = ["SheetShift session. Python %d.%d.%d." % (v[0], v[1], v[2])]
    if v < (3, 11):
        out.append("Warning: harness and service target Python 3.12 (3.11 works); hooks still work on 3.8+.")
    groups = C.open_groups()
    if groups:
        shown = ", ".join("%s %s %s" % (g.get("id"), g.get("class"), g.get("cell", ""))
                          for g in groups[:4])
        out.append("Open mismatch groups: %d (%s)" % (len(groups), shown))
    else:
        out.append("Open mismatch groups: 0 (or /shift-verify not run yet)")
    pending = C.pending_decisions()
    out.append("Pending decisions: " + (", ".join(pending) if pending else "none"))
    out.append(C.smoke_summary())
    if C.handle() == "unknown":
        out.append("Note: git config sheetshift.handle is unset; audit logs go to audit/unknown/.")
    return out


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
        print("\n".join(lines()))
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
