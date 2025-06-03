#!/usr/bin/env python
# LoginCookieModule.py

from dependencies import *
import sys
import json
import asyncio
import os
import httpx
from logconfig import logger, flush_logs
from config import (
    launch_remote_browser,
    REMOTE_DEBUGGING_PORT,
    REMOTE_BROWSER_PATH,
    REMOTE_BROWSER_USER_DATA_DIR
)
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Windows'ta ProactorEventLoop kullanımı
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Bypass sınıfını import ediyoruz
from CloudflareBypasser import CloudflareBypasser

async def get_cdp_websocket_url() -> str:
    """
    Brave'ın uzaktan debug portundan CDP WebSocket URL'i alır.
    """
    endpoint = f"http://127.0.0.1:{REMOTE_DEBUGGING_PORT}/json/version"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(endpoint)
        resp.raise_for_status()
        return resp.json()["webSocketDebuggerUrl"]

async def login_and_save_cookies(email: str, password: str, login_url: str, cookies_file: str):
    try:
        logger.info("Login işlemi başlatılıyor...")
        flush_logs()

        # --- 1) CloudflareBypasser ile Cloudflare testi geç ve çerezleri al ---
        bypass = CloudflareBypasser(
            browser_path=REMOTE_BROWSER_PATH,
            user_data_dir=REMOTE_BROWSER_USER_DATA_DIR,
            # headless=False
        )
        # Bypass metodunu asenkrona çevirmek için to_thread kullanıyoruz
        await asyncio.to_thread(lambda: bypass.bypass(target_url=login_url))

        # Bypass sonrası DrissionPage oturumundan çerezleri al
        raw_cookies = bypass.driver.session.cookies.get_dict(domain=".mediamarkt.com.tr")
        cookie_list = []
        for name, value in raw_cookies.items():
            # Herhangi bir olası encoding sorunu için str'e dönüştür ve hataları ignore et
            safe_name = str(name)
            safe_value = str(value)
            cookie_list.append({
                "name": safe_name,
                "value": safe_value,
                "domain": ".mediamarkt.com.tr",
                "path": "/"
            })
        # Çerezleri dosyaya yazarken encoding hatası olmasın diye bytes olarak encode/decode ediyoruz
        try:
            with open(cookies_file, "w", encoding="utf-8") as f:
                json.dump(cookie_list, f, ensure_ascii=False, indent=4)
        except Exception:
            # Daha güvenli yazma: hatalı karakterleri ignore ederek
            with open(cookies_file, "wb") as f:
                data = json.dumps(cookie_list, ensure_ascii=False).encode("utf-8", "ignore")
                f.write(data)
        logger.info(f"Cloudflare bypass sonrası çerezler '{cookies_file}' kaydedildi.")
        flush_logs()

        # DrissionPage tarayıcısını kapat
        bypass.driver.close()

        # --- 2) Uzaktan debug modunda Brave/Chromium'u başlat ---
        launch_remote_browser(loopback_ip="127.0.0.1")
        await asyncio.sleep(3)

        # 3) Proxy ayarlarını temizle
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)
        os.environ["NO_PROXY"] = "127.0.0.1,localhost"

        # --- 4) Playwright ile CDP üzerinden Brave'a bağlan ve çerez ekle ---
        async with async_playwright() as p:
            ws = await get_cdp_websocket_url()
            logger.info(f"CDP WebSocket URL alındı: {ws}")
            flush_logs()

            browser = await p.chromium.connect_over_cdp(ws)
            context = await browser.new_context()

            # Bypass sonrası aldığımız çerezleri Playwright context'e ekle
            await context.add_cookies(cookie_list)
            logger.info("Playwright context'e Cloudflare bypass çerezleri eklendi.")
            flush_logs()

            page = await context.new_page()

            # --- 5) Login sayfasına git ve formu doldur ---
            logger.info("Login sayfasına gidiliyor...")
            flush_logs()
            await page.goto(login_url, wait_until="domcontentloaded")

            logger.info("Form ve alanlar bekleniyor...")
            flush_logs()
            await page.wait_for_selector("form#myaccount-login-form")
            await page.wait_for_selector("input#email")
            await page.wait_for_selector("input#password")

            logger.info("Credentials dolduruluyor...")
            flush_logs()
            await page.fill("input#email", email)
            await page.fill("input#password", password)
            await page.click("button#mms-login-form__login-button")

            # --- 6) Çerez onay popup'ını atla veya onayla ---
            try:
                logger.info("Çerez onay popup'ı aranıyor...")
                flush_logs()
                btn = await page.wait_for_selector(
                    "button#pwa-consent-layer-accept-all-button",
                    timeout=5000
                )
                if btn:
                    await btn.click()
                    logger.info("Popup onaylandı.")
                    flush_logs()
            except PlaywrightTimeoutError:
                logger.info("Popup görünür değil, atlanıyor.")
                flush_logs()

            # --- 7) Login sonrası Playwright çerezlerini al ve dosyaya kaydet ---
            await asyncio.sleep(1)
            final_cookies = await context.cookies()
            safe_final = []
            for c in final_cookies:
                # Her öğeyi str() ile güvenli hale getir
                safe_final.append({
                    "name": str(c.get("name", "")),
                    "value": str(c.get("value", "")),
                    "domain": str(c.get("domain", "")),
                    "path": str(c.get("path", "/")),
                    "expires": c.get("expires", 0),
                    "httpOnly": c.get("httpOnly", False),
                    "secure": c.get("secure", False),
                    "sameSite": c.get("sameSite", "")
                })
            try:
                with open(cookies_file, "w", encoding="utf-8") as f:
                    json.dump(safe_final, f, ensure_ascii=False, indent=4)
            except Exception:
                with open(cookies_file, "wb") as f:
                    data = json.dumps(safe_final, ensure_ascii=False).encode("utf-8", "ignore")
                    f.write(data)
            logger.info(f"Playwright ile güncel çerezler '{cookies_file}' dosyasına yazıldı.")
            flush_logs()

            # --- 8) Temizlik ---
            await page.close()
            await context.close()
            logger.info("Login işlemi tamamlandı; context kapatıldı.")
            flush_logs()

    except Exception as e:
        logger.exception(f"Login ve çerez kaydetme hatası: {e}")
        flush_logs()
        sys.exit(1)
