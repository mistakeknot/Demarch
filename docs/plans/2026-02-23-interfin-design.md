# Design: interfin — Local Business Expense & Receipt Tracker

## Problem

Tracking recurring AI/dev-tool subscription expenses for tax deductions is tedious. Receipts arrive as PDF invoices from vendor portals with inconsistent names. Bank CSV exports need manual categorization. There's no lightweight local tool that handles both flows, links receipts to transactions, and produces audit-ready reports — without requiring a paid SaaS service.

## Solution

**interfin** is a hybrid: a standalone Python CLI tool (`apps/interfin/`) plus a thin Interverse plugin (`interverse/interfin/`) that adds Claude-assisted workflows.

The CLI handles: CSV bank export ingestion, PDF invoice extraction and renaming, vendor categorization via configurable regex rules, receipt-to-transaction linking, and report/audit-pack generation. All data stays local in a SQLite database.

The plugin provides four skills that wrap the CLI with Claude's reasoning for ambiguous categorization, natural language expense queries, and interactive receipt matching.

## Architecture

```
PDF invoices ──→ extract text ──→ parse vendor/amount/date ──→ SQLite
                 (pdfplumber)     (vendor rules + fallback)       ↑
                                                                  │
Bank CSV     ──→ map columns  ──→ normalize transactions    ─────┘
                 (column_maps.yml) (vendors.yml)                  │
                                                                  ↓
                                                           Reports + Audit Packs
```

Both ingestion paths feed into the same SQLite database with a canonical transaction schema. PDFs get renamed to `YYYY-MM-DD_vendor_amount.pdf` and archived. A link table matches receipts to transactions by date + amount + vendor with confidence scoring.

## Database Schema

Three tables:

```sql
transactions (
  id            TEXT PRIMARY KEY,   -- SHA-256(date|amount|description|account)
  date          TEXT NOT NULL,      -- YYYY-MM-DD
  description   TEXT NOT NULL,      -- raw from bank CSV
  merchant      TEXT,               -- normalized vendor name (from rules)
  amount        REAL NOT NULL,      -- always negative for expenses
  currency      TEXT DEFAULT 'USD',
  category      TEXT,               -- AI Software, Dev Tools, Cloud Infra, etc.
  subcategory   TEXT,               -- Claude, OpenAI, Vercel, etc.
  account       TEXT,               -- "Chase Ink" etc.
  card_last4    TEXT,
  source_file   TEXT NOT NULL,
  notes         TEXT,
  created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(id)
)

receipts (
  id              TEXT PRIMARY KEY, -- SHA-256 of file content
  original_name   TEXT NOT NULL,
  canonical_name  TEXT NOT NULL,    -- YYYY-MM-DD_vendor_amount.pdf
  vendor          TEXT,
  amount          REAL,
  date            TEXT,
  raw_text        TEXT,             -- full extracted text for re-parsing
  file_path       TEXT NOT NULL,
  source_dir      TEXT NOT NULL,
  created_at      TEXT DEFAULT CURRENT_TIMESTAMP
)

transaction_receipts (
  transaction_id  TEXT REFERENCES transactions(id),
  receipt_id      TEXT REFERENCES receipts(id),
  match_type      TEXT,             -- 'auto' or 'manual'
  confidence      REAL,             -- 0.0-1.0 for auto-matches
  PRIMARY KEY (transaction_id, receipt_id)
)
```

**Idempotency:** Transaction IDs are hashed from `date|amount|description|account`. Receipt IDs are hashed from file content. Re-ingesting the same data is a no-op via UNIQUE constraints.

**`raw_text` on receipts:** Stores full extracted PDF text so categorization rules can be re-run without re-parsing the PDF.

## CLI Commands

Single entrypoint: `interfin` (via `uv run interfin` or `python -m interfin`).

| Command | Purpose |
|---|---|
| `ingest csv <path> --account "Chase Ink" --card-last4 1234` | Import bank CSV export |
| `ingest receipts <dir> [--archive-to <dir>]` | Scan folder for PDFs, extract, rename, archive |
| `categorize [--uncategorized-only]` | Re-run vendor rules (after editing vendors.yml) |
| `link [--month 2026-02] [--threshold 0.8]` | Auto-match receipts to transactions |
| `report --month 2026-02` / `report --year 2026` | Generate markdown + CSV summaries |
| `audit-pack --month 2026-02` | Assemble audit folder with all artifacts |
| `status` | Dashboard: totals, unlinked receipts, uncategorized items |

## PDF Extraction Pipeline

Three stages:

1. **Extract text** — `pdfplumber` extracts all text from all pages into a single string.
2. **Parse fields** — Vendor-specific `extract` patterns in `vendors.yml` find amount and date. Falls back to generic patterns for unknown vendors.
3. **Rename + archive** — Rename to `YYYY-MM-DD_vendor_amount.pdf`, move to `data/receipts/`, insert into `receipts` table.

Vendor extraction profiles extend the existing `vendors.yml`:

```yaml
vendors:
  - match: "(?i)anthropic|claude"
    merchant: "Anthropic"
    category: "AI Software"
    subcategory: "Claude"
    extract:
      amount: '(?:Total|Amount Due)[:\s]*\$?([\d,]+\.\d{2})'
      date: '(?:Invoice Date|Date)[:\s]*(\d{4}-\d{2}-\d{2}|\w+ \d{1,2},?\s*\d{4})'
```

Generic fallback patterns handle invoices from unrecognized vendors:
- **Amount:** matches "Total", "Amount Due", "Balance Due" labels, or falls back to largest dollar figure.
- **Date:** tries ISO, "Month DD, YYYY", and MM/DD/YYYY formats, picks most recent.

Failed extractions are stored with NULL fields. The `status` command flags these, and the Claude Code plugin skill helps resolve them.

## Vendor Rules (shipped out of the box)

7 categories, ~30 vendors:

| Category | Vendors |
|---|---|
| AI Software | Anthropic, OpenAI, Google AI, Midjourney, Cursor, Replicate |
| Cloud Infra | Hetzner, AWS, GCP, DigitalOcean, Neon, Supabase |
| Platform | Cloudflare, Vercel, Netlify, Railway, Fly.io, Render |
| Dev Tools | GitHub, GitLab, Linear, Notion, Figma, 1Password, Tailscale, Postmark, Resend |
| Domains & Web | Squarespace, Namecheap, GoDaddy, Porkbun |
| Communication | Slack, Zoom, Discord |
| Other | Uncategorized fallback |

Rules are regex-based in `vendors.yml`. First match wins. Adding new vendors requires no code changes.

## Interverse Plugin Skills

The plugin at `interverse/interfin/` provides four skills:

**`/interfin:ingest`** — Guided ingestion. Walks through importing CSVs and/or PDF folders. After import, identifies uncategorized items, reads their descriptions, and suggests vendor rules to add.

**`/interfin:review`** — Conversational analysis. Natural language questions about expenses ("What did I spend on AI tools this quarter?", "Show month-over-month cloud infra trend"). Reads SQLite directly, no data leaves the machine.

**`/interfin:link`** — Receipt matching assist. Presents auto-match results, resolves low-confidence matches interactively, reads PDF raw text to identify vendors that regex rules missed.

**`/interfin:audit`** — Audit pack generation with validation. Runs `audit-pack`, then checks for gaps: transactions without receipts, receipts without transactions, uncategorized items. Presents a checklist before finalizing.

No hooks, no MCP server. Skills invoke the CLI via Bash.

## Repo Structure

```
apps/interfin/
├── pyproject.toml
├── README.md
├── src/interfin/
│   ├── __init__.py
│   ├── __main__.py           # python -m interfin
│   ├── cli.py                # click subcommand routing
│   ├── ingest.py             # CSV parsing + PDF text extraction
│   ├── categorize.py         # vendor rule matching
│   ├── extract.py            # PDF field parsing (amount/date/vendor)
│   ├── store.py              # SQLite operations, schema migration
│   ├── link.py               # receipt-to-transaction matching
│   ├── report.py             # markdown + CSV report generation
│   ├── audit.py              # audit pack assembly
│   └── models.py             # dataclasses (Transaction, Receipt)
├── config/
│   ├── vendors.yml           # categorization + extraction rules
│   └── column_maps.yml       # bank CSV column mappings
├── data/                     # runtime (gitignored)
│   ├── interfin.db
│   └── receipts/
├── out/                      # generated outputs (gitignored)
├── tests/
│   ├── test_categorize.py
│   ├── test_ingest.py
│   ├── test_extract.py
│   ├── test_link.py
│   └── fixtures/
└── examples/

interverse/interfin/
├── plugin.json
├── CLAUDE.md
├── README.md
└── skills/
    ├── ingest/SKILL.md
    ├── review/SKILL.md
    ├── link/SKILL.md
    └── audit/SKILL.md
```

## Dependencies

3 runtime, all pure Python:

| Package | Purpose |
|---|---|
| `click` | CLI framework with subcommand routing |
| `pdfplumber` | PDF text extraction (handles invoice tables well) |
| `pyyaml` | Parse vendors.yml and column_maps.yml |

Everything else is stdlib: `sqlite3`, `hashlib`, `csv`, `re`, `pathlib`, `datetime`.

## Report Outputs

Monthly and yearly reports in `out/reports/`:

- `2026-02-summary.md` — human-readable markdown with totals, top merchants, unknown vendor list
- `2026-02-by-vendor.csv` — machine-readable vendor breakdown
- `2026-02-by-category.csv` — machine-readable category breakdown
- `2026-year-summary.md` — yearly rollup across all months

Audit packs in `out/audit/2026-02/`:

- Raw source CSVs for that month
- Normalized transactions CSV
- All linked receipt PDFs (copied)
- Summary report
