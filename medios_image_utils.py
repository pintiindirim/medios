# medios_image_utils.py

import os
import hashlib
import requests
from bs4 import BeautifulSoup
import urllib.parse
import asyncio
from playwright.async_api import async_playwright
from PIL import Image
from io import BytesIO
from logconfig import logger, flush_logs

CACHE_DIR = "cache_previews"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
    logger.info("CACHE_DIR created: %s", CACHE_DIR)
    flush_logs()
else:
    logger.info("CACHE_DIR exists: %s", CACHE_DIR)
    flush_logs()

def get_cache_filename(url: str) -> str:
    logger.debug("get_cache_filename: URL: %s", url)
    flush_logs()
    hash_val = hashlib.md5(url.encode('utf-8')).hexdigest()
    filename = os.path.join(CACHE_DIR, f"{hash_val}.png")
    logger.debug("get_cache_filename: Generated filename: %s", filename)
    flush_logs()
    return filename

def fetch_preview_image(url: str) -> Image.Image:
    logger.info("fetch_preview_image: Downloading image from URL: %s", url)
    flush_logs()
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        logger.debug("fetch_preview_image: Initial request status: %s", response.status_code)
        flush_logs()
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            meta_tag = soup.find("meta", property="og:image")
            img_url = meta_tag["content"] if meta_tag and meta_tag.get("content") else None
            if not img_url:
                logger.warning("fetch_preview_image: og:image meta tag not found, trying fallback.")
                flush_logs()
                img = soup.find("picture", {"data-test": "product-image"})
                if img and img.img and img.img.get("src"):
                    img_url = img.img["src"]
            if img_url:
                if not img_url.startswith("http"):
                    img_url = urllib.parse.urljoin(url, img_url)
                logger.debug("fetch_preview_image: Final image URL: %s", img_url)
                flush_logs()
                img_resp = requests.get(img_url, headers=headers, timeout=5)
                logger.debug("fetch_preview_image: Image request status: %s", img_resp.status_code)
                flush_logs()
                if img_resp.status_code == 200:
                    try:
                        image = Image.open(BytesIO(img_resp.content))
                        logger.info("fetch_preview_image: Image downloaded successfully.")
                        flush_logs()
                        return image
                    except Exception as e:
                        logger.warning("fetch_preview_image: Error loading image: %s", e)
                        flush_logs()
    except Exception as e:
        logger.error("fetch_preview_image: Error downloading image: %s", e)
        flush_logs()
    return None

async def _fetch_preview_image_playwright(url: str) -> Image.Image:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=10000)
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            meta_tag = soup.find("meta", property="og:image")
            img_url = meta_tag["content"] if meta_tag and meta_tag.get("content") else None
            if not img_url:
                pic = soup.find("picture", {"data-test": "product-image"})
                if pic and pic.img and pic.img.get("src"):
                    img_url = pic.img["src"]
            if not img_url:
                for img in soup.find_all("img"):
                    src = img.get("src")
                    if src and "logo" not in src and "favicon" not in src:
                        img_url = src
                        break
            if img_url:
                if not img_url.startswith("http"):
                    img_url = urllib.parse.urljoin(url, img_url)
                logger.debug("Playwright: Final image URL: %s", img_url)
                flush_logs()
                img_resp = requests.get(img_url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
                if img_resp.status_code == 200:
                    try:
                        image = Image.open(BytesIO(img_resp.content))
                        logger.info("Playwright: Image downloaded successfully.")
                        flush_logs()
                        return image
                    except Exception as e:
                        logger.warning("Playwright: Error loading image: %s", e)
                        flush_logs()
        except Exception as e:
            logger.error("Playwright: Error downloading image: %s", e)
            flush_logs()
        finally:
            await browser.close()
    return None

def fetch_preview_image_via_playwright(url: str) -> Image.Image:
    try:
        return asyncio.run(_fetch_preview_image_playwright(url))
    except Exception as e:
        logger.error("fetch_preview_image_via_playwright: Error: %s", e)
        flush_logs()
    return None

def get_cached_preview_image(url: str) -> str:
    """
    URL'deki görseli cache'e kaydeder ve cache dosya yolunu döner.
    """
    cache_file = get_cache_filename(url)
    if os.path.exists(cache_file):
        logger.info("get_cached_preview_image: Cache already exists: %s", cache_file)
        flush_logs()
        return cache_file

    logger.info("get_cached_preview_image: Cache not found, downloading: %s", url)
    flush_logs()

    pil_image = fetch_preview_image(url)
    if pil_image is None:
        logger.info("get_cached_preview_image: Requests ile indirme başarısız, Playwright ile denenecek.")
        flush_logs()
        pil_image = fetch_preview_image_via_playwright(url)

    if pil_image:
        try:
            pil_image.save(cache_file)
            logger.info("get_cached_preview_image: Image saved to cache: %s", cache_file)
            flush_logs()
            return cache_file
        except Exception as e:
            logger.warning("get_cached_preview_image: Cache kaydetme hatası: %s", e)
            flush_logs()

    logger.warning("get_cached_preview_image: Görsel indirilemedi: %s", url)
    flush_logs()
    return None
