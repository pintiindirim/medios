# telegram_notifier.py
import os
import itertools
import httpx
from logconfig import logger, flush_logs

# .env'den Telegram token ve chat id bilgilerini alıyoruz
TELEGRAM_TOKEN_1 = os.getenv("TELEGRAM_TOKEN_1")
TELEGRAM_TOKEN_2 = os.getenv("TELEGRAM_TOKEN_2")
TELEGRAM_TOKEN_3 = os.getenv("TELEGRAM_TOKEN_3")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Token listesini oluştur ve döngüsel olarak geçiş sağlayacak yapı kur
TELEGRAM_TOKENS = [token for token in (TELEGRAM_TOKEN_1, TELEGRAM_TOKEN_2, TELEGRAM_TOKEN_3) if token]
TELEGRAM_TOKEN_CYCLE = itertools.cycle(TELEGRAM_TOKENS)

async def send_telegram_notification(message: str, image_path: str = None):
    """
    Telegram kanalına mesaj gönderimi için asenkron fonksiyon.
    Eğer image_path belirtilmiş ve dosya mevcutsa, sendPhoto API'si kullanılarak ürün resmiyle beraber gönderilir;
    aksi durumda sendMessage ile sadece metin gönderilir.
    """
    token = next(TELEGRAM_TOKEN_CYCLE)
    base_url = f"https://api.telegram.org/bot{token}/"
    async with httpx.AsyncClient(timeout=10) as client:
        if image_path and os.path.exists(image_path):
            url = base_url + "sendPhoto"
            # Dosyayı baytlara çevirerek multipart olarak gönderiyoruz.
            try:
                with open(image_path, "rb") as f:
                    files = {"photo": f}
                    data = {"chat_id": TELEGRAM_CHAT_ID, "caption": message}
                    response = await client.post(url, data=data, files=files)
                    logger.info("Telegram sendPhoto response: %s", response.text)
                    flush_logs()
            except Exception as e:
                logger.error("Telegram sendPhoto error: %s", e)
                flush_logs()
        else:
            url = base_url + "sendMessage"
            data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
            try:
                response = await client.post(url, data=data)
                logger.info("Telegram sendMessage response: %s", response.text)
                flush_logs()
            except Exception as e:
                logger.error("Telegram sendMessage error: %s", e)
                flush_logs()
