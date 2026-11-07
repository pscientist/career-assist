import asyncio
import os
import re

from playwright.async_api import async_playwright

# Technologies to watch for in each ad. Longer names are matched as whole words.
TECH_WATCHLIST = [
    "python", "javascript", "typescript", "react", "next.js",
    "node.js", "php", "postgresql", "aws", "docker", "fastapi",
    "django", "flask", "vue", "angular", "azure", "openai", "anthropic",
    "java", "wordpress", "claude code", "ai", "cursor", ".net", "c#", "net", "c++",
    "restful api", "codex",
]

# #, ., and + are not word characters, so a boundary on both sides misses these.
_SPECIAL_TECH = {
    "c#": r"\bc#(?!\w)",
    "c++": r"\bc\+\+(?!\w)",
    ".net": r"\.net\b",
    "net": r"(?<!\.)\bnet\b",
}


def extract_tech_stack(text):
    if not text:
        return []
    text_lower = text.lower()
    found_tech = []
    for tech in TECH_WATCHLIST:
        pattern = _SPECIAL_TECH.get(tech) or r"\b" + re.escape(tech) + r"\b"
        if re.search(pattern, text_lower):
            found_tech.append(tech)
    return found_tech


async def parse_one_job(card, detail_page):
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

        # Card bullets often name the stack and sit outside the short description.
        bullet_texts = []
        for bullet in await card.query_selector_all("ul li"):
            bullet_text = (await bullet.inner_text()).strip()
            if bullet_text:
                bullet_texts.append(bullet_text)

        full_description = ""
        if job_url and job_url.startswith("http"):
            try:
                await detail_page.goto(job_url, wait_until="domcontentloaded", timeout=15000)
                desc_elem = await detail_page.query_selector('[data-automation="jobAdDetails"]')
                if desc_elem:
                    full_description = await desc_elem.inner_text()
            except Exception as detail_err:
                print(f"Could not load job details ({job_url}): {detail_err}")

        combined_text = "\n".join(
            part for part in (title, "\n".join(bullet_texts), teaser, full_description) if part and part != "N/A"
        )

        # Match a requirements heading at the start of a line, not inside a sentence.
        requirements_heading = re.compile(
            r"(?im)^[ \t]*(?:"
            r"what you['’]?ll bring"
            r"|what you bring"
            r"|skills and qualifications"
            r"|qualifications and experience"
            r"|skills\s+(?:&|and)\s+experience"
            r"|about you"
            r"|must-haves"
            r"|Ideally you will have"
            r")\s*:?[ \t]*"
        )
        section_match = requirements_heading.search(full_description)
        if section_match:
            requirements = full_description[section_match.end():].strip()
        else:
            requirements = full_description.strip()

        job_id = await card.get_attribute("data-job-id")
        if not job_id and raw_href:
            job_id_match = re.search(r"/job/(\d+)", raw_href)
            job_id = job_id_match.group(1) if job_id_match else None

        if title == "N/A":
            return None

        detected_stack = extract_tech_stack(combined_text)
        print(f"Scraped: {title} @ {company} | Detected Stack: {detected_stack}")
        return {
            "seek_id": job_id,
            "title": title.strip(),
            "company": company.strip(),
            "location": job_location.strip(),
            "tech_stack": detected_stack,
            "requirements": requirements.strip(),
            "url": job_url,
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


async def scrape_seek_nz(search_term="developer", location="All New Zealand", pages_to_scrape=1):
    """Scrape Seek and return job dicts. The caller stores them."""
    # A sandbox browser cache can hide the Chromium Playwright already installed.
    os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)
    jobs_data = []
    page_error = None
    base_url = build_search_url(search_term, location)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        list_page = await context.new_page()
        detail_page = await context.new_page()

        for current_page in range(1, pages_to_scrape + 1):
            url = f"{base_url}?page={current_page}"
            print(f"Scraping list page {current_page}: {url}")
            try:
                job_cards = await load_job_cards(list_page, url)
            except Exception as error:
                page_error = error
                print(f"Could not load page {current_page} or no jobs found: {error}")
                break

            print(f"Found {len(job_cards)} job listings on page {current_page}.")
            for card in job_cards:
                job = await parse_one_job(card, detail_page)
                if job is not None:
                    jobs_data.append(job)

            await asyncio.sleep(2)

        await browser.close()

    if not jobs_data:
        raise RuntimeError(str(page_error or "No jobs found."))
    print(f"Scraped {len(jobs_data)} jobs")
    return jobs_data
