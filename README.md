# Canadian Procurement Matchmaker — setup only

Implementation is intentionally deferred to Luna. No model calls, application,
matching logic, report, or evaluation have been built.

Python 3.9+; no dependencies. From this directory:

```sh
python3 download_data.py
python3 download_data.py --refresh
```

The downloader caches the three requested official CSVs and the published XML
data dictionary in `data/`. It prints bytes, parsed record counts, retrieval
timestamps, and actual column names. CSV parsing handles BOM and quoted multiline
fields. Failed downloads do not replace existing files. HTTP/network errors are
reported without attempting to bypass access restrictions.

For manual downloads, save files using the exact names printed by the downloader
in `data/`, then rerun without `--refresh`. Manual retrieval timestamps remain
unknown rather than being inferred from file modification times.

## Current status and handoff to Luna

- Download attempts in the Codex terminal failed with DNS resolution errors.
- The web reader cannot save the CSV or XML attachments.
- No input records are downloaded yet; actual sizes/counts and schemas are unknown.
- `OPENROUTER_API_KEY` was present in the environment; its value was not read out
  or persisted. Zero Jev calls made.
- First run the downloader in a terminal with network access or download manually.
- Inspect the CSV headers and dictionary before implementing field mappings.
- Then implement a deterministic vertical slice: normalization, amendment handling,
  technology prioritization, supplier candidates, expiries, plain `report.html`
  and auditable `decisions.json`. Keep the original task's limits (10 tenders,
  5 suppliers each, 50 model decisions per run).
- Add Jev supplier/retendering choices only after that slice works, then meaningful
  unit tests and real labeled evaluation. Human labels must actually be supplied
  by a human; do not fabricate labels or metrics.

Official sources:

- [Tender dataset](https://open.canada.ca/data/en/dataset/6abd20d4-7a1c-4b38-baa2-9525d0bb2fd2)
- [Contract history dataset](https://open.canada.ca/data/en/dataset/4fe645a1-ffcd-40c1-9385-2c771be956a4)
- [Data dictionary](https://donnees-data.tpsgc-pwgsc.gc.ca/ba2/ac-cb/achatscanada-canadabuys-dd.xml)
- [OpenRouter Decisions API](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request)
- [OpenRouter's request/response reference](https://github.com/OpenRouterTeam/skills/blob/main/skills/openrouter-decisions/references/decisions-api.md)

The official catalog reports a March–April 2026 contract-history schema update.
It describes annual files as initial-award fiscal-year cohorts including subsequent
amendments; do not assume rows are independent contracts or sum amendment values.

Verified API shape from OpenRouter's reference: POST
`https://openrouter.ai/api/alpha/decisions`, bearer auth, model
`typesafe/jev-1.14`, `state`, and `questions` keyed by question ID. A choice
question uses `type: choice`, `instructions`, and a `criteria` object mapping
option labels to definitions. Read `answers[question_id].choice`, optional
`probabilities` and `confidence`, and the response's exact `model` build.
