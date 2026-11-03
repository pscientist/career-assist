import argparse
import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright

from render_jobs import render_jobs_html

# Define the watchlist of technologies you want to monitor (expandable as needed)
TECH_WATCHLIST = [
    "python", "javascript", "typescript", "react", "next.js", 
    "node.js", "php", "postgresql", "aws", "docker", "fastapi", 
    "django", "flask", "vue", "angular", "azure", "openai", "anthropic"
]

# Yellow text, then reset. Longer names are matched first so "javascript"
# is not split by a shorter keyword.
ANSI_HIGHLIGHT = "\033[33m"
ANSI_RESET = "\033[0m"

def extract_tech_stack(text):
    if not text:
        return []
    text_lower = text.lower()
    found_tech = []
    for tech in TECH_WATCHLIST:
        # Use word boundaries to prevent partial string false positives (e.g. ensuring 'python' matches as a standalone word)
        pattern = r'\b' + re.escape(tech) + r'\b'
        if re.search(pattern, text_lower):
            found_tech.append(tech)
    return found_tech

def highlight_tech_keywords(text, keywords):
    if not text or not keywords:
        return text or ""
    ordered = sorted(set(keywords), key=len, reverse=True)
    pattern = re.compile(
        r"\b(?:" + "|".join(re.escape(keyword) for keyword in ordered) + r")\b",
        re.IGNORECASE,
    )
    return pattern.sub(lambda match: f"{ANSI_HIGHLIGHT}{match.group(0)}{ANSI_RESET}", text)

async def parseOneJob(card, detail_page, debug=False):
    try:
        title_elem = await card.query_selector('a[data-automation="jobTitle"]')
        title = await title_elem.inner_text() if title_elem else "N/A"
        raw_href = (await title_elem.get_attribute("href") if title_elem else "") or ""
        job_url = f"https://www.seek.co.nz{raw_href}" if raw_href.startswith("/") else raw_href

        company_elem = await card.query_selector('a[data-automation="jobCompany"]')
        company = await company_elem.inner_text() if company_elem else "N/A"

        location_elem = await card.query_selector('a[data-automation="jobLocation"]')
        job_location = await location_elem.inner_text() if location_elem else "N/A"

        teaser_elem = await card.query_selector('[data-automation="jobShortDescription"]')
        teaser = await teaser_elem.inner_text() if teaser_elem else ""

        # Card bullets often name the stack ("Tech Stack: .NET, AWS, SQL, React.JS")
        # and are separate from the short description.
        bullet_texts = []
        for bullet in await card.query_selector_all("ul li"):
            bullet_text = (await bullet.inner_text()).strip()
            if bullet_text:
                bullet_texts.append(bullet_text)

        # Navigate to the individual job detail page to fetch the full description
        full_description = ""
        if job_url and job_url.startswith("http"):
            try:
                await detail_page.goto(job_url, wait_until="domcontentloaded", timeout=15000)
                desc_elem = await detail_page.query_selector('[data-automation="jobAdDetails"]') # updated from jobDetails to jobAdDetails
                if desc_elem:
                    full_description = await desc_elem.inner_text()
            except Exception as detail_err:
                print(f"Could not load job details ({job_url}): {detail_err}")

        # Title, bullets, teaser, and the ad body. The stack is often only in the bullets.
        combined_text = "\n".join(
            part for part in (title, "\n".join(bullet_texts), teaser, full_description) if part and part != "N/A"
        )

        # Requirements sections use several headings. Match at the start of a
        # line so a phrase like "about you" inside a sentence is ignored.
        requirements_heading = re.compile(
            r"(?im)^[ \t]*(?:"
            r"what you['’]?ll bring"
            r"|what you bring"
            r"|skills and qualifications"
            r"|qualifications and experience"
            r"|skills\s+(?:&|and)\s+experience"
            r"|about you"
            r"|must-haves"
            r")\s*:?[ \t]*"
        )
        section_match = requirements_heading.search(full_description)
        requirements = full_description[section_match.end():].strip() if section_match else ""

        # tech words
        detected_stack = extract_tech_stack(combined_text)

        job_id = await card.get_attribute("data-job-id")
        if not job_id and raw_href:
            job_id_match = re.search(r'/job/(\d+)', raw_href)
            job_id = job_id_match.group(1) if job_id_match else None

        if title == "N/A":
            return None

        print(f"Scraped: {title} @ {company} | Detected Stack: {detected_stack}")
        if debug:
            print(highlight_tech_keywords(requirements, detected_stack))

        return {
            "id": job_id,
            "title": title.strip(),
            "company": company.strip(),
            "location": job_location.strip(),
            "tech_stack": detected_stack,
            # "teaser": teaser.strip(),
            "requirements": requirements.strip(),
            "url": job_url,
            # "scraped_at": datetime.utcnow().isoformat()
        }
    except Exception as card_err:
        print(f"Error parsing individual job card: {card_err}")
        return None

def build_search_url(search_term, location):
    formatted_term = search_term.lower().replace(" ", "-")
    formatted_location = location.lower().replace(" ", "-")
    return f"https://www.seek.co.nz/{formatted_term}-jobs/in-{formatted_location}"

async def load_job_cards(list_page, url):
    # Hashed class names change. These data attributes are on the list and each card.
    card_selector = '[data-automation="search-result-job-list"] article[data-testid="job-card"]'
    await list_page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await list_page.wait_for_selector(card_selector, timeout=10000)
    return await list_page.query_selector_all(card_selector)

def save_jobs(jobs_data):
    filename = f"seek_jobs_with_stack_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(jobs_data, f, indent=2, ensure_ascii=False)
    print(f"Saved browsable copy to {render_jobs_html(filename)}")
    return filename

async def scrape_seek_nz(search_term="software engineer", location="All New Zealand", pages_to_scrape=1, debug=False):
    jobs_data = []
    base_url = build_search_url(search_term, location)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Create two pages: one for navigating the listing search results, one for pulling full details
        list_page = await context.new_page()
        detail_page = await context.new_page()

        for current_page in range(1, pages_to_scrape + 1):
            url = f"{base_url}?page={current_page}"
            print(f"Scraping list page {current_page}: {url}")

            try:
                job_cards = await load_job_cards(list_page, url)
            except Exception as e:
                print(f"Could not load page {current_page} or no jobs found: {e}")
                break

            print(f"Found {len(job_cards)} job listings on page {current_page}.")

            for card in job_cards:
                job = await parseOneJob(card, detail_page, debug=debug)
                if job is None:
                    continue
                jobs_data.append(job)
                if debug:
                    break

            if debug and jobs_data:
                break

            # Polite delay between pages
            await asyncio.sleep(2)

        await browser.close()

    filename = save_jobs(jobs_data)
    print(f"\nScraping complete! Saved data and tech requirements to {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Print one job's requirements and then stop")
    args = parser.parse_args()
    asyncio.run(scrape_seek_nz(
        search_term="developer",
        location="All New Zealand",
        pages_to_scrape=1,
        debug=args.debug,
    ))