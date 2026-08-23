import json
from collections import defaultdict
from pathlib import Path

from nlp.parser import parse_command


TEST_PATH = Path(
    "data/nlp/final_test_commands.json"
)


ENTITY_FIELDS = [
    "price_type",
    "max_price",
    "min_rating",
    "min_rating_count",
]


# ============================================================
# Load Test Data
# ============================================================

def load_tests():
    with TEST_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "test_commands.json must contain a list"
        )

    return data


# ============================================================
# Compare Helpers
# ============================================================

def values_equal(
    predicted,
    expected,
):
    """
    Compare values safely.

    Numeric values are compared as floats.
    """

    if (
        predicted is None
        and expected is None
    ):
        return True

    if (
        isinstance(predicted, (int, float))
        and isinstance(expected, (int, float))
    ):
        return abs(
            float(predicted)
            - float(expected)
        ) < 1e-6

    return predicted == expected


# ============================================================
# Single Test Evaluation
# ============================================================

def evaluate_case(test_case):
    text = test_case["text"]

    expected = test_case[
        "expected"
    ]

    predicted = parse_command(
        text
    )

    # ----------------------------------------
    # Intent
    # ----------------------------------------

    intent_correct = values_equal(
        predicted.get("intent"),
        expected.get("intent"),
    )

    # ----------------------------------------
    # Category
    # ----------------------------------------

    category_correct = values_equal(
        predicted.get("category_id"),
        expected.get("category_id"),
    )

    # ----------------------------------------
    # Entities
    # ----------------------------------------

    entity_results = {}

    for field in ENTITY_FIELDS:
        entity_results[field] = (
            values_equal(
                predicted.get(field),
                expected.get(field),
            )
        )

    entity_correct_count = sum(
        entity_results.values()
    )

    entity_total = len(
        ENTITY_FIELDS
    )

    # ----------------------------------------
    # Overall
    # ----------------------------------------

    overall_correct = (
        intent_correct
        and category_correct
        and all(
            entity_results.values()
        )
    )

    return {
        "text":
            text,

        "type":
            test_case.get(
                "type",
                "unknown",
            ),

        "expected":
            expected,

        "predicted":
            predicted,

        "intent_correct":
            intent_correct,

        "category_correct":
            category_correct,

        "entity_results":
            entity_results,

        "entity_correct_count":
            entity_correct_count,

        "entity_total":
            entity_total,

        "overall_correct":
            overall_correct,
    }


# ============================================================
# Aggregate Metrics
# ============================================================

def calculate_metrics(
    results,
):
    total = len(results)

    if total == 0:
        return {}

    intent_correct = sum(
        result[
            "intent_correct"
        ]
        for result in results
    )

    category_correct = sum(
        result[
            "category_correct"
        ]
        for result in results
    )

    entity_correct = sum(
        result[
            "entity_correct_count"
        ]
        for result in results
    )

    entity_total = sum(
        result[
            "entity_total"
        ]
        for result in results
    )

    overall_correct = sum(
        result[
            "overall_correct"
        ]
        for result in results
    )

    return {
        "total":
            total,

        "intent_accuracy":
            intent_correct
            / total,

        "category_accuracy":
            category_correct
            / total,

        "entity_accuracy":
            (
                entity_correct
                / entity_total
                if entity_total
                else 0
            ),

        "overall_accuracy":
            overall_correct
            / total,
    }


# ============================================================
# Metrics by Type
# ============================================================

def calculate_metrics_by_type(
    results,
):
    grouped = defaultdict(
        list
    )

    for result in results:
        grouped[
            result["type"]
        ].append(
            result
        )

    return {
        command_type:
            calculate_metrics(
                items
            )
        for command_type, items
        in grouped.items()
    }


# ============================================================
# Error Analysis
# ============================================================

def collect_errors(
    results,
):
    errors = []

    for result in results:
        if result[
            "overall_correct"
        ]:
            continue

        differences = []

        expected = result[
            "expected"
        ]

        predicted = result[
            "predicted"
        ]

        if not result[
            "intent_correct"
        ]:
            differences.append(
                {
                    "field":
                        "intent",

                    "expected":
                        expected.get(
                            "intent"
                        ),

                    "predicted":
                        predicted.get(
                            "intent"
                        ),
                }
            )

        if not result[
            "category_correct"
        ]:
            differences.append(
                {
                    "field":
                        "category_id",

                    "expected":
                        expected.get(
                            "category_id"
                        ),

                    "predicted":
                        predicted.get(
                            "category_id"
                        ),
                }
            )

        for field, correct in (
            result[
                "entity_results"
            ].items()
        ):
            if not correct:
                differences.append(
                    {
                        "field":
                            field,

                        "expected":
                            expected.get(
                                field
                            ),

                        "predicted":
                            predicted.get(
                                field
                            ),
                    }
                )

        errors.append(
            {
                "text":
                    result["text"],

                "type":
                    result["type"],

                "differences":
                    differences,

                "intent_method":
                    predicted.get(
                        "intent_method"
                    ),

                "category_method":
                    predicted.get(
                        "category_method"
                    ),

                "intent_score":
                    predicted.get(
                        "intent_score"
                    ),

                "category_score":
                    predicted.get(
                        "category_score"
                    ),
            }
        )

    return errors


# ============================================================
# Display
# ============================================================

def percentage(value):
    return (
        f"{value * 100:.2f}%"
    )


def print_metrics(
    metrics,
):
    print()
    print("=" * 70)
    print("NLP EVALUATION")
    print("=" * 70)

    print(
        "Test commands:",
        metrics["total"],
    )

    print(
        "Intent Accuracy:",
        percentage(
            metrics[
                "intent_accuracy"
            ]
        ),
    )

    print(
        "Category Accuracy:",
        percentage(
            metrics[
                "category_accuracy"
            ]
        ),
    )

    print(
        "Entity Accuracy:",
        percentage(
            metrics[
                "entity_accuracy"
            ]
        ),
    )

    print(
        "Overall Command Accuracy:",
        percentage(
            metrics[
                "overall_accuracy"
            ]
        ),
    )

    print("=" * 70)


def print_metrics_by_type(
    metrics_by_type,
):
    print()
    print("ACCURACY BY COMMAND TYPE")
    print("-" * 70)

    for command_type in sorted(
        metrics_by_type
    ):
        metrics = (
            metrics_by_type[
                command_type
            ]
        )

        print()
        print(
            command_type.upper()
        )

        print(
            f"  Commands : "
            f"{metrics['total']}"
        )

        print(
            "  Intent   :",
            percentage(
                metrics[
                    "intent_accuracy"
                ]
            ),
        )

        print(
            "  Category :",
            percentage(
                metrics[
                    "category_accuracy"
                ]
            ),
        )

        print(
            "  Entities :",
            percentage(
                metrics[
                    "entity_accuracy"
                ]
            ),
        )

        print(
            "  Overall  :",
            percentage(
                metrics[
                    "overall_accuracy"
                ]
            ),
        )


def print_errors(
    errors,
    limit=20,
):
    print()
    print("FAILED COMMANDS")
    print("-" * 70)

    if not errors:
        print(
            "No failed commands."
        )

        return

    for index, error in enumerate(
        errors[:limit],
        start=1,
    ):
        print()
        print(
            f"{index}. "
            f"[{error['type']}] "
            f"{error['text']}"
        )

        for difference in error[
            "differences"
        ]:
            print(
                f"   {difference['field']}: "
                f"{difference['predicted']!r} "
                f"!= "
                f"{difference['expected']!r}"
            )

        print(
            "   intent_method:",
            error[
                "intent_method"
            ],
        )

        print(
            "   category_method:",
            error[
                "category_method"
            ],
        )

        print(
            "   intent_score:",
            error[
                "intent_score"
            ],
        )

        print(
            "   category_score:",
            error[
                "category_score"
            ],
        )

    if len(errors) > limit:
        print()
        print(
            f"... and "
            f"{len(errors) - limit} "
            "more failed commands"
        )


# ============================================================
# Save Report
# ============================================================

def save_report(
    metrics,
    metrics_by_type,
    errors,
):
    output_path = Path(
        "data/nlp/evaluation_report.json"
    )

    report = {
        "metrics":
            metrics,

        "metrics_by_type":
            metrics_by_type,

        "failed_commands":
            errors,
    }

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        "Saved report:",
        output_path
    )


# ============================================================
# Main
# ============================================================

def main():
    tests = load_tests()

    results = []

    print(
        f"Evaluating "
        f"{len(tests)} commands..."
    )

    for index, test_case in enumerate(
        tests,
        start=1,
    ):
        result = evaluate_case(
            test_case
        )

        results.append(
            result
        )

        status = (
            "PASS"
            if result[
                "overall_correct"
            ]
            else "FAIL"
        )

        print(
            f"[{index:03}/{len(tests):03}] "
            f"{status} | "
            f"{test_case['text']}"
        )

    metrics = calculate_metrics(
        results
    )

    metrics_by_type = (
        calculate_metrics_by_type(
            results
        )
    )

    errors = collect_errors(
        results
    )

    print_metrics(
        metrics
    )

    print_metrics_by_type(
        metrics_by_type
    )

    print_errors(
        errors
    )

    save_report(
        metrics,
        metrics_by_type,
        errors,
    )


if __name__ == "__main__":
    main()