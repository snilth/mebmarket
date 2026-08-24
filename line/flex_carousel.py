from urllib.parse import (
    quote,
    urlsplit,
    urlunsplit,
)

from line.theme import (
    ACCENT_DARK,
    BACKGROUND,
    FAINT_TEXT,
    FREE_TAG,
    MUTED_TEXT,
    TITLE_TEXT,
)


# ============================================================
# URL
# ============================================================

def encode_url(url):
    if not url:
        return None

    url = str(url).strip()

    if not url:
        return None

    parts = urlsplit(
        url
    )

    path = quote(
        parts.path,
        safe="/%:@",
    )

    query = quote(
        parts.query,
        safe="=&%:@/?",
    )

    fragment = quote(
        parts.fragment,
        safe="%:@/?",
    )

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            path,
            query,
            fragment,
        )
    )


# ============================================================
# Text Helpers
# ============================================================

def safe_text(
    value,
    fallback="-",
):
    if value is None:
        return fallback

    value = str(
        value
    ).strip()

    return value or fallback


def truncate(
    text,
    max_length,
):
    text = safe_text(
        text
    )

    if len(text) <= max_length:
        return text

    return (
        text[
            :max_length - 1
        ]
        + "…"
    )


# ============================================================
# Formatting
# ============================================================

def format_price(book):
    if book.get(
        "is_free"
    ):
        return "ฟรี"

    price_text = book.get(
        "price_text"
    )

    if price_text:
        return str(
            price_text
        )

    price = book.get(
        "price"
    )

    if price is None:
        return "-"

    try:
        price = float(
            price
        )

        if price.is_integer():
            return (
                f"฿ {int(price)}"
            )

        return (
            f"฿ {price:.2f}"
        )

    except (
        TypeError,
        ValueError,
    ):
        return (
            f"฿ {price}"
        )


def format_rating(book):
    rating = book.get(
        "rating"
    )

    rating_count = book.get(
        "rating_count"
    )

    try:
        rating = float(
            rating or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        rating = 0.0

    try:
        rating_count = int(
            rating_count or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        rating_count = 0

    if rating_count <= 0:
        return "ยังไม่มีรีวิว"

    return (
        f"★ {rating:.2f} "
        f"· {rating_count} รีวิว"
    )


# ============================================================
# Book Bubble
# ============================================================

def build_book_bubble(book):
    title = truncate(
        book.get(
            "title"
        ),
        55,
    )

    author = truncate(
        book.get(
            "author"
        ),
        38,
    )

    price = format_price(
        book
    )

    rating = format_rating(
        book
    )

    cover_url = encode_url(
        book.get(
            "cover_url"
        )
    )

    book_url = encode_url(
        book.get(
            "book_url"
        )
    )

    bubble = {
        "type":
            "bubble",

        "size":
            "kilo",

        "body": {
            "type":
                "box",

            "layout":
                "vertical",

            "paddingAll":
                "12px",

            "spacing":
                "xs",

            "contents": [
                {
                    "type":
                        "text",

                    "text":
                        title,

                    "weight":
                        "bold",

                    "size":
                        "sm",

                    "wrap":
                        True,

                    "maxLines":
                        2,

                    "color":
                        TITLE_TEXT,
                },

                {
                    "type":
                        "text",

                    "text":
                        author,

                    "size":
                        "xs",

                    "color":
                        MUTED_TEXT,

                    "margin":
                        "xs",

                    "wrap":
                        True,

                    "maxLines":
                        1,
                },

                {
                    "type":
                        "box",

                    "layout":
                        "horizontal",

                    "margin":
                        "md",

                    "alignItems":
                        "center",

                    "contents": [
                        {
                            "type":
                                "text",

                            "text":
                                rating,

                            "size":
                                "xs",

                            "color":
                                MUTED_TEXT,

                            "flex":
                                1,
                        },

                        {
                            "type":
                                "text",

                            "text":
                                price,

                            "size":
                                "sm",

                            "weight":
                                "bold",

                            "align":
                                "end",

                            "color": (
                                FREE_TAG
                                if book.get(
                                    "is_free"
                                )
                                else ACCENT_DARK
                            ),

                            "flex":
                                0,
                        },
                    ],
                },

                {
                    "type":
                        "text",

                    "text":
                        "แตะหน้าปกเพื่อดูบน MEB",

                    "size":
                        "xxs",

                    "color":
                        FAINT_TEXT,

                    "margin":
                        "sm",

                    "align":
                        "center",
                },
            ],
        },

        "styles": {
            "body": {
                "backgroundColor":
                    BACKGROUND,
            },
        },
    }

    # ========================================================
    # Cover
    # ========================================================

    if cover_url:

        bubble[
            "hero"
        ] = {
            "type":
                "image",

            "url":
                cover_url,

            "size":
                "full",

            # Fill the card width without side whitespace
            "aspectRatio":
                "2:3",

            "aspectMode":
                "cover",
        }

        if book_url:

            bubble[
                "hero"
            ][
                "action"
            ] = {
                "type":
                    "uri",

                "uri":
                    book_url,
            }

    # ========================================================
    # Title Link
    # ========================================================

    if book_url:

        bubble[
            "body"
        ][
            "contents"
        ][0][
            "action"
        ] = {
            "type":
                "uri",

            "uri":
                book_url,
        }

    return bubble


# ============================================================
# Carousel
# ============================================================

def build_book_carousel(
    books,
    alt_text="หนังสือแนะนำจาก MEB",
    limit=5,
):
    if not books:
        return {
            "type":
                "text",

            "text":
                (
                    "ไม่พบหนังสือที่ตรงกับเงื่อนไขนี้\n"
                    "ลองลดเงื่อนไขบางอย่างดูนะ"
                ),
        }

    bubbles = [
        build_book_bubble(
            book
        )
        for book
        in books[:limit]
    ]

    return {
        "type":
            "flex",

        "altText":
            alt_text,

        "contents": {
            "type":
                "carousel",

            "contents":
                bubbles,
        },
    }


# ============================================================
# Recommendation Response
# ============================================================

def build_line_response(
    recommendation_result,
):
    status = recommendation_result.get(
        "status"
    )

    if status == "unsupported_intent":

        return {
            "type":
                "text",

            "text":
                (
                    "ลองบอกหนังสือหรือแนวที่อยากอ่านได้เลย\n\n"
                    "เช่น\n"
                    "• ขอนิยายแฟนตาซี\n"
                    "• หนังสือคอมไม่เกิน 200 บาท\n"
                    "• อยากอ่านเรื่องนักสืบ"
                ),
        }

    if status == "no_results":

        return {
            "type":
                "text",

            "text":
                (
                    "ไม่พบหนังสือที่ตรงกับเงื่อนไขนี้\n"
                    "ลองลดราคา เรตติ้ง "
                    "หรือจำนวนรีวิวลงดูนะ"
                ),
        }

    if status == "ok":

        return build_book_carousel(
            recommendation_result.get(
                "books",
                [],
            ),

            alt_text=(
                "หนังสือ 5 เล่มที่แนะนำจาก MEB"
            ),

            limit=5,
        )

    return {
        "type":
            "text",

        "text":
            (
                "ไม่สามารถประมวลผลคำขอได้ "
                "ลองใหม่อีกครั้งนะ"
            ),
    }