import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


BOOKS_PATH = Path("data/processed/books.json")
CONFIG_PATH = Path("data/config/target_categories.json")


# ============================================================
# Load Data
# ============================================================

def load_json(path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def load_books():
    if not BOOKS_PATH.exists():
        raise FileNotFoundError(
            f"Processed dataset not found: {BOOKS_PATH}"
        )

    books = load_json(BOOKS_PATH)

    if not isinstance(books, list):
        raise ValueError(
            "books.json must contain a JSON array."
        )

    return books


def load_target_categories():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Category config not found: {CONFIG_PATH}"
        )

    config = load_json(CONFIG_PATH)

    return {
        str(category["category_id"]): category
        for category in config["categories"]
    }


# ============================================================
# Helpers
# ============================================================

def is_valid_http_url(value):
    if not isinstance(value, str):
        return False

    try:
        parsed = urlparse(value)

        return (
            parsed.scheme in {"http", "https"}
            and bool(parsed.netloc)
        )

    except Exception:
        return False


def is_meb_book_url(value):
    if not is_valid_http_url(value):
        return False

    parsed = urlparse(value)

    hostname = (
        parsed.hostname or ""
    ).lower()

    return (
        hostname in {
            "mebmarket.com",
            "www.mebmarket.com",
        }
        and parsed.path.startswith("/ebook-")
    )


def add_error(errors, book_id, message):
    errors.append(
        {
            "book_id": book_id,
            "message": message,
        }
    )


def add_warning(warnings, book_id, message):
    warnings.append(
        {
            "book_id": book_id,
            "message": message,
        }
    )


# ============================================================
# Dataset-level Validation
# ============================================================

def validate_dataset_level(books):
    errors = []

    book_ids = [
        book.get("book_id")
        for book in books
        if book.get("book_id") is not None
    ]

    counts = Counter(book_ids)

    duplicates = [
        book_id
        for book_id, count in counts.items()
        if count > 1
    ]

    if duplicates:
        errors.append(
            {
                "book_id": None,
                "message": (
                    "Duplicate book_id values found: "
                    f"{duplicates[:20]}"
                ),
            }
        )

    return errors


# ============================================================
# Book Validation
# ============================================================

def validate_book(
    book,
    target_categories,
):
    errors = []
    warnings = []

    book_id = book.get("book_id")

    # --------------------------------------------------------
    # Book ID
    # --------------------------------------------------------

    if not isinstance(book_id, int):
        add_error(
            errors,
            book_id,
            "book_id must be an integer.",
        )

    elif book_id <= 0:
        add_error(
            errors,
            book_id,
            "book_id must be greater than 0.",
        )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    title = book.get("title")

    if (
        not isinstance(title, str)
        or not title.strip()
    ):
        add_error(
            errors,
            book_id,
            "title is missing or empty.",
        )

    # --------------------------------------------------------
    # Author
    # --------------------------------------------------------

    author = book.get("author")

    if (
        not isinstance(author, str)
        or not author.strip()
    ):
        add_error(
            errors,
            book_id,
            "author is missing or empty.",
        )

    # --------------------------------------------------------
    # Publisher
    #
    # Publisher is allowed to be null because MEB does not
    # expose it for every book.
    # --------------------------------------------------------

    publisher = book.get("publisher")

    if publisher is None or (
        isinstance(publisher, str)
        and not publisher.strip()
    ):
        add_warning(
            warnings,
            book_id,
            "publisher is missing.",
        )

    # --------------------------------------------------------
    # Price
    # --------------------------------------------------------

    price = book.get("price")

    if not isinstance(
        price,
        (int, float),
    ):
        add_error(
            errors,
            book_id,
            "price must be numeric.",
        )

    elif price < 0:
        add_error(
            errors,
            book_id,
            "price cannot be negative.",
        )

    # --------------------------------------------------------
    # is_free
    # --------------------------------------------------------

    is_free = book.get("is_free")

    if not isinstance(is_free, bool):
        add_error(
            errors,
            book_id,
            "is_free must be boolean.",
        )

    elif isinstance(
        price,
        (int, float),
    ):
        if is_free and price != 0:
            add_error(
                errors,
                book_id,
                (
                    "is_free is true but "
                    f"price is {price}."
                ),
            )

        if not is_free and price == 0:
            add_error(
                errors,
                book_id,
                (
                    "price is 0 but "
                    "is_free is false."
                ),
            )

    # --------------------------------------------------------
    # Rating
    # --------------------------------------------------------

    rating = book.get("rating")

    if not isinstance(
        rating,
        (int, float),
    ):
        add_error(
            errors,
            book_id,
            "rating must be numeric.",
        )

    elif not 0 <= rating <= 5:
        add_error(
            errors,
            book_id,
            (
                "rating must be between "
                "0 and 5."
            ),
        )

    # --------------------------------------------------------
    # Rating Count
    # --------------------------------------------------------

    rating_count = book.get(
        "rating_count"
    )

    if not isinstance(
        rating_count,
        int,
    ):
        add_error(
            errors,
            book_id,
            "rating_count must be an integer.",
        )

    elif rating_count < 0:
        add_error(
            errors,
            book_id,
            "rating_count cannot be negative.",
        )

    # --------------------------------------------------------
    # Cover URL
    # --------------------------------------------------------

    cover_url = book.get(
        "cover_url"
    )

    if not is_valid_http_url(
        cover_url
    ):
        add_error(
            errors,
            book_id,
            "cover_url is invalid.",
        )

    # --------------------------------------------------------
    # MEB Book URL
    # --------------------------------------------------------

    book_url = book.get(
        "book_url"
    )

    if not is_meb_book_url(
        book_url
    ):
        add_error(
            errors,
            book_id,
            (
                "book_url is not a valid "
                "MEB ebook URL."
            ),
        )

    # --------------------------------------------------------
    # Categories
    # --------------------------------------------------------

    categories = book.get(
        "categories"
    )

    if (
        not isinstance(categories, list)
        or not categories
    ):
        add_error(
            errors,
            book_id,
            "categories must be a non-empty list.",
        )

    else:
        seen_category_ids = set()

        for category in categories:
            if not isinstance(
                category,
                dict,
            ):
                add_error(
                    errors,
                    book_id,
                    (
                        "Each category must "
                        "be an object."
                    ),
                )

                continue

            category_id = str(
                category.get(
                    "category_id",
                    "",
                )
            )

            category_name = (
                category.get(
                    "category_name"
                )
            )

            if not category_id:
                add_error(
                    errors,
                    book_id,
                    "category_id is missing.",
                )

                continue

            # Duplicate category inside one book
            if category_id in seen_category_ids:
                add_error(
                    errors,
                    book_id,
                    (
                        "Duplicate category "
                        f"{category_id} "
                        "inside book."
                    ),
                )

            seen_category_ids.add(
                category_id
            )

            # Category must belong to our target dataset
            if (
                category_id
                not in target_categories
            ):
                add_error(
                    errors,
                    book_id,
                    (
                        "Unknown category_id: "
                        f"{category_id}"
                    ),
                )

                continue

            expected = (
                target_categories[
                    category_id
                ]
            )

            expected_name = (
                expected[
                    "category_name"
                ]
            )

            if (
                category_name
                != expected_name
            ):
                add_error(
                    errors,
                    book_id,
                    (
                        "Category name mismatch "
                        f"for {category_id}: "
                        f"{category_name!r} "
                        "!= "
                        f"{expected_name!r}"
                    ),
                )

    return errors, warnings


# ============================================================
# Validation Runner
# ============================================================

def validate_books(
    books,
    target_categories,
):
    errors = []
    warnings = []

    errors.extend(
        validate_dataset_level(
            books
        )
    )

    for book in books:
        (
            book_errors,
            book_warnings,
        ) = validate_book(
            book,
            target_categories,
        )

        errors.extend(
            book_errors
        )

        warnings.extend(
            book_warnings
        )

    return errors, warnings


# ============================================================
# Summary
# ============================================================

def print_summary(
    books,
    target_categories,
    errors,
    warnings,
):
    print()
    print("=" * 70)
    print("DATASET VALIDATION")
    print("=" * 70)

    print(
        "Dataset:",
        BOOKS_PATH,
    )

    print(
        "Records:",
        len(books),
    )

    print(
        "Target categories:",
        len(target_categories),
    )

    print(
        "Errors:",
        len(errors),
    )

    print(
        "Warnings:",
        len(warnings),
    )

    print("-" * 70)

    print(
        "Unique book IDs:",
        len(
            {
                book.get("book_id")
                for book in books
            }
        ),
    )

    print(
        "Free books:",
        sum(
            book.get("is_free")
            is True
            for book in books
        ),
    )

    print(
        "Paid books:",
        sum(
            book.get("is_free")
            is False
            for book in books
        ),
    )

    print(
        "Missing publisher:",
        sum(
            not book.get("publisher")
            for book in books
        ),
    )

    print(
        "Multi-category books:",
        sum(
            len(
                book.get(
                    "categories",
                    []
                )
            ) > 1
            for book in books
        ),
    )

    print("=" * 70)


def print_issues(
    errors,
    warnings,
    limit=20,
):
    if errors:
        print()
        print("ERRORS")
        print("-" * 70)

        for issue in errors[:limit]:
            print(
                f"[{issue['book_id']}] "
                f"{issue['message']}"
            )

        if len(errors) > limit:
            print(
                f"... and "
                f"{len(errors) - limit} "
                "more errors"
            )

    if warnings:
        print()
        print("WARNINGS")
        print("-" * 70)

        for issue in warnings[:limit]:
            print(
                f"[{issue['book_id']}] "
                f"{issue['message']}"
            )

        if len(warnings) > limit:
            print(
                f"... and "
                f"{len(warnings) - limit} "
                "more warnings"
            )


# ============================================================
# Main
# ============================================================

def main():
    books = load_books()

    target_categories = (
        load_target_categories()
    )

    errors, warnings = (
        validate_books(
            books,
            target_categories,
        )
    )

    print_summary(
        books,
        target_categories,
        errors,
        warnings,
    )

    print_issues(
        errors,
        warnings,
    )

    print()

    if errors:
        print(
            "RESULT: FAILED"
        )

        sys.exit(1)

    print(
        "RESULT: PASSED"
    )

    if warnings:
        print(
            "Dataset is valid, "
            "but contains non-critical warnings."
        )

    sys.exit(0)


if __name__ == "__main__":
    main()