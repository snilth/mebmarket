import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer


# ============================================================
# Configuration
# ============================================================

MODEL_NAME = "intfloat/multilingual-e5-base"

CATEGORY_CONFIG_PATH = Path(
    "data/config/target_categories.json"
)


# ============================================================
# Semantic Descriptions: Categories
# ============================================================

CATEGORY_DESCRIPTIONS = {
    "21": (
        "นิยายรัก โรแมนติก ความรัก ความสัมพันธ์ "
        "คู่รัก การตกหลุมรัก ชีวิตรัก"
    ),

    "228": (
        "นิยายรักจีนโบราณ จีนย้อนยุค ฮ่องเต้ ฮองเฮา "
        "อ๋อง แม่ทัพ วังหลวง คุณหนู ราชวงศ์จีน"
    ),

    "54": (
        "นิยายวาย Boy Love BL Yaoi "
        "ความรักและความสัมพันธ์ระหว่างผู้ชายกับผู้ชาย"
    ),

    "51": (
        "นิยาย Girl Love GL Yuri "
        "ความรักและความสัมพันธ์ระหว่างผู้หญิงกับผู้หญิง"
    ),

    "4": (
        "นิยายแฟนตาซี เวทมนตร์ พลังวิเศษ มังกร "
        "โลกต่างมิติ โลกสมมติ การผจญภัย สิ่งเหนือธรรมชาติ"
    ),

    "48": (
        "นิยายสืบสวนสอบสวน ทริลเลอร์ นักสืบ "
        "คดีฆาตกรรม อาชญากรรม ไขปริศนา "
        "ตามหาความจริง"
    ),

    "32": (
        "นิยายลึกลับ เขย่าขวัญ สยองขวัญ ผี "
        "วิญญาณ ความหลอน ความน่ากลัว "
        "เหตุการณ์ประหลาด"
    ),

    "20": (
        "นิยายไซไฟ science fiction อวกาศ "
        "มนุษย์ต่างดาว ยานอวกาศ หุ่นยนต์ "
        "เทคโนโลยีอนาคต โลกอนาคต"
    ),

    "15": (
        "หนังสือพัฒนาตนเอง พัฒนาตัวเอง "
        "ความสำเร็จ เปลี่ยนนิสัย การตั้งเป้าหมาย "
        "บริหารเวลา เพิ่มประสิทธิภาพชีวิต"
    ),

    "154": (
        "หนังสือจิตวิทยา ความคิด อารมณ์ "
        "พฤติกรรมมนุษย์ สุขภาพใจ ความสัมพันธ์ "
        "การเข้าใจตนเองและผู้อื่น"
    ),

    "60": (
        "หนังสือการเงินการลงทุน เงิน หุ้น กองทุน "
        "การออม วางแผนการเงิน ตลาดทุน "
        "การสร้างความมั่งคั่ง"
    ),

    "18": (
        "หนังสือคอมพิวเตอร์ ไอที เขียนโปรแกรม "
        "programming Python JavaScript software "
        "AI cybersecurity network database cloud"
    ),

    "8": (
        "หนังสือวิทยาศาสตร์และเทคโนโลยี "
        "ฟิสิกส์ เคมี ชีววิทยา วิทยาศาสตร์ "
        "เทคโนโลยี นวัตกรรม วิทยาการ"
    ),

    "22": (
        "หนังสือสุขภาพ การดูแลร่างกาย "
        "อาหาร ออกกำลังกาย โรค การแพทย์ "
        "สุขภาพกาย การใช้ชีวิตเพื่อสุขภาพ"
    ),

    "23": (
        "หนังสือท่องเที่ยว การเดินทาง "
        "สถานที่ท่องเที่ยว ประเทศ เมือง "
        "โรงแรม วางแผนเที่ยว คู่มือเดินทาง"
    ),

    "148": (
        "การ์ตูนทั่วไป comic manga มังงะ "
        "หนังสือการ์ตูน เรื่องราวในรูปแบบภาพ"
    ),

    "12": (
        "การ์ตูนผู้หญิง shoujo shojo manga "
        "โรแมนติก ความรัก ชีวิตวัยรุ่น "
        "การ์ตูนสำหรับผู้อ่านหญิง"
    ),
}


# ============================================================
# Semantic Descriptions: Intents
# ============================================================

INTENT_DESCRIPTIONS = {
    "recommend": [
        "ช่วยแนะนำหนังสือให้ฉันอ่าน",
        "เลือกหนังสือที่น่าอ่านให้หน่อย",
        "สุ่มหนังสือมาแนะนำ",
        "ฉันไม่รู้ว่าจะอ่านอะไรดี",
        "อยากได้หนังสือมาอ่าน",
        "อยากอ่านหนังสือสักเล่ม",

        "ช่วยค้นหาหนังสือให้หน่อย",
        "ช่วยหาหนังสือให้หน่อย",
        "มีหนังสือประเภทนี้ไหม",
        "มีหนังสือตามเงื่อนไขนี้หรือเปล่า",
        "ค้นหาหนังสือที่ต้องการ",

        "อยากเรียนเรื่องนี้",
        "อยากเข้าใจเรื่องนี้",
        "อยากพัฒนาตัวเอง",
        "อยากเริ่มเรียนรู้เรื่องนี้",
    ],

    "unknown": [
        "สวัสดี",
        "ขอบคุณ",
        "วันนี้อากาศดี",
        "ทำอะไรอยู่",
        "โอเค",
        "ลาก่อน",
        "กินข้าวหรือยัง",
        "ขอบใจมาก",
        "สวัสดีครับ",
        "ขอบคุณมากครับ",
    ],
}


# ============================================================
# Device
# ============================================================

def get_device():
    """
    PyTorch ROCm uses the CUDA-compatible API.

    Therefore AMD ROCm GPU is accessed with device="cuda".
    """

    if torch.cuda.is_available():
        return "cuda"

    return "cpu"


# ============================================================
# Model
# ============================================================

@lru_cache(maxsize=1)
def get_model():
    device = get_device()

    print(
        f"Loading NLP model: {MODEL_NAME}"
    )

    print(
        f"Device: {device}"
    )

    if device == "cuda":
        print(
            "GPU:",
            torch.cuda.get_device_name(0),
        )

    return SentenceTransformer(
        MODEL_NAME,
        device=device,
    )


# ============================================================
# Embedding Helpers
# ============================================================

def encode_queries(texts):
    """
    E5 expects query texts to have the 'query:' prefix.
    """

    model = get_model()

    prepared = [
        f"query: {text}"
        for text in texts
    ]

    return model.encode(
        prepared,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )


def encode_passages(texts):
    """
    E5 expects candidate/reference texts
    to have the 'passage:' prefix.
    """

    model = get_model()

    prepared = [
        f"passage: {text}"
        for text in texts
    ]

    return model.encode(
        prepared,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )


# ============================================================
# Category Config
# ============================================================

@lru_cache(maxsize=1)
def load_categories():
    with CATEGORY_CONFIG_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    return {
        str(category["category_id"]):
            category
        for category in config["categories"]
    }


# ============================================================
# Category Index
# ============================================================

@lru_cache(maxsize=1)
def build_category_index():
    """
    Build embeddings for all selected MEB categories once.
    """

    categories = load_categories()

    category_ids = []
    category_names = []
    descriptions = []

    for category_id, category in categories.items():
        category_name = category[
            "category_name"
        ]

        description = (
            CATEGORY_DESCRIPTIONS.get(
                category_id,
                category_name,
            )
        )

        semantic_text = (
            f"{category_name}. "
            f"{description}"
        )

        category_ids.append(
            category_id
        )

        category_names.append(
            category_name
        )

        descriptions.append(
            semantic_text
        )

    embeddings = encode_passages(
        descriptions
    )

    return {
        "category_ids":
            category_ids,

        "category_names":
            category_names,

        "descriptions":
            descriptions,

        "embeddings":
            embeddings,
    }


# ============================================================
# Category Ranking
# ============================================================

def rank_categories(
    text,
    top_k=5,
):
    """
    Rank the 17 MEB categories by semantic similarity.
    """

    if not text or not text.strip():
        return []

    query_embedding = encode_queries(
        [text]
    )[0]

    index = build_category_index()

    scores = np.dot(
        index["embeddings"],
        query_embedding,
    )

    ranking = np.argsort(
        scores
    )[::-1][:top_k]

    results = []

    for position in ranking:
        results.append(
            {
                "category_id":
                    index[
                        "category_ids"
                    ][position],

                "category":
                    index[
                        "category_names"
                    ][position],

                "score":
                    round(
                        float(
                            scores[position]
                        ),
                        4,
                    ),
            }
        )

    return results


# ============================================================
# Category Classification
# ============================================================

def classify_category(
    text,
    threshold=0.78,
    min_margin=0.015,
):
    """
    Select the best semantic MEB category.

    Two confidence checks are used:

    1. Top-1 similarity must exceed threshold.
    2. Top-1 must be separated from Top-2
       by at least min_margin.

    These values are initial defaults.
    They will later be tuned using evaluator.py.
    """

    results = rank_categories(
        text,
        top_k=2,
    )

    if not results:
        return None

    best = results[0]

    if best["score"] < threshold:
        return None

    margin = None

    if len(results) >= 2:
        margin = (
            best["score"]
            - results[1]["score"]
        )

        if margin < min_margin:
            return None

    return {
        "category_id":
            best["category_id"],

        "category":
            best["category"],

        "score":
            best["score"],

        "margin":
            (
                round(
                    margin,
                    4,
                )
                if margin is not None
                else None
            ),

        "method":
            "semantic_e5",
    }


# ============================================================
# Intent Index
# ============================================================

@lru_cache(maxsize=1)
def build_intent_index():
    """
    Instead of averaging intent examples into one vector,
    keep every example separately.

    The query is compared against all examples and each
    intent receives the mean of its best semantic matches.
    """

    labels = []
    texts = []

    for intent, examples in INTENT_DESCRIPTIONS.items():
        for example in examples:
            labels.append(
                intent
            )

            texts.append(
                example
            )

    embeddings = encode_passages(
        texts
    )

    return {
        "labels":
            labels,

        "texts":
            texts,

        "embeddings":
            embeddings,
    }


# ============================================================
# Intent Ranking
# ============================================================

def rank_intents(
    text,
    top_matches_per_intent=3,
):
    """
    Rank intents using semantic similarity.

    For each intent, use the average score of its
    top semantic examples.
    """

    if not text or not text.strip():
        return []

    query_embedding = encode_queries(
        [text]
    )[0]

    index = build_intent_index()

    scores = np.dot(
        index["embeddings"],
        query_embedding,
    )

    grouped = {}

    for label, score in zip(
        index["labels"],
        scores,
    ):
        grouped.setdefault(
            label,
            []
        ).append(
            float(score)
        )

    results = []

    for intent, intent_scores in grouped.items():
        intent_scores.sort(
            reverse=True
        )

        selected = intent_scores[
            :top_matches_per_intent
        ]

        score = sum(
            selected
        ) / len(selected)

        results.append(
            {
                "intent":
                    intent,

                "score":
                    round(
                        score,
                        4,
                    ),
            }
        )

    results.sort(
        key=lambda item:
            item["score"],
        reverse=True,
    )

    return results


# ============================================================
# Intent Classification
# ============================================================

def classify_intent(
    text,
    threshold=0.76,
    min_margin=0.01,
):
    """
    Semantic intent classification.

    Intents:
        recommend
        search
        unknown

    Thresholds are preliminary and will later be tuned
    using the evaluation dataset.
    """

    results = rank_intents(
        text
    )

    if not results:
        return {
            "intent": "unknown",
            "score": 0.0,
            "margin": None,
            "method": "semantic_e5",
        }

    best = results[0]

    if best["score"] < threshold:
        return {
            "intent": "unknown",
            "score": best["score"],
            "margin": None,
            "method": "semantic_e5",
        }

    margin = None

    if len(results) >= 2:
        margin = (
            best["score"]
            - results[1]["score"]
        )

        if margin < min_margin:
            return {
                "intent": "unknown",
                "score": best["score"],
                "margin": round(
                    margin,
                    4,
                ),
                "method": "semantic_e5",
            }

    return {
        "intent":
            best["intent"],

        "score":
            best["score"],

        "margin":
            (
                round(
                    margin,
                    4,
                )
                if margin is not None
                else None
            ),

        "method":
            "semantic_e5",
    }

# ============================================================
# Preload
# ============================================================

def preload_nlp():
    """
    Preload the semantic model and all static embeddings.

    This is useful for production/webhook servers because
    the first LINE user should not have to wait for model
    initialization.
    """

    print("=" * 70)
    print("PRELOADING NLP")
    print("=" * 70)

    # Load multilingual-e5-base into memory / GPU.
    get_model()

    # Precompute the 17 MEB category embeddings.
    build_category_index()

    # Precompute semantic intent embeddings.
    build_intent_index()

    print("NLP model and embeddings are ready.")
    print("=" * 70)


# ============================================================
# Manual Test
# ============================================================

if __name__ == "__main__":
    examples = [
        "แนะนำอะไรให้อ่านหน่อย",

        "ไม่รู้จะอ่านอะไรดี",

        "สุ่มนิยายมาให้หน่อย",

        "ช่วยหาหนังสือเกี่ยวกับหุ้น",

        "มีหนังสือเกี่ยวกับการลงทุนไหม",

        "อยากอ่านเรื่องเวทมนตร์กับมังกร",

        "ช่วยหาเรื่องนักสืบไขคดีฆาตกรรม",

        "มีอะไรหลอนๆ เกี่ยวกับผีไหม",

        "อยากอ่านเรื่องอวกาศกับมนุษย์ต่างดาว",

        "อยากเริ่มลงทุนหุ้น",

        "อยากเรียนเขียนโปรแกรม python",

        "อยากเข้าใจอารมณ์ตัวเองมากขึ้น",

        "อยากดูแลสุขภาพและออกกำลังกาย",

        "อยากไปเที่ยวญี่ปุ่น",

        "อยากอ่านเรื่องฮ่องเต้กับแม่ทัพจีน",

        "อยากอ่านเรื่องความรักของผู้ชายสองคน",

        "อยากอ่านเรื่องความรักของผู้หญิงสองคน",

        "อยากปรับนิสัยและบริหารเวลา",

        "อยากอ่านมังงะ",

        "ขอบคุณมาก",

        "สวัสดีครับ",
    ]

    for text in examples:
        print()
        print("=" * 80)
        print(
            "TEXT:",
            text
        )

        intent = classify_intent(
            text
        )

        category = classify_category(
            text
        )

        print(
            "INTENT:",
            intent
        )

        print(
            "CATEGORY:",
            category
        )

        print(
            "TOP CATEGORY:"
        )

        for result in rank_categories(
            text,
            top_k=3,
        ):
            print(
                f"  {result['category_id']:>3} | "
                f"{result['score']:.4f} | "
                f"{result['category']}"
            )

        print(
            "INTENT RANKING:"
        )

        for result in rank_intents(
            text
        ):
            print(
                f"  {result['score']:.4f} | "
                f"{result['intent']}"
            )