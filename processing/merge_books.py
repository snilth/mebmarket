import json
from pathlib import Path


RAW_DIR = Path("data/raw/categories")
OUTPUT_DIR = Path("data/processed")
OUTPUT_PATH = OUTPUT_DIR / "books.json"


def load_raw_books():
    """
    Load all category_*.json files from the raw directory.
    """

    files = sorted(
        RAW_DIR.glob("category_*.json")
    )

    all_books = []

    print(
        f"Found {len(files)} category files"
    )

    for path in files:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            books = json.load(file)

        print(
            f"{path.name}: {len(books)} records"
        )

        all_books.extend(
            books
        )

    return all_books


def make_category_entry(book):
    """
    Convert raw category fields into a normalized
    category object.
    """

    return {
        "category_id":
            str(book["category_id"]),

        "category_name":
            book["category"],

        "parent_category_id":
            (
                str(
                    book[
                        "parent_category_id"
                    ]
                )
                if book.get(
                    "parent_category_id"
                )
                is not None
                else None
            ),

        "parent_category_name":
            book.get(
                "parent_category"
            ),
    }


def create_processed_book(book):
    """
    Create the processed schema for a new book.
    """

    return {
        "book_id":
            book["book_id"],

        "title":
            book["title"],

        "author":
            book["author"],

        "publisher":
            book.get(
                "publisher"
            ),

        "categories": [
            make_category_entry(
                book
            )
        ],

        "price":
            book["price"],

        "price_text":
            book.get(
                "price_text"
            ),

        "is_free":
            book["is_free"],

        "rating":
            book["rating"],

        "rating_count":
            book[
                "rating_count"
            ],

        "cover_url":
            book["cover_url"],

        "book_url":
            book["book_url"],
    }


def category_exists(
    categories,
    new_category,
):
    """
    Check whether the category is already attached
    to the processed book.
    """

    return any(
        category["category_id"]
        == new_category["category_id"]
        for category in categories
    )


def merge_missing_fields(
    existing,
    incoming,
):
    """
    Fill nullable fields when another category record
    contains better data.

    We do not blindly overwrite existing values.
    """

    nullable_fields = [
        "publisher",
        "cover_url",
        "book_url",
    ]

    for field in nullable_fields:
        if (
            not existing.get(field)
            and incoming.get(field)
        ):
            existing[field] = (
                incoming[field]
            )

    # Price may theoretically change between requests,
    # so keep the incoming value only if the existing
    # value is missing.
    if (
        existing.get("price")
        is None
        and incoming.get("price")
        is not None
    ):
        existing["price"] = (
            incoming["price"]
        )

        existing["price_text"] = (
            incoming.get(
                "price_text"
            )
        )

        existing["is_free"] = (
            incoming[
                "is_free"
            ]
        )

    # Same approach for rating.
    if (
        existing.get("rating")
        is None
        and incoming.get("rating")
        is not None
    ):
        existing["rating"] = (
            incoming["rating"]
        )

    # Prefer the larger rating count if records
    # from different category pages differ slightly.
    if (
        incoming.get(
            "rating_count",
            0
        )
        >
        existing.get(
            "rating_count",
            0
        )
    ):
        existing[
            "rating_count"
        ] = incoming[
            "rating_count"
        ]


def merge_books(raw_books):
    """
    Deduplicate raw records using book_id.

    If the same book appears in multiple categories,
    merge those categories into a single record.
    """

    books_by_id = {}

    duplicate_records = 0
    category_links_added = 0

    for book in raw_books:
        book_id = book.get(
            "book_id"
        )

        if book_id is None:
            continue

        new_category = (
            make_category_entry(
                book
            )
        )

        # First time this book is seen.
        if book_id not in books_by_id:
            books_by_id[
                book_id
            ] = (
                create_processed_book(
                    book
                )
            )

            continue

        # Duplicate across categories.
        duplicate_records += 1

        existing = books_by_id[
            book_id
        ]

        if not category_exists(
            existing["categories"],
            new_category,
        ):
            existing[
                "categories"
            ].append(
                new_category
            )

            category_links_added += 1

        merge_missing_fields(
            existing,
            book,
        )

    books = list(
        books_by_id.values()
    )

    return (
        books,
        duplicate_records,
        category_links_added,
    )


def save_processed_books(
    books,
):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            books,
            file,
            ensure_ascii=False,
            indent=2,
        )


def print_summary(
    raw_books,
    processed_books,
    duplicate_records,
    category_links_added,
):
    print()
    print("=" * 70)
    print("MERGE SUMMARY")
    print("=" * 70)

    print(
        "Raw records:",
        len(raw_books),
    )

    print(
        "Unique books:",
        len(processed_books),
    )

    print(
        "Duplicate records:",
        duplicate_records,
    )

    print(
        "Additional category links:",
        category_links_added,
    )

    print(
        "Books in multiple categories:",
        sum(
            len(book["categories"])
            > 1
            for book in processed_books
        ),
    )

    print(
        "Missing title:",
        sum(
            not book["title"]
            for book in processed_books
        ),
    )

    print(
        "Missing author:",
        sum(
            not book["author"]
            for book in processed_books
        ),
    )

    print(
        "Missing publisher:",
        sum(
            not book["publisher"]
            for book in processed_books
        ),
    )

    print(
        "Missing price:",
        sum(
            book["price"] is None
            for book in processed_books
        ),
    )

    print(
        "Missing rating:",
        sum(
            book["rating"] is None
            for book in processed_books
        ),
    )

    print(
        "Missing cover:",
        sum(
            not book["cover_url"]
            for book in processed_books
        ),
    )

    print(
        "Free books:",
        sum(
            book["is_free"]
            for book in processed_books
        ),
    )

    print(
        "Paid books:",
        sum(
            (
                not book["is_free"]
                and
                book["price"]
                is not None
            )
            for book in processed_books
        ),
    )

    print("=" * 70)


def main():
    raw_books = (
        load_raw_books()
    )

    (
        processed_books,
        duplicate_records,
        category_links_added,
    ) = merge_books(
        raw_books
    )

    save_processed_books(
        processed_books
    )

    print_summary(
        raw_books,
        processed_books,
        duplicate_records,
        category_links_added,
    )

    print()
    print(
        "Saved:",
        OUTPUT_PATH
    )


if __name__ == "__main__":
    main()