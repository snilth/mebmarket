import os

from dotenv import (
    load_dotenv,
)

from flask import (
    Flask,
    abort,
    request,
)

from linebot.v3 import (
    WebhookHandler,
)

from linebot.v3.exceptions import (
    InvalidSignatureError,
)

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    FlexContainer,
    FlexMessage,
    MessagingApi,
    PostbackAction,
    QuickReply,
    QuickReplyItem,
    ReplyMessageRequest,
    TextMessage,
)

from linebot.v3.webhooks import (
    MessageEvent,
    PostbackEvent,
    TextMessageContent,
)

from line.flex_carousel import (
    build_line_response,
)

from nlp.model import (
    preload_nlp,
)

from recommendation.engine import (
    recommend_books,
    recommend_from_text,
)


# ============================================================
# Environment
# ============================================================

load_dotenv()


CHANNEL_ACCESS_TOKEN = os.getenv(
    "LINE_CHANNEL_ACCESS_TOKEN"
)

CHANNEL_SECRET = os.getenv(
    "LINE_CHANNEL_SECRET"
)


if not CHANNEL_ACCESS_TOKEN:
    raise RuntimeError(
        "LINE_CHANNEL_ACCESS_TOKEN "
        "is missing"
    )


if not CHANNEL_SECRET:
    raise RuntimeError(
        "LINE_CHANNEL_SECRET "
        "is missing"
    )


# ============================================================
# LINE
# ============================================================

configuration = Configuration(
    access_token=
        CHANNEL_ACCESS_TOKEN
)


handler = WebhookHandler(
    CHANNEL_SECRET
)


# ============================================================
# Flask
# ============================================================

app = Flask(
    __name__
)


# ============================================================
# User Sessions
# ============================================================

# Development-only in-memory session.
#
# Ranked:
#
# {
#     "command": {...},
#     "next_offset": 5
# }
#
# Random:
#
# {
#     "command": {...},
#     "seen_book_ids": {...}
# }

USER_SESSIONS = {}


def get_user_id(event):
    source = getattr(
        event,
        "source",
        None,
    )

    if source is None:
        return None

    return getattr(
        source,
        "user_id",
        None,
    )


# ============================================================
# Session
# ============================================================

def save_new_session(
    user_id,
    result,
):
    if not user_id:
        return

    if result.get(
        "status"
    ) != "ok":
        USER_SESSIONS.pop(
            user_id,
            None,
        )

        return

    command = result.get(
        "command",
        {},
    )

    randomize = bool(
        command.get(
            "randomize",
            False,
        )
    )

    if randomize:
        shown_ids = {
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
            if book.get(
                "book_id"
            ) is not None
        }

        USER_SESSIONS[
            user_id
        ] = {
            "command":
                command,

            "seen_book_ids":
                shown_ids,

            "next_offset":
                0,
        }

        return

    USER_SESSIONS[
        user_id
    ] = {
        "command":
            command,

        "next_offset":
            result.get(
                "next_offset",
                5,
            ),

        "seen_book_ids":
            set(),
    }


def add_seen_books(
    user_id,
    books,
):
    session = USER_SESSIONS.get(
        user_id
    )

    if not session:
        return

    seen = session.get(
        "seen_book_ids"
    )

    if not isinstance(
        seen,
        set,
    ):
        seen = set()

        session[
            "seen_book_ids"
        ] = seen

    for book in books:
        book_id = book.get(
            "book_id"
        )

        if book_id is None:
            continue

        seen.add(
            str(book_id)
        )


# ============================================================
# Routes
# ============================================================

@app.route(
    "/",
    methods=["GET"],
)
def health_check():
    return {
        "status":
            "ok",

        "service":
            "meb-line-bot",
    }


@app.route(
    "/callback",
    methods=["POST"],
)
def callback():
    signature = request.headers.get(
        "X-Line-Signature"
    )

    if not signature:
        abort(
            400
        )

    body = request.get_data(
        as_text=True
    )

    try:
        handler.handle(
            body,
            signature,
        )

    except InvalidSignatureError:
        abort(
            400
        )

    return "OK"


# ============================================================
# Internal -> LINE Message
# ============================================================

def convert_line_message(
    message,
):
    message_type = message.get(
        "type"
    )

    if message_type == "text":
        return TextMessage(
            text=message[
                "text"
            ]
        )

    if message_type == "flex":
        return FlexMessage(
            alt_text=message[
                "altText"
            ],

            contents=
                FlexContainer.from_dict(
                    message[
                        "contents"
                    ]
                ),
        )

    raise ValueError(
        f"Unsupported LINE message type: "
        f"{message_type}"
    )


# ============================================================
# Controls
# ============================================================

def build_control_message(
    result,
):
    """
    Normal recommendation:
        📚 ดูเพิ่ม

    Explicit random:
        🎲 สุ่มอีก
    """

    if result.get(
        "randomized"
    ):
        return TextMessage(
            text="อยากได้ชุดอื่น?",

            quick_reply=QuickReply(
                items=[
                    QuickReplyItem(
                        action=PostbackAction(
                            label=
                                "🎲 สุ่มอีก",

                            data=
                                "action=random_more",

                            display_text=
                                "🎲 สุ่มอีก",
                        )
                    )
                ]
            ),
        )

    if result.get(
        "has_more"
    ):
        return TextMessage(
            text="มีหนังสือเพิ่มเติม",

            quick_reply=QuickReply(
                items=[
                    QuickReplyItem(
                        action=PostbackAction(
                            label=
                                "📚 ดูเพิ่ม",

                            data=
                                "action=next_page",

                            display_text=
                                "📚 ดูเพิ่ม",
                        )
                    )
                ]
            ),
        )

    return None


# ============================================================
# Reply
# ============================================================

def reply_result(
    reply_token,
    result,
):
    response = build_line_response(
        result
    )

    messages = [
        convert_line_message(
            response
        )
    ]

    control = build_control_message(
        result
    )

    if control is not None:
        messages.append(
            control
        )

    with ApiClient(
        configuration
    ) as api_client:
        messaging_api = MessagingApi(
            api_client
        )

        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=
                    reply_token,

                messages=
                    messages,
            )
        )


def reply_text(
    reply_token,
    text,
):
    with ApiClient(
        configuration
    ) as api_client:
        messaging_api = MessagingApi(
            api_client
        )

        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=
                    reply_token,

                messages=[
                    TextMessage(
                        text=text
                    )
                ],
            )
        )


# ============================================================
# Text Handler
# ============================================================

@handler.add(
    MessageEvent,
    message=TextMessageContent,
)
def handle_text_message(
    event,
):
    user_text = event.message.text

    print()
    print("=" * 80)

    print(
        "LINE MESSAGE:",
        user_text
    )

    try:
        result = recommend_from_text(
            user_text,
            limit=5,
        )

    except Exception as exc:
        print(
            "Recommendation error:",
            repr(exc),
        )

        try:
            reply_text(
                event.reply_token,
                (
                    "เกิดข้อผิดพลาดระหว่าง"
                    "ค้นหาหนังสือ "
                    "ลองใหม่อีกครั้งนะ"
                ),
            )

        except Exception as reply_exc:
            print(
                "Fallback reply error:",
                repr(reply_exc),
            )

        return

    print(
        "STATUS:",
        result.get(
            "status"
        ),
    )

    print(
        "CANDIDATES:",
        result.get(
            "candidate_count"
        ),
    )

    print(
        "RANDOMIZED:",
        result.get(
            "randomized"
        ),
    )

    print(
        "OFFSET:",
        result.get(
            "offset"
        ),
    )

    print(
        "NEXT OFFSET:",
        result.get(
            "next_offset"
        ),
    )

    print(
        "HAS MORE:",
        result.get(
            "has_more"
        ),
    )

    books = result.get(
        "books",
        [],
    )

    print(
        "RETURNED BOOKS:",
        len(books),
    )

    for index, book in enumerate(
        books,
        start=1,
    ):
        print(
            f"  {index}. "
            f"{book.get('title')}"
        )

    user_id = get_user_id(
        event
    )

    save_new_session(
        user_id,
        result,
    )

    try:
        reply_result(
            event.reply_token,
            result,
        )

        print(
            "LINE reply: OK"
        )

    except Exception as exc:
        print(
            "LINE reply error:",
            repr(exc),
        )


# ============================================================
# Postback Handler
# ============================================================

@handler.add(
    PostbackEvent,
)
def handle_postback(
    event,
):
    data = (
        event.postback.data
        or ""
    )

    print()
    print("=" * 80)

    print(
        "LINE POSTBACK:",
        data
    )

    user_id = get_user_id(
        event
    )

    if not user_id:
        return

    session = USER_SESSIONS.get(
        user_id
    )

    if not session:
        reply_text(
            event.reply_token,
            (
                "ลองค้นหาหนังสือก่อนนะ 📚"
            ),
        )

        return

    command = session[
        "command"
    ]

    # ========================================================
    # NEXT PAGE
    # ========================================================

    if data == "action=next_page":
        if command.get(
            "randomize",
            False,
        ):
            reply_text(
                event.reply_token,
                (
                    "คำสั่งนี้เป็นโหมดสุ่ม "
                    "ลองกดสุ่มอีกแทนนะ"
                ),
            )

            return

        offset = session.get(
            "next_offset",
            0,
        )

        result = recommend_books(
            command,
            limit=5,
            offset=offset,
        )

        if result.get(
            "status"
        ) != "ok":
            reply_text(
                event.reply_token,
                (
                    "ไม่มีหนังสือเพิ่มเติมแล้ว 📚"
                ),
            )

            return

        session[
            "next_offset"
        ] = result.get(
            "next_offset",
            offset + 5,
        )

        print(
            "PAGE OFFSET:",
            result.get(
                "offset"
            ),
        )

        print(
            "NEXT OFFSET:",
            result.get(
                "next_offset"
            ),
        )

        try:
            reply_result(
                event.reply_token,
                result,
            )

            print(
                "Next page reply: OK"
            )

        except Exception as exc:
            print(
                "Next page reply error:",
                repr(exc),
            )

        return

    # ========================================================
    # RANDOM MORE
    # ========================================================

    if data == "action=random_more":
        if not command.get(
            "randomize",
            False,
        ):
            return

        seen_book_ids = session.get(
            "seen_book_ids",
            set(),
        )

        result = recommend_books(
            command,
            limit=5,
            exclude_book_ids=
                seen_book_ids,
        )

        # If the quality/random pool has already been used,
        # reset and allow it to cycle again.
        if result.get(
            "status"
        ) != "ok":
            seen_book_ids.clear()

            result = recommend_books(
                command,
                limit=5,
            )

        add_seen_books(
            user_id,
            result.get(
                "books",
                [],
            ),
        )

        print(
            "RANDOM RETURNED:",
            len(
                result.get(
                    "books",
                    [],
                )
            ),
        )

        print(
            "TOTAL SEEN:",
            len(
                session.get(
                    "seen_book_ids",
                    set(),
                )
            ),
        )

        try:
            reply_result(
                event.reply_token,
                result,
            )

            print(
                "Random reply: OK"
            )

        except Exception as exc:
            print(
                "Random reply error:",
                repr(exc),
            )

        return

    print(
        "Unknown postback action."
    )


# ============================================================
# Startup
# ============================================================

def startup():
    print()
    print("=" * 80)
    print("MEB MARKET LINE BOT")
    print("=" * 80)

    print()
    print(
        "Preloading NLP model..."
    )

    preload_nlp()

    print()
    print(
        "NLP preload complete."
    )

    print(
        "LINE bot is ready."
    )

    print()


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    startup()

    app.run(
        host="0.0.0.0",
        port=8000,

        debug=False,
        use_reloader=False,
    )