#!/usr/bin/env python3
"""AWMF Crawler - URL extraction only."""
import asyncio
import sys
sys.path.insert(0, "/opt/awmf-sync")
from scripts.awmf_document import AWMFDocument

try:
    from playwright.async_api import async_playwright
except ImportError:
    import subprocess
    subprocess.run(["pip3", "install", "playwright"], check=True)
    subprocess.run(["python3", "-m", "playwright", "install", "chromium"], check=True)
    from playwright.async_api import async_playwright

BASE_URL = "https://register.awmf.org"
LEITLINIEN_URL = f"{BASE_URL}/de/leitlinien/aktuelle-leitlinien"
REQUEST_DELAY = 2

async def get_fachgesellschaft_links(page):
    await page.goto(LEITLINIEN_URL, wait_until="networkidle", timeout=60000)
    await page.wait_for_timeout(5000)
    links = await page.eval_on_selector_all(
        "a[href*='/fachgesellschaft/']",
        "elements => elements.map(el => ({href: el.href, text: el.textContent.trim()}))"
    )
    seen = set()
    return [l for l in links if l["href"] not in seen and not seen.add(l["href"])]

async def get_leitlinien_links(page, fg_url, fg_name):
    await page.goto(fg_url, wait_until="networkidle", timeout=60000)
    await page.wait_for_timeout(4000)
    links = await page.eval_on_selector_all(
        "a[href*='/leitlinien/detail/']",
        "elements => elements.map(el => ({href: el.href, text: el.textContent.trim()}))"
    )
    seen = set()
    return [l for l in links if l["href"] not in seen and not seen.add(l["href"])]

async def get_pdf_links(page, leitlinie_url):
    try:
        await page.goto(leitlinie_url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(4000)
        pdf_links = await page.eval_on_selector_all("a[href$='.pdf']",
            "elements => elements.map(el => ({href: el.href, text: el.textContent.trim()}))")
        more_links = await page.eval_on_selector_all("a[href*='assets/guidelines']",
            "elements => elements.map(el => ({href: el.href, text: el.textContent.trim()}))")
        seen = set()
        return [l for l in pdf_links + more_links if l["href"].endswith(".pdf") and l["href"] not in seen and not seen.add(l["href"])]
    except Exception as e:
        print(f"Error loading {leitlinie_url}: {e}")
        return []

async def crawl_for_urls(progress_callback=None):
    async def log(msg):
        print(msg)
        if progress_callback: await progress_callback(msg)

    await log("[1/3] Starting AWMF registry crawl...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        page = await context.new_page()
        fg_links = await get_fachgesellschaft_links(page)
        await log(f"    Found {len(fg_links)} Fachgesellschaft pages")

        all_leitlinien = []
        await log(f"[2/3] Scanning Fachgesellschaft pages...")
        for i, fg in enumerate(fg_links):
            if (i + 1) % 10 == 0: await log(f"    [{i+1}/{len(fg_links)}] Scanning...")
            all_leitlinien.extend(await get_leitlinien_links(page, fg["href"], fg["text"]))
            await asyncio.sleep(REQUEST_DELAY)

        seen = set()
        unique_leitlinien = [ll for ll in all_leitlinien if ll["href"] not in seen and not seen.add(ll["href"])]
        await log(f"    Total unique Leitlinien: {len(unique_leitlinien)}")

        all_pdfs = []
        await log(f"[3/3] Scanning Leitlinien for PDFs...")
        for i, ll in enumerate(unique_leitlinien):
            if (i + 1) % 50 == 0: await log(f"    [{i+1}/{len(unique_leitlinien)}] Processing...")
            for pdf in await get_pdf_links(page, ll["href"]):
                if pdf["href"] not in [p["href"] for p in all_pdfs]: all_pdfs.append(pdf)
            await asyncio.sleep(REQUEST_DELAY)
        await browser.close()

    await log(f"    Building index for {len(all_pdfs)} PDFs...")
    documents = {AWMFDocument.from_url(pdf["href"]).filename: AWMFDocument.from_url(pdf["href"]) for pdf in all_pdfs}
    await log(f"    Crawl complete: {len(documents)} unique PDFs")
    return documents
