#!/usr/bin/env python
# medios_iki.py

import os
import json
import re
import asyncio
from datetime import datetime
import aiomysql

from config import BASE_URL, DATABASE_CONFIG, logger
from utilities import extract_product_name_from_url, clean_price, format_price_to_user_friendly
from telegram_notifier import send_telegram_notification
from logconfig import flush_logs
from medios_image_utils import get_cache_filename
from dependencies import zmq_publish_message
async def process_product(
    product_link: str,
    product_price_str: str,
    pool,
    db_update_queue: asyncio.Queue,
    notification_queue: asyncio.Queue,
    state: dict
):
    # sayaçı artır
    state["count"] += 1

    # fiyatı ayrıştır ve formatla
    price, _ = clean_price(product_price_str)
    formatted = format_price_to_user_friendly(price)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # tam link
    if not product_link.startswith("http"):
        product_link = BASE_URL + product_link

    # mevcut kayıt
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT product_price, product_name FROM products WHERE product_link=%s",
                (product_link,)
            )
            existing = await cur.fetchone()

    # db güncelle/ekle
    if existing:
        product_name = existing[1]
        db_update_queue.put_nowait({
            "product_link": product_link,
            "product_price": price,
            "now": now,
            "is_update": True
        })
    else:
        product_name = extract_product_name_from_url(product_link)
        db_update_queue.put_nowait({
            "product_link": product_link,
            "product_name": product_name,
            "product_price": price,
            "now": now
        })

    # akakçe fiyatını al
    try:
        akak_price = await get_akakce_primary_price(product_name)
    except:
        akak_price = None

    if akak_price is not None:
        diff = price - akak_price

        # **ÖNCE**: eğer daha önce bildirdiğimiz fiyattan şu anki fiyat yüksekse,
        # bir sonraki düşüşte yeniden bildirim atabilmek için sıfırla
        last_notified = state["notified_prices"].get(product_link)
        if last_notified is not None and price > last_notified:
            del state["notified_prices"][product_link]

        # **SONRA**: sadece diff ≤ -1500 ve fiyat, son bildirilen fiyattan **daha düşük**se bildirim
        last_notified = state["notified_prices"].get(product_link)
        if diff <= -1000 and (last_notified is None or price < last_notified):
            # bildirim yükle
            payload = {
                "project": "medios",
                "message": (
                    f"{'Güncelleme' if existing else 'Yeni Fırsat'}:\n"
                    f"{product_name}\n"
                    f"{product_link}\n"
                    f"Fiyat: {formatted}\n"
                    f"Akakçeden: {format_price_to_user_friendly(abs(diff))} daha ucuz!\n"
                    f"Time: {now}"
                )
            }
            notification_queue.put_nowait(json.dumps(payload))

            # telegram
            img = get_cache_filename(product_link)
            asyncio.create_task(send_telegram_notification(
                f"{product_name}\n{product_link}\n"
                f"Fiyat: {formatted}\n"
                f"Akakçeden: {format_price_to_user_friendly(abs(diff))} daha ucuz!",
                img
            ))

            # son bildirim fiyatını güncelle
            state["notified_prices"][product_link] = price

    flush_logs()

async def get_dynamic_price_text(element) -> str | None:
    sel1 = "div[data-test='mms-price'] span[aria-hidden='true']"
    el = await element.query_selector(sel1)
    if el:
        txt = (await el.text_content()).strip()
        if txt.startswith("₺") and re.search(r"\d", txt):
            return txt

    sel2 = "div[data-test='mms-price'] span.sc-e0c7d9f7-0"
    els = await element.query_selector_all(sel2)
    for e in els:
        txt = (await e.text_content()).strip()
        if txt.startswith("₺") and re.search(r"\d", txt):
            return txt

    return None

async def process_product_element(
    product_element,
    page_url: str,
    pool,
    db_update_queue: asyncio.Queue,
    notification_queue: asyncio.Queue,
    state: dict
):
    try:
        link_el = await product_element.query_selector("a[data-test='mms-router-link']")
        if not link_el:
            return
        href = await link_el.get_attribute("href")
        price_txt = await get_dynamic_price_text(product_element) or "Price Not Specified"
        await process_product(href, price_txt, pool,
                              db_update_queue, notification_queue, state)
    except Exception as e:
        logger.error(f"process_product_element hata: {e}")
        flush_logs()

async def scrape_page_with_context(
    context,
    client,
    url: str,
    pool,
    db_update_queue: asyncio.Queue,
    notification_queue: asyncio.Queue,
    state: dict
):
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(0)

        # Sepet konteyneri
        try:
            await page.wait_for_selector("div[data-test='mms-seller-basket']", timeout=15000)
        except:
            pass
        basket = await page.query_selector("div[data-test='mms-seller-basket']")
        if not basket:
            logger.warning("scrape_page: Basket bulunamadı")
            return

        items = await basket.query_selector_all("div[data-test^='basket-lineitem-']")
        logger.info(f"scrape_page: Ürün elementi sayısı: {len(items)}")
        flush_logs()

        # paralel işleme
        await asyncio.gather(*[
            process_product_element(
                it, url, pool,
                db_update_queue, notification_queue, state
            ) for it in items
        ])
    finally:
        await page.close()
        flush_logs()
async def get_akakce_primary_price(product_name: str) -> float | None:
    """
    Akakçe DB’den ürüne ait üç satıcı + fiyatı alır
    ve öncelik sırasına göre en uygun fiyatı döner.
    """
    logger.debug("get_akakce_primary_price: Urun adi: %s", product_name)
    flush_logs()
    conn = None
    try:
        conn = await aiomysql.connect(
            user=DATABASE_CONFIG['user'],
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", "3306")),
            db="akakce",
            autocommit=True,
        )
        async with conn.cursor() as cur:
            query = """
                SELECT satici_bir,    satici_bir_fiyat,
                       satici_iki,    satici_iki_fiyat,
                       satici_uc,     satici_uc_fiyat
                FROM products
                WHERE urun_adi = %s
                LIMIT 1
            """
            await cur.execute(query, (product_name,))
            row = await cur.fetchone()
            logger.debug("get_akakce_primary_price: Sorgu sonucu: %s", row)
            flush_logs()

            if not row:
                logger.warning("get_akakce_primary_price: AK kaydı yok: %s", product_name)
                flush_logs()
                return None

            s1, p1, s2, p2, s3, p3 = row
            # normalize et
            n1 = (s1 or "").strip().lower().replace(" ", "")
            n2 = (s2 or "").strip().lower().replace(" ", "")

            # 1) İlk satıcı “mediamarkt” ise:
            #       → ikincil “pttavm” ise p3, değilse p2
            # 2) İlk satıcı “pttavm” ise:
            #       → ikincil “mediamarkt” ise p3, değilse p2
            # 3) Diğer tüm durumlar → p1
            if n1 == "mediamarkt":
                chosen = p3 if n2 == "pttavm" else p2
            elif n1 == "pttavm":
                chosen = p3 if n2 == "mediamarkt" else p2
            else:
                chosen = p1

            logger.debug("get_akakce_primary_price: Seçilen fiyat: %s", chosen)
            flush_logs()
            return float(chosen) if chosen is not None else None

    except Exception as e:
        logger.exception("get_akakce_primary_price: Hata (%s): %s", product_name, e)
        flush_logs()
        return None

    finally:
        if conn:
            conn.close()
