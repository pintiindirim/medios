#C:\Users\Administrator\Desktop\medios\medios_db_utils.py
from dependencies import *
from logconfig import logger, flush_logs  # Merkezi log tan�m�n� kullan�yoruz
import pymysql
from datetime import datetime

DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "2123020080.Ac",
    "database": "medios",
    "port": 3306,
    "charset": "utf8mb4",
    "autocommit": True,
}

def get_connection(use_db=True):
    config = DB_CONFIG.copy()
    if not use_db and "database" in config:
        del config["database"]
    logger.debug("get_connection: Kullanilan DB konfigurasyonu: %s", config)
    flush_logs()
    return pymysql.connect(**config)

def init_db():
    try:
        logger.info("init_db: Veritabani baslatma islemi baslatiliyor...")
        flush_logs()
        conn = get_connection(use_db=False)
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        conn.close()
        logger.info("init_db: Veritabani olusturuldu veya zaten mevcut.")
        flush_logs()
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    message TEXT,
                    timestamp VARCHAR(50)
                )
            """)
        conn.close()
        logger.info("init_db: 'notifications' tablosu olusturuldu veya zaten mevcut.")
        flush_logs()
    except Exception as e:
        logger.error("init_db: DB initialization error: %s", e)
        flush_logs()

def save_notification(message):
    try:
        logger.info("save_notification: Bildirim kaydediliyor. Mesaj: %s", message)
        flush_logs()
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO notifications (message, timestamp) VALUES (%s, %s)",
                (message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
        conn.close()
        logger.info("save_notification: Bildirim basariyla kaydedildi.")
        flush_logs()
    except Exception as e:
        logger.error("save_notification: DB Save error: %s", e)
        flush_logs()

def load_notifications():
    try:
        logger.info("load_notifications: Bildirimler yukleniyor...")
        flush_logs()
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT message, timestamp FROM notifications ORDER BY id ASC")
            rows = cursor.fetchall()
        conn.close()
        logger.info("load_notifications: Bildirimler basariyla yuklendi.")
        flush_logs()
        return [{"message": msg, "timestamp": ts} for msg, ts in rows]
    except Exception as e:
        logger.error("load_notifications: DB Load error: %s", e)
        flush_logs()
        return []
