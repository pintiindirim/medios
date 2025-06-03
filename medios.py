#!/usr/bin/env python
# medios.py

import os
import asyncio

# --- Windows için SelectorEventLoopPolicy’i en başta ayarlıyoruz ---
if os.name == "nt":
    from asyncio import WindowsSelectorEventLoopPolicy
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
# ---------------------------------------------------------------

import sys
import json
import time

from database import create_pool, create_database, create_table, db_bulk_worker
from proxy_manager import initialize_proxy_manager, get_next_proxy
from telegram_notifier import send_telegram_notification
from logconfig import flush_logs, logger
from dependencies import zmq_publish_message
from medios_image_utils import get_cached_preview_image, get_cache_filename

from LoginCookieModule import login_and_save_cookies
from medios_iki import scrape_page_with_context
from medios_uc import wait_for_products, notification_worker

BASE_URL = "https://www.mediamarkt.com.tr"
DATABASE_CONFIG = {
    'user': os.getenv("DB_USER", "root"),
    'password': os.getenv("DB_PASSWORD"),
    'db': os.getenv("DB_NAME"),
    'host': os.getenv("DB_HOST"),
    'port': int(os.getenv("DB_PORT", "3306")),
    'minsize': 80,
    'maxsize': 150
}

db_update_queue    = asyncio.Queue()
notification_queue = asyncio.Queue()
state = {
    "count": 0,
    "notified_prices": {}
}

def log_info(msg: str):
    logger.info(msg)
    flush_logs()

async def is_products_table_filled(pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM products")
            return (await cur.fetchone())[0] > 0

async def scrape_med():
    log_info("scrape_med: Başlatılıyor.")
    state["count"] = 0
    start = time.time()
    pool = None

    # --- Proxy ve çerez ortamını temizle ---
    os.environ.pop("HTTP_PROXY", None)
    os.environ.pop("HTTPS_PROXY", None)
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"

    # --- Proxy seçimi ---
    proxy_str, proxy_cfg, _ = get_next_proxy()
    if proxy_str:
        log_info(f"scrape_med: Seçilen proxy: {proxy_str}")
        try:
            proxy_cfg = {"server": proxy_str}
        except Exception as e:
            logger.error(f"scrape_med: Proxy config hatası: {e}")
            flush_logs()
            proxy_cfg = None
    else:
        log_info("scrape_med: Proxy kullanılmıyor.")
        proxy_cfg = None

    try:
        from playwright.async_api import async_playwright
        log_info("scrape_med: Playwright başlatılıyor.")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            if proxy_cfg:
                context = await browser.new_context(proxy=proxy_cfg)
            else:
                context = await browser.new_context()

            log_info("scrape_med: Browser context hazır.")

            # Eğer daha önce kaydedilmiş cerez varsa ekleyelim
            if os.path.exists("cookies.json"):
                with open("cookies.json", "r", encoding="utf-8") as f:
                    saved_cookies = json.load(f)
                await context.add_cookies(saved_cookies)
                log_info("scrape_med: Kayıtlı cerezler context'e eklendi.")

            # Gereksiz kaynakları abort et
            await context.route(
                "**/*",
                lambda r, req: r.abort() if req.resource_type in {
                    "image","media","font","iframe","track","analytics","pixel","tag","facebook","doubleclick"
                } else r.continue_()
            )
            log_info("scrape_med: Routing ayarlandı.")

            # Veritabanı hazırlığı
            await create_database()
            pool = await create_pool()
            await create_table(pool)
            log_info("scrape_med: Veritabanı hazır.")

            import httpx
            url = BASE_URL + "/tr/checkout"

            if proxy_str:
                os.environ["HTTP_PROXY"] = proxy_str
                os.environ["HTTPS_PROXY"] = proxy_str

            async with httpx.AsyncClient(
                http2=True,
                timeout=httpx.Timeout(10.0, connect=5.0)
            ) as client:
                await scrape_page_with_context(
                    context, client, url, pool,
                    db_update_queue, notification_queue, state
                )

            await browser.close()

    except Exception as e:
        logger.error(f"scrape_med: Hata: {e}")
        flush_logs()
    finally:
        if pool:
            pool.close()
            await pool.wait_closed()
            log_info("scrape_med: DB pool kapatıldı.")

    elapsed = time.time() - start
    log_info(f"scrape_med: Tamamlandı: {elapsed:.2f} sn, ürün sayısı: {state['count']}")

async def preload_images(pool):
    log_info("preload_images: Linkler alınıyor...")
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT product_link FROM products")
            rows = await cur.fetchall()
    links = [r[0] for r in rows if r[0]]
    log_info(f"preload_images: {len(links)} link bulundu.")
    tasks = []
    for link in links:
        cache_file = get_cache_filename(link)
        if not os.path.exists(cache_file):
            tasks.append(asyncio.to_thread(get_cached_preview_image, link))
    if tasks:
        await asyncio.gather(*tasks)
    log_info("preload_images: Tamamlandı.")

async def repeated_scrape():
    log_info("repeated_scrape: Başlatılıyor.")
    pool = await create_pool()
    await create_table(pool)

    dbw  = asyncio.create_task(db_bulk_worker(pool, db_update_queue))
    notw = asyncio.create_task(notification_worker(notification_queue))

    try:
        while True:
            log_info("repeated_scrape: Yeni döngü.")
            t0 = time.time()
            await scrape_med()
            dt = time.time() - t0
            cnt = state["count"]
            log_info(f"repeated_scrape: Döngü süresi {dt:.2f} sn, {cnt} ürün.")
            await wait_for_products(pool, expected_minimum=1, timeout=2)
            await preload_images(pool)
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        log_info("repeated_scrape: İptal edildi.")
    finally:
        dbw.cancel()
        notw.cancel()
        pool.close()
        await pool.wait_closed()
        log_info("repeated_scrape: Worker’lar durduruldu, pool kapandı.")

async def main():
    log_info("main: Başlatılıyor.")
    email    = os.getenv("MEDIA_LOGIN_EMAIL")
    password = os.getenv("MEDIA_LOGIN_PASSWORD")
    if not (email and password):
        logger.error("main: ENV’de MEDIA_LOGIN_EMAIL / PASSWORD yok!")
        sys.exit(1)

    await initialize_proxy_manager()
    log_info("main: Login yapılıyor...")
    await login_and_save_cookies(
        email,
        password,
        BASE_URL + "/tr/myaccount/auth/login",
        "cookies.json"
    )
    log_info("main: Login başarılı.")

    await create_database()
    pool = await create_pool()
    await create_table(pool)
    if not await is_products_table_filled(pool):
        log_info("main: İlk scrape yapılıyor...")
        await scrape_med()
        cnt = await wait_for_products(pool, expected_minimum=1, timeout=2)
        log_info(f"main: {cnt} kayıt eklendi.")
    else:
        log_info("main: Veritabanı zaten dolu, başlatılıyor...")

    pool.close()
    await pool.wait_closed()

    pool2 = await create_pool()
    await wait_for_products(pool2, expected_minimum=1, timeout=2)
    await preload_images(pool2)
    pool2.close()
    await pool2.wait_closed()

    await repeated_scrape()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        msg = str(e).encode("ascii", "ignore").decode("ascii", "ignore")
        logger.error(f"main: Kritik hata: {msg}")
        flush_logs()
        sys.exit(1)
