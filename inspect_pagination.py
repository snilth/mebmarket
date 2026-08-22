from playwright.sync_api import sync_playwright


URL = (
    "https://www.mebmarket.com/"
    "?store=category"
    "&action=book_list"
    "&category_id=228"
    "&category_name=นิยายรักจีนโบราณ"
    "&condition=new"
)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    page = browser.new_page(
        viewport={
            "width": 1440,
            "height": 1000
        }
    )

    page.goto(
        URL,
        wait_until="networkidle",
        timeout=60000
    )

    page.wait_for_timeout(1500)

    # scroll ลงล่างสุด
    page.evaluate(
        """
        window.scrollTo(
            0,
            document.body.scrollHeight
        )
        """
    )

    page.wait_for_timeout(1000)

    print("\n=== LINKS RELATED TO PAGINATION ===")

    links = page.locator("a")

    for i in range(links.count()):
        link = links.nth(i)

        try:
            text = link.inner_text().strip()
            href = link.get_attribute("href")
            class_name = link.get_attribute("class")

            combined = (
                f"{text} "
                f"{href or ''} "
                f"{class_name or ''}"
            ).lower()

            if any(
                keyword in combined
                for keyword in [
                    "page",
                    "next",
                    "ถัด",
                    "pagination",
                    "load",
                    "more",
                ]
            ):
                print(
                    f"\n[{i}]"
                    f"\ntext  = {text!r}"
                    f"\nhref  = {href!r}"
                    f"\nclass = {class_name!r}"
                    f"\nhtml  = "
                    f"{link.evaluate('(e) => e.outerHTML')}"
                )

        except Exception:
            pass

    print("\n=== PAGINATION-LIKE ELEMENTS ===")

    candidates = page.locator(
        '[class*="page" i], '
        '[id*="page" i], '
        '[class*="pagination" i], '
        '[id*="pagination" i], '
        '[class*="load" i], '
        '[id*="load" i], '
        '[class*="more" i], '
        '[id*="more" i]'
    )

    print("Found:", candidates.count())

    for i in range(candidates.count()):
        element = candidates.nth(i)

        try:
            print("\nCandidate", i)
            print(
                "tag:",
                element.evaluate("(e) => e.tagName")
            )
            print(
                "id:",
                element.get_attribute("id")
            )
            print(
                "class:",
                element.get_attribute("class")
            )
            print(
                "text:",
                repr(element.inner_text()[:200])
            )
            print(
                "HTML:",
                element.evaluate(
                    "(e) => e.outerHTML"
                )[:2000]
            )

        except Exception:
            pass

    input("\nPress Enter to close...")

    browser.close()