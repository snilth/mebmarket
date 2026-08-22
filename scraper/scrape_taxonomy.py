import json

from playwright.sync_api import sync_playwright


URL = "https://www.mebmarket.com/index.php?action=search_book"


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


def get_select_options(select):
    """
    Return usable category options from a select.
    Generic placeholders are ignored.
    """

    results = []

    options = select.locator("option")

    for i in range(options.count()):
        option = options.nth(i)

        name = option.inner_text().strip()
        value = option.get_attribute("value")

        if not name:
            continue

        if value in (
            None,
            "",
            "All",
            "all",
        ):
            continue

        if name in (
            "ทุกหมวด",
            "ทั้งหมด",
        ):
            continue

        results.append(
            {
                "category_id": str(value),
                "category_name": name,
            }
        )

    return results


def category_select_exists(page, level):
    selector = f"#category-{level}"

    return page.locator(selector).count() > 0


def get_category_select(page, level):
    return page.locator(
        f"#category-{level}"
    )


def trigger_category(page, level, category_id):
    """
    Select a category by calling MEB's own JS behavior.

    Example:
        category-1 -> getBookCategory('category-1')
    """

    selector_id = f"category-{level}"

    select = page.locator(
        f"#{selector_id}"
    )

    select.evaluate(
        """
        (el, value) => {
            el.value = value;

            if (
                typeof getBookCategory === "function"
            ) {
                getBookCategory(el.id);
            } else {
                el.dispatchEvent(
                    new Event(
                        "change",
                        { bubbles: true }
                    )
                );
            }
        }
        """,
        category_id,
    )


def wait_for_next_level(
    page,
    next_level,
    timeout_ms=3000,
):
    """
    Wait briefly for a dynamically generated next-level category select.

    Returns True if it appears.
    """

    selector = f"#category-{next_level}"

    try:
        page.wait_for_selector(
            selector,
            state="attached",
            timeout=timeout_ms,
        )

        return True

    except Exception:
        return False


def remove_deeper_levels(
    page,
    level,
):
    """
    Remove stale category selects deeper than the current level.

    This helps prevent data from a previously selected branch
    from being mistaken as children of the new branch.
    """

    page.evaluate(
        """
        (level) => {
            const selects =
                document.querySelectorAll(
                    'select[id^="category-"]'
                );

            selects.forEach((select) => {
                const match =
                    select.id.match(
                        /^category-(\\d+)$/
                    );

                if (!match) {
                    return;
                }

                const selectLevel =
                    parseInt(
                        match[1],
                        10
                    );

                if (
                    selectLevel > level
                ) {
                    const wrapper =
                        select.closest(
                            ".form-group"
                        );

                    if (wrapper) {
                        wrapper.remove();
                    } else {
                        select.remove();
                    }
                }
            });
        }
        """,
        level,
    )


def explore_level(
    page,
    level,
    max_depth=10,
):
    """
    Recursively explore one category level.

    Returns:
        [
            {
                category_id,
                category_name,
                level,
                children
            }
        ]
    """

    if level > max_depth:
        return []

    if not category_select_exists(
        page,
        level,
    ):
        return []

    select = get_category_select(
        page,
        level,
    )

    options = get_select_options(
        select
    )

    results = []

    print(
        f"\nLevel {level}: "
        f"{len(options)} categories"
    )

    for index, option in enumerate(
        options,
        start=1,
    ):
        category_id = option[
            "category_id"
        ]

        category_name = option[
            "category_name"
        ]

        indent = "  " * (
            level - 1
        )

        print(
            f"{indent}"
            f"[{index}/{len(options)}] "
            f"{category_name} "
            f"({category_id})"
        )

        close_popup_if_present(
            page
        )

        # ล้าง level เก่าๆ
        # ที่อาจค้างจาก branch ก่อนหน้า
        remove_deeper_levels(
            page,
            level,
        )

        try:
            trigger_category(
                page,
                level,
                category_id,
            )

        except Exception as error:
            print(
                f"{indent}"
                f"  ERROR selecting: "
                f"{error}"
            )

            results.append(
                {
                    "category_id":
                        category_id,
                    "category_name":
                        category_name,
                    "level":
                        level,
                    "children":
                        [],
                }
            )

            continue

        page.wait_for_timeout(
            700
        )

        close_popup_if_present(
            page
        )

        next_level = level + 1

        has_next = (
            wait_for_next_level(
                page,
                next_level,
                timeout_ms=1500,
            )
        )

        children = []

        if has_next:
            next_select = (
                get_category_select(
                    page,
                    next_level,
                )
            )

            child_options = (
                get_select_options(
                    next_select
                )
            )

            if child_options:
                print(
                    f"{indent}"
                    f"  -> found "
                    f"{len(child_options)} "
                    f"children"
                )

                children = explore_level(
                    page,
                    next_level,
                    max_depth=max_depth,
                )

        results.append(
            {
                "category_id":
                    category_id,
                "category_name":
                    category_name,
                "level":
                    level,
                "children":
                    children,
            }
        )

    return results


def count_nodes(
    categories,
):
    total = 0

    for category in categories:
        total += 1

        total += count_nodes(
            category["children"]
        )

    return total


def max_tree_depth(
    categories,
):
    if not categories:
        return 0

    depths = []

    for category in categories:
        child_depth = (
            max_tree_depth(
                category["children"]
            )
        )

        depths.append(
            1 + child_depth
        )

    return max(depths)


def save_json(
    data,
    filename,
):
    with open(
        filename,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def explore_full_taxonomy():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False
        )

        page = browser.new_page(
            viewport={
                "width": 1440,
                "height": 1200,
            }
        )

        print(
            "Opening MEB Advanced Search..."
        )

        page.goto(
            URL,
            wait_until="networkidle",
            timeout=60000,
        )

        print(
            "Title:",
            page.title(),
        )

        page.wait_for_timeout(
            1500
        )

        close_popup_if_present(
            page
        )

        page.wait_for_selector(
            "#category-1",
            state="attached",
            timeout=30000,
        )

        print(
            "category-1 found"
        )

        taxonomy = explore_level(
            page,
            level=1,
            max_depth=10,
        )

        browser.close()

    return taxonomy


if __name__ == "__main__":
    taxonomy = (
        explore_full_taxonomy()
    )

    filename = (
        "categories_full.json"
    )

    save_json(
        taxonomy,
        filename,
    )

    total_nodes = count_nodes(
        taxonomy
    )

    depth = max_tree_depth(
        taxonomy
    )

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(
        "Top-level categories:",
        len(taxonomy),
    )

    print(
        "Total category nodes:",
        total_nodes,
    )

    print(
        "Maximum depth:",
        depth,
    )

    print(
        "Saved:",
        filename,
    )