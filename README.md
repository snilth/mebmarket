# MEB Market Book Recommendation System

A Python-based book recommendation system that collects book metadata
from MEB Market, processes Thai natural-language user commands, ranks
matching books, and returns recommendations through a LINE Flex Carousel
interface.

## Project Status

  Component                               Status
  --------------------------------------- --------------
  Web Scraping & Data Pipeline            ✅ Completed
  NLP Command Processing                  ✅ Completed
  Top 5 Recommendation & Randomization    ✅ Completed
  LINE Interface & Chat UX                ✅ Completed
  Code Quality & Performance Evaluation   ✅ Completed

## System Overview

``` text
MEB Market
    │
    ▼
Web Scraping → Merge & Deduplication → Data Validation → Processed Dataset
                                                        │
User Command → NLP Command Processing → Structured Command
                                                        │
                                                        ▼
                                                  Hard Filtering
                                                        │
                                                        ▼
                                                  Quality Ranking
                                                  ┌─────┴─────┐
                                                  ▼           ▼
                                             Ranked Top 5   Random Top 5
                                                  │           │
                                                  └─────┬─────┘
                                                        ▼
                                                LINE Flex Carousel
                                                        │
                                                        ▼
                                                     MEB Page
```

# 1. Web Scraping & Data Pipeline

The scraping pipeline collects book metadata from selected MEB Market
categories using Python and Playwright. It handles dynamic page content,
pagination, popup dialogs, and JavaScript-rendered book listings.

## Dataset

``` text
Categories:       17
Total records:  2550
Unique books:   2550
Duplicates:        0
```

The processed dataset is stored at `data/processed/books.json`.

Each book contains `book_id`, `title`, `author`, `publisher`,
`categories`, `price`, `price_text`, `is_free`, `rating`,
`rating_count`, `cover_url`, and `book_url`.

Example:

``` json
{
  "book_id": "465787",
  "title": "Example Book",
  "categories": [
    {
      "category_id": "12",
      "category_name": "การ์ตูนผู้หญิง",
      "parent_category_id": "227",
      "parent_category_name": "การ์ตูน"
    }
  ],
  "price": 85.0,
  "rating": 5.0,
  "rating_count": 1
}
```

## Data Validation

``` text
Records:                  2550
Unique books:             2550
Duplicates:                  0
Unique categories:          17
Missing publisher:         635 (warning only)
Free books:                 95
Paid books:               2455
Critical errors:             0

RESULT: PASS
```

Missing publisher values are treated as warnings because publisher
information is an optional, non-critical field.

# 2. NLP Command Processing

The NLP module converts Thai natural-language commands into structured
recommendation constraints.

Example:

``` text
ขอนิยายแฟนตาซีฟรี ราคาไม่เกิน 200 บาท เรต 4 ขึ้นไป
```

``` json
{
  "intent": "recommend",
  "category_id": "4",
  "category": "นิยายแฟนตาซี",
  "price_type": "free",
  "max_price": 200.0,
  "min_rating": 4.0,
  "min_rating_count": null
}
```

## NLP Architecture

The system uses a hybrid NLP approach:

``` text
User Command
    │
    ▼
Text Normalization
    │
    ▼
Intent Detection
    ├── Rule-based Detection
    └── Semantic Model Fallback
    │
    ▼
Category Recognition
    ├── Exact Alias Matching
    ├── Semantic Matching
    └── Fuzzy Matching
    │
    ▼
Constraint Extraction
    ├── Price Type
    ├── Maximum Price
    ├── Minimum Rating
    └── Minimum Rating Count
    │
    ▼
Validation
    │
    ▼
Structured Command
```

## NLP Model

The project uses the pretrained model `intfloat/multilingual-e5-base` as
a multilingual text embedding model for semantic matching.

The model is not trained or fine-tuned by this project. It is one
component of the hybrid NLP pipeline. Text normalization, rule-based
intent detection, category aliases, fuzzy matching, constraint
extraction, validation, and the matching logic surrounding the model are
implemented as part of the project.

The recommendation engine itself does not use an LLM or generative AI
model.

## Typo Handling

Semantic matching and fuzzy matching are combined to handle common
typing errors.

For example:

``` text
ขอนิยายสืบสวยหน่อย
```

can still be recognized as `นิยายสืบสวนสอบสวน/ทริลเลอร์`.

## Constraint Extraction

The parser supports expressions such as:

``` text
ฟรี
ราคาไม่เกิน 200 บาท
งบ 300 บาท
เรต 4 ขึ้นไป
4.5 ดาวขึ้นไป
รีวิวอย่างน้อย 20 คน
50 รีวิวขึ้นไป
```

These are converted into `price_type`, `max_price`, `min_rating`, and
`min_rating_count`.

## NLP Evaluation

The final NLP evaluation contains 120 commands:

``` text
Normal       30
Colloquial   30
Typo         30
Complex      30
----------------
Total       120
```

  Metric                       Accuracy
  -------------------------- ----------
  Intent Accuracy                97.50%
  Category Accuracy              95.00%
  Entity Accuracy                99.17%
  Overall Command Accuracy       90.00%

  Command Type      Intent   Category    Entity   Overall
  -------------- --------- ---------- --------- ---------
  Normal           100.00%    100.00%   100.00%   100.00%
  Colloquial       100.00%     96.67%    99.17%    93.33%
  Complex           93.33%     96.67%   100.00%    90.00%
  Typo              96.67%     86.67%    97.50%    76.67%

The primary remaining NLP weakness is heavily misspelled Thai text,
especially when typing errors affect category names or numeric
constraint keywords.

# 3. Recommendation Engine

The recommendation engine receives structured constraints from the NLP
parser and applies them to the processed book dataset.

``` text
Structured Command
       │
       ▼
Hard Filtering
       ├── Category
       ├── Free / Paid
       ├── Maximum Price
       ├── Minimum Rating
       └── Minimum Review Count
       │
       ▼
Candidate Pool
       │
       ▼
Quality Ranking
       │
       ▼
Top Recommendations
```

User constraints are treated as hard filters. For example,
`ขอหนังสือคอมราคาไม่เกิน 200 บาท` requires the computer category and
`price <= 200`.

## Quality Ranking

The system combines a Bayesian-style weighted rating with a popularity
bonus rather than ranking only by raw star rating.

``` text
WR = (v / (v + m)) × R + (m / (v + m)) × C
```

where:

``` text
R = book rating
v = number of ratings
C = global average rating
m = review-confidence constant
```

A logarithmic popularity component is added:

``` text
Popularity = log(1 + rating_count) × weight

Final Score = Weighted Rating + Popularity Bonus
```

## Ranked Recommendation and Pagination

Normal recommendation requests return the highest-ranked books first:

``` text
Rank 1–5 → Rank 6–10 → Rank 11–15 → ...
```

Pagination allows users to continue browsing without repeatedly
receiving the same first five books.

## Randomization

Randomization selects from a high-quality candidate pool rather than
blindly sampling from the entire dataset.

``` text
Hard Filtering
      │
      ▼
Quality Ranking
      │
      ▼
High-quality Pool
      │
      ▼
Random Selection
      │
      ▼
Random Top 5
```

## Recommendation Evaluation

``` text
Category filter                PASS
Maximum price filter           PASS
Free-book filter               PASS
Minimum rating filter          PASS
Minimum review-count filter    PASS
Complex multi-constraint       PASS

Constraint tests: 6/6
Ranking Top-5:    PASS
Pagination:       PASS
```

Randomization was evaluated over 100 runs:

``` text
Runs:                      100
Invalid Top-5 results:       0
Duplicate inside Top-5:      0
Unique result sets:         99
Unique books observed:      20
Repeated identical sets:     1

RESULT: PASS
```

# 4. LINE Interface & Chat UX

The recommendation system is connected to a LINE Official Account
through the LINE Messaging API.

During local development, Cloudflare Tunnel exposes the Flask webhook to
LINE:

``` text
LINE OA
   │
   ▼
LINE Messaging API
   │
   ▼
Cloudflare Tunnel
   │
   ▼
Flask Webhook
   │
   ▼
NLP Parser
   │
   ▼
Recommendation Engine
   │
   ▼
LINE Flex Carousel
```

Each Flex Carousel card displays the book cover, title, author, rating,
review count, and price. The cover/title can link to the corresponding
MEB page.

# 5. Performance

The semantic NLP model is preloaded when the webhook starts, preventing
it from being loaded from scratch for every user request.

The backend benchmark measures NLP parsing, recommendation
filtering/ranking, and Flex Message generation after preload.

``` text
Target: < 1500 ms
Result: PASS
```

Measured backend latency is in the millisecond range after preload.
External LINE and Cloudflare network latency is not included in this
benchmark.

# Final Evaluation

Run the complete evaluation suite with:

``` bash
python -m evaluation.run_all
```

It evaluates:

1.  Data Quality
2.  NLP Accuracy
3.  Recommendation & Randomization
4.  Performance

Final result:

``` text
DATA QUALITY       PASS
NLP                PASS
RECOMMENDATION     PASS
PERFORMANCE        PASS

FINAL RESULT: PASS
```

Evaluation outputs are stored under `data/evaluation/`.

# Project Structure

``` text
Mebmarket/
├── data/
│   ├── config/
│   │   └── target_categories.json
│   ├── evaluation/
│   │   ├── data_quality.json
│   │   ├── evaluation_summary.json
│   │   ├── nlp_results.json
│   │   ├── performance_results.json
│   │   └── recommendation_results.json
│   ├── nlp/
│   │   ├── category_aliases.json
│   │   ├── evaluation_report.json
│   │   ├── final_test_commands.json
│   │   └── test_commands.json
│   └── processed/
│       └── books.json
├── evaluation/
│   ├── __init__.py
│   ├── data_quality.py
│   ├── nlp_eval.py
│   ├── performance_eval.py
│   ├── recommendation_eval.py
│   └── run_all.py
├── line/
│   ├── __init__.py
│   ├── flex_carousel.py
│   └── webhook.py
├── nlp/
│   ├── __init__.py
│   ├── evaluator.py
│   ├── model.py
│   ├── normalizer.py
│   └── parser.py
├── recommendation/
│   ├── __init__.py
│   └── engine.py
├── scraper/
│   ├── __init__.py
│   └── ...
├── processing/
│   └── ...
├── .gitignore
├── requirements.txt
└── README.md
```

`data/raw/`, the virtual environment, caches, documentation drafts, and
`.env` secrets are excluded from version control.

# Installation

Create and activate a virtual environment:

``` bash
python -m venv meb_env
source meb_env/bin/activate
```

Install dependencies:

``` bash
pip install -r requirements.txt
```

The project uses PyTorch and Sentence Transformers for semantic NLP
processing. A compatible ROCm-enabled PyTorch installation can be used
for AMD GPU acceleration.

# Running the Project

## NLP Parser

``` bash
python -m nlp.parser
```

## Recommendation Engine

``` bash
python -m recommendation.engine
```

## Evaluation Suite

``` bash
python -m evaluation.run_all
```

## LINE Webhook

Create a `.env` file:

``` text
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_CHANNEL_SECRET=...
```

Start the webhook:

``` bash
python -m line.webhook
```

Expose the local Flask server:

``` bash
cloudflared tunnel --url http://localhost:8000
```

Configure the LINE Messaging API webhook URL as:

``` text
https://<cloudflare-tunnel-url>/callback
```

# Example Commands

``` text
ขอนิยายแฟนตาซี
อยากอ่านเรื่องเวทมนตร์กับมังกร
ขอหนังสือคอมราคาไม่เกิน 200 บาท
ขอหนังสือสุขภาพฟรี
แนะนำหนังสือการเงินเรต 4 ขึ้นไป
หานิยายสืบสวนรีวิวอย่างน้อย 20 คน
ขอนิยายแฟนตาซีราคาไม่เกิน 200 บาท เรต 4 ขึ้นไป
```

# Limitations

-   Heavily misspelled Thai text remains the weakest NLP case.
-   Semantic processing is primarily used for command understanding and
    category matching rather than full book-content similarity.
-   The system does not currently use book summaries or descriptions for
    semantic recommendation.
-   Publisher information is missing for some MEB records.
-   Development LINE sessions are stored in memory and reset when the
    webhook process restarts.
-   Performance benchmarks exclude external LINE and Cloudflare network
    latency.
-   Recommendation quality depends on the metadata available in the
    scraped dataset.

Potential future improvements include description-based semantic
retrieval, stronger Thai typo correction, persistent user sessions, user
preference modeling, and personalized recommendations.

# Final Status

``` text
Web Scraping & Data Pipeline
████████████████████ 100%

NLP Command Processing
████████████████████ 100%

Top 5 Recommendation & Randomization
████████████████████ 100%

LINE Interface & Chat UX
████████████████████ 100%

Evaluation & Performance
████████████████████ 100%

FINAL EVALUATION: PASS
```