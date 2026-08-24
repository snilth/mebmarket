import json
import traceback

from pathlib import Path

from evaluation.data_quality import (
    evaluate_data_quality,
    print_result as print_data_quality,
)

from evaluation.nlp_eval import (
    run_nlp_evaluation,
    print_result as print_nlp,
)

from evaluation.recommendation_eval import (
    evaluate_recommendation,
    print_result as print_recommendation,
)

from evaluation.performance_eval import (
    evaluate_performance,
    print_result as print_performance,
)


OUTPUT_PATH = Path(
    "data/evaluation/evaluation_summary.json"
)


def run_section(
    name,
    callback,
):
    print()
    print()
    print("#" * 78)

    print(
        name
    )

    print("#" * 78)

    try:
        result = callback()

        return {
            "success":
                True,

            "result":
                result,

            "error":
                None,
        }

    except Exception as exc:
        print()
        print(
            f"ERROR in {name}:"
        )

        print(
            repr(exc)
        )

        traceback.print_exc()

        return {
            "success":
                False,

            "result":
                None,

            "error":
                repr(exc),
        }


def main():
    print()
    print("=" * 78)

    print(
        "MEB MARKET RECOMMENDATION SYSTEM"
    )

    print(
        "FINAL EVALUATION"
    )

    print("=" * 78)

    # ========================================================
    # Data Quality
    # ========================================================

    data_quality = run_section(
        "[1/4] DATA QUALITY",

        evaluate_data_quality,
    )

    if data_quality[
        "success"
    ]:
        print_data_quality(
            data_quality[
                "result"
            ]
        )

    # ========================================================
    # NLP
    # ========================================================

    nlp = run_section(
        "[2/4] NLP",

        run_nlp_evaluation,
    )

    nlp_passed = False

    if nlp[
        "success"
    ]:
        nlp_passed = print_nlp(
            nlp[
                "result"
            ]
        )

    # ========================================================
    # Recommendation
    # ========================================================

    recommendation = run_section(
        "[3/4] RECOMMENDATION",

        evaluate_recommendation,
    )

    if recommendation[
        "success"
    ]:
        print_recommendation(
            recommendation[
                "result"
            ]
        )

    # ========================================================
    # Performance
    # ========================================================

    performance = run_section(
        "[4/4] PERFORMANCE",

        lambda:
            evaluate_performance(
                iterations=3
            ),
    )

    if performance[
        "success"
    ]:
        print_performance(
            performance[
                "result"
            ]
        )

    # ========================================================
    # Final Status
    # ========================================================

    data_passed = (
        data_quality[
            "success"
        ]
        and data_quality[
            "result"
        ][
            "passed"
        ]
    )

    recommendation_passed = (
        recommendation[
            "success"
        ]
        and recommendation[
            "result"
        ][
            "passed"
        ]
    )

    performance_passed = (
        performance[
            "success"
        ]
        and performance[
            "result"
        ][
            "passed"
        ]
    )

    final_passed = (
        data_passed
        and nlp_passed
        and recommendation_passed
        and performance_passed
    )

    summary = {
        "data_quality":
            data_quality,

        "nlp":
            nlp,

        "recommendation":
            recommendation,

        "performance":
            performance,

        "passed":
            final_passed,
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print()
    print("=" * 78)

    print(
        "FINAL RESULT:",
        (
            "PASS"
            if final_passed
            else "FAIL"
        ),
    )

    print("=" * 78)

    print()
    print(
        "Saved:"
    )

    print(
        OUTPUT_PATH
    )


if __name__ == "__main__":
    main()