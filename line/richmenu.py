"""
Rich Menu — shown automatically the moment a user opens the chat, so
picking a category doesn't require typing Thai.

The artwork (data/line/richmenu.png) is hand-designed, not generated
by this module — it only defines where each tile sits on that image
and what postback each tap sends. Tile pixel bounds below were
measured directly off the image and confirmed by drawing them back
over it as an overlay.

16 of the 17 catalog categories are on the menu — "การ์ตูนผู้หญิง"
didn't fit the artwork and was dropped by request; it's still
reachable by typing.

This module only builds the LINE-side objects. Pushing it live
(create + upload + set default) is a real change visible to every
user of the OA, so that step is gated behind __main__ and is not run
as a side effect of importing this module.
"""

import json

from pathlib import Path


# ============================================================
# Config
# ============================================================

CATEGORIES_PATH = Path(
    "data/config/target_categories.json"
)

SOURCE_IMAGE_PATH = Path(
    "data/line/richmenu.png"
)

IMAGE_PATH = Path(
    "data/line/richmenu_upload.jpg"
)

SOURCE_WIDTH = 1527
SOURCE_HEIGHT = 1030

# LINE rejects rich menu images with width:height under 1.45
# ("invalid richmenu size"). This art was made at ~1.4825, already
# clear of that — PAD_LEFT comes out to 0, but the math stays generic
# so a future re-export that falls short still gets padded instead of
# failing the push outright.
CANVAS_WIDTH = max(
    SOURCE_WIDTH,
    round(SOURCE_HEIGHT * 1.45),
)
CANVAS_HEIGHT = SOURCE_HEIGHT

PAD_LEFT = (CANVAS_WIDTH - SOURCE_WIDTH) // 2

BORDER_COLOR = (254, 254, 254)

CHAT_BAR_TEXT = "หมวดหนังสือ"

# Reading order matches the artwork's 4x4 grid, left-to-right,
# top-to-bottom. Names are display_text only (what shows in the chat
# log when a tile is tapped) — actual category matching runs on
# category_id, looked up against the full catalog in webhook.py, so
# these follow the artwork's on-tile labels rather than the raw
# catalog names.
CATEGORY_GRID = [
    ("21", "นิยายรัก"),
    ("228", "นิยายรักจีนโบราณ"),
    ("54", "นิยายวาย Boy Love / Yaoi"),
    ("51", "นิยายยูริ Girl Love / Yuri"),
    ("4", "นิยายแฟนตาซี"),
    ("48", "นิยายสืบสวนสอบสวน/ทริลเลอร์"),
    ("32", "นิยายลึกลับ/เขย่าขวัญ"),
    ("20", "นิยายไซไฟ"),
    ("15", "พัฒนาตนเอง"),
    ("154", "จิตวิทยา"),
    ("60", "การเงินการลงทุน"),
    ("18", "คอมพิวเตอร์"),
    ("8", "วิทยาศาสตร์และเทคโนโลยี"),
    ("22", "สุขภาพ"),
    ("23", "ท่องเที่ยว"),
    ("148", "การ์ตูนทั่วไป"),
]

GRID_COLS = 4
GRID_ROWS = 4

# All measured against the unpadded source art — shifted right by
# PAD_LEFT wherever they're turned into actual RichMenuArea bounds.
GRID_LEFT = 16
GRID_RIGHT = 1511
GRID_TOP = 17
GRID_BOTTOM = 740

ACTION_ROW_TOP = 748
ACTION_ROW_BOTTOM = 887

# The 3 action tiles are custom widths, not part of the 4-column
# grid above — measured off the artwork the same way.
ACTION_TILES = [
    {
        "x0": 16,
        "x1": 495,
        "action": "quick_random",
        "display_text": "🎲 สุ่มหนังสือ",
    },
    {
        "x0": 505,
        "x1": 1006,
        "action": "custom_search",
        "display_text": "พิมพ์คำค้นเอง",
    },
    {
        "x0": 1016,
        "x1": 1511,
        "action": "help",
        "display_text": "วิธีใช้งาน",
    },
]


# ============================================================
# Categories (full config — used for postback → category-name
# lookups, independent of which ones made it onto the menu)
# ============================================================

def load_categories():
    data = json.loads(
        CATEGORIES_PATH.read_text(
            encoding="utf-8"
        )
    )

    return data["categories"]


# ============================================================
# Tile geometry
# ============================================================

def category_bounds(index):
    col = index % GRID_COLS
    row = index // GRID_COLS

    col_width = (
        GRID_RIGHT - GRID_LEFT
    ) / GRID_COLS

    row_height = (
        GRID_BOTTOM - GRID_TOP
    ) / GRID_ROWS

    x = round(
        PAD_LEFT + GRID_LEFT + col * col_width
    )
    y = round(GRID_TOP + row * row_height)
    width = round(col_width)
    height = round(row_height)

    return x, y, width, height


def build_areas():
    from linebot.v3.messaging import (
        PostbackAction,
        RichMenuArea,
        RichMenuBounds,
    )

    areas = []

    for index, (category_id, category_name) in enumerate(
        CATEGORY_GRID
    ):
        x, y, width, height = category_bounds(index)

        areas.append(
            RichMenuArea(
                bounds=RichMenuBounds(
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                ),

                action=PostbackAction(
                    data=(
                        "action=category"
                        f"&category_id={category_id}"
                    ),
                    display_text=category_name,
                ),
            )
        )

    for tile in ACTION_TILES:
        areas.append(
            RichMenuArea(
                bounds=RichMenuBounds(
                    x=PAD_LEFT + tile["x0"],
                    y=ACTION_ROW_TOP,
                    width=tile["x1"] - tile["x0"],
                    height=ACTION_ROW_BOTTOM - ACTION_ROW_TOP,
                ),

                action=PostbackAction(
                    data=f"action={tile['action']}",
                    display_text=tile["display_text"],
                ),
            )
        )

    return areas


def build_richmenu_request():
    from linebot.v3.messaging import (
        RichMenuRequest,
        RichMenuSize,
    )

    return RichMenuRequest(
        size=RichMenuSize(
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
        ),

        selected=True,
        name="meb-category-menu",
        chat_bar_text=CHAT_BAR_TEXT,
        areas=build_areas(),
    )


def build_upload_image():
    """
    Pads the source art with its own border color on both sides if
    needed to clear LINE's 1.45 width:height minimum (PAD_LEFT is 0
    when the art already satisfies it, as it does now), and saves it
    to IMAGE_PATH. Regenerated on every push so edits to the source
    art are picked up automatically.

    Saved as JPEG, not PNG — the source PNG is ~1.2MB, over LINE's
    1MB rich menu image cap ("413 Request Entity Too Large"). JPEG at
    quality 90 comes out under 260KB with no visible loss on this
    flat-illustration + text artwork.
    """

    from PIL import Image

    source = Image.open(SOURCE_IMAGE_PATH).convert("RGB")

    padded = Image.new(
        "RGB",
        (CANVAS_WIDTH, CANVAS_HEIGHT),
        BORDER_COLOR,
    )

    padded.paste(source, (PAD_LEFT, 0))

    padded.save(
        IMAGE_PATH,
        format="JPEG",
        quality=90,
    )

    return IMAGE_PATH


# ============================================================
# LINE API — pushes a live change to the OA, run manually only
# ============================================================

def push_live():
    """
    Creates the rich menu on the connected LINE OA, uploads the
    padded artwork, and sets it as the default menu for
    every user. Run explicitly: `python -m line.richmenu`.
    """

    import os

    from dotenv import load_dotenv
    from linebot.v3.messaging import (
        ApiClient,
        Configuration,
        MessagingApi,
        MessagingApiBlob,
    )

    load_dotenv()

    configuration = Configuration(
        access_token=os.getenv(
            "LINE_CHANNEL_ACCESS_TOKEN"
        )
    )

    image_path = build_upload_image()

    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        blob_api = MessagingApiBlob(api_client)

        # Sweep up menus from earlier attempts (e.g. a run that
        # created the menu but crashed before set_default) so retries
        # don't pile up orphaned rich menus on the account.
        for existing in messaging_api.get_rich_menu_list().richmenus:
            if existing.name == "meb-category-menu":
                messaging_api.delete_rich_menu(
                    existing.rich_menu_id
                )

        response = messaging_api.create_rich_menu(
            build_richmenu_request()
        )

        rich_menu_id = response.rich_menu_id

        # `_content_type=` looks like the right kwarg but this SDK's
        # generated code never wires it to the request header — the
        # header only gets set via `_headers`, otherwise the client
        # defaults to JSON-encoding the body and this call fails with
        # "Object of type bytes is not JSON serializable".
        blob_api.set_rich_menu_image(
            rich_menu_id,
            image_path.read_bytes(),
            _headers={
                "Content-Type": "image/jpeg",
            },
        )

        messaging_api.set_default_rich_menu(
            rich_menu_id
        )

    print(f"Rich menu live: {rich_menu_id}")

    return rich_menu_id


if __name__ == "__main__":
    push_live()
