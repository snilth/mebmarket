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
| NLP Command Processing | 🚧 Next |
| Top 5 Carousel & Randomization | ⏳ Planned |
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
    ▼
NLP Command Processing
    │
    ▼
Book Filtering
    │
    ▼
Random Top 5
    │
    ▼
LINE Carousel