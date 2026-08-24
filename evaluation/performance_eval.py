import json
import statistics
import time

from pathlib import Path

from nlp.model import (
    preload_nlp,
)

from nlp.parser import (
    parse_command,
)

from recommendation.engine import (
    recommend_books,
)

from line.flex_carousel import (
    build_line_response,
)


OUTPUT_PATH = Path(
    "data/evaluation/performance_results.json"
)


TEST_QUERIES = [
    "ขอนิยายแฟนตาซี",

    "อยากอ่านเรื่องเวทมนตร์กับมังกร",

    "ขอหนังสือคอมราคาไม่เกิน 200 บาท",

    "แนะนำหนังสือการเงินเรต 4 ขึ้นไป",

    "หานิยายสืบสวนรีวิวอย่างน้อย 20 คน",

    (
        "ขอนิยายแฟนตาซีราคาไม่เกิน "
        "200 บาท เรต 4 ขึ้นไป"
    ),

    "ขอหนังสือสุขภาพฟรี",

    "ชช ฟรี",

    "ญญ ราคาไม่เกิน 150",

    "สุ่มนิยายแฟนตาซี",
]


def percentile(
    values,
    percentile_value,
):
    if not values:
        return 0.0

    values = sorted(
        values
    )

    index = (
        percentile_value
        / 100
        * (
            len(values)
            - 1
        )
    )

    lower = int(
        index
    )

    upper = min(
        lower + 1,
        len(values) - 1,
    )

    fraction = (
        index
        - lower
    )

    return (
        values[
            lower
        ]
        * (
            1 - fraction
        )
        +
        values[
            upper
        ]
        * fraction
    )


def summarize(
    values,
):
    if not values:
        return {
            "average_ms":
                0,

            "median_ms":
                0,

            "min_ms":
                0,

            "max_ms":
                0,

            "p95_ms":
                0,
        }

    return {
        "average_ms":
            statistics.mean(
                values
            ),

        "median_ms":
            statistics.median(
                values
            ),

        "min_ms":
            min(
                values
            ),

        "max_ms":
            max(
                values
            ),

        "p95_ms":
            percentile(
                values,
                95,
            ),
    }


def evaluate_performance(
    iterations=3,
):
    """
    Warm-start performance evaluation.

    Model loading is intentionally excluded because
    the LINE webhook preloads E5 at server startup.
    """

    print()
    print(
        "Preloading NLP model..."
    )

    preload_nlp()

    print(
        "Warm-up..."
    )

    # --------------------------------------------------------
    # Warm-up
    # --------------------------------------------------------

    for query in TEST_QUERIES:
        command = parse_command(
            query
        )

        result = recommend_books(
            command,
            limit=5,
        )

        build_line_response(
            result
        )

    # --------------------------------------------------------
    # Measurements
    # --------------------------------------------------------

    nlp_times = []
    recommendation_times = []
    flex_times = []
    total_times = []

    for _ in range(
        iterations
    ):
        for query in TEST_QUERIES:

            total_start = (
                time.perf_counter()
            )

            # ------------------------------------------------
            # NLP
            # ------------------------------------------------

            nlp_start = (
                time.perf_counter()
            )

            command = parse_command(
                query
            )

            nlp_end = (
                time.perf_counter()
            )

            # ------------------------------------------------
            # Recommendation
            # ------------------------------------------------

            recommendation_start = (
                time.perf_counter()
            )

            result = recommend_books(
                command,
                limit=5,
            )

            recommendation_end = (
                time.perf_counter()
            )

            # ------------------------------------------------
            # Flex
            # ------------------------------------------------

            flex_start = (
                time.perf_counter()
            )

            build_line_response(
                result
            )

            flex_end = (
                time.perf_counter()
            )

            total_end = (
                time.perf_counter()
            )

            nlp_times.append(
                (
                    nlp_end
                    - nlp_start
                )
                * 1000
            )

            recommendation_times.append(
                (
                    recommendation_end
                    - recommendation_start
                )
                * 1000
            )

            flex_times.append(
                (
                    flex_end
                    - flex_start
                )
                * 1000
            )

            total_times.append(
                (
                    total_end
                    - total_start
                )
                * 1000
            )

    result = {
        "iterations":
            iterations,

        "queries_per_iteration":
            len(
                TEST_QUERIES
            ),

        "total_requests":
            (
                iterations
                * len(
                    TEST_QUERIES
                )
            ),

        "model_loading_included":
            False,

        "nlp":
            summarize(
                nlp_times
            ),

        "recommendation":
            summarize(
                recommendation_times
            ),

        "flex_message":
            summarize(
                flex_times
            ),

        "total":
            summarize(
                total_times
            ),
    }

    # Rubric target:
    # < 1.5 - 2 seconds.
    #
    # We use the stricter 1.5 sec threshold.
    result[
        "target_ms"
    ] = 1500

    result[
        "passed"
    ] = (
        result[
            "total"
        ][
            "p95_ms"
        ]
        < result[
            "target_ms"
        ]
    )

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


def print_metric(
    title,
    metric,
):
    print()
    print(
        title
    )

    print(
        f"  Average : "
        f"{metric['average_ms']:.2f} ms"
    )

    print(
        f"  Median  : "
        f"{metric['median_ms']:.2f} ms"
    )

    print(
        f"  Min     : "
        f"{metric['min_ms']:.2f} ms"
    )

    print(
        f"  Max     : "
        f"{metric['max_ms']:.2f} ms"
    )

    print(
        f"  P95     : "
        f"{metric['p95_ms']:.2f} ms"
    )


def print_result(
    result,
):
    print()
    print("=" * 70)
    print("PERFORMANCE EVALUATION")
    print("=" * 70)

    print(
        "Requests:",
        result[
            "total_requests"
        ],
    )

    print(
        "Model loading included:",
        result[
            "model_loading_included"
        ],
    )

    print_metric(
        "NLP",
        result[
            "nlp"
        ],
    )

    print_metric(
        "Recommendation",
        result[
            "recommendation"
        ],
    )

    print_metric(
        "Flex Message",
        result[
            "flex_message"
        ],
    )

    print_metric(
        "TOTAL",
        result[
            "total"
        ],
    )

    print()
    print(
        "Target:",
        f"< {result['target_ms']} ms",
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


if __name__ == "__main__":
    result = evaluate_performance(
        iterations=3,
    )

    print_result(
        result
    )