# De-Influence AI — Architecture (for judges)

A quick map of the inner workings so the prototype is easy to follow.

## One-paragraph summary

A FastAPI backend serves a REST API and an installable, offline-capable multi-page web app
(PWA). A local **SQLite** database is the single source of truth for the catalogue, user
preferences and wishlist. Three transparent engines (defect NLP, Gompertz hype-decay, Cost-Per-
Wear) fuse into an explainable Longevity Score and Regret Probability. Security is mapped to the
**OWASP Top 10**. The user's scan history stays private in their browser.

## Request lifecycle

```
Browser (static/app.js)
  --> FastAPI (app/main.py)        middleware: security headers, rate limit, strict CORS
      --> app/db.py                SQLite read/write (parameter-bound; A03-safe)
      --> app/link_resolver.py     emulated link -> catalogue lookup (no outbound fetch; A10-safe)
      --> app/engines/*            defect_nlp, hype_decay, truecost
      --> app/engines/scoring.py   fuse -> Longevity + Regret (explainable breakdown)
      --> app/personalization.py   tailored note from saved preferences
      --> app/ethics.py            confidence band + responsible-use disclaimers
  <-- JSON verdict
```

## Backend modules (`app/`)

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app + all routes; wires middleware and the pipeline |
| `db.py` | SQLite layer: catalogue, reviews, preferences, wishlist (source of truth) |
| `security.py` | OWASP controls: headers, CORS allow-list, rate limit, error sanitisation |
| `link_resolver.py` | Emulated paste-a-link resolution (no network fetch) |
| `engines/defect_nlp.py` | Localized Malaysian code-switch defect detector |
| `engines/hype_decay.py` | Gompertz trend-decay forecaster |
| `engines/truecost.py` | Cost-Per-Wear simulator |
| `engines/scoring.py` | Fuses the three signals into the headline scores |
| `personalization.py` | Tailored note from preferences |
| `ethics.py` | Defamation guard, privacy note, confidence band, disclaimers |
| `evaluation.py` | F1 (defect) + MAE (hype) vs the real benchmark |
| `positioning.py` | Competitor comparison + investor value props |
| `debug.py` | Read-only inspection snapshot (only mounted when `DEINFLUENCE_DEBUG=1`) |
| `data/` | `sample_products.py` (seed), `benchmark.py` + `Sample_Data.xlsx` (validation), runtime `deinfluence.db` |

## Frontend (`static/`)

| File | Responsibility |
|---|---|
| `index.html` | App shell + header/nav |
| `app.css` | All styles (glassmorphism, responsive nav) |
| `app.js` | Hash router + one renderer per page |
| `sw.js` | Service worker: install + offline precache |
| `manifest.webmanifest`, `icon.svg` | PWA metadata |

Pages: Analyse · Dashboard · Personalize · Compare · Wishlist · Why Us · Validation · Debug
(Debug only when the server is started with `DEINFLUENCE_DEBUG=1`).

## OWASP Top 10 mapping

See `app/security.py` and `app/debug.py` docstrings. Highlights: strict CORS allow-list and
security headers (A05), parameter-bound SQLite and input validation (A03), no PII at rest and a
stateless server (A02/A04), sanitized errors (A09), pinned dependencies (A06), and no server-side
outbound requests at all (A10 — the link feature resolves locally).
