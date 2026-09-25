"""Stop hook: append one run-log record {ts, session_id, handle, smoke} to reports/run_log.jsonl.

It never writes the certificate; only `python3 -m harness.certify` does, run by a person or CI.
Always exits 0.

Standard library only; Python 3.8+.
Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402


def main():
    try:
        payload = C.Payload(C.read_stdin(sys.stdin))
        who = C.handle()
        C.append_jsonl(os.path.join(C.REPORTS, "run_log.jsonl"), {
            "ts": C.now(), "session_id": payload.session_id, "handle": who,
            "smoke": C.smoke_summary()})
        C.log_payload_keys(payload, who)
    except Exception as e:
        sys.stderr.write("stop_report: %s\n" % type(e).__name__)
    sys.exit(0)


if __name__ == "__main__":
    main()
