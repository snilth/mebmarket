import re
import unicodedata


THAI_DIGITS = str.maketrans(
    {
        "๐": "0",
        "๑": "1",
        "๒": "2",
        "๓": "3",
        "๔": "4",
        "๕": "5",
        "๖": "6",
        "๗": "7",
        "๘": "8",
        "๙": "9",
    }
)


def normalize_thai_digits(text):
    return text.translate(
        THAI_DIGITS
    )


def normalize_spaces(text):
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def normalize_punctuation(text):
    text = re.sub(
        r"[!?！？]+",
        " ",
        text,
    )

    text = re.sub(
        r"[“”\"']",
        "",
        text,
    )

    return text


def normalize_repeated_characters(text):
    """
    Reduce excessive repeated characters.

    Example:
        ฟรีๆๆๆ -> ฟรีๆ
        จิตวิทยาาาา -> จิตวิทยาา
    """

    return re.sub(
        r"(.)\1{2,}",
        r"\1\1",
        text,
    )


def normalize_text(text):
    """
    Main Thai text normalization pipeline.
    """

    if not isinstance(text, str):
        raise TypeError(
            "text must be a string"
        )

    # NFC is safer for Thai text than NFKC
    text = unicodedata.normalize(
        "NFC",
        text,
    )

    text = text.lower()

    text = normalize_thai_digits(
        text
    )

    text = normalize_punctuation(
        text
    )

    text = normalize_repeated_characters(
        text
    )

    text = normalize_spaces(
        text
    )

    return text


if __name__ == "__main__":
    examples = [
        "แนะนำนิยายแฟนตาซีให้หน่อย",
        "ขอ BL ฟรีๆๆๆ เรต ๔.๕ ขึ้นไป???",
        "อยากอ่านจิตวิทยาาาา",
    ]

    for example in examples:
        print(
            "ORIGINAL:",
            example
        )

        print(
            "NORMALIZED:",
            normalize_text(
                example
            )
        )

        print()