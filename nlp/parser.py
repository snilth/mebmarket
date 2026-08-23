import json
import re
from pathlib import Path

from rapidfuzz.fuzz import partial_ratio

from nlp.model import (
    classify_category,
    classify_intent,
)
from nlp.normalizer import normalize_text


CATEGORY_ALIASES_PATH = Path(
    "data/nlp/category_aliases.json"
)


def load_category_aliases():
    if not CATEGORY_ALIASES_PATH.exists():
        return {}

    with CATEGORY_ALIASES_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def exact_category_match(text):
    normalized = normalize_text(
        text
    )

    aliases = load_category_aliases()

    matches = []

    for category_id, data in aliases.items():
        category_name = data[
            "category_name"
        ]

        for alias in data.get(
            "aliases",
            []
        ):
            normalized_alias = normalize_text(
                alias
            )

            if (
                normalized_alias
                and normalized_alias
                in normalized
            ):
                matches.append(
                    {
                        "category_id":
                            str(category_id),

                        "category":
                            category_name,

                        "matched_alias":
                            alias,

                        "score":
                            1.0,

                        "method":
                            "exact_alias",
                    }
                )

    if not matches:
        return None

    matches.sort(
        key=lambda item: len(
            normalize_text(
                item["matched_alias"]
            )
        ),
        reverse=True,
    )

    return matches[0]


def fuzzy_category_match(
    text,
    threshold=75.0,
):
    normalized = normalize_text(
        text
    )

    aliases = load_category_aliases()

    best = None

    for category_id, data in aliases.items():
        for alias in data.get(
            "aliases",
            []
        ):
            normalized_alias = normalize_text(
                alias
            )

            score = partial_ratio(
                normalized_alias,
                normalized,
            )

            if (
                best is None
                or score > best["score"]
            ):
                best = {
                    "category_id":
                        str(category_id),

                    "category":
                        data[
                            "category_name"
                        ],

                    "matched_alias":
                        alias,

                    "score":
                        score,

                    "method":
                        "fuzzy_alias",
                }

    if (
        best
        and best["score"]
        >= threshold
    ):
        return best

    return None


RECOMMEND_PATTERNS = [
    r"แนะนำ",
    r"สุ่ม",
    r"ช่วยเลือก",
    r"เลือก.*ให้หน่อย",

    # Search-style requests are still recommendation
    # requests in this project.
    r"ค้นหา",
    r"ช่วยหา",
    r"หา(?=หนังสือ|นิยาย|การ์ตูน|เรื่อง|แนว)",

    # Existence questions
    r"มี.+ไหม",
    r"มี.+มั้ย",
    r"มี.+มั๊ย",
    r"มี.+หรือเปล่า",
    r"มี.+รึเปล่า",

    # User preference / need patterns
    r"อยาก\s*อ่าน",
    r"อยาก\s*ได้",
    r"อยาก\s*เรียน",
    r"อยาก\s*เข้าใจ",
    r"อยาก\s*รู้",
    r"อยาก\s*ปรับ",
    r"อยาก\s*พัฒนา",
    r"อยาก\s*ดูแล",
    r"อยาก\s*เริ่ม",

    r"ไม่รู้จะอ่านอะไร",

    r"ขอ(?=หนังสือ|นิยาย|การ์ตูน|เรื่อง|แนว)",

    r"เอา(?=หนังสือ|นิยาย|การ์ตูน|เรื่อง|แนว)",
]


def detect_intent_rule(text):
    normalized = normalize_text(
        text
    )

    for pattern in RECOMMEND_PATTERNS:
        if re.search(
            pattern,
            normalized,
        ):
            return {
                "intent":
                    "recommend",

                "score":
                    1.0,

                "method":
                    "rule",
            }

    return None


def detect_intent(text):
    rule_result = detect_intent_rule(
        text
    )

    if rule_result:
        return rule_result

    return classify_intent(
        text
    )


def detect_category(text):
    # 1. Explicit category aliases
    exact_result = exact_category_match(
        text
    )

    if exact_result:
        return exact_result

    # 2. Semantic category matching
    semantic_result = classify_category(
        text
    )

    if semantic_result:
        return semantic_result

    # 3. Typo fallback
    return fuzzy_category_match(
        text
    )


FREE_KEYWORDS = [
    "ฟรี",
    "ไม่เสียเงิน",
    "ไม่ต้องจ่าย",
    "ไม่คิดเงิน",
]

PAID_KEYWORDS = [
    "เสียเงิน",
    "หนังสือขาย",
    "แบบขาย",
    "แบบเสียเงิน",
]


def extract_price_type(text):
    normalized = normalize_text(
        text
    )

    for keyword in FREE_KEYWORDS:
        if keyword in normalized:
            return "free"

    for keyword in PAID_KEYWORDS:
        if keyword in normalized:
            return "paid"

    return None


MAX_PRICE_PATTERNS = [
    r"(?:ราคา)?ไม่เกิน\s*(\d+(?:\.\d+)?)\s*(?:บาท)?",

    r"(?:ราคา)?ต่ำกว่า\s*(\d+(?:\.\d+)?)\s*(?:บาท)?",

    r"งบ\s*(?:ไม่เกิน)?\s*(\d+(?:\.\d+)?)\s*(?:บาท)?",

    r"ภายใน\s*(\d+(?:\.\d+)?)\s*(?:บาท)?",
]


def extract_max_price(text):
    normalized = normalize_text(
        text
    )

    for pattern in MAX_PRICE_PATTERNS:
        match = re.search(
            pattern,
            normalized,
        )

        if match:
            return float(
                match.group(1)
            )

    return None


RATING_PATTERNS = [
    r"(?:เรตติ้ง|เรต|rating)\s*"
    r"(\d(?:\.\d+)?)"
    r"(?!\d)"
    r"\s*(?:ขึ้นไป|กว่า|มากกว่า)?",

    r"(\d(?:\.\d+)?)"
    r"(?!\d)"
    r"\s*(?:ดาว|star|stars)"
    r"\s*(?:ขึ้นไป|กว่า|มากกว่า)?",

    r"(?:คะแนน)\s*"
    r"(?:อย่างน้อย\s*)?"
    r"(\d(?:\.\d+)?)"
    r"(?!\d)"
    r"\s*(?:ขึ้นไป|กว่า|มากกว่า)?",

    r"(?:อย่างน้อย|ไม่น้อยกว่า)\s*"
    r"(\d(?:\.\d+)?)"
    r"(?!\d)"
    r"\s*(?:ดาว|คะแนน)",
]


def extract_min_rating(text):
    normalized = normalize_text(
        text
    )

    for pattern in RATING_PATTERNS:
        match = re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE,
        )

        if match:
            value = float(
                match.group(1)
            )

            if 0 <= value <= 5:
                return value

    return None


REVIEW_COUNT_PATTERNS = [
    r"(?:รีวิว|review|reviews)\s*"
    r"(?:อย่างน้อย|ไม่น้อยกว่า)?\s*"
    r"(\d+)\s*"
    r"(?:คน|รีวิว)?\s*"
    r"(?:ขึ้นไป|กว่า|มากกว่า)?",

    r"(?:อย่างน้อย|ไม่น้อยกว่า)\s*"
    r"(\d+)\s*"
    r"(?:รีวิว|review|reviews|คน)",

    r"(\d+)\s*"
    r"(?:รีวิว|review|reviews)\s*"
    r"(?:ขึ้นไป|กว่า|มากกว่า)",
]


def extract_min_rating_count(text):
    normalized = normalize_text(
        text
    )

    for pattern in REVIEW_COUNT_PATTERNS:
        match = re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE,
        )

        if match:
            value = int(
                match.group(1)
            )

            if value >= 0:
                return value

    return None


def validate_command(command):
    errors = []

    intent = command.get(
        "intent"
    )

    if intent not in {
        "recommend",
        "unknown",
    }:
        errors.append(
            "invalid_intent"
        )

    price_type = command.get(
        "price_type"
    )

    if price_type not in {
        None,
        "free",
        "paid",
    }:
        errors.append(
            "invalid_price_type"
        )

    max_price = command.get(
        "max_price"
    )

    if (
        max_price is not None
        and max_price < 0
    ):
        errors.append(
            "invalid_max_price"
        )

    min_rating = command.get(
        "min_rating"
    )

    if (
        min_rating is not None
        and not (
            0 <= min_rating <= 5
        )
    ):
        errors.append(
            "invalid_min_rating"
        )

    min_rating_count = command.get(
        "min_rating_count"
    )

    if (
        min_rating_count is not None
        and min_rating_count < 0
    ):
        errors.append(
            "invalid_min_rating_count"
        )

    return {
        "valid":
            len(errors) == 0,

        "errors":
            errors,
    }


def parse_command(text):
    normalized_text = normalize_text(
        text
    )

    intent_result = detect_intent(
        normalized_text
    )

    intent = intent_result[
        "intent"
    ]

    if intent == "unknown":
        command = {
            "text":
                text,

            "normalized_text":
                normalized_text,

            "intent":
                "unknown",

            "intent_score":
                intent_result.get(
                    "score"
                ),

            "intent_method":
                intent_result.get(
                    "method"
                ),

            "category_id":
                None,

            "category":
                None,

            "category_score":
                None,

            "category_method":
                None,

            "price_type":
                None,

            "max_price":
                None,

            "min_rating":
                None,

            "min_rating_count":
                None,
        }

        command[
            "validation"
        ] = validate_command(
            command
        )

        return command

    category_result = detect_category(
        normalized_text
    )

    command = {
        "text":
            text,

        "normalized_text":
            normalized_text,

        "intent":
            intent,

        "intent_score":
            intent_result.get(
                "score"
            ),

        "intent_method":
            intent_result.get(
                "method"
            ),

        "category_id":
            (
                category_result[
                    "category_id"
                ]
                if category_result
                else None
            ),

        "category":
            (
                category_result[
                    "category"
                ]
                if category_result
                else None
            ),

        "category_score":
            (
                category_result.get(
                    "score"
                )
                if category_result
                else None
            ),

        "category_method":
            (
                category_result.get(
                    "method"
                )
                if category_result
                else None
            ),

        "price_type":
            extract_price_type(
                normalized_text
            ),

        "max_price":
            extract_max_price(
                normalized_text
            ),

        "min_rating":
            extract_min_rating(
                normalized_text
            ),

        "min_rating_count":
            extract_min_rating_count(
                normalized_text
            ),
    }

    command[
        "validation"
    ] = validate_command(
        command
    )

    return command


if __name__ == "__main__":
    examples = [
        "หาหนังสือการเงินราคาไม่เกิน 200 บาท",

        "มีหนังสือคอมฟรีๆ มั้ย",

        "ขอนิยายสืบสวยหน่อย",

        "หาเรื่องการเงินการลงทุนน",

        (
            "หาหนังสือคอม "
            "ราคาไม่เกิน 200 บาท "
            "รีวิวอย่างน้อย 20 คน"
        ),

        (
            "อยากได้หนังสือการเงิน "
            "ไม่เกิน 300 "
            "เรต 4 ขึ้นไป "
            "รีวิว 20 คนขึ้นไป"
        ),

        "อยากอ่านจิตวิดยา",

        "ขอบคุณมาก",
    ]

    for text in examples:
        result = parse_command(
            text
        )

        print()
        print("=" * 80)

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )