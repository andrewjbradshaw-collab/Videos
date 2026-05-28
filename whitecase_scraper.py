#!/usr/bin/env python3
"""
White & Case People Directory Scraper
Requires: pip install playwright && playwright install chromium
Run: python3 whitecase_scraper.py
"""

import asyncio
import csv
import json
import re
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

BASE_URL = "https://www.whitecase.com"
PEOPLE_URL = "https://www.whitecase.com/people"
OUTPUT_JSON = "whitecase_people.json"
OUTPUT_CSV = "whitecase_people.csv"
PROGRESS_FILE = "whitecase_progress.json"
DELAY_BETWEEN_PAGES = 1.5  # seconds between profile requests


async def get_all_profile_links(page) -> list[str]:
    """Scroll through the people listing and collect all profile URLs."""
    print("Loading people directory...")
    await page.goto(PEOPLE_URL, wait_until="networkidle", timeout=60000)
    await page.wait_for_timeout(2000)

    links = set()
    prev_count = -1

    while True:
        # Collect all person links visible so far
        anchors = await page.query_selector_all("a[href*='/people/']")
        for a in anchors:
            href = await a.get_attribute("href")
            if href and re.search(r"/people/[^?#]+$", href):
                full = href if href.startswith("http") else BASE_URL + href
                links.add(full)

        # Try clicking a "Load more" / "Show more" button if present
        load_more = await page.query_selector(
            "button:has-text('Load more'), button:has-text('Show more'), "
            "a:has-text('Load more'), a:has-text('Show more'), "
            "[class*='load-more'], [class*='loadmore']"
        )
        if load_more:
            try:
                await load_more.scroll_into_view_if_needed()
                await load_more.click()
                await page.wait_for_timeout(2000)
            except Exception:
                pass

        # Also try scrolling to the bottom to trigger infinite scroll
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1500)

        current_count = len(links)
        if current_count == prev_count:
            # No new links loaded — check for numbered pagination
            next_btn = await page.query_selector(
                "a[aria-label='Next page'], a[rel='next'], "
                "[class*='pagination'] a:has-text('Next'), "
                "[class*='pager'] a:has-text('Next')"
            )
            if next_btn:
                await next_btn.scroll_into_view_if_needed()
                await next_btn.click()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(2000)
                prev_count = -1  # reset so we re-collect
                continue
            else:
                break  # nothing more to load
        prev_count = current_count
        print(f"  Found {current_count} profiles so far...", end="\r")

    print(f"\nTotal profile links found: {len(links)}")
    return sorted(links)


async def scrape_profile(page, url: str) -> dict:
    """Visit a single attorney profile page and extract all bio fields."""
    bio = {"url": url}
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(1000)

        async def text(selector):
            el = await page.query_selector(selector)
            return (await el.inner_text()).strip() if el else ""

        async def texts(selector):
            els = await page.query_selector_all(selector)
            return [((await e.inner_text()).strip()) for e in els if (await e.inner_text()).strip()]

        # Name
        bio["name"] = await text("h1, [class*='name'][class*='attorney'], [class*='attorney'][class*='name']")

        # Title / position
        bio["title"] = await text(
            "[class*='title']:not(title), [class*='position'], [class*='role'], "
            "[class*='job-title'], [class*='designation']"
        )

        # Office locations
        offices = await texts("[class*='office'] a, [class*='location'] a, [class*='offices'] li")
        bio["offices"] = offices

        # Phone numbers
        phones = await texts("a[href^='tel:'], [class*='phone'], [class*='tel']")
        bio["phones"] = [re.sub(r"\s+", " ", p) for p in phones]

        # Email
        email_el = await page.query_selector("a[href^='mailto:']")
        bio["email"] = (await email_el.get_attribute("href")).replace("mailto:", "") if email_el else ""

        # Practice areas
        bio["practice_areas"] = await texts(
            "[class*='practice'] a, [class*='expertise'] a, [class*='service'] a, "
            "[class*='practices'] li, [class*='practice-areas'] li"
        )

        # Industries
        bio["industries"] = await texts(
            "[class*='industr'] a, [class*='sector'] a, [class*='industr'] li"
        )

        # Bar admissions
        bio["bar_admissions"] = await texts(
            "[class*='admission'] li, [class*='bar'] li, [class*='qualified'] li"
        )

        # Education
        bio["education"] = await texts(
            "[class*='education'] li, [class*='academic'] li"
        )

        # Languages
        bio["languages"] = await texts(
            "[class*='language'] li, [class*='languages'] li"
        )

        # Bio / overview text
        bio_paras = await texts(
            "[class*='bio'] p, [class*='overview'] p, [class*='profile'] p, "
            "[class*='description'] p, article p"
        )
        bio["bio_text"] = " ".join(bio_paras[:10])  # cap at first 10 paragraphs

        # Publications / notable work
        bio["publications"] = await texts(
            "[class*='publication'] li, [class*='insight'] li, [class*='article'] li"
        )

        # Awards / recognition
        bio["awards"] = await texts(
            "[class*='award'] li, [class*='recogni'] li, [class*='ranking'] li"
        )

        # LinkedIn / social
        linkedin_el = await page.query_selector("a[href*='linkedin.com']")
        bio["linkedin"] = await linkedin_el.get_attribute("href") if linkedin_el else ""

    except PWTimeout:
        bio["error"] = "timeout"
    except Exception as e:
        bio["error"] = str(e)

    return bio


def load_progress() -> dict:
    if Path(PROGRESS_FILE).exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"done_urls": [], "results": []}


def save_progress(done_urls: list, results: list):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({"done_urls": done_urls, "results": results}, f)


def write_outputs(results: list):
    with open(OUTPUT_JSON, "w") as f:
        json.dump(results, f, indent=2)

    if results:
        all_keys = []
        for r in results:
            for k in r:
                if k not in all_keys:
                    all_keys.append(k)
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
            writer.writeheader()
            for row in results:
                flat = {}
                for k, v in row.items():
                    flat[k] = " | ".join(v) if isinstance(v, list) else v
                writer.writerow(flat)

    print(f"\nSaved {len(results)} records to {OUTPUT_JSON} and {OUTPUT_CSV}")


async def main():
    progress = load_progress()
    done_urls = set(progress["done_urls"])
    results = progress["results"]

    if done_urls:
        print(f"Resuming — {len(done_urls)} profiles already scraped.")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
        )
        page = await context.new_page()

        # Step 1: Collect all profile URLs
        all_links = await get_all_profile_links(page)

        # If the directory scrape found nothing (WAF/JS issue), bail early
        if not all_links:
            print("No profile links found. The site may require a real browser session or CAPTCHA solving.")
            await browser.close()
            sys.exit(1)

        # Step 2: Scrape each profile
        todo = [u for u in all_links if u not in done_urls]
        print(f"Scraping {len(todo)} remaining profiles (of {len(all_links)} total)...")

        for i, url in enumerate(todo, 1):
            bio = await scrape_profile(page, url)
            results.append(bio)
            done_urls.add(url)

            name = bio.get("name") or url
            status = f"[{i}/{len(todo)}] {name}"
            if "error" in bio:
                status += f"  ERROR: {bio['error']}"
            print(status)

            # Save progress every 25 profiles
            if i % 25 == 0:
                save_progress(list(done_urls), results)
                write_outputs(results)

            await asyncio.sleep(DELAY_BETWEEN_PAGES)

        await browser.close()

    save_progress(list(done_urls), results)
    write_outputs(results)


if __name__ == "__main__":
    asyncio.run(main())
