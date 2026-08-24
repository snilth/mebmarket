import json
import re

from pathlib import Path

from rapidfuzz.fuzz import partial_ratio

from nlp.model import (
    classify_category,
    classify_intent,
)

from nlp.normalizer import (
    normalize_text,
)


# ============================================================
# Configuration
# ============================================================

CATEGORY_ALIASES_PATH = Path(
    "data/nlp/category_aliases.json"
)


# ============================================================
# Category Aliases
# ============================================================

def load_category_aliases():
    if not CATEGORY_ALIASES_PATH.exists():
        return {}

    with CATEGORY_ALIASES_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


# ============================================================
# Exact Category Matching
# ============================================================

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
            [],
        ):
            normalized_alias = normalize_text(
                alias
            )

            if not normalized_alias:
                continue

            if normalized_alias in normalized:
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

    # Prefer the longest / most specific alias.
    matches.sort(
        key=lambda item: len(
            normalize_text(
                item[
                    "matched_alias"
                ]
            )
        ),
        reverse=True,
    )

    return matches[0]


# ============================================================
# Fuzzy Category Matching
# ============================================================

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
        category_name = data[
            "category_name"
        ]

        for alias in data.get(
            "aliases",
            [],
        ):
            normalized_alias = normalize_text(
                alias
            )

            if not normalized_alias:
                continue

            score = partial_ratio(
                normalized_alias,
                normalized,
            )

            if (
                best is None
                or score > best[
                    "score"
                ]
            ):
                best = {
                    "category_id":
                        str(category_id),

                    "category":
                        category_name,

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


# ============================================================
# Intent Rules
# ============================================================

RECOMMEND_PATTERNS = [
    r"แนะนำ",
    r"สุ่ม",
    r"random",
    r"ช่วยเลือก",
    r"เลือก.*ให้หน่อย",

    r"ค้นหา",
    r"ช่วยหา",
    r"หา(?=หนังสือ|นิยาย|การ์ตูน|เรื่อง|แนว)",

    r"มี.+ไหม",
    r"มี.+มั้ย",
    r"มี.+มั๊ย",
    r"มี.+หรือเปล่า",
    r"มี.+รึเปล่า",

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
            flags=re.IGNORECASE,
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
    """
    Detection order:

    1. Explicit linguistic rule
    2. Explicit category signal
    3. Semantic E5 fallback
    """

    rule_result = detect_intent_rule(
        text
    )

    if rule_result:
        return rule_result

    # Allow category-only commands:
    #
    #   แฟนตาซี
    #   ชช ฟรี
    #   ญญ ไม่เกิน 200
    #   จิตวิทยา
    #
    category_result = exact_category_match(
        text
    )

    if category_result:
        return {
            "intent":
                "recommend",

            "score":
                1.0,

            "method":
                "category_signal",
        }

    return classify_intent(
        text
    )


# ============================================================
# Random Request Detection
# ============================================================

RANDOM_PATTERNS = [
    r"สุ่ม",
    r"random",
    r"แรนดอม",
    r"เลือกแบบสุ่ม",
    r"สุ่มมา",
]


def extract_randomize(text):
    """
    randomize=True only when the user explicitly asks
    for random recommendations.
    """

    normalized = normalize_text(
        text
    )

    for pattern in RANDOM_PATTERNS:
        if re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE,
        ):
            return True

    return False


# ============================================================
# Category Detection
# ============================================================

def detect_category(text):
    # --------------------------------------------------------
    # 1. Exact alias
    # --------------------------------------------------------

    exact_result = exact_category_match(
        text
    )

    if exact_result:
        return exact_result

    # --------------------------------------------------------
    # 2. Semantic E5
    # --------------------------------------------------------

    semantic_result = classify_category(
        text
    )

    if semantic_result:
        return semantic_result

    # --------------------------------------------------------
    # 3. Typo fallback
    # --------------------------------------------------------

    return fuzzy_category_match(
        text
    )


# ============================================================
# Price Type
# ============================================================

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


# ============================================================
# Maximum Price
# ============================================================

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


# ============================================================
# Minimum Rating
# ============================================================

RATING_PATTERNS = [
    (
        r"(?:เรตติ้ง|เรต|rating)\s*"
        r"(\d(?:\.\d+)?)"
        r"(?!\d)"
        r"\s*(?:ขึ้นไป|กว่า|มากกว่า)?"
    ),

    (
        r"(\d(?:\.\d+)?)"
        r"(?!\d)"
        r"\s*(?:ดาว|star|stars)"
        r"\s*(?:ขึ้นไป|กว่า|มากกว่า)?"
    ),

    (
        r"(?:คะแนน)\s*"
        r"(?:อย่างน้อย\s*)?"
        r"(\d(?:\.\d+)?)"
        r"(?!\d)"
        r"\s*(?:ขึ้นไป|กว่า|มากกว่า)?"
    ),

    (
        r"(?:อย่างน้อย|ไม่น้อยกว่า)\s*"
        r"(\d(?:\.\d+)?)"
        r"(?!\d)"
        r"\s*(?:ดาว|คะแนน)"
    ),
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


# ============================================================
# Minimum Rating Count
# ============================================================

REVIEW_COUNT_PATTERNS = [
    (
        r"(?:รีวิว|review|reviews)\s*"
        r"(?:อย่างน้อย|ไม่น้อยกว่า)?\s*"
        r"(\d+)\s*"
        r"(?:คน|รีวิว)?\s*"
        r"(?:ขึ้นไป|กว่า|มากกว่า)?"
    ),

    (
        r"(?:อย่างน้อย|ไม่น้อยกว่า)\s*"
        r"(\d+)\s*"
        r"(?:รีวิว|review|reviews|คน)"
    ),

    (
        r"(\d+)\s*"
        r"(?:รีวิว|review|reviews)\s*"
        r"(?:ขึ้นไป|กว่า|มากกว่า)"
    ),
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


# ============================================================
# Validation
# ============================================================

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


# ============================================================
# Main Parser
# ============================================================

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

    randomize = extract_randomize(
        normalized_text
    )

    # --------------------------------------------------------
    # Unknown
    # --------------------------------------------------------

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

            "randomize":
                False,

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

    # --------------------------------------------------------
    # Category
    # --------------------------------------------------------

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

        # NEW
        "randomize":
            randomize,

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


# ============================================================
# Manual Test
# ============================================================

if __name__ == "__main__":
    examples = [
        "ขอนิยายแฟนตาซี",

        "สุ่มนิยายแฟนตาซี",

        "ขอหนังสือคอมราคาไม่เกิน 200 บาท",

        "หานิยายสืบสวนรีวิวอย่างน้อย 20 คน",

        "ชช ฟรี",

        "ญญ ราคาไม่เกิน 150",

        "อยากอ่านเรื่องเวทมนตร์กับมังกร",

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