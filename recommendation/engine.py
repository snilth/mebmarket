import json
import random
from functools import lru_cache
from pathlib import Path

from nlp.parser import parse_command


BOOKS_PATH = Path(
    "data/processed/books.json"
)


# ============================================================
# Load Dataset
# ============================================================

@lru_cache(maxsize=1)
def load_books():
    """
    Load processed MEB dataset once.
    """

    with BOOKS_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        books = json.load(file)

    if not isinstance(books, list):
        raise ValueError(
            "books.json must contain a list"
        )

    return books


# ============================================================
# Category Helper
# ============================================================

def book_matches_category(
    book,
    category_id,
):
    """
    Support both dataset formats:

    Old format:
        category_id: "4"

    Newer merged format:
        categories: [
            {
                "category_id": "4",
                ...
            }
        ]
    """

    if category_id is None:
        return True

    category_id = str(
        category_id
    )

    # ----------------------------------------
    # Flat schema
    # ----------------------------------------

    if "category_id" in book:
        return (
            str(
                book.get(
                    "category_id"
                )
            )
            == category_id
        )

    # ----------------------------------------
    # Multi-category schema
    # ----------------------------------------

    categories = book.get(
        "categories",
        []
    )

    for category in categories:
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
# Individual Filters
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

    price = book.get(
        "price"
    )

    if price is None:
        return False

    try:
        price = float(
            price
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    return (
        price <= float(
            max_price
        )
    )


def matches_min_rating(
    book,
    min_rating,
):
    if min_rating is None:
        return True

    rating = book.get(
        "rating"
    )

    if rating is None:
        return False

    try:
        rating = float(
            rating
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    return (
        rating >= float(
            min_rating
        )
    )


def matches_min_rating_count(
    book,
    min_rating_count,
):
    if min_rating_count is None:
        return True

    rating_count = book.get(
        "rating_count"
    )

    if rating_count is None:
        return False

    try:
        rating_count = int(
            rating_count
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    return (
        rating_count
        >= int(
            min_rating_count
        )
    )


# ============================================================
# Filter Books
# ============================================================

def filter_books(
    books,
    command,
):
    """
    Filter books using parsed NLP constraints.
    """

    category_id = command.get(
        "category_id"
    )

    price_type = command.get(
        "price_type"
    )

    max_price = command.get(
        "max_price"
    )

    min_rating = command.get(
        "min_rating"
    )

    min_rating_count = command.get(
        "min_rating_count"
    )

    results = []

    for book in books:
        if not book_matches_category(
            book,
            category_id,
        ):
            continue

        if not matches_price_type(
            book,
            price_type,
        ):
            continue

        if not matches_max_price(
            book,
            max_price,
        ):
            continue

        if not matches_min_rating(
            book,
            min_rating,
        ):
            continue

        if not matches_min_rating_count(
            book,
            min_rating_count,
        ):
            continue

        results.append(
            book
        )

    return results


# ============================================================
# Ranking
# ============================================================

def ranking_score(book):
    """
    Simple quality score.

    Rating is primary.
    Rating count gives a small confidence bonus.
    """

    rating = book.get(
        "rating"
    ) or 0

    rating_count = book.get(
        "rating_count"
    ) or 0

    try:
        rating = float(
            rating
        )

    except (
        TypeError,
        ValueError,
    ):
        rating = 0

    try:
        rating_count = int(
            rating_count
        )

    except (
        TypeError,
        ValueError,
    ):
        rating_count = 0

    return (
        rating,
        rating_count,
    )


# ============================================================
# Top-K Recommendation
# ============================================================

def select_top_books(
    candidates,
    limit=5,
    randomize=True,
    pool_size=20,
):
    """
    Rank candidates first, then optionally randomize
    inside the high-quality candidate pool.

    This avoids showing exactly the same books every time
    while still preferring good results.
    """

    if not candidates:
        return []

    ranked = sorted(
        candidates,
        key=ranking_score,
        reverse=True,
    )

    if not randomize:
        return ranked[
            :limit
        ]

    pool = ranked[
        :max(
            limit,
            min(
                pool_size,
                len(ranked),
            ),
        )
    ]

    if len(pool) <= limit:
        return pool

    return random.sample(
        pool,
        k=limit,
    )


# ============================================================
# Recommendation
# ============================================================

def recommend_books(
    command,
    limit=5,
    randomize=True,
):
    """
    Recommend books from an already-parsed command.
    """

    if command.get(
        "intent"
    ) != "recommend":
        return {
            "status":
                "unsupported_intent",

            "command":
                command,

            "candidate_count":
                0,

            "books":
                [],
        }

    books = load_books()

    candidates = filter_books(
        books,
        command,
    )

    selected = select_top_books(
        candidates,
        limit=limit,
        randomize=randomize,
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
    }


# ============================================================
# End-to-End
# ============================================================

def recommend_from_text(
    text,
    limit=5,
    randomize=True,
):
    """
    Full pipeline:

        Natural language
        -> NLP parser
        -> filters
        -> Top books
    """

    command = parse_command(
        text
    )

    return recommend_books(
        command,
        limit=limit,
        randomize=randomize,
    )


# ============================================================
# Pretty Print
# ============================================================

def print_result(result):
    print()
    print("=" * 80)

    command = result[
        "command"
    ]

    print(
        "Intent:",
        command.get(
            "intent"
        ),
    )

    print(
        "Category:",
        command.get(
            "category"
        ),
    )

    print(
        "Price type:",
        command.get(
            "price_type"
        ),
    )

    print(
        "Max price:",
        command.get(
            "max_price"
        ),
    )

    print(
        "Min rating:",
        command.get(
            "min_rating"
        ),
    )

    print(
        "Min rating count:",
        command.get(
            "min_rating_count"
        ),
    )

    print(
        "Candidates:",
        result[
            "candidate_count"
        ],
    )

    print(
        "Status:",
        result[
            "status"
        ],
    )

    print()

    for index, book in enumerate(
        result["books"],
        start=1,
    ):
        print(
            f"{index}. "
            f"{book.get('title')}"
        )

        print(
            "   Author:",
            book.get(
                "author"
            ),
        )

        print(
            "   Price:",
            book.get(
                "price_text",
                book.get(
                    "price"
                ),
            ),
        )

        print(
            "   Rating:",
            book.get(
                "rating"
            ),
            f"({book.get('rating_count')} ratings)",
        )

        print(
            "   URL:",
            book.get(
                "book_url"
            ),
        )

        print()


# ============================================================
# Manual Test
# ============================================================

if __name__ == "__main__":
    examples = [
        "ขอนิยายแฟนตาซี",

        "ขอหนังสือคอมราคาไม่เกิน 200 บาท",

        "แนะนำหนังสือการเงินเรต 4 ขึ้นไป",

        "อยากอ่านเรื่องเวทมนตร์กับมังกร",

        "หานิยายสืบสวนรีวิวอย่างน้อย 20 คน",

        "ขอหนังสือสุขภาพฟรี",
    ]

    for text in examples:
        print()
        print(
            "QUERY:",
            text
        )

        result = recommend_from_text(
            text,
            limit=5,
            randomize=True,
        )

        print_result(
            result
        )