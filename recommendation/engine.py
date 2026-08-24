import json
import math
import random

from functools import lru_cache
from pathlib import Path

from nlp.parser import (
    parse_command,
)


# ============================================================
# Configuration
# ============================================================

BOOKS_PATH = Path(
    "data/processed/books.json"
)

MIN_REVIEW_CONFIDENCE = 10

POPULARITY_WEIGHT = 0.08

RANDOM_POOL_SIZE = 20


# ============================================================
# Dataset
# ============================================================

@lru_cache(maxsize=1)
def load_books():
    if not BOOKS_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: "
            f"{BOOKS_PATH}"
        )

    with BOOKS_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        books = json.load(file)

    if not isinstance(
        books,
        list,
    ):
        raise ValueError(
            "books.json must contain a list"
        )

    return books


# ============================================================
# Numeric Helpers
# ============================================================

def safe_float(
    value,
    default=0.0,
):
    try:
        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return default


def safe_int(
    value,
    default=0,
):
    try:
        return int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return default


# ============================================================
# Category Matching
# ============================================================

def book_matches_category(
    book,
    category_id,
):
    if category_id is None:
        return True

    category_id = str(
        category_id
    )

    if book.get(
        "category_id"
    ) is not None:
        return (
            str(
                book.get(
                    "category_id"
                )
            )
            == category_id
        )

    categories = book.get(
        "categories",
        [],
    )

    if not isinstance(
        categories,
        list,
    ):
        return False

    for category in categories:
        if not isinstance(
            category,
            dict,
        ):
            continue

        if (
            str(
                category.get(
                    "category_id"
                )
            )
            == category_id
        ):
            return True

    return False


# ============================================================
# Hard Filters
# ============================================================

def matches_price_type(
    book,
    price_type,
):
    if price_type is None:
        return True

    is_free = bool(
        book.get(
            "is_free",
            False,
        )
    )

    if price_type == "free":
        return is_free

    if price_type == "paid":
        return not is_free

    return True


def matches_max_price(
    book,
    max_price,
):
    if max_price is None:
        return True

    price = safe_float(
        book.get(
            "price"
        ),
        default=None,
    )

    if price is None:
        return False

    return (
        price
        <= float(max_price)
    )


def matches_min_rating(
    book,
    min_rating,
):
    if min_rating is None:
        return True

    rating = safe_float(
        book.get(
            "rating"
        ),
        default=None,
    )

    if rating is None:
        return False

    return (
        rating
        >= float(min_rating)
    )


def matches_min_rating_count(
    book,
    min_rating_count,
):
    if min_rating_count is None:
        return True

    rating_count = safe_int(
        book.get(
            "rating_count"
        ),
        default=None,
    )

    if rating_count is None:
        return False

    return (
        rating_count
        >= int(
            min_rating_count
        )
    )


# ============================================================
# Filtering
# ============================================================

def filter_books(
    books,
    command,
    exclude_book_ids=None,
):
    """
    User constraints are HARD FILTERS.

    Ranking never overrides these conditions.
    """

    excluded = {
        str(book_id)
        for book_id in (
            exclude_book_ids
            or []
        )
    }

    results = []

    for book in books:
        book_id = str(
            book.get(
                "book_id"
            )
        )

        if book_id in excluded:
            continue

        if not book_matches_category(
            book,
            command.get(
                "category_id"
            ),
        ):
            continue

        if not matches_price_type(
            book,
            command.get(
                "price_type"
            ),
        ):
            continue

        if not matches_max_price(
            book,
            command.get(
                "max_price"
            ),
        ):
            continue

        if not matches_min_rating(
            book,
            command.get(
                "min_rating"
            ),
        ):
            continue

        if not matches_min_rating_count(
            book,
            command.get(
                "min_rating_count"
            ),
        ):
            continue

        results.append(
            book
        )

    return results


# ============================================================
# Global Rating Average
# ============================================================

@lru_cache(maxsize=1)
def get_global_rating_average():
    books = load_books()

    ratings = []

    for book in books:
        rating = safe_float(
            book.get(
                "rating"
            ),
            default=0.0,
        )

        rating_count = safe_int(
            book.get(
                "rating_count"
            ),
            default=0,
        )

        if rating <= 0:
            continue

        if rating_count <= 0:
            continue

        ratings.append(
            rating
        )

    if not ratings:
        return 3.5

    return (
        sum(ratings)
        / len(ratings)
    )


# ============================================================
# Bayesian Weighted Rating
# ============================================================

def weighted_rating(book):
    rating = safe_float(
        book.get(
            "rating"
        ),
        default=0.0,
    )

    rating_count = safe_int(
        book.get(
            "rating_count"
        ),
        default=0,
    )

    if (
        rating <= 0
        or rating_count <= 0
    ):
        return 0.0

    R = rating
    v = rating_count

    C = (
        get_global_rating_average()
    )

    m = MIN_REVIEW_CONFIDENCE

    return (
        (v / (v + m)) * R
        +
        (m / (v + m)) * C
    )


# ============================================================
# Popularity
# ============================================================

def popularity_score(book):
    rating_count = safe_int(
        book.get(
            "rating_count"
        ),
        default=0,
    )

    if rating_count <= 0:
        return 0.0

    return (
        math.log1p(
            rating_count
        )
        * POPULARITY_WEIGHT
    )


# ============================================================
# Final Ranking Score
# ============================================================

def ranking_score(book):
    return (
        weighted_rating(
            book
        )
        +
        popularity_score(
            book
        )
    )


# ============================================================
# Ranking
# ============================================================

def rank_candidates(
    candidates,
):
    """
    Best books first.
    """

    return sorted(
        candidates,
        key=ranking_score,
        reverse=True,
    )


# ============================================================
# Deterministic Page Selection
# ============================================================

def select_ranked_page(
    candidates,
    offset=0,
    limit=5,
):
    """
    Normal recommendation:

        #1 - #5
        #6 - #10
        #11 - #15
        ...
    """

    ranked = rank_candidates(
        candidates
    )

    start = max(
        0,
        int(offset),
    )

    end = (
        start
        + limit
    )

    selected = ranked[
        start:end
    ]

    has_more = (
        end
        < len(ranked)
    )

    return (
        selected,
        has_more,
    )


# ============================================================
# Explicit Random Selection
# ============================================================

def select_random_books(
    candidates,
    limit=5,
    exclude_book_ids=None,
):
    """
    Used ONLY when the user explicitly says "สุ่ม".
    """

    excluded = {
        str(book_id)
        for book_id in (
            exclude_book_ids
            or []
        )
    }

    candidates = [
        book
        for book in candidates
        if (
            str(
                book.get(
                    "book_id"
                )
            )
            not in excluded
        )
    ]

    if not candidates:
        return []

    ranked = rank_candidates(
        candidates
    )

    # Prefer good books even when randomizing.
    quality_pool = ranked[
        :min(
            RANDOM_POOL_SIZE,
            len(ranked),
        )
    ]

    if len(quality_pool) <= limit:
        return quality_pool

    scores = [
        max(
            ranking_score(book),
            0.05,
        )
        for book in quality_pool
    ]

    selected = []
    remaining = list(
        quality_pool
    )
    remaining_scores = list(
        scores
    )

    while (
        remaining
        and len(selected)
        < limit
    ):
        chosen_index = random.choices(
            range(
                len(remaining)
            ),
            weights=
                remaining_scores,
            k=1,
        )[0]

        selected.append(
            remaining.pop(
                chosen_index
            )
        )

        remaining_scores.pop(
            chosen_index
        )

    return selected


# ============================================================
# Recommendation
# ============================================================

def recommend_books(
    command,
    limit=5,
    offset=0,
    exclude_book_ids=None,
):
    """
    Main recommendation logic.

    Normal command:
        ranked Top 5

    Explicit random command:
        weighted random from high-quality pool
    """

    if (
        command.get(
            "intent"
        )
        != "recommend"
    ):
        return {
            "status":
                "unsupported_intent",

            "command":
                command,

            "candidate_count":
                0,

            "books":
                [],

            "offset":
                0,

            "next_offset":
                0,

            "has_more":
                False,

            "randomized":
                False,
        }

    books = load_books()

    candidates = filter_books(
        books,
        command,
    )

    randomize = bool(
        command.get(
            "randomize",
            False,
        )
    )

    # --------------------------------------------------------
    # Explicit Random
    # --------------------------------------------------------

    if randomize:
        selected = select_random_books(
            candidates,
            limit=limit,
            exclude_book_ids=
                exclude_book_ids,
        )

        return {
            "status":
                (
                    "ok"
                    if selected
                    else "no_results"
                ),

            "command":
                command,

            "candidate_count":
                len(candidates),

            "books":
                selected,

            "offset":
                0,

            "next_offset":
                0,

            "has_more":
                (
                    len(candidates)
                    > len(selected)
                ),

            "randomized":
                True,
        }

    # --------------------------------------------------------
    # Ranked Recommendation
    # --------------------------------------------------------

    selected, has_more = (
        select_ranked_page(
            candidates,
            offset=offset,
            limit=limit,
        )
    )

    return {
        "status":
            (
                "ok"
                if selected
                else "no_results"
            ),

        "command":
            command,

        "candidate_count":
            len(candidates),

        "books":
            selected,

        "offset":
            offset,

        "next_offset":
            (
                offset
                + len(selected)
            ),

        "has_more":
            has_more,

        "randomized":
            False,
    }


# ============================================================
# Natural Language -> Recommendation
# ============================================================

def recommend_from_text(
    text,
    limit=5,
):
    command = parse_command(
        text
    )

    return recommend_books(
        command,
        limit=limit,
        offset=0,
    )


# ============================================================
# Debug
# ============================================================

def print_result(result):
    print()
    print("=" * 100)

    command = result.get(
        "command",
        {},
    )

    print(
        "Category:",
        command.get(
            "category"
        ),
    )

    print(
        "Randomize:",
        command.get(
            "randomize"
        ),
    )

    print(
        "Candidates:",
        result.get(
            "candidate_count"
        ),
    )

    print(
        "Offset:",
        result.get(
            "offset"
        ),
    )

    print(
        "Next offset:",
        result.get(
            "next_offset"
        ),
    )

    print(
        "Has more:",
        result.get(
            "has_more"
        ),
    )

    print(
        "Randomized:",
        result.get(
            "randomized"
        ),
    )

    print()

    for index, book in enumerate(
        result.get(
            "books",
            [],
        ),
        start=1,
    ):
        rank_number = (
            result.get(
                "offset",
                0,
            )
            + index
        )

        print(
            f"{rank_number}. "
            f"{book.get('title')}"
        )

        print(
            f"   Rating : "
            f"{book.get('rating')}"
        )

        print(
            f"   Reviews: "
            f"{book.get('rating_count')}"
        )

        print(
            f"   Price  : "
            f"{book.get('price_text')}"
        )

        print(
            f"   Score  : "
            f"{ranking_score(book):.4f}"
        )

        print()


# ============================================================
# Manual Test
# ============================================================

if __name__ == "__main__":
    tests = [
        "ขอนิยายแฟนตาซีไม่เกิน 200 บาท",

        "สุ่มนิยายแฟนตาซีไม่เกิน 200 บาท",

        "ขอหนังสือคอมราคาไม่เกิน 200 บาท",

        "หานิยายสืบสวนรีวิวอย่างน้อย 20 คน",
    ]

    for query in tests:
        print()
        print(
            "QUERY:",
            query
        )

        result = recommend_from_text(
            query,
            limit=5,
        )

        print_result(
            result
        )