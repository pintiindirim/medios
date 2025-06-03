from dotenv import load_dotenv
import os
import sys
import asyncio
import zmq.asyncio
import zmq
import itertools
import urllib.parse
import subprocess
from logconfig import logger, flush_logs
from pathlib import Path

env_path = Path(__file__).parent / "medios.env"
if not env_path.exists():
    logger.error(f"{env_path} bulunamadı!")
    sys.exit(1)
load_dotenv(dotenv_path=env_path, override=True)

try:
    REMOTE_DEBUGGING_PORT = int(os.getenv("REMOTE_DEBUGGING_PORT", "9242"))
except ValueError:
    logger.warning("REMOTE_DEBUGGING_PORT geçersiz; varsayılan 9242 kullanılıyor.")
    REMOTE_DEBUGGING_PORT = 9242
logger.info("REMOTE_DEBUGGING_PORT=%d olarak ayarlandı", REMOTE_DEBUGGING_PORT)
flush_logs()

DEFAULT_BROWSER = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
REMOTE_BROWSER_PATH = os.getenv("BROWSER_PATH", DEFAULT_BROWSER)
logger.info("REMOTE_BROWSER_PATH=%s olarak ayarlandı", REMOTE_BROWSER_PATH)
flush_logs()

DEFAULT_USER_DATA_DIR = (
    Path.home() / "AppData" / "Local" / "BraveSoftware" / "Brave-Browser" / "User Data" / "Profile_medios"
)
REMOTE_BROWSER_USER_DATA_DIR = os.getenv(
    "BROWSER_USER_DATA_DIR",
    str(DEFAULT_USER_DATA_DIR)
)
logger.info("REMOTE_BROWSER_USER_DATA_DIR=%s olarak ayarlandı", REMOTE_BROWSER_USER_DATA_DIR)
flush_logs()

default_loop = asyncio.get_event_loop_policy()
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

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

MEDIA_LOGIN_EMAIL = os.getenv("MEDIA_LOGIN_EMAIL")
MEDIA_LOGIN_PASSWORD = os.getenv("MEDIA_LOGIN_PASSWORD")

CENTRAL_PUSH_ENDPOINT = "tcp://127.0.0.1:5560"
CENTRAL_PUB_ENDPOINT  = "tcp://127.0.0.1:5570"
zmq_context = zmq.asyncio.Context()

logger.info("Program basladi.")
flush_logs()

PROXY_LIST_RAW = os.getenv("PROXY_LIST", "")
if PROXY_LIST_RAW:
    PROXY_LIST = [p.strip() for p in PROXY_LIST_RAW.split(",")]
    PROXY_CYCLE = itertools.cycle(PROXY_LIST)
else:
    PROXY_LIST = []
    PROXY_CYCLE = None

def parse_proxy(proxy_url: str) -> dict:
    parsed = urllib.parse.urlparse(proxy_url)
    cfg = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
    if parsed.username:
        cfg["username"] = parsed.username
    if parsed.password:
        cfg["password"] = parsed.password
    return cfg

def get_httpx_proxies(proxy_url: str) -> dict:
    return {"http": proxy_url, "https": proxy_url}

def get_next_proxy():
    if PROXY_CYCLE:
        p = next(PROXY_CYCLE)
        return p, parse_proxy(p), get_httpx_proxies(p)
    return None, None, None

browser_process = None
launched_ports = set()

def launch_remote_browser(loopback_ip="127.0.0.1"):
    global browser_process
    port = REMOTE_DEBUGGING_PORT
    profile = REMOTE_BROWSER_USER_DATA_DIR

    if port in launched_ports:
        logger.info(f"[BROWSER OPEN] Port {port} zaten başlatıldı, atlanıyor.")
        flush_logs()
        return

    cmd = (
        f'"{REMOTE_BROWSER_PATH}" '
        f'--remote-debugging-port={port} '
        f'--remote-debugging-address={loopback_ip} '
        f'--user-data-dir="{profile}" '
        '--no-first-run --no-default-browser-check --homepage="about:blank"'
    )
    try:
        browser_process = subprocess.Popen(cmd, shell=True)
        launched_ports.add(port)
        logger.info(f"[BROWSER OPEN] Brave başlatıldı: debug port={port}, profil={profile}")
        flush_logs()
    except Exception as e:
        logger.exception(f"[BROWSER OPEN] Brave başlatılırken hata: {e}")
        sys.exit(1)

TELEGRAM_TOKEN_1 = os.getenv("TELEGRAM_TOKEN_1")
TELEGRAM_TOKEN_2 = os.getenv("TELEGRAM_TOKEN_2")
TELEGRAM_TOKEN_3 = os.getenv("TELEGRAM_TOKEN_3")
TELEGRAM_TOKENS = [t for t in (TELEGRAM_TOKEN_1, TELEGRAM_TOKEN_2, TELEGRAM_TOKEN_3) if t]
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_TOKEN_CYCLE = itertools.cycle(TELEGRAM_TOKENS) if TELEGRAM_TOKENS else None
