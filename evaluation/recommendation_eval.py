import json

from collections import Counter
from pathlib import Path

from nlp.parser import (
    parse_command,
)

from recommendation.engine import (
    load_books,
    filter_books,
    rank_candidates,
    recommend_books,
)


# ============================================================
# Paths
# ============================================================

OUTPUT_PATH = Path(
    "data/evaluation/recommendation_results.json"
)


# ============================================================
# Test Cases
# ============================================================

CONSTRAINT_TESTS = [
    {
        "name":
            "category",

        "query":
            "ขอนิยายแฟนตาซี",

        "expected_category_id":
            "4",
    },

    {
        "name":
            "max_price",

        "query":
            "ขอหนังสือคอมราคาไม่เกิน 200 บาท",

        "max_price":
            200,
    },

    {
        "name":
            "free",

        "query":
            "ขอหนังสือสุขภาพฟรี",

        "price_type":
            "free",
    },

    {
        "name":
            "min_rating",

        "query":
            "แนะนำหนังสือการเงินเรต 4 ขึ้นไป",

        "min_rating":
            4.0,
    },

    {
        "name":
            "min_review_count",

        "query":
            "หานิยายสืบสวนรีวิวอย่างน้อย 20 คน",

        "min_rating_count":
            20,
    },

    {
        "name":
            "complex",

        "query": (
            "ขอนิยายแฟนตาซีราคาไม่เกิน "
            "200 บาท เรต 4 ขึ้นไป"
        ),

        "expected_category_id":
            "4",

        "max_price":
            200,

        "min_rating":
            4.0,
    },
]


# ============================================================
# Category Helper
# ============================================================

def book_has_category(
    book,
    expected_category_id,
):
    """
    Support the actual processed dataset schema:

    {
        "categories": [
            {
                "category_id": "4",
                "category_name": "นิยายแฟนตาซี"
            }
        ]
    }

    Also supports a flat category_id field in case
    the dataset schema changes later.
    """

    if expected_category_id is None:
        return True

    expected_category_id = str(
        expected_category_id
    )

    # --------------------------------------------------------
    # Flat schema fallback
    # --------------------------------------------------------

    flat_category_id = book.get(
        "category_id"
    )

    if flat_category_id is not None:
        return (
            str(flat_category_id)
            == expected_category_id
        )

    # --------------------------------------------------------
    # Actual schema
    # --------------------------------------------------------

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
            == expected_category_id
        ):
            return True

    return False


# ============================================================
# Validate One Recommended Book
# ============================================================

def validate_book_against_case(
    book,
    case,
):
    errors = []

    # --------------------------------------------------------
    # Category
    # --------------------------------------------------------

    expected_category_id = case.get(
        "expected_category_id"
    )

    if expected_category_id is not None:

        if not book_has_category(
            book,
            expected_category_id,
        ):
            errors.append(
                "category"
            )

    # --------------------------------------------------------
    # Maximum Price
    # --------------------------------------------------------

    max_price = case.get(
        "max_price"
    )

    if max_price is not None:

        try:
            price = float(
                book.get(
                    "price"
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            errors.append(
                "price"
            )

        else:
            if price > max_price:
                errors.append(
                    "price"
                )

    # --------------------------------------------------------
    # Free
    # --------------------------------------------------------

    price_type = case.get(
        "price_type"
    )

    if price_type == "free":

        if not bool(
            book.get(
                "is_free"
            )
        ):
            errors.append(
                "free"
            )

    # --------------------------------------------------------
    # Minimum Rating
    # --------------------------------------------------------

    min_rating = case.get(
        "min_rating"
    )

    if min_rating is not None:

        try:
            rating = float(
                book.get(
                    "rating"
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            errors.append(
                "rating"
            )

        else:
            if rating < min_rating:
                errors.append(
                    "rating"
                )

    # --------------------------------------------------------
    # Minimum Review Count
    # --------------------------------------------------------

    min_rating_count = case.get(
        "min_rating_count"
    )

    if min_rating_count is not None:

        try:
            rating_count = int(
                book.get(
                    "rating_count"
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            errors.append(
                "rating_count"
            )

        else:
            if (
                rating_count
                < min_rating_count
            ):
                errors.append(
                    "rating_count"
                )

    return errors


# ============================================================
# Constraint Evaluation
# ============================================================

def evaluate_constraints():
    results = []

    for case in CONSTRAINT_TESTS:

        command = parse_command(
            case[
                "query"
            ]
        )

        result = recommend_books(
            command,
            limit=5,
            offset=0,
        )

        books = result.get(
            "books",
            [],
        )

        errors = []

        for book in books:
            errors.extend(
                validate_book_against_case(
                    book,
                    case,
                )
            )

        # ----------------------------------------------------
        # Top-5 validation
        # ----------------------------------------------------

        count_valid = (
            1 <= len(books) <= 5
        )

        # If candidates >= 5,
        # the engine should return exactly 5.
        candidate_count = int(
            result.get(
                "candidate_count",
                0,
            )
            or 0
        )

        if (
            candidate_count >= 5
            and len(books) != 5
        ):
            count_valid = False

            errors.append(
                "top5_count"
            )

        case_passed = (
            result.get(
                "status"
            )
            == "ok"
            and count_valid
            and not errors
        )

        results.append(
            {
                "name":
                    case[
                        "name"
                    ],

                "query":
                    case[
                        "query"
                    ],

                "candidate_count":
                    candidate_count,

                "returned_books":
                    len(books),

                "errors":
                    sorted(
                        set(
                            errors
                        )
                    ),

                "passed":
                    case_passed,
            }
        )

    return results


# ============================================================
# Ranking Evaluation
# ============================================================

def evaluate_ranking():
    """
    Verify that normal recommendations return the actual
    highest-ranked five books, not randomized results.
    """

    query = (
        "ขอนิยายแฟนตาซี"
    )

    command = parse_command(
        query
    )

    books = load_books()

    candidates = filter_books(
        books,
        command,
    )

    ranked = rank_candidates(
        candidates
    )

    result = recommend_books(
        command,
        limit=5,
        offset=0,
    )

    returned_ids = [
        str(
            book.get(
                "book_id"
            )
        )
        for book
        in result.get(
            "books",
            [],
        )
    ]

    expected_ids = [
        str(
            book.get(
                "book_id"
            )
        )
        for book
        in ranked[:5]
    ]

    return {
        "query":
            query,

        "returned_ids":
            returned_ids,

        "expected_top5_ids":
            expected_ids,

        "returned_count":
            len(
                returned_ids
            ),

        "passed":
            (
                returned_ids
                == expected_ids
            ),
    }


# ============================================================
# Pagination Evaluation
# ============================================================

def evaluate_pagination():
    """
    Check that:
        first request = rank 1-5
        next page     = rank 6-10

    and no books overlap between pages.
    """

    command = parse_command(
        "ขอนิยายแฟนตาซี"
    )

    page_1 = recommend_books(
        command,
        limit=5,
        offset=0,
    )

    page_2 = recommend_books(
        command,
        limit=5,
        offset=5,
    )

    page_1_ids = [
        str(
            book.get(
                "book_id"
            )
        )
        for book
        in page_1.get(
            "books",
            [],
        )
    ]

    page_2_ids = [
        str(
            book.get(
                "book_id"
            )
        )
        for book
        in page_2.get(
            "books",
            [],
        )
    ]

    overlap = (
        set(page_1_ids)
        & set(page_2_ids)
    )

    passed = (
        len(page_1_ids) == 5
        and len(page_2_ids) == 5
        and len(overlap) == 0
    )

    return {
        "page_1_count":
            len(page_1_ids),

        "page_2_count":
            len(page_2_ids),

        "overlap_count":
            len(overlap),

        "overlap_ids":
            sorted(
                overlap
            ),

        "passed":
            passed,
    }


# ============================================================
# Randomization Evaluation
# ============================================================

def evaluate_randomization(
    runs=100,
):
    """
    Explicit random command only.

    Measures:
        - duplicate books inside one Top-5
        - number of unique result sets
        - number of unique books observed
        - repeated identical sets
    """

    command = parse_command(
        "สุ่มนิยายแฟนตาซี"
    )

    all_sets = []

    duplicate_inside_run = 0

    invalid_result_count = 0

    book_frequency = Counter()

    for _ in range(
        runs
    ):

        result = recommend_books(
            command,
            limit=5,
        )

        books = result.get(
            "books",
            [],
        )

        ids = [
            str(
                book.get(
                    "book_id"
                )
            )
            for book in books
        ]

        if len(ids) != 5:
            invalid_result_count += 1

        if (
            len(ids)
            != len(
                set(ids)
            )
        ):
            duplicate_inside_run += 1

        normalized_set = tuple(
            sorted(
                ids
            )
        )

        all_sets.append(
            normalized_set
        )

        book_frequency.update(
            ids
        )

    unique_sets = len(
        set(
            all_sets
        )
    )

    identical_set_repeats = (
        runs
        - unique_sets
    )

    unique_books_observed = len(
        book_frequency
    )

    most_common = (
        book_frequency.most_common(
            10
        )
    )

    passed = (
        invalid_result_count == 0
        and duplicate_inside_run == 0
        and unique_sets > 1
        and unique_books_observed > 5
    )

    return {
        "runs":
            runs,

        "books_per_run":
            5,

        "invalid_result_count":
            invalid_result_count,

        "duplicate_inside_run":
            duplicate_inside_run,

        "unique_result_sets":
            unique_sets,

        "identical_set_repeats":
            identical_set_repeats,

        "unique_books_observed":
            unique_books_observed,

        "most_common_books":
            [
                {
                    "book_id":
                        book_id,

                    "appearances":
                        count,
                }
                for (
                    book_id,
                    count
                )
                in most_common
            ],

        "passed":
            passed,
    }


# ============================================================
# Full Recommendation Evaluation
# ============================================================

def evaluate_recommendation():
    constraint_results = (
        evaluate_constraints()
    )

    ranking_result = (
        evaluate_ranking()
    )

    pagination_result = (
        evaluate_pagination()
    )

    randomization_result = (
        evaluate_randomization(
            runs=100,
        )
    )

    constraint_pass_count = sum(
        1
        for item
        in constraint_results
        if item[
            "passed"
        ]
    )

    total_constraint_tests = len(
        constraint_results
    )

    passed = (
        constraint_pass_count
        == total_constraint_tests
        and ranking_result[
            "passed"
        ]
        and pagination_result[
            "passed"
        ]
        and randomization_result[
            "passed"
        ]
    )

    result = {
        "constraint_tests":
            constraint_results,

        "constraint_pass_count":
            constraint_pass_count,

        "constraint_total":
            total_constraint_tests,

        "ranking":
            ranking_result,

        "pagination":
            pagination_result,

        "randomization":
            randomization_result,

        "passed":
            passed,
    }

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

def print_result(
    result,
):
    print()
    print("=" * 70)
    print("RECOMMENDATION EVALUATION")
    print("=" * 70)

    print()
    print("CONSTRAINT TESTS")
    print("-" * 70)

    for test in result[
        "constraint_tests"
    ]:

        status = (
            "PASS"
            if test[
                "passed"
            ]
            else "FAIL"
        )

        print(
            f"{status:4} | "
            f"{test['name']:<18} "
            f"| candidates="
            f"{test['candidate_count']:<4} "
            f"| returned="
            f"{test['returned_books']}"
        )

        if test[
            "errors"
        ]:
            print(
                "     Errors:",
                test[
                    "errors"
                ],
            )

    print()

    print(
        "Constraint tests:",
        (
            f"{result['constraint_pass_count']}"
            f"/{result['constraint_total']}"
        ),
    )

    print(
        "Ranking Top-5:",
        (
            "PASS"
            if result[
                "ranking"
            ][
                "passed"
            ]
            else "FAIL"
        ),
    )

    print(
        "Pagination:",
        (
            "PASS"
            if result[
                "pagination"
            ][
                "passed"
            ]
            else "FAIL"
        ),
    )

    random_result = result[
        "randomization"
    ]

    print()
    print("RANDOMIZATION")
    print("-" * 70)

    print(
        "Runs:",
        random_result[
            "runs"
        ],
    )

    print(
        "Invalid Top-5 results:",
        random_result[
            "invalid_result_count"
        ],
    )

    print(
        "Duplicate inside Top-5:",
        random_result[
            "duplicate_inside_run"
        ],
    )

    print(
        "Unique result sets:",
        random_result[
            "unique_result_sets"
        ],
    )

    print(
        "Unique books observed:",
        random_result[
            "unique_books_observed"
        ],
    )

    print(
        "Repeated identical sets:",
        random_result[
            "identical_set_repeats"
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
        evaluate_recommendation()
    )

    print_result(
        result
    )