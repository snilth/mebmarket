import json
import subprocess
import sys

from pathlib import Path


# ============================================================
# Paths
# ============================================================

SOURCE_REPORT_PATH = Path(
    "data/nlp/evaluation_report.json"
)

OUTPUT_PATH = Path(
    "data/evaluation/nlp_results.json"
)


# ============================================================
# Helpers
# ============================================================

def normalize_percentage(
    value,
):
    """
    Convert either:

        1.0   -> 100.0
        0.95  -> 95.0
        95.0  -> 95.0
        100.0 -> 100.0

    Returns None if the value is invalid.
    """

    if value is None:
        return None

    try:
        value = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    if 0 <= value <= 1:
        return (
            value
            * 100
        )

    return value


def recursive_find_metric(
    data,
    candidate_keys,
):
    """
    Search recursively for a numeric metric whose key
    matches one of candidate_keys.
    """

    candidate_keys = {
        key.lower()
        for key in candidate_keys
    }

    if isinstance(
        data,
        dict,
    ):

        for key, value in data.items():

            normalized_key = (
                str(key)
                .lower()
                .strip()
            )

            if (
                normalized_key
                in candidate_keys
            ):
                normalized = (
                    normalize_percentage(
                        value
                    )
                )

                if normalized is not None:
                    return normalized

        for value in data.values():

            found = recursive_find_metric(
                value,
                candidate_keys,
            )

            if found is not None:
                return found

    elif isinstance(
        data,
        list,
    ):

        for item in data:

            found = recursive_find_metric(
                item,
                candidate_keys,
            )

            if found is not None:
                return found

    return None


def extract_metrics(
    report,
):
    intent_accuracy = recursive_find_metric(
        report,
        {
            "intent_accuracy",
            "intent accuracy",
        },
    )

    category_accuracy = recursive_find_metric(
        report,
        {
            "category_accuracy",
            "category accuracy",
        },
    )

    entity_accuracy = recursive_find_metric(
        report,
        {
            "entity_accuracy",
            "entity accuracy",
        },
    )

    overall_accuracy = recursive_find_metric(
        report,
        {
            "overall_accuracy",
            "overall accuracy",
            "command_accuracy",
            "overall_command_accuracy",
        },
    )

    return {
        "intent_accuracy":
            intent_accuracy,

        "category_accuracy":
            category_accuracy,

        "entity_accuracy":
            entity_accuracy,

        "overall_accuracy":
            overall_accuracy,
    }


# ============================================================
# NLP Evaluation
# ============================================================

def run_nlp_evaluation():
    """
    Run the project's original NLP evaluator as-is.

    This prevents the final evaluation suite from
    duplicating or changing the original NLP test logic.
    """

    print(
        "Running original NLP evaluator..."
    )

    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "nlp.evaluator",
        ],

        text=True,
        capture_output=True,
    )

    # --------------------------------------------------------
    # Show original evaluator output
    # --------------------------------------------------------

    if process.stdout:
        print(
            process.stdout,
            end=(
                ""
                if process.stdout.endswith(
                    "\n"
                )
                else "\n"
            ),
        )

    if process.stderr:
        print(
            process.stderr,
            file=sys.stderr,
            end=(
                ""
                if process.stderr.endswith(
                    "\n"
                )
                else "\n"
            ),
        )

    if process.returncode != 0:
        raise RuntimeError(
            "nlp.evaluator failed with "
            f"exit code {process.returncode}"
        )

    # --------------------------------------------------------
    # Original evaluator must have generated its report
    # --------------------------------------------------------

    if not SOURCE_REPORT_PATH.exists():
        raise FileNotFoundError(
            "NLP evaluator completed but report "
            f"was not found: {SOURCE_REPORT_PATH}"
        )

    with SOURCE_REPORT_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        original_report = (
            json.load(
                file
            )
        )

    metrics = extract_metrics(
        original_report
    )

    missing_metrics = [
        key
        for key, value
        in metrics.items()
        if value is None
    ]

    if missing_metrics:
        raise ValueError(
            "Could not find NLP metrics in "
            "evaluation_report.json: "
            + ", ".join(
                missing_metrics
            )
        )

    # --------------------------------------------------------
    # Rubric threshold
    # --------------------------------------------------------

    threshold = 85.0

    passed = (
        metrics[
            "intent_accuracy"
        ]
        >= threshold
        and metrics[
            "category_accuracy"
        ]
        >= threshold
        and metrics[
            "entity_accuracy"
        ]
        >= threshold
        and metrics[
            "overall_accuracy"
        ]
        >= threshold
    )

    result = {
        **metrics,

        "threshold":
            threshold,

        "source_report":
            str(
                SOURCE_REPORT_PATH
            ),

        "passed":
            passed,

        # Preserve original report for final report writing.
        "original_report":
            original_report,
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
    print("NLP FINAL EVALUATION")
    print("=" * 70)

    print(
        f"Intent Accuracy   : "
        f"{result['intent_accuracy']:.2f}%"
    )

    print(
        f"Category Accuracy : "
        f"{result['category_accuracy']:.2f}%"
    )

    print(
        f"Entity Accuracy   : "
        f"{result['entity_accuracy']:.2f}%"
    )

    print(
        f"Overall Accuracy  : "
        f"{result['overall_accuracy']:.2f}%"
    )

    print()
    print(
        f"Rubric threshold  : "
        f">= {result['threshold']:.2f}%"
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

    return result[
        "passed"
    ]


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    result = (
        run_nlp_evaluation()
    )

    print_result(
        result
    )