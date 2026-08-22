import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright


BASE_URL = "https://www.mebmarket.com/"
CONFIG_PATH = Path("data/config/target_categories.json")
OUTPUT_DIR = Path("data/raw/categories")


# ============================================================
# Config
# ============================================================

def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_category(config, category_id):
    for category in config["categories"]:
        if str(category["category_id"]) == str(category_id):
            return category

    raise ValueError(
        f"Category ID {category_id} "
        f"not found in {CONFIG_PATH}"
    )


# ============================================================
# URL
# ============================================================

def build_category_url(category):
    params = {
        "store": "category",
        "action": "book_list",
        "category_id": category["category_id"],
        "category_name": category["category_name"],
        "condition": "new",
    }

    return f"{BASE_URL}?{urlencode(params)}"


# ============================================================
# Popup
# ============================================================

def close_popup_if_present(page):
    selectors = [
        'button.close[aria-label="Close"]',
        ".swal2-close",
    ]

    for selector in selectors:
        elements = page.locator(selector)

        for i in range(elements.count()):
            element = elements.nth(i)

            try:
                if element.is_visible():
                    element.click(timeout=2000)
                    page.wait_for_timeout(300)
                    return True

            except Exception:
                pass

    return False


# ============================================================
# Lazy Loading
# ============================================================

def scroll_page(page):
    """
    Scroll through current page to trigger lazy-loaded covers.
    """

    page.evaluate(
        """
        async () => {
            await new Promise((resolve) => {
                let previousHeight = 0;
                let stableCount = 0;

                const timer = setInterval(() => {
                    window.scrollBy(0, 700);

                    const currentHeight =
                        document.body.scrollHeight;

                    const atBottom =
                        window.innerHeight +
                        window.scrollY >=
                        currentHeight - 100;

                    if (currentHeight === previousHeight) {
                        stableCount += 1;
                    } else {
                        stableCount = 0;
                    }

                    previousHeight = currentHeight;

                    if (atBottom && stableCount >= 3) {
                        clearInterval(timer);

                        setTimeout(
                            resolve,
                            800
                        );
                    }
                }, 150);
            });
        }
        """
    )

    page.wait_for_timeout(500)


# ============================================================
# Cover
# ============================================================

def get_cover_url(card):
    image = card.locator(
        "img.img_book_list"
    )

    if image.count() == 0:
        return None

    attributes = [
        "src",
        "data-src",
        "data-original",
        "data-lazy-src",
        "data-srcset",
    ]

    for attribute in attributes:
        value = image.get_attribute(
            attribute
        )

        if (
            value
            and not value.startswith("data:image/")
        ):
            return value

    return None


# ============================================================
# Book Extraction
# ============================================================

def extract_book(card, category):
    # ----------------------------
    # Title + URL
    # ----------------------------

    title_link = card.locator(
        "h3.book_name a"
    )

    if title_link.count() == 0:
        raise ValueError(
            "Book title not found"
        )

    title = (
        title_link
        .inner_text()
        .strip()
    )

    book_url = (
        title_link
        .get_attribute("href")
    )

    # ----------------------------
    # Book ID
    # ----------------------------

    book_id = None

    if book_url:
        match = re.search(
            r"/ebook-(\d+)-?",
            book_url
        )

        if match:
            book_id = int(
                match.group(1)
            )

    # ----------------------------
    # Cover
    # ----------------------------

    cover_url = get_cover_url(
        card
    )

    # ----------------------------
    # Author + Publisher
    # ----------------------------

    meta_links = card.locator(
        ".book_meta_info a"
    )

    author = None
    publisher = None

    if meta_links.count() >= 1:
        author = (
            meta_links
            .nth(0)
            .inner_text()
            .strip()
        )

    if meta_links.count() >= 2:
        publisher = (
            meta_links
            .nth(1)
            .inner_text()
            .strip()
            .lstrip("/")
            .strip()
        )

    # ----------------------------
    # Category
    # ----------------------------

    category_element = card.locator(
        ".div_book_list_category a"
    )

    category_name = (
        category_element
        .first
        .inner_text()
        .strip()
        if category_element.count()
        else category["category_name"]
    )

    # ----------------------------
    # Rating
    # ----------------------------

    rating = None

    rating_image = card.locator(
        "img.img_rating_book_list"
    ).first

    if rating_image.count():
        rating_title = (
            rating_image
            .get_attribute("title")
        )

        if rating_title:
            match = re.search(
                r"Ratings\s*:\s*([\d.]+)",
                rating_title
            )

            if match:
                rating = float(
                    match.group(1)
                )

    # ----------------------------
    # Rating Count
    # ----------------------------

    rating_count = 0

    rating_element = card.locator(
        ".text_rating_book_list"
    )

    if rating_element.count():
        text = (
            rating_element
            .inner_text()
            .strip()
        )

        match = re.search(
            r"(\d[\d,]*)",
            text
        )

        if match:
            rating_count = int(
                match.group(1)
                .replace(",", "")
            )

    # ----------------------------
    # Price
    # ----------------------------

    price = None
    price_text = None
    is_free = False

    button = card.locator(
        ".button_book_list"
    )

    if button.count():
        price_text = (
            button.first
            .get_attribute("value")
        )

        if price_text:
            price_text = (
                price_text.strip()
            )

            if price_text.startswith("ฟรี"):
                price = 0
                is_free = True

            else:
                match = re.search(
                    r"[\d,.]+",
                    price_text
                )

                if match:
                    price = float(
                        match.group()
                        .replace(",", "")
                    )

    return {
        "book_id": book_id,
        "title": title,
        "author": author,
        "publisher": publisher,

        "parent_category_id":
            category.get(
                "parent_category_id"
            ),

        "parent_category":
            category.get(
                "parent_category_name"
            ),

        "category_id":
            str(
                category["category_id"]
            ),

        "category":
            category_name,

        "price": price,
        "price_text": price_text,
        "is_free": is_free,

        "rating": rating,
        "rating_count": rating_count,

        "cover_url": cover_url,
        "book_url": book_url,
    }


# ============================================================
# Extract Current Page
# ============================================================

def extract_current_page(
    page,
    category,
    books_by_id,
    limit,
):
    cards = page.locator(
        ".book_listing"
    )

    total = cards.count()

    added = 0

    for index in range(total):
        if len(books_by_id) >= limit:
            break

        try:
            book = extract_book(
                cards.nth(index),
                category,
            )

            book_id = book["book_id"]

            if book_id is None:
                continue

            if book_id in books_by_id:
                continue

            books_by_id[
                book_id
            ] = book

            added += 1

            print(
                f"  [{len(books_by_id)}/"
                f"{limit}] "
                f"{book['title']}"
            )

        except Exception as error:
            print(
                f"  [ERROR] "
                f"Card {index + 1}: "
                f"{error}"
            )

    return added


# ============================================================
# Pagination
# ============================================================

def go_to_next_page(
    page,
    next_page_number,
):
    """
    MEB pagination uses JavaScript:

        userGetCacheBook(page_number)

    Example:
        userGetCacheBook(2)
        userGetCacheBook(3)
        userGetCacheBook(4)
    """

    function_exists = page.evaluate(
        """
        () => (
            typeof userGetCacheBook === "function"
        )
        """
    )

    if not function_exists:
        print(
            "userGetCacheBook() not found."
        )

        return False

    # จำหนังสือเล่มแรกของหน้าปัจจุบัน
    old_first_title = None

    first_book = page.locator(
        ".book_listing h3.book_name a"
    ).first

    if first_book.count():
        try:
            old_first_title = (
                first_book
                .inner_text()
                .strip()
            )
        except Exception:
            pass

    print(
        f"Loading page "
        f"{next_page_number} "
        f"with "
        f"userGetCacheBook("
        f"{next_page_number})"
    )

    # เรียก pagination function ของ MEB
    page.evaluate(
        """
        (pageNumber) => {
            userGetCacheBook(
                pageNumber
            );
        }
        """,
        next_page_number,
    )

    # รอจนหนังสือหน้าใหม่เปลี่ยน
    if old_first_title:
        try:
            page.wait_for_function(
                """
                (oldTitle) => {
                    const element =
                        document.querySelector(
                            ".book_listing "
                            + "h3.book_name a"
                        );

                    if (!element) {
                        return false;
                    }

                    return (
                        element
                        .innerText
                        .trim()
                        !== oldTitle
                    );
                }
                """,
                old_first_title,
                timeout=30000,
            )

        except Exception:
            # fallback เผื่อชื่อเล่มแรกซ้ำ
            page.wait_for_timeout(
                2000
            )

    else:
        page.wait_for_timeout(
            2000
        )

    # รอ ajax/render เพิ่มอีกนิด
    page.wait_for_timeout(
        500
    )

    return True


# ============================================================
# Scraper
# ============================================================

def scrape_category(
    category,
    limit,
    headless=False,
):
    url = build_category_url(
        category
    )

    books_by_id = {}

    print()
    print("=" * 70)

    print(
        f"Category: "
        f"{category['category_name']} "
        f"({category['category_id']})"
    )

    print(
        f"Limit: {limit}"
    )

    print("=" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless
        )

        page = browser.new_page(
            viewport={
                "width": 1440,
                "height": 1000,
            }
        )

        page.goto(
            url,
            wait_until="networkidle",
            timeout=60000,
        )

        page.wait_for_timeout(
            1200
        )

        close_popup_if_present(
            page
        )

        page_number = 1

        while (
            len(books_by_id)
            < limit
        ):
            print()
            print(
                f"Page {page_number}"
            )

            # ----------------------------
            # Wait for book cards
            # ----------------------------

            try:
                page.wait_for_selector(
                    ".book_listing",
                    state="attached",
                    timeout=30000,
                )

            except Exception:
                print(
                    "No book cards found."
                )

                break

            # ----------------------------
            # Lazy-load covers
            # ----------------------------

            scroll_page(
                page
            )

            close_popup_if_present(
                page
            )

            # ----------------------------
            # Extract current page
            # ----------------------------

            added = extract_current_page(
                page,
                category,
                books_by_id,
                limit,
            )

            print(
                f"Added from page: "
                f"{added}"
            )

            # ถึง limit แล้ว
            if (
                len(books_by_id)
                >= limit
            ):
                break

            # ถ้าหน้านี้ไม่เพิ่มข้อมูล
            # ให้หยุด เพื่อกัน infinite loop
            if added == 0:
                print(
                    "No new books found "
                    "on this page."
                )

                break

            # ----------------------------
            # Next Page
            # ----------------------------

            next_page_number = (
                page_number + 1
            )

            try:
                success = (
                    go_to_next_page(
                        page,
                        next_page_number,
                    )
                )

                if not success:
                    print(
                        "Could not load "
                        f"page "
                        f"{next_page_number}."
                    )

                    break

                page_number = (
                    next_page_number
                )

                close_popup_if_present(
                    page
                )

            except Exception as error:
                print(
                    f"Could not load "
                    f"page "
                    f"{next_page_number}: "
                    f"{error}"
                )

                break

        browser.close()

    return list(
        books_by_id.values()
    )


# ============================================================
# Save
# ============================================================

def save_books(
    books,
    category_id,
):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIR
        / f"category_"
        f"{category_id}.json"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            books,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return output_path


# ============================================================
# Data Quality
# ============================================================

def print_summary(
    books,
):
    print()
    print("=" * 70)
    print("DATA QUALITY")
    print("=" * 70)

    print(
        "Unique books:",
        len(books),
    )

    print(
        "Missing title:",
        sum(
            not book["title"]
            for book in books
        ),
    )

    print(
        "Missing author:",
        sum(
            not book["author"]
            for book in books
        ),
    )

    print(
        "Missing publisher:",
        sum(
            not book["publisher"]
            for book in books
        ),
    )

    print(
        "Missing price:",
        sum(
            book["price"] is None
            for book in books
        ),
    )

    print(
        "Missing rating:",
        sum(
            book["rating"] is None
            for book in books
        ),
    )

    print(
        "Missing cover:",
        sum(
            not book["cover_url"]
            for book in books
        ),
    )

    print(
        "Free:",
        sum(
            book["is_free"]
            for book in books
        ),
    )

    print(
        "Paid:",
        sum(
            (
                not book["is_free"]
                and
                book["price"]
                is not None
            )
            for book in books
        ),
    )


# ============================================================
# CLI
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Scrape books from "
            "a configured MEB category."
        )
    )

    parser.add_argument(
        "--category-id",
        required=True,
        help=(
            "MEB category ID "
            "from target_categories.json"
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Maximum number of "
            "unique books to scrape."
        ),
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help=(
            "Run Chromium "
            "without visible window."
        ),
    )

    return parser.parse_args()


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    args = parse_args()

    config = load_config()

    category = find_category(
        config,
        args.category_id,
    )

    limit = (
        args.limit
        if args.limit is not None
        else config[
            "max_books_per_category"
        ]
    )

    books = scrape_category(
        category,
        limit,
        headless=args.headless,
    )

    output_path = save_books(
        books,
        category["category_id"],
    )

    print_summary(
        books
    )

    print()
    print(
        "Saved:",
        output_path
    )