# MEB Market Book Recommendation System

A book recommendation chatbot for LINE. It scrapes book data from MEB
Market, understands Thai natural-language requests ("ขอนิยายแฟนตาซีฟรี
เรต 4 ขึ้นไป"), and replies with a Top 5 carousel of matching books.

```
MEB Market → Scraper → Cleaned dataset (books.json)

LINE user → Webhook → NLP Parser → Recommendation Engine → Flex Carousel → LINE user
```

Status: all 5 components complete and passing evaluation (data quality,
NLP accuracy, recommendation logic, performance).

---

## How it works

### 1. Data pipeline (`scraper/`, `processing/`)
Playwright scrapes 17 MEB categories (JS-rendered pages, so plain
`requests` doesn't work — see `docs/design.txt` for why). Results are
merged, deduplicated, and validated into `data/processed/books.json`.

- 2,550 books, 0 duplicates, 0 critical validation errors
- Each book: `book_id`, `title`, `author`, `publisher`, `categories`,
  `price`, `is_free`, `rating`, `rating_count`, `cover_url`, `book_url`

### 2. NLP command parsing (`nlp/`)
Turns a Thai sentence into a structured command:

```
"ขอนิยายแฟนตาซีฟรี ราคาไม่เกิน 200 บาท เรต 4 ขึ้นไป"
  → {intent: recommend, category: นิยายแฟนตาซี, price_type: free,
     max_price: 200, min_rating: 4}
```

Pipeline: normalize text → detect intent (rules, semantic model as
fallback) → match category (exact alias → semantic → fuzzy, so typos
like "สืบสวย" still match "สืบสวน") → extract price/rating constraints
→ validate.

Uses `intfloat/multilingual-e5-base` (pretrained, not fine-tuned) for
semantic matching only — no LLM, no generative model anywhere in the
pipeline.

**Accuracy (120 test commands):** intent 97.5%, category 95%, entity
99.2%, overall 90%. Weakest case: heavily misspelled Thai, especially
in category names or numeric keywords (typo commands: 76.7% overall).

### 3. Recommendation engine (`recommendation/`)
User constraints (category, free/paid, max price, min rating, min
review count) are **hard filters** — not preferences. What passes the
filter is then ranked by a Bayesian-style weighted rating plus a
popularity bonus, so a 5.0★ book with 1 review doesn't outrank a 4.6★
book with 500 reviews:

```
WR = (v / (v+m)) × R + (m / (v+m)) × C      (R=rating, v=review count,
Popularity = log(1 + v) × weight             C=global avg, m=confidence const)
Final Score = WR + Popularity
```

Two response modes:
- **Ranked** — top 5 by score, paginated (6–10, 11–15, ...)
- **Random** — 5 random picks from the high-quality candidate pool
  (not the raw dataset), so results stay relevant but not repetitive

### 4. LINE interface (`line/`)
Flask webhook, `line-bot-sdk` v3. In development, Cloudflare Tunnel
exposes the local server to LINE's Messaging API. Each carousel card
shows cover, title, author, rating, review count, price, and links to
the MEB page. Carousel colors come from `line/theme.py`, a shared
book-market palette (warm brown/gold) also used by the Rich Menu.

A Rich Menu (`line/richmenu.py`) shows automatically the moment a user
opens the chat — a 4x5 grid with all 17 categories plus "สุ่มหนังสือ",
"พิมพ์คำค้นเอง", and "วิธีใช้", so picking a category doesn't require
typing. Tapping a tile sends a postback (`line/webhook.py:handle_postback`)
that runs the recommendation engine directly, the same way a typed
command does.

### 5. Evaluation (`evaluation/`)
```
python -m evaluation.run_all
```
Runs data quality, NLP accuracy, recommendation/randomization, and
performance checks. Results land in `data/evaluation/`. Backend latency
(NLP + filtering + ranking + Flex generation, model preloaded at
startup) is well under the 1500ms target — LINE/Cloudflare network time
isn't included in that number.

---

## Setup

```bash
python -m venv meb_env
source meb_env/bin/activate
pip install -r requirements.txt
```

`torch` and `sentence-transformers` are required for the semantic NLP
model. If you have an AMD GPU, install a ROCm-enabled `torch` build
instead of the default CPU/CUDA one.

Generating the Rich Menu image (`line/richmenu.py`) needs Thai + Latin
system fonts — on Debian/Ubuntu: `sudo apt install fonts-noto-core`.

Create `.env` for the LINE webhook:
```
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_CHANNEL_SECRET=...
```

## Running things

| Task | Command |
|---|---|
| Parse a command (dev/test) | `python -m nlp.parser` |
| Get recommendations (dev/test) | `python -m recommendation.engine` |
| Run full evaluation suite | `python -m evaluation.run_all` |
| Start LINE webhook | `python -m line.webhook` |
| Expose webhook locally | `cloudflared tunnel --url http://localhost:8000` |
| Push the Rich Menu live (one-time / after category changes) | `python -m line.richmenu` |

Set the LINE Messaging API webhook URL to
`https://<cloudflare-tunnel-url>/callback`.

`python -m line.richmenu` creates the rich menu on the connected LINE
OA, uploads the generated image, and sets it as the default for every
user — it's a real, visible change to the live bot, so run it
deliberately rather than as part of routine startup.

## Example commands

```
ขอนิยายแฟนตาซี
อยากอ่านเรื่องเวทมนตร์กับมังกร
ขอหนังสือคอมราคาไม่เกิน 200 บาท
ขอหนังสือสุขภาพฟรี
แนะนำหนังสือการเงินเรต 4 ขึ้นไป
หานิยายสืบสวนรีวิวอย่างน้อย 20 คน
```

## Project layout

```
scraper/         → Playwright scraper (MEB categories)
processing/       → merge, dedupe, validate scraped data
nlp/              → text normalization, intent, category match, constraints
recommendation/   → hard filtering + ranking + randomization
line/             → Flask webhook, Flex Carousel builder, Rich Menu, theme
evaluation/       → data quality / NLP / recommendation / performance checks
data/             → processed dataset, config, evaluation outputs
docs/design.txt   → original architecture sketch
```

`data/raw/`, `data/line/`, `meb_env/`, caches, `docs/`, and `.env` are
gitignored.

## Known limitations

- Heavily misspelled Thai is the weakest NLP case
- No book-description/summary-based semantic matching yet — category
  and command understanding only
- 635 books missing publisher info (non-critical field)
- LINE sessions (paging state, seen-books for randomize) are cached in
  memory and persisted to `data/line/sessions.json` on every change, so
  a webhook restart no longer drops active users' state
- Performance numbers exclude LINE/Cloudflare network latency

Possible next steps: description-based semantic retrieval, stronger
Thai typo correction, persistent sessions, personalization.
