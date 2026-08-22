import argparse
import json
import random
import time
from pathlib import Path

from scraper.scrape_category import (
    CONFIG_PATH,
    OUTPUT_DIR,
    load_config,
    print_summary,
    save_books,
    scrape_category,
)


# ============================================================
# Existing Data
# ============================================================

def load_existing_books(output_path):
    """
    Load an existing category JSON file.

    Returns:
        list: Existing books.

    If the file cannot be read, return an empty list so that
    the category will be scraped again.
    """

    if not output_path.exists():
        return []

    try:
        with output_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

    except Exception as error:
        print(
            f"Could not read existing file "
            f"{output_path}: {error}"
        )

    return []


def get_output_path(category_id):
    return (
        OUTPUT_DIR
        / f"category_{category_id}.json"
    )


def should_skip_category(
    category_id,
    limit,
):
    """
    Skip a category only when an existing output file
    already contains at least the requested number
    of unique books.
    """

    output_path = get_output_path(
        category_id
    )

    existing_books = load_existing_books(
        output_path
    )

    if len(existing_books) >= limit:
        return True, len(existing_books)

    return False, len(existing_books)


# ============================================================
# Delay
# ============================================================

def wait_between_categories(
    min_delay,
    max_delay,
):
    """
    Wait a random amount of time between categories.
    """

    if max_delay < min_delay:
        max_delay = min_delay

    delay = random.uniform(
        min_delay,
        max_delay,
    )

    print()
    print(
        f"Waiting {delay:.1f} seconds "
        f"before next category..."
    )

    time.sleep(delay)


# ============================================================
# Batch Scraper
# ============================================================

def scrape_all_categories(
    categories,
    limit,
    headless,
    min_delay,
    max_delay,
    force,
):
    total_categories = len(categories)

    results = []

    print()
    print("=" * 70)
    print("MEB BATCH SCRAPER")
    print("=" * 70)
    print(
        f"Config: {CONFIG_PATH}"
    )
    print(
        f"Categories: {total_categories}"
    )
    print(
        f"Maximum books/category: {limit}"
    )
    print(
        f"Headless: {headless}"
    )
    print(
        f"Force re-scrape: {force}"
    )
    print("=" * 70)

    for index, category in enumerate(
        categories,
        start=1,
    ):
        category_id = str(
            category["category_id"]
        )

        category_name = (
            category["category_name"]
        )

        output_path = get_output_path(
            category_id
        )

        print()
        print()
        print("#" * 70)

        print(
            f"[{index}/{total_categories}] "
            f"{category_name} "
            f"({category_id})"
        )

        print("#" * 70)

        # ----------------------------------------
        # Check existing data
        # ----------------------------------------

        skip, existing_count = (
            should_skip_category(
                category_id,
                limit,
            )
        )

        if skip and not force:
            print(
                f"SKIP: {output_path}"
            )

            print(
                f"Existing books: "
                f"{existing_count}"
            )

            results.append(
                {
                    "category_id":
                        category_id,

                    "category_name":
                        category_name,

                    "status":
                        "skipped",

                    "books":
                        existing_count,

                    "output":
                        str(output_path),
                }
            )

            continue

        if (
            existing_count > 0
            and not force
        ):
            print(
                f"Existing file contains "
                f"{existing_count} books."
            )

            print(
                "The category will be "
                "scraped again because "
                f"the target is {limit}."
            )

        if force and output_path.exists():
            print(
                "FORCE: existing data "
                "will be replaced."
            )

        # ----------------------------------------
        # Scrape
        # ----------------------------------------

        try:
            books = scrape_category(
                category,
                limit,
                headless=headless,
            )

            output_path = save_books(
                books,
                category_id,
            )

            print_summary(
                books
            )

            print()
            print(
                "Saved:",
                output_path,
            )

            status = (
                "completed"
                if len(books) >= limit
                else "partial"
            )

            results.append(
                {
                    "category_id":
                        category_id,

                    "category_name":
                        category_name,

                    "status":
                        status,

                    "books":
                        len(books),

                    "output":
                        str(output_path),
                }
            )

        except KeyboardInterrupt:
            print()
            print()
            print(
                "Batch scraping stopped "
                "by user."
            )

            break

        except Exception as error:
            print()
            print(
                f"ERROR while scraping "
                f"{category_name} "
                f"({category_id}):"
            )

            print(error)

            results.append(
                {
                    "category_id":
                        category_id,

                    "category_name":
                        category_name,

                    "status":
                        "failed",

                    "books":
                        0,

                    "output":
                        None,

                    "error":
                        str(error),
                }
            )

        # ----------------------------------------
        # Delay
        # ----------------------------------------

        if index < total_categories:
            wait_between_categories(
                min_delay,
                max_delay,
            )

    return results


# ============================================================
# Batch Summary
# ============================================================

def print_batch_summary(
    results,
):
    print()
    print()
    print("=" * 70)
    print("BATCH SUMMARY")
    print("=" * 70)

    completed = 0
    skipped = 0
    partial = 0
    failed = 0

    total_books = 0

    for result in results:
        status = result["status"]

        if status == "completed":
            completed += 1

        elif status == "skipped":
            skipped += 1

        elif status == "partial":
            partial += 1

        elif status == "failed":
            failed += 1

        total_books += result["books"]

        print(
            f"{result['category_id']:>4} | "
            f"{status:<9} | "
            f"{result['books']:>4} | "
            f"{result['category_name']}"
        )

    print("-" * 70)

    print(
        f"Processed: {len(results)}"
    )

    print(
        f"Completed: {completed}"
    )

    print(
        f"Skipped:   {skipped}"
    )

    print(
        f"Partial:   {partial}"
    )

    print(
        f"Failed:    {failed}"
    )

    print(
        f"Raw records: {total_books}"
    )

    print("=" * 70)


# ============================================================
# Save Batch Report
# ============================================================

def save_batch_report(
    results,
):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = (
        OUTPUT_DIR
        / "scrape_report.json"
    )

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        "Batch report:",
        report_path,
    )


# ============================================================
# CLI
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Scrape all configured "
            "MEB categories."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Maximum books per category. "
            "Defaults to the value in "
            "target_categories.json."
        ),
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help=(
            "Run Chromium without "
            "a visible browser window."
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Re-scrape categories even "
            "when their existing JSON "
            "already contains enough books."
        ),
    )

    parser.add_argument(
        "--min-delay",
        type=float,
        default=2.0,
        help=(
            "Minimum delay between "
            "categories in seconds."
        ),
    )

    parser.add_argument(
        "--max-delay",
        type=float,
        default=4.0,
        help=(
            "Maximum delay between "
            "categories in seconds."
        ),
    )

    return parser.parse_args()


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    args = parse_args()

    config = load_config()

    categories = config[
        "categories"
    ]

    limit = (
        args.limit
        if args.limit is not None
        else config[
            "max_books_per_category"
        ]
    )

    results = scrape_all_categories(
        categories=categories,
        limit=limit,
        headless=args.headless,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        force=args.force,
    )

    print_batch_summary(
        results
    )

    save_batch_report(
        results
    )