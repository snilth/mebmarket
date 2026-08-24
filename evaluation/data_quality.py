import json

from pathlib import Path
from urllib.parse import urlparse


# ============================================================
# Paths
# ============================================================

BOOKS_PATH = Path(
    "data/processed/books.json"
)

OUTPUT_PATH = Path(
    "data/evaluation/data_quality.json"
)


# ============================================================
# Dataset
# ============================================================

def load_books():
    if not BOOKS_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {BOOKS_PATH}"
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
# URL Validation
# ============================================================

def is_valid_http_url(value):
    if not value:
        return False

    try:
        parsed = urlparse(
            str(value)
        )

        return (
            parsed.scheme
            in {
                "http",
                "https",
            }
            and bool(
                parsed.netloc
            )
        )

    except Exception:
        return False


# ============================================================
# Category Validation
# ============================================================

def has_valid_category(book):
    """
    Dataset schema:

    "categories": [
        {
            "category_id": "...",
            "category_name": "...",
            "parent_category_id": "...",
            "parent_category_name": "..."
        }
    ]

    A book is considered to have a valid category if at least
    one category contains both category_id and category_name.
    """

    categories = book.get(
        "categories"
    )

    if not isinstance(
        categories,
        list,
    ):
        return False

    if not categories:
        return False

    for category in categories:
        if not isinstance(
            category,
            dict,
        ):
            continue

        category_id = category.get(
            "category_id"
        )

        category_name = category.get(
            "category_name"
        )

        if (
            category_id
            and category_name
        ):
            return True

    return False


# ============================================================
# Data Quality Evaluation
# ============================================================

def evaluate_data_quality():
    books = load_books()

    total_records = len(
        books
    )

    # --------------------------------------------------------
    # Book IDs
    # --------------------------------------------------------

    book_ids = [
        str(
            book.get(
                "book_id"
            )
        )
        for book in books
        if book.get(
            "book_id"
        ) is not None
    ]

    unique_book_ids = len(
        set(book_ids)
    )

    missing_book_id = (
        total_records
        - len(book_ids)
    )

    duplicate_records = (
        len(book_ids)
        - unique_book_ids
    )

    # --------------------------------------------------------
    # Missing Values
    # --------------------------------------------------------

    missing_title = 0
    missing_author = 0
    missing_publisher = 0
    missing_price = 0
    missing_category = 0
    missing_cover = 0
    missing_book_url = 0

    # --------------------------------------------------------
    # Invalid Values
    # --------------------------------------------------------

    invalid_price = 0
    invalid_rating = 0
    invalid_rating_count = 0
    invalid_cover_url = 0
    invalid_book_url = 0
    invalid_category_structure = 0

    # --------------------------------------------------------
    # Dataset Statistics
    # --------------------------------------------------------

    free_books = 0
    paid_books = 0

    category_ids = set()
    category_names = set()

    multi_category_books = 0

    # ========================================================
    # Validate Every Record
    # ========================================================

    for book in books:

        # ----------------------------------------------------
        # Title
        # ----------------------------------------------------

        if not book.get(
            "title"
        ):
            missing_title += 1

        # ----------------------------------------------------
        # Author
        # ----------------------------------------------------

        if not book.get(
            "author"
        ):
            missing_author += 1

        # ----------------------------------------------------
        # Publisher
        #
        # Publisher is optional in this project.
        # Missing publisher creates a warning but is NOT
        # considered a critical validation failure.
        # ----------------------------------------------------

        if not book.get(
            "publisher"
        ):
            missing_publisher += 1

        # ----------------------------------------------------
        # Price
        # ----------------------------------------------------

        price_value = book.get(
            "price"
        )

        if price_value is None:
            missing_price += 1

        else:
            try:
                price = float(
                    price_value
                )

                if price < 0:
                    invalid_price += 1

            except (
                TypeError,
                ValueError,
            ):
                invalid_price += 1

        # ----------------------------------------------------
        # Categories
        # ----------------------------------------------------

        categories = book.get(
            "categories"
        )

        if not categories:
            missing_category += 1

        elif not isinstance(
            categories,
            list,
        ):
            invalid_category_structure += 1

        else:
            valid_category_found = False

            if len(categories) > 1:
                multi_category_books += 1

            for category in categories:

                if not isinstance(
                    category,
                    dict,
                ):
                    continue

                category_id = category.get(
                    "category_id"
                )

                category_name = category.get(
                    "category_name"
                )

                if (
                    category_id
                    and category_name
                ):
                    valid_category_found = True

                    category_ids.add(
                        str(category_id)
                    )

                    category_names.add(
                        str(category_name)
                    )

            if not valid_category_found:
                invalid_category_structure += 1

        # ----------------------------------------------------
        # Cover
        # ----------------------------------------------------

        cover_url = book.get(
            "cover_url"
        )

        if not cover_url:
            missing_cover += 1

        elif not is_valid_http_url(
            cover_url
        ):
            invalid_cover_url += 1

        # ----------------------------------------------------
        # Book URL
        # ----------------------------------------------------

        book_url = book.get(
            "book_url"
        )

        if not book_url:
            missing_book_url += 1

        elif not is_valid_http_url(
            book_url
        ):
            invalid_book_url += 1

        # ----------------------------------------------------
        # Rating
        # ----------------------------------------------------

        try:
            rating = float(
                book.get(
                    "rating",
                    0,
                )
            )

            if not (
                0 <= rating <= 5
            ):
                invalid_rating += 1

        except (
            TypeError,
            ValueError,
        ):
            invalid_rating += 1

        # ----------------------------------------------------
        # Rating Count
        # ----------------------------------------------------

        try:
            rating_count = int(
                book.get(
                    "rating_count",
                    0,
                )
            )

            if rating_count < 0:
                invalid_rating_count += 1

        except (
            TypeError,
            ValueError,
        ):
            invalid_rating_count += 1

        # ----------------------------------------------------
        # Free / Paid
        # ----------------------------------------------------

        if book.get(
            "is_free"
        ):
            free_books += 1

        else:
            paid_books += 1

    # ========================================================
    # Critical Errors
    # ========================================================

    critical_errors = (
        missing_book_id
        + duplicate_records
        + missing_title
        + missing_author
        + missing_price
        + missing_category
        + missing_cover
        + missing_book_url
        + invalid_price
        + invalid_rating
        + invalid_rating_count
        + invalid_cover_url
        + invalid_book_url
        + invalid_category_structure
    )

    # ========================================================
    # Warnings
    # ========================================================

    warnings = (
        missing_publisher
    )

    # ========================================================
    # Result
    # ========================================================

    result = {
        "total_records":
            total_records,

        "unique_book_ids":
            unique_book_ids,

        "duplicate_records":
            duplicate_records,

        "missing_book_id":
            missing_book_id,

        "categories": {
            "unique_category_ids":
                len(
                    category_ids
                ),

            "unique_category_names":
                len(
                    category_names
                ),

            "category_ids":
                sorted(
                    category_ids
                ),

            "category_names":
                sorted(
                    category_names
                ),

            "multi_category_books":
                multi_category_books,
        },

        "missing": {
            "title":
                missing_title,

            "author":
                missing_author,

            "publisher":
                missing_publisher,

            "price":
                missing_price,

            "category":
                missing_category,

            "cover_url":
                missing_cover,

            "book_url":
                missing_book_url,
        },

        "invalid": {
            "price":
                invalid_price,

            "rating":
                invalid_rating,

            "rating_count":
                invalid_rating_count,

            "category_structure":
                invalid_category_structure,

            "cover_url":
                invalid_cover_url,

            "book_url":
                invalid_book_url,
        },

        "free_books":
            free_books,

        "paid_books":
            paid_books,

        "critical_errors":
            critical_errors,

        "warnings":
            warnings,

        "passed":
            critical_errors == 0,
    }

    # ========================================================
    # Save
    # ========================================================

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return result


# ============================================================
# Print
# ============================================================

def print_result(result):
    print()
    print("=" * 70)
    print("DATA QUALITY")
    print("=" * 70)

    print(
        "Records:",
        result[
            "total_records"
        ],
    )

    print(
        "Unique books:",
        result[
            "unique_book_ids"
        ],
    )

    print(
        "Duplicates:",
        result[
            "duplicate_records"
        ],
    )

    print(
        "Unique categories:",
        result[
            "categories"
        ][
            "unique_category_ids"
        ],
    )

    print(
        "Multi-category books:",
        result[
            "categories"
        ][
            "multi_category_books"
        ],
    )

    print("-" * 70)

    print(
        "Missing title:",
        result[
            "missing"
        ][
            "title"
        ],
    )

    print(
        "Missing author:",
        result[
            "missing"
        ][
            "author"
        ],
    )

    print(
        "Missing publisher:",
        result[
            "missing"
        ][
            "publisher"
        ],
        "(warning only)",
    )

    print(
        "Missing price:",
        result[
            "missing"
        ][
            "price"
        ],
    )

    print(
        "Missing category:",
        result[
            "missing"
        ][
            "category"
        ],
    )

    print(
        "Missing cover:",
        result[
            "missing"
        ][
            "cover_url"
        ],
    )

    print(
        "Missing book URL:",
        result[
            "missing"
        ][
            "book_url"
        ],
    )

    print("-" * 70)

    print(
        "Invalid price:",
        result[
            "invalid"
        ][
            "price"
        ],
    )

    print(
        "Invalid rating:",
        result[
            "invalid"
        ][
            "rating"
        ],
    )

    print(
        "Invalid rating count:",
        result[
            "invalid"
        ][
            "rating_count"
        ],
    )

    print(
        "Invalid category structure:",
        result[
            "invalid"
        ][
            "category_structure"
        ],
    )

    print(
        "Invalid cover URL:",
        result[
            "invalid"
        ][
            "cover_url"
        ],
    )

    print(
        "Invalid book URL:",
        result[
            "invalid"
        ][
            "book_url"
        ],
    )

    print("-" * 70)

    print(
        "Free books:",
        result[
            "free_books"
        ],
    )

    print(
        "Paid books:",
        result[
            "paid_books"
        ],
    )

    print(
        "Warnings:",
        result[
            "warnings"
        ],
    )

    print(
        "Critical errors:",
        result[
            "critical_errors"
        ],
    )

    print("-" * 70)

    print(
        "RESULT:",
        (
            "PASS"
            if result[
                "passed"
            ]
            else "FAIL"
        ),
    )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    result = (
        evaluate_data_quality()
    )

    print_result(
        result
    )