# MEB Market Book Recommendation System

A Python-based book recommendation system that collects book metadata from MEB Market, processes natural-language user commands, and recommends five matching books through a LINE Carousel interface.

The project consists of five main components:

1. Web Scraping & Data Pipeline
2. NLP Command Processing
3. Top 5 Carousel Logic & Randomization
4. LINE Interface & Chat UX
5. Code Quality & Performance

---

## Project Status

| Component | Status |
|---|---|
| Web Scraping & Data Pipeline | ✅ Completed |
| NLP Command Processing | ✅ Completed |
| Top 5 Carousel & Randomization | 🚧 Next |
| LINE Interface & Chat UX | ⏳ Planned |
| Code Quality & Performance | 🔄 Ongoing |

---

## System Overview

```text
MEB Market
    │
    ▼
Web Scraping
    │
    ▼
Raw Category Data
    │
    ▼
Merge & Deduplication
    │
    ▼
Data Validation
    │
    ▼
Processed Dataset
    │
    ├──────────────────────────┐
    │                          │
    │                    User Command
    │                          │
    │                          ▼
    │                 NLP Command Processing
    │                          │
    │                          ▼
    │                 Structured Command
    │                          │
    └──────────────┬───────────┘
                   ▼
              Book Filtering
                   │
                   ▼
          Ranking / Randomization
                   │
                   ▼
                Top 5
                   │
                   ▼
             LINE Carousel
```

---

## 1. Web Scraping & Data Pipeline

The scraping pipeline collects book metadata from selected MEB Market categories using Python and Playwright.

The scraper handles dynamic page content, pagination, popup dialogs, and JavaScript-rendered book listings.

### Dataset

A total of **17 categories** were collected with **150 books per category**.

```text
Categories:       17
Raw records:    2550
Unique books:   2550
Duplicates:        0
```

The processed dataset is stored at:

```text
data/processed/books.json
```

Each book contains metadata such as:

```text
book_id
title
author
publisher
category_id
category
price
price_text
is_free
rating
rating_count
cover_url
book_url
```

### Data Validation

The processed dataset is validated before being used by downstream components.

Validation result:

```text
Records:             2550
Errors:                 0
Warnings:             635
Free books:            95
Paid books:          2455

RESULT: PASSED
```

The warnings are caused by missing publisher information, which is treated as a non-critical optional field.

---

## 2. NLP Command Processing

The NLP module converts Thai natural-language commands into structured constraints that can be used by the recommendation engine.

Example input:

```text
ขอนิยายแฟนตาซีฟรี ราคาไม่เกิน 200 บาท เรต 4 ขึ้นไป
```

Example output:

```json
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

### NLP Architecture

The system uses a hybrid NLP approach combining deterministic rules with semantic language understanding.

```text
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

### Semantic Matching

The NLP pipeline uses:

```text
intfloat/multilingual-e5-base
```

for semantic intent and category matching.

This allows the system to understand commands that do not explicitly contain a category name.

For example:

```text
อยากอ่านเรื่องเวทมนตร์กับมังกร
```

can be mapped to:

```text
นิยายแฟนตาซี
```

Similarly:

```text
อยากเข้าใจอารมณ์ตัวเองมากขึ้น
```

can be mapped to:

```text
จิตวิทยา
```

### Typo Handling

The system combines semantic matching and fuzzy string matching to handle common typing errors.

Example:

```text
ขอนิยายสืบสวยหน่อย
```

is recognized as:

```text
นิยายสืบสวนสอบสวน/ทริลเลอร์
```

### Constraint Extraction

Rule-based patterns and regular expressions are used for deterministic constraints such as:

```text
ฟรี
ราคาไม่เกิน 200 บาท
งบ 300 บาท
เรต 4 ขึ้นไป
4.5 ดาวขึ้นไป
รีวิวอย่างน้อย 20 คน
50 รีวิวขึ้นไป
```

These constraints are converted into structured fields:

```text
price_type
max_price
min_rating
min_rating_count
```

---

## NLP Evaluation

During development, a 20-command development set was used for debugging and parser improvement.

A separate **120-command evaluation set** was then used to evaluate the completed NLP pipeline.

The final test set contains four command types:

```text
Normal       30
Colloquial   30
Typo         30
Complex      30
----------------
Total       120
```

### Final Results

| Metric | Accuracy |
|---|---:|
| Intent Accuracy | 95.83% |
| Category Accuracy | 93.33% |
| Entity Accuracy | 98.96% |
| Overall Command Accuracy | 88.33% |

### Accuracy by Command Type

| Command Type | Intent | Category | Entity | Overall |
|---|---:|---:|---:|---:|
| Normal | 100.00% | 100.00% | 100.00% | 100.00% |
| Colloquial | 96.67% | 96.67% | 100.00% | 90.00% |
| Complex | 93.33% | 96.67% | 98.33% | 90.00% |
| Typo | 93.33% | 83.33% | 97.50% | 73.33% |

The results show that the NLP pipeline exceeds the project's target accuracy of **85%** for intent and entity recognition.

The primary remaining weakness is heavily misspelled Thai text, particularly when typing errors affect category names or constraint keywords.

---

## Current Pipeline

The following components are now complete:

```text
MEB Market
    │
    ▼
Scraping                         ✅
    │
    ▼
2550 Book Records                ✅
    │
    ▼
Merge & Deduplication            ✅
    │
    ▼
Dataset Validation               ✅
    │
    ▼
Processed Dataset                ✅

User Command
    │
    ▼
Text Normalization               ✅
    │
    ▼
Intent Detection                 ✅
    │
    ▼
Category Recognition             ✅
    │
    ▼
Constraint Extraction            ✅
    │
    ▼
Structured Command               ✅
```

The next development phase connects these two pipelines.

---

## Next Step: Top 5 Recommendation Logic

The next component will use the structured NLP command to filter the processed MEB dataset.

Example:

```text
User:
ขอนิยายแฟนตาซีฟรี 4 ดาวขึ้นไป

        │
        ▼

NLP Parser

category_id = 4
price_type = free
min_rating = 4.0

        │
        ▼

data/processed/books.json

        │
        ▼

Book Filtering

category_id == 4
is_free == true
rating >= 4.0

        │
        ▼

Candidate Books

        │
        ▼

Ranking / Randomization

        │
        ▼

Top 5 Books

        │
        ▼

LINE Carousel
```

The recommendation component will be responsible for:

- filtering books using NLP-generated constraints
- generating a valid candidate pool
- ranking or randomizing matching books
- selecting up to five books
- preparing results for the LINE Carousel interface

---

## Project Structure

```text
Mebmarket/
├── data/
│   ├── nlp/
│   ├── processed/
│   │   └── books.json
│   └── raw/
│       └── categories/
│
├── nlp/
│   ├── category_matcher.py
│   ├── constraint_extractor.py
│   ├── evaluator.py
│   ├── intent.py
│   ├── model.py
│   ├── normalizer.py
│   └── parser.py
│
├── processing/
│   └── validate_books.py
│
├── scraper/
│
└── README.md
```

---

## Current Development Status

```text
Web Scraping & Data Pipeline
████████████████████ 100%

NLP Command Processing
████████████████████ 100%

Top 5 Carousel & Randomization
░░░░░░░░░░░░░░░░░░░░   0%  ← NEXT

LINE Interface & Chat UX
░░░░░░░░░░░░░░░░░░░░   0%

Code Quality & Performance
██████████░░░░░░░░░░  Ongoing
```