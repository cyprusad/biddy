# Canadian Procurement Matchmaker

A small Vercel demo for inspecting CanadaBuys records, finding deterministic supplier/retendering candidates, and optionally assessing selected pairs with Jev.

## Local setup

Requires Python 3.9+ and Node.js 20+.

```sh
npm install
npm run dev
```

The checked-in `public/data` files are a dated snapshot from the official CSVs. Refresh and prepare them with:

```sh
python3 download_data.py --refresh
npm run snapshot
```

Review the snapshot manifest and commit updated `public/data` artifacts before deploying. The current schema and source field meanings are documented in the CanadaBuys data dictionary XML.

## Jev

Copy `.env.example` to `.env.local`, set `OPENROUTER_API_KEY`, and optionally set `DEMO_RUN_TOKEN`. The key is read only by `api/assess.py`; never prefix it with `VITE_`. If a demo code is configured, send it as `x-demo-token` from the assessment UI. Assessment happens only after a user clicks the Jev button. The UI sends up to 50 selected or top-ranked candidates in one OpenRouter Decisions request; Jev returns one typed choice and probability set per candidate. That can bill for multiple judgments even though it is one HTTP request.

## Deploy

Import this repository directory in Vercel. Configure `OPENROUTER_API_KEY` and a `DEMO_RUN_TOKEN` for live Jev assessments. Vercel builds the Vite app to `dist` and serves Python API functions under `/api`.

The app uses no database. Dataset snapshots are deployed as static JSON; recent assessments are kept in the visitor's browser. The original CLI remains available:

```sh
python3 main.py --max-tenders 10
python3 main.py --max-tenders 10 --reuse-decisions
```

Sources and schemas: official [tender dataset](https://open.canada.ca/data/en/dataset/6abd20d4-7a1c-4b38-baa2-9525d0bb2fd2), [contract history](https://open.canada.ca/data/en/dataset/4fe645a1-ffcd-40c1-9385-2c771be956a4), and [combined data dictionary](https://donnees-data.tpsgc-pwgsc.gc.ca/ba2/ac-cb/achatscanada-canadabuys-dd.xml).
