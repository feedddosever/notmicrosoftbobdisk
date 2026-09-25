# Sheet Translator

- Translate the column rule. Ignore single-cell exceptions such as `Calc!AM17` or `Calc!X31`; the harness handles them as anomalies.
- If a column rule disagrees with its table or the manual, still translate the rule faithfully. Add `# SHEETSHIFT-FLAG <id>: <reason>` and do not fix it.
- Implement a decision only when `decisions/decisions.jsonl` records it, with one test per decision.
