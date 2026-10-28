# De-Influence AI — User Manual

A friendly, step-by-step guide to running and reviewing the prototype. No prior setup
knowledge needed. Written for **users, judges, and teammates**.

Team: Outlier Behaviour · Project: The Micro-Trend Lifespan & Fast-Fashion Regret Predictor

---

## 1. What this is (30-second version)

Paste a Shopee / TikTok Shop / Shein product link and De-Influence gives an instant, honest
verdict — **KEEP / CONSIDER / CAUTION / AVOID** — plus a Longevity Score, Regret Probability and
Cost-Per-Wear. If an item is weak, it even suggests a **better alternative** from the catalogue.

Everything runs locally and free. No accounts, no cloud, no API keys.

---

## 2. What you need

- **Python 3** installed (check with `python --version`).
- A terminal (on Windows, use **PowerShell**).
- A web browser.

That's it.

---

## 3. Run it in 3 steps (Windows PowerShell)

Open PowerShell in the project folder, then:

```powershell
# 1. Install the dependencies (first time only)
python -m pip install -r requirements.txt

# 2. Start the app
python -m uvicorn app.main:app --port 8000

# 3. Open your browser to:
#    http://127.0.0.1:8000
```

> **Tip:** always use `python -m uvicorn ...` (not bare `uvicorn`) so it works even if the
> scripts folder isn't on your PATH.

**Port already in use?** If you see `WinError 10013` or "address in use", start on another port:
```powershell
python -m uvicorn app.main:app --port 8010
```
Then open `http://127.0.0.1:8010`.

To stop the app: press **Ctrl + C** in the terminal.

---

## 4. How to use the app (a quick tour)

The app has a top menu. Each item is its own page:

| Page | What it does |
|---|---|
| **Analyse** | Paste a product link (or tap a demo item) to get the verdict |
| **Dashboard** | Your private analytics of everything you've analysed (stays on your device) |
| **Personalize** | Save your preferred style, favourite colour and monthly budget |
| **Compare** | Put two or more analysed items side by side |
| **Wishlist** | Favourite items and see stock status (email alerts: coming soon) |
| **Why us** | How we compare to other tools + the investor case |
| **Validation** | The model's accuracy (F1/MAE) and a **download of the exact dataset** |

### Try it fast
1. Go to **Analyse**.
2. Tap a demo chip (e.g. *Viral Mesh Corset Top*) — it scores **AVOID** and suggests a better
   alternative you can analyse with one click.
3. Or paste a link like `https://shopee.com.my/anything` — you'll get an instant *emulated*
   result (see the honesty note below).

### Honest note for judges
We **cannot** read live Shopee/TikTok pages (platform restrictions + security). So a pasted link
is resolved against our own database: a known demo link gives an exact match, any other link
gives a clearly-labelled **emulated** result. The app **never makes an outbound web request** —
this is deliberate and keeps us safe under OWASP A10 (SSRF).

---

## 5. Seeing the validation data (for judges)

Go to the **Validation** page. You will see:
- the headline metrics (F1 ≈ 0.91, accuracy 94%, beating the dataset's own baseline),
- every labeled review row rendered in a table, and
- a **Download .xlsx** button that gives you the exact `Sample_Data.xlsx` the model is scored on.

This is full transparency — you can open the spreadsheet and check our numbers yourself.

---

## 6. Developer / debug mode (last-minute inspection)

A hidden **Debug** page lets you inspect the live database and engine internals. It is OFF by
default and only turns on when you start the server with an environment flag.

```powershell
# Windows PowerShell
$env:DEINFLUENCE_DEBUG = "1"
python -m uvicorn app.main:app --port 8000
```

Now a **Debug** tab appears in the menu. It shows:
- the SQLite database file path,
- every table and its rows (products, reviews, preferences, wishlist),
- the engine configuration (scoring weights, thresholds, lexicon size).

Without the flag, the Debug page and its API endpoint **do not exist at all** (a deliberate
security choice — OWASP A05). To turn it off again, just restart the server without the flag:
```powershell
$env:DEINFLUENCE_DEBUG = ""
python -m uvicorn app.main:app --port 8000
```

---

## 7. Critical files to look at

| File | What it is |
|---|---|
| `app/data/deinfluence.db` | **The database.** All catalogue, preferences and wishlist data lives here (created on first run). |
| `app/data/Sample_Data.xlsx` | The real 50-row labeled benchmark the model is validated against. |
| `app/main.py` | The backend: every API route and the analysis pipeline. |
| `app/db.py` | The SQLite data layer (the single source of truth). |
| `static/app.js` | The whole front-end (pages + logic). |
| `docs/architecture.md` | System map + how we meet the OWASP Top 10. |
| `docs/user-flow.md` | The user-interaction flowchart for the pitch. |

### Inspect the database without the app
From the project folder:
```powershell
python scripts/db_peek.py
```
This prints the database file location and the contents of every table — handy for a quick look.

### Reset to a clean demo state
If the database gets messy during testing, reset it (wipes and reseeds in place):
```powershell
python -c "import sys; sys.path.insert(0,'.'); from app import db; db.reset_catalogue(); print('reset done')"
```

---

## 8. Running the tests (optional, for reviewers)

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```
Expected result: **`49 passed`**.

---

## 9. Install it on your phone via Cloudflare HTTPS (the "web app")

The app is a Progressive Web App (PWA) — it can be installed like a real app. But phones only
allow true install over **HTTPS**, and your local server is plain HTTP. The free **Cloudflare
Tunnel** gives you a public `https://...` address that forwards to your local app — no Cloudflare
account, no DNS setup, no cost. (The `cloudflared.exe` binary already ships in `tools/`.)

### Step by step

1. **Start the app** (Terminal A):
   ```powershell
   python -m uvicorn app.main:app --port 8000
   ```

2. **Start the tunnel** (Terminal B — leave Terminal A running):
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/run_tunnel.ps1
   ```
   If your app is on a different port, pass it: `... run_tunnel.ps1 -Port 8010`

3. **Copy the HTTPS link** the tunnel prints, e.g.:
   ```
   https://nose-easy-gale-day.trycloudflare.com
   ```

4. **Open that link on your phone** (any browser). Then install it:
   - **Android / Chrome:** menu (⋮) → *Add to Home screen* / *Install app*
   - **iPhone / Safari:** Share → *Add to Home Screen*

   You now have a De-Influence app icon that opens full-screen and works offline.

5. **To stop:** press **Ctrl + C** in Terminal B (tunnel), then in Terminal A (app).

### Raw command (if you skip the script)
```powershell
.\tools\cloudflared.exe tunnel --url http://localhost:8000
```

### Good to know
- The `trycloudflare.com` URL is **random and temporary** — it changes every run, which is fine
  for a demo. For a fixed URL (e.g. judging day), deploy to any free HTTPS host
  (Render, Railway, Fly.io) or set up a *named* Cloudflare tunnel with a Cloudflare account.
- The tunnel only exposes the app while it is running on your machine; close it and the link dies.
- Same-Wi-Fi quick look without install (no HTTPS):
  `powershell -ExecutionPolicy Bypass -File scripts/run_mobile.ps1`, then open the printed
  `http://<your-PC-IP>:8000` on your phone (loads, but the phone offers only a shortcut, not a
  real install).

---

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| `WinError 10013` / port in use | Start on another port: `--port 8010` |
| Page looks old / features missing | Hard-refresh: **Ctrl + Shift + R** (clears the cached app shell) |
| `uvicorn: command not found` | Use `python -m uvicorn ...` |
| Debug tab not showing | Make sure you set `$env:DEINFLUENCE_DEBUG = "1"` before starting the server |
| Want a fresh database | Run the reset command in section 7 |

---

That's everything. Start at section 3, open the browser, and you're golden.
