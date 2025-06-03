
MEDIOS Scraper & Notification Tool
==================================

Overview
--------
Medios is an asynchronous scraper and notification system designed to collect product data from MediaMarkt Türkiye, bypass Cloudflare protections, log in to user accounts, store product details in a MySQL database, and send price-difference notifications via Telegram.

Features:
- **Cloudflare bypass** using DrissionPage (CloudflareBypasser.py).
- **Automated login** using Playwright over a remote Brave/Chromium session (LoginCookieModule.py).
- **Asynchronous scraping** of the MediaMarkt checkout page, extracting product links, names, and prices (medios.py & medios_iki.py).
- **Database management** of product records in MySQL (database.py).
- **Proxy rotation** and health-checking via ICMP pings (proxy_manager.py).
- **Telegram notifications** for significant price drops compared to Akakçe prices (telegram_notifier.py).
- **Utility functions** for cleaning product names, adjusting brand-specific naming conventions, and formatting prices (utilities.py).
- **Image caching** of product preview images (medios_image_utils.py).
- **Configuration** via a `medios.env` file.

Prerequisites
-------------
- Python 3.10+
- MySQL server (or compatible) running and accessible
- [Brave browser](https://brave.com/) installed for remote debugging (optional; can adjust for Chromium)
- Telegram bot tokens and chat ID for notifications

Install Dependencies
--------------------
```bash
pip install aiomysql httpx zmq asyncio Playwright DrissionPage ping3 beautifulsoup4 Pillow numba python-dotenv
# Then install Playwright browsers:
python -m playwright install
```

Configuration (.env)
--------------------
Copy the example `medios.env` and fill in:
```
# Database
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=medios
DB_HOST=127.0.0.1
DB_PORT=3306

# MediaMarkt Login
MEDIA_LOGIN_EMAIL=you@example.com
MEDIA_LOGIN_PASSWORD=your_password

# Proxy List (comma-separated)
PROXY_LIST="http://user:pass@host:port,..."
PROXY_USER=your_proxy_user
PROXY_PASS=your_proxy_pass

# Telegram Notifications
TELEGRAM_TOKEN_1=<bot_token_1>
TELEGRAM_TOKEN_2=<bot_token_2>
TELEGRAM_TOKEN_3=<bot_token_3>
TELEGRAM_CHAT_ID=<chat_id>

# Remote Debugging for Brave/Chromium
REMOTE_DEBUGGING_PORT=9242
BROWSER_USER_DATA_DIR=C:/Path/To/Brave/User Data/Profile_medios
```
Place this file alongside the Python modules.

Module Descriptions
-------------------

1. **CloudflareBypasser.py**
   - Uses **DrissionPage.ChromiumPage** to navigate a target URL and repeatedly click Cloudflare Turnstile verification buttons until the “Just a moment” page is bypassed.
   - Key methods:
     - `bypass(target_url)`: load URL, detect Cloudflare challenge, click verification button, repeat until page loads.

2. **config.py**
   - Loads environment variables via `dotenv`.
   - Defines constants: `REMOTE_DEBUGGING_PORT`, `REMOTE_BROWSER_PATH`, `REMOTE_BROWSER_USER_DATA_DIR`.
   - Sets up Windows asyncio policy.
   - Defines `BASE_URL` and `DATABASE_CONFIG`.
   - Manages proxy list parsing: `parse_proxy`, `get_httpx_proxies`, `get_next_proxy`.
   - Provides `launch_remote_browser()` which spawns Brave in remote-debug mode for Playwright to connect.

3. **database.py**
   - Creates an asynchronous MySQL connection pool (`create_pool()`).
   - Checks/creates the database (`create_database()`).
   - Creates the `products` table with fields: `product_link`, `product_name`, `product_price`, `first_seen_date`, `last_update_date`.
   - `db_bulk_worker(pool, db_update_queue, ...)`: consumes item batches to insert or update product records efficiently.

4. **LoginCookieModule.py**
   - Performs a login flow:
     1. Instantiates `CloudflareBypasser` to bypass Cloudflare and collect initial cookies.
     2. Saves those cookies to `cookies_file`.
     3. Calls `launch_remote_browser()` to start Brave in remote-debug mode.
     4. Uses Playwright to connect via CDP and create a browser context.
     5. Adds bypass cookies to Playwright context.
     6. Navigates to login URL, waits for `form#myaccount-login-form`.
     7. Fills `input#email` and `input#password` fields, clicks the login button.
     8. Optionally accepts cookie‑consent popup.
     9. Collects final context cookies and writes them to `cookies_file`.

5. **medios.py**
   - Entry point script:
     - Applies Windows selector event loop if needed.
     - Calls `initialize_proxy_manager()`.
     - Calls `login_and_save_cookies()` to obtain and persist cookies.
     - Ensures database and table exist.
     - If database is empty, runs `scrape_med()` once to populate initial data.
     - Then repeatedly scrapes via `repeated_scrape()`, which delegates to `scrape_med()` in a loop with a short sleep.
     - Coordinates two background workers:
       - `db_bulk_worker`: writes to the database.
       - `notification_worker`: publishes notifications to a central ZMQ endpoint.
     - `scrape_med()`:
       - Clears any existing `HTTP_PROXY`/`HTTPS_PROXY`.
       - Obtains a proxy from `get_next_proxy()`, configures Playwright context (headless).
       - If `cookies.json` exists, loads cookies into context.
       - Aborts unnecessary resources (images, media, fonts, analytics, etc.) for faster scraping.
       - Creates DB and table, then invokes `scrape_page_with_context()` for the checkout URL.

6. **medios_iki.py**
   - Contains functions to process each product element found on the “basket” container:
     - `process_product_element()`: extracts link and price text, then calls `process_product()`.
     - `process_product(product_link, price_str, pool, db_update_queue, notification_queue, state)`:
       - Cleans/parses price via `clean_price()`.
       - Formats price via `format_price_to_user_friendly()`.
       - Normalizes `product_link` to an absolute URL.
       - Checks existing record in DB:
         - If exists, enqueues an update item.
         - Otherwise, enqueues an insert item (derives `product_name` via `extract_product_name_from_url()`).
       - Queries `get_akakce_primary_price(product_name)` from an “akakce” database to find competitive pricing:
         - If the scraped price is at least 1000₺ cheaper than Akakçe’s primary price, sends a Telegram notification via `send_telegram_notification()`.
         - Uses `state["notified_prices"]` to avoid duplicate notifications for the same price.
   - `scrape_page_with_context(context, client, url, pool, db_update_queue, notification_queue, state)`:
     - Opens a new Playwright page, navigates to `url`.
     - Waits for `div[data-test='mms-seller-basket']` container, iterates all `basket-lineitem-` elements to process in parallel.

   - `get_akakce_primary_price(product_name: str)`: asynchronously queries the “akakce” MySQL database to fetch up to three sellers/prices, then picks the appropriate seller’s price using rules:
     1. If first seller is “mediamarkt”:
        - If second is “pttavm”, use third price; otherwise, use second price.
     2. If first seller is “pttavm”:
        - If second is “mediamarkt”, use third price; otherwise, use second price.
     3. Otherwise, use first price.

7. **medios_uc.py**
   - `wait_for_products(pool, expected_minimum, timeout)`: polls the `products` table until at least `expected_minimum` rows exist (or timeout).
   - `notification_worker(notification_queue)`: consumes JSON notifications and forwards them to a ZMQ central push endpoint.

8. **proxy_manager.py**
   - Loads `PROXY_LIST` from `medios.env`.
   - Tests each proxy by ICMP ping (using `ping3`) to filter out non‑responsive proxies.
   - Maintains a rotating iterator (`_proxy_iterator`) over working proxies.
   - Functions:
     - `initialize_proxy_manager()`: populates `working_proxies`.
     - `get_next_proxy()`: returns the next working proxy string.
     - `remove_bad_proxy(bad_proxy)`: removes unreliable proxies from the list.

9. **telegram_notifier.py**
   - Reads `TELEGRAM_TOKEN_*` and `TELEGRAM_CHAT_ID` from environment.
   - `send_telegram_notification(message, image_path)`: asynchronously sends either a photo (if `image_path` exists) or a text message to the configured Telegram chat. Rotates among available bot tokens (`TELEGRAM_TOKEN_CYCLE`) to avoid rate limits.

10. **utilities.py**
    - Various helper functions for product name normalization, price cleaning, and formatting:
      - `compute_difference(p_price, ak_price)`: Numba‑JITed subtraction.
      - `turkishize(text)`: replaces certain English substrings with Turkish equivalents (e.g., “akilli”→“akıllı”).
      - `adjust_product_name_for_akakce(text)`: general regex replacements to match Akakçe’s name conventions, unify capacity units.
      - Brand‑specific name adjusters:
        - `adjust_xiaomi_product_name(...)`
        - `adjust_oppo_product_name(...)`
        - `adjust_realme_product_name(...)`
        - `adjust_samsung_product_name(...)`
        - `adjust_apple_product_name(...)`
      - `extract_product_name_from_url(url)`: parses MediaMarkt product URLs to derive a human‑friendly product name by tokenizing, converting numeric tokens to capacities (e.g., “512GB”), removing superfluous tokens, and then applying brand‑specific adjusters.
      - `clean_price(price_str)`: strips “TL” and formatting, returns a `float`.
      - `format_price_to_user_friendly(price_float)`: formats a float as a Turkish Lira string with comma decimal and dot thousands separator (e.g., “1.234,56 TL”).

11. **medios_image_utils.py**
    - Maintains a `cache_previews/` directory to store preview images.
    - `get_cache_filename(url)`: returns an MD5-based filename under `cache_previews/`.
    - `fetch_preview_image(url)`: uses `requests` + BeautifulSoup to extract the `og:image` meta tag or fallback `picture[data-test="product-image"]`. Downloads via `requests`, returns a PIL `Image`.
    - `_fetch_preview_image_playwright(url)`: similar logic using Playwright to obtain the page HTML, then parse with BeautifulSoup.
    - `get_cached_preview_image(url)`: checks if the cache PNG exists; if not, attempts `fetch_preview_image()`, then falls back to `fetch_preview_image_via_playwright()`. Saves the PIL image as PNG in the cache.

Usage
-----
1. **Setup Environment**
   - Place the provided modules in a directory (e.g., `medios/`).
   - Create `medios.env` next to those files, filling in all required settings.
   - Ensure your MySQL server is running, and the credentials in `medios.env` are valid.
   - Install all Python dependencies and run `playwright install`.

2. **First Run**
   ```bash
   python medios.py
   ```
   - This will:
     1. Ping and select a working proxy.
     2. Bypass Cloudflare via DrissionPage and save initial cookies.
     3. Launch Brave in remote debug mode.
     4. Launch Playwright context, add cookies, perform login, and save final cookies.
     5. Create or verify MySQL database/tables.
     6. Perform an initial scrape of `/tr/checkout`.
     7. Populate the `products` table.
     8. Download preview images to `cache_previews/`.
     9. Enter a repeating loop: scrape, process price updates, and send notifications if criteria met.

3. **Notifications**
   - When a scraped price for a product is at least 1000₺ lower than the Akakçe “primary price”, a Telegram message will be sent, including the product preview image if found.

4. **Stopping**
   - To stop the repeated loop, press `Ctrl+C`. The `medios.py` script ensures workers are cancelled and DB pool closed gracefully.

Directory Structure
-------------------
```
medios/
├── CloudflareBypasser.py
├── config.py
├── database.py
├── LoginCookieModule.py
├── medios.py
├── medios_iki.py
├── medios_uc.py
├── proxy_manager.py
├── telegram_notifier.py
├── utilities.py
├── medios_image_utils.py
├── medios.env
└── cache_previews/       # automatically created upon first run
```

Development & Contribution
--------------------------
- Feel free to refine selectors if MediaMarkt’s page structure changes.
- Adjust CloudflareBypasser to support future Turnstile updates.
- Enhance utility functions to cover more brands or edge-case URL patterns.
- Add unit tests for `utilities.py` name‑normalization logic.

License
-------
(If applicable, add your license details here.)
