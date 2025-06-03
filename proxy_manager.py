#C:\Users\Administrator\Desktop\medios\proxy_manager.py
#!/usr/bin/env python
import os
import asyncio
import time
import urllib.parse
import logging
from dotenv import load_dotenv
from logconfig import logger, flush_logs
import ping3  # ICMP ping ölçümü için ping3 kütüphanesi

# .env dosyasını yükle
load_dotenv("medios.env")
TEST_URL = "https://httpbin.org/ip"  # Bu URL, artık kullanılmayacak
ENV_FILENAME = "medios.env"

def load_proxy_list(filename: str = ENV_FILENAME) -> list:
    proxy_list = []
    if not os.path.exists(filename):
        logger.error(f"{filename} dosyasi bulunamadi!")
        flush_logs()
        return proxy_list
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("PROXY_LIST="):
                value = line.split("=", 1)[1].strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                proxy_list = [proxy.strip() for proxy in value.split(",") if proxy.strip()]
                break
    logger.info(f"Yuklenen proxy sayisi: {len(proxy_list)}")
    flush_logs()
    return proxy_list

async def test_proxy(proxy_str: str) -> bool:
    proxy_str = proxy_str.strip()
    if not (proxy_str.startswith("http://") or proxy_str.startswith("https://")):
        proxy_str = "http://" + proxy_str
    # Proxy stringinden host bilgisini ayıklıyoruz.
    parsed = urllib.parse.urlparse(proxy_str)
    host = parsed.hostname
    try:
        # ping3 pingi asenkron çalıştırmak için asyncio.to_thread kullanıyoruz.
        delay = await asyncio.to_thread(ping3.ping, host, timeout=5)
        if delay is None:
            logger.error(f"Proxy ping hatasi ({proxy_str}): Timeout veya ulaşım başarısız")
            flush_logs()
            return False
        elapsed_ms = delay * 1000
        logger.info(f"Proxy ICMP ping: {proxy_str} (Elapsed time: {elapsed_ms:.2f} ms)")
        flush_logs()
        return True
    except Exception as e:
        logger.error(f"Proxy ping error ({proxy_str}): {e}")
        flush_logs()
        return False
    finally:
        pass

async def filter_working_proxies(proxy_list: list) -> list:
    working = []
    for proxy in proxy_list:
        result = await test_proxy(proxy)
        if result:
            working.append(proxy)
    logger.info(f"{len(working)} calisan proxy bulundu (toplam {len(proxy_list)}).")
    flush_logs()
    return working

working_proxies = []
_proxy_iterator = None

async def initialize_proxy_manager(filename: str = ENV_FILENAME):
    global working_proxies, _proxy_iterator
    proxy_list = load_proxy_list(filename)
    working_proxies = await filter_working_proxies(proxy_list)
    if working_proxies:
        _proxy_iterator = iter(working_proxies)
        logger.info("Proxy manager basariyla baslatildi.")
        flush_logs()
    else:
        _proxy_iterator = None
        logger.error("Hicbir calisan proxy bulunamadi!")
        flush_logs()

def get_next_proxy() -> str:
    global _proxy_iterator, working_proxies
    if not working_proxies:
        logger.error("Calisan proxy listesi bos!")
        flush_logs()
        return None
    try:
        proxy = next(_proxy_iterator)
        flush_logs()
        return proxy
    except StopIteration:
        _proxy_iterator = iter(working_proxies)
        proxy = next(_proxy_iterator)
        flush_logs()
        return proxy

def remove_bad_proxy(bad_proxy: str):
    global working_proxies, _proxy_iterator
    if bad_proxy in working_proxies:
        working_proxies.remove(bad_proxy)
        logger.info(f"Calismayan proxy kaldirildi: {bad_proxy}")
        flush_logs()
        _proxy_iterator = iter(working_proxies)

if __name__ == "__main__":
    async def main():
        await initialize_proxy_manager()
        if working_proxies:
            logger.info("Calisan proxy listesi:")
            flush_logs()
            for proxy in working_proxies:
                logger.info(proxy)
                flush_logs()
        else:
            logger.info("Hic calisan proxy bulunamadi!")
            flush_logs()
    asyncio.run(main())
