# Luna implementation handoff: minimal procurement demo

## Objective and scope

Implement this plan in the existing `procurement-matchmaker` Git repository. The user wants a shareable, Vercel-compatible demo with spreadsheet views of the three actual datasets and two workflows: potential suppliers and retendering signals. React is now explicitly requested, superseding the original static-only restriction. Keep the original restrained appearance and auditable evidence.

This document is the planning deliverable. No UI implementation, dependency installation, deployment, or paid model calls were performed while preparing it. Work sequentially; no subagents are needed. Preserve the existing CLI/report and saved responses. Do not touch the adjacent `ai-detective-demo` project.

## Chosen approach

- React + TypeScript + Vite, plain CSS.
- AG Grid **Community**, MIT licensed, for read-only dataset and result grids. Sorting, text filtering, column resizing, horizontal scrolling, and virtualization. Do not install Enterprise or build a spreadsheet editor.
- Keep Python for CSV parsing, normalization, deterministic matching, and OpenRouter calls. Extract reusable functions from `main.py`; use small Vercel Python functions with the documented standard-library HTTP handler. Do not introduce another web framework or duplicate matching rules in JavaScript.
- Ship a fixed, dated public-data snapshot with the deployment. Generate JSON locally from the cached CSVs using Python's `csv` module. Track the generated snapshot artifacts so a fresh Vercel checkout builds without CanadaBuys downloads or untracked local files.
- Server functions read immutable bundled records; no runtime file writes, SQLite, database, uploads, accounts, background jobs, or scheduled refresh. New data means running the existing downloader and snapshot preparation script, then redeploying.
- Browser memory holds loaded grid data. Store only the latest small result sets and successful assessments in localStorage, keyed by snapshot hash and rules/prompt version. Handle disabled/full browser storage without breaking the UI. Never put datasets or API credentials there.

Vercel functions have a read-only filesystem and temporary scratch space; persistent SQLite on the instance is not a suitable default. The dataset snapshot plus browser result storage is enough for this demo.

## Current repository facts

- `main.py`: normalization, matching, Jev calls, and report rendering are combined.
- `download_data.py`: cached downloads, CSV inspection, metadata hashes.
- `report.html`, `decisions.json`: real outputs already committed by the user.
- `README.md`: outdated; incorrectly says no implementation/data/model results exist. Replace with current instructions during implementation.
- `data/` is Git-ignored. Vercel will not receive it automatically.
- Snapshot downloaded November 18, 2026, approximately 22:40 UTC:

| CSV | Bytes | Parsed records |
| --- | ---: | ---: |
| Open tender notices | 6,409,483 | 937 |
| Contract history 2025–26 | 15,318,448 | 5,734 |
| Contract history 2026–27 | 6,741,384 | 2,466 |

The XML data dictionary is present locally. Inspect its date, amendment, buyer, and category definitions before changing those rules.

Fifty successful Jev responses exist in the saved audit, including exact model build and probabilities. These resulted mostly in poor matches because the existing candidate generator is too broad. Preserve them as historical evidence; do not present them as validation of improved matching.

## Screens and interactions

Three top-level tabs, one page: **Datasets | Supplier matches | Retendering**. No separate dashboard or landing page. Header: project name, snapshot retrieval date, and a brief description. System font, white background, dark text, thin grey rules; compact, readable controls and tables.

### Datasets

- Three dataset sub-tabs, showing each file's name, size, row count, and retrieval timestamp.
- Lazy-load the selected dataset JSON. Display all source rows, including repeated/amendment rows; this is the raw-data view.
- Default columns: identifier, title, buyer, dates, supplier/value where applicable. An ordinary column selector enables every original bilingual column, with raw field names available. No Enterprise sidebar.
- Search, sortable columns, column filters, and resizable columns. Keep a bounded grid height and row/column virtualization. Do not render thousands of HTML rows at once.
- Row selection opens a simple detail area with full description, source identifiers, original fields, and source/search links. Render source content as plain text, never injected HTML.
- From a tender detail, “Find potential suppliers”; from a contract detail, “Find related tenders.” These navigate to and preselect the corresponding workflow. If a record is closed or outside the expiry window, show that clearly.

### Supplier matches

1. Select one open tender from the snapshot; show title, buyer, closing timestamp and scope. Default to newest published eligible technology tender. Allow an optional batch of at most 10 tenders.
2. **Find candidates** performs deterministic matching, yielding at most five distinct standardized suppliers per tender. Show overlap evidence and up to three historical contracts per supplier. Zero candidates is valid.
3. **Assess with Jev** explicitly evaluates selected candidates, showing the number of new decisions before starting. No paid calls on load, tab change, or grid selection.
4. Results grid: RFP, buyer, closes, supplier, deterministic evidence, Jev choice, previous contract references. Row details show source scope, category codes, returned probabilities, exact model build, and assessment time. Do not generate explanatory prose attributed to Jev.

### Retendering

1. Select an expiring contract, or run the next-365-days batch. Technology filter on by default; expose it visibly.
2. **Find related tenders** searches all eligible open tenders, independently of the supplier screen's 10-tender limit. Show at most three credible candidates per expiring contract and count all eligible expiries.
3. **Assess with Jev** evaluates selected ambiguous pairs. Display the typed Jev choice separately from the evidence-based relationship label.
4. Results grid: expiring contract, buyer, recorded end date, related RFP, deterministic evidence, relationship, Jev assessment. Preserve no-match rows. Unrelated assessments must not remain positive retender signals.

Both result tabs are the reports. Provide “Download HTML” and “Download audit JSON” for the current result set, without rerunning matching or Jev. Include snapshot date, analysis time, filters, source IDs, model versions, and partial/failed assessments. Opening the shared URL should immediately show a clearly labelled saved example if one has been prepared; users can then run either workflow.

## Fix the existing matching defects before exposing them

These are observed in `main.py`, not speculative enhancements:

1. Closing-date parsing truncates timestamps and includes already-closed notices for the entire day. Parse timestamps according to the dictionary and apply status plus a strictly future close time. Use an explicit analysis timestamp and disclose timezone assumptions. Distinguish a dated snapshot analysis from current live opportunities; old snapshots must not silently appear current.
2. Technology filtering matches generic words anywhere in long descriptions, including boilerplate. Prefer relevant GSIN/UNSPSC codes/descriptions and specific technology terms in titles/scope. Do not qualify unrelated goods solely because their description mentions data or a website.
3. `procurementCategory` values such as “Goods” or “Services” are too broad to establish overlap. Compare parsed specific GSIN/UNSPSC codes and defensible code families. Buyer-only matches also need scope evidence. Require meaningful category or text evidence before ranking; never fill five slots just to reach the limit.
4. Precompute normalized text/tokens per record; avoid tokenizing full descriptions inside every pair loop. Remove shared boilerplate from similarity inputs. Keep named thresholds and scores auditable.
5. Existing amendment grouping uses contract number alone and award-date priority. Inspect real history and dictionary; use an appropriate identity key including buyer/supplier where needed, latest explicit amendment sequence/date, and flag conflicting or missing end dates. Never silently resolve uncertain expiry histories.
6. Shared buyer/category does not settle semantic equivalence. The current supplier condition `best[2] and best[3]` actually checks buyer and a nonzero similarity number while labelling it category overlap. Replace positional tuples with named fields and show their actual evidence.
7. Retendering currently searches only the 10 supplier-screen tenders. Correct that. Exact meaningful identifiers support a documented connection, not a confirmed replacement. No-match text must acknowledge the snapshot/search scope.
8. Cached retender responses currently fail to assign the displayed `relation`. Fix this. Separate API attempts, successful assessments, failures, cache hits, and unevaluated pairs; `count` currently conflates them.
9. `--reuse-decisions` can still call the API on cache misses. Make it strictly offline. Cache validity requires model/prompt/rules versions plus input content hashes, not IDs alone. Preserve previous successful records and save new responses immediately so a later rendering failure cannot erase them.
10. Links must use actual source URLs when available and clearly labelled CanadaBuys search links otherwise. Allow only http/https URLs. Include identifiers in every row, and inspect several real tender and contract links. A search link is not a verified direct notice link.

Do not fix unrelated application behavior or start a broad rewrite. Factor the necessary functions so the CLI and web endpoints share these corrected rules.

## Data preparation and API boundary

Suggested structure (combine small files where clearer):

```text
main.py                         # existing CLI, using shared functions
matching.py                     # pure normalization/filter/candidate functions
jev.py                          # typed Decisions request/response handling
api/matches.py                  # deterministic supplier/retender request
api/assess.py                   # one validated candidate assessment
scripts/prepare_snapshot.py     # standard CSV parsing; emits tracked artifacts
snapshot/records.json           # normalized server evidence, hashes, versions
public/data/manifest.json       # provenance, file counts, sizes, snapshot hash
public/data/tenders.json        # raw field names + rows, all original columns
public/data/contracts-2025.json
public/data/contracts-2026.json
public/demo/results.json        # clearly dated example, generated from real records
src/App.tsx
src/components/DatasetGrid.tsx
src/components/ResultsGrid.tsx
src/styles.css
package.json / package-lock.json / vite.config.ts / vercel.json
```

Generated raw JSON must preserve strings (leading zeros, identifiers, multiline values). Keep original CSVs unchanged locally. The XML dictionary need not load into the browser. Verify the Vercel function bundle includes `snapshot/records.json` and shared Python modules; it must work from a fresh checkout. Pin runtime/dependency versions in the project, following current official docs.

`POST /api/matches`: `{flow, snapshotId, asOf, selectedIds, maxTenders, technologyOnly}`. Validate allowed IDs, dates, and limits server-side. Return normalized subject/evidence references, deterministic scores/reasons, candidate IDs, omitted/uncertain counts, and metadata. Use the immutable snapshot as the source of truth.

`POST /api/assess`: accept a bounded candidate reference (flow, subject ID, supplier/history IDs or tender ID, snapshotId), not arbitrary prompts or client-provided source text. Resolve and validate it against server records. Construct one typed question with the original four choices for that flow, using `typesafe/jev-1.14` and the documented Decisions API. Preserve returned choice, probabilities when present, exact model build, response ID, source references and input/prompt hashes. Validate choice membership and response schema, not just `type`.

The browser queues individual assessments with at most two in flight, maximum 50 new decisions across a run; default to assessing only selected rows. This avoids a single long function request. Server validation also bounds each request and allowed candidate scope. Stop on authentication, quota, DNS, or repeated upstream failure; show actionable status. Do not retry paid requests automatically when the outcome is unknown. Persist each successful browser result immediately. Refreshing must never automatically resume paid calls.

`OPENROUTER_API_KEY` stays in Vercel server environment variables, never `VITE_*`, JavaScript bundles, reports, or logs. Public browsing and saved examples should work without it. To avoid exposing the owner's paid endpoint to unrestricted visitors, use a simple shared demo code for live assessment (`DEMO_RUN_TOKEN`, server checked, entered only when running live); no accounts or auth framework. Do not describe a per-browser cap or an in-memory counter as a global spending limit. Configure a provider-side credit limit for the deployment key before broad public sharing.

## Implementation order and completion checks

1. Preserve a copy of existing successful outputs. Extract/correct core matching, add focused regression tests for the defects above, and prepare the tracked snapshot and manifest. Keep the CLI usable.
2. Build the React shell and three raw-data grids. Confirm exact row counts, bilingual fields, multiline text, sorting/filtering and detail views on actual data.
3. Wire the two deterministic flows to Python functions. Confirm dates/categories exclude the obvious unrelated examples from the old report, distinct supplier grouping, uncertain expiry handling, and all-open-tender retender search.
4. Add Jev assessment controls, server secret handling, typed results, progress/error states, and offline cached results. Reuse legacy responses only when inputs are actually identical and clearly mark legacy provenance; do not use them to fake responses for improved candidates.
5. Add report/audit downloads and a small truthful saved example. Update README with one local dev command, snapshot preparation, CLI commands, and deployment steps. Existing `--evaluate` is a no-op: disclose this pending original task; don't claim evaluation metrics or invent human labels.
6. Run focused Python tests, frontend production build/type checking, and browser checks for all three tabs. Exercise mocked upstream errors and reload behavior. Check API missing-key/code behavior and secret exclusion. Make one live assessment for each flow if execution networking works; no bulk 50-call smoke test.
7. Verify `vercel dev` serves both Vite and Python routes. Document any local tool limits. Configure Vercel root as this repository directory, build `npm run build`, output `dist`; preserve `/api/*` routes when adding SPA fallback. Verify with Vercel's build tooling when available. Do not guess deployment success.
8. When Vercel account access is available, deploy and verify the returned URL: dataset loading, deterministic flow, one small live run, downloaded reports. If access is unavailable, leave a fully buildable project with exact import/environment instructions and state that the live URL remains outstanding.

Acceptance: a recipient opens one URL, browses each real dataset, runs either workflow, sees deterministic evidence and optional Jev assessments, and downloads the report. No database or filesystem persistence is required. No new Jev spending occurs just from viewing the site.

## Official references checked for this plan

- AG Grid Community/Enterprise boundary: https://www.ag-grid.com/react-data-grid/community-vs-enterprise/
- React installation: https://www.ag-grid.com/react-data-grid/installation/
- AG Grid MIT license/feature summary: https://github.com/ag-grid/ag-grid/blob/latest/packages/ag-grid-react/README.md
- Vite deployment: https://vercel.com/docs/frameworks/frontend/vite
- Python handlers/runtime: https://vercel.com/docs/functions/runtimes/python
- Filesystem constraints: https://vercel.com/docs/functions/runtimes
- Decisions schema: https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request

Execution note: this agent's sandbox previously blocked DNS and Rex socket access, while the user's ordinary Rex pane could call OpenRouter successfully. That was not a Mac DNS failure. Do not change system DNS or bypass sandbox restrictions. Distinguish unattempted/failed API requests from completed billable decisions.
