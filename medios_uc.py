#!/usr/bin/env python
# medios_uc.py

import time
import asyncio
from logconfig import logger, flush_logs
from database import db_bulk_worker
from dependencies import zmq_publish_message

async def wait_for_products(pool, expected_minimum=1, timeout=10):
    """
    DB’ye en az expected_minimum adet kayıt gelene dek bekler.
    """
    start = time.time()
    while time.time() - start < timeout:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT COUNT(*) FROM products")
                cnt = (await cur.fetchone())[0]
                logger.debug("wait_for_products: %d kayıt var", cnt)
                flush_logs()
                if cnt >= expected_minimum:
                    return cnt
        await asyncio.sleep(0.5)
    return 0

async def notification_worker(notification_queue: asyncio.Queue):
    """
    notification_queue’dan gelen JSON’ları merkezi servise yollayan worker.
    """
    logger.info("notification_worker: Başlatıldı")
    flush_logs()
    while True:
        try:
            msg = await notification_queue.get()
            logger.debug("notification_worker: %s", msg)
            flush_logs()
            await zmq_publish_message(msg)
            flush_logs()
        except Exception as e:
            logger.error("notification_worker hata: %s", e)
            flush_logs()

async def setup_and_run_workers(pool, db_update_queue: asyncio.Queue, notification_queue: asyncio.Queue):
    """
    DB ve bildirim worker’larını aynı anda başlatır.
    """
    logger.info("setup_and_run_workers: Worker’lar başlatılıyor")
    flush_logs()
    dbw = asyncio.create_task(db_bulk_worker(pool, db_update_queue))
    nw  = asyncio.create_task(notification_worker(notification_queue))
    return dbw, nw
