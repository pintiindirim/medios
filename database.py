from dependencies import *
from logconfig import logger, flush_logs  
import time
import asyncio
import aiomysql
from config import DATABASE_CONFIG
warnings.filterwarnings("ignore", message=".*already exists")
warnings.filterwarnings("ignore", message=".*Can't create database .*; database exists")
async def create_pool():
    try:
        logger.info("create_pool: Creating database connection pool...")
        flush_logs()
        pool = await aiomysql.create_pool(**DATABASE_CONFIG)
        logger.info("create_pool: Connection pool created successfully.")
        flush_logs()
        return pool
    except Exception as e:
        logger.error("create_pool: Error occurred: %s", e)
        flush_logs()
        raise
async def create_database():
    try:
        db_name = DATABASE_CONFIG.get('database', 'medios')
        if not db_name:
            raise KeyError("DATABASE_CONFIG is missing 'database' key or it is empty.")
        logger.info("create_database: Checking database (%s)...", db_name)
        flush_logs()
        conn = await aiomysql.connect(
            user=DATABASE_CONFIG['user'],
            password=DATABASE_CONFIG['password'],
            host=DATABASE_CONFIG['host'],
            port=DATABASE_CONFIG['port']
        )
        async with conn.cursor() as cur:
            await cur.execute("SHOW DATABASES LIKE %s", (db_name,))
            result = await cur.fetchone()
            if result:
                logger.info("create_database: Database '%s' already exists.", db_name)
            else:
                logger.info("create_database: Database '%s' does not exist, creating...", db_name)
                await cur.execute("CREATE DATABASE " + db_name)
                await conn.commit()
                logger.info("create_database: Database created successfully.")
        conn.close()
        flush_logs()
    except KeyError as ke:
        logger.error("create_database: Configuration error: %s", ke)
        flush_logs()
        raise
    except Exception as e:
        logger.error("create_database: Error occurred: %s", e)
        flush_logs()
async def create_table(pool):
    try:
        logger.info("create_table: Creating 'products' table...")
        flush_logs()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS products (
                        product_link VARCHAR(500) UNIQUE,
                        product_name VARCHAR(255),
                        product_price REAL,
                        first_seen_date TEXT,
                        last_update_date TEXT,
                        INDEX idx_product_link (product_link),
                        INDEX idx_product_name (product_name)
                    )
                """)
                await conn.commit()
        logger.info("create_table: 'products' table created successfully.")
        flush_logs()
    except Exception as e:
        logger.error("create_table: Error occurred: %s", e)
        flush_logs()
async def db_bulk_worker(pool, db_update_queue, flush_interval=1.0, batch_size=100):
    logger.info("db_bulk_worker: Database bulk worker started.")
    flush_logs()
    while True:
        batch = []
        try:
            item = await db_update_queue.get()
            batch.append(item)
            start = time.time()
            while len(batch) < batch_size and (time.time() - start) < flush_interval:
                try:
                    item = db_update_queue.get_nowait()
                    batch.append(item)
                except asyncio.QueueEmpty:
                    await asyncio.sleep(0.01)
            logger.info("db_bulk_worker: Batch size collected: %d", len(batch))
            flush_logs()
            inserts = [item for item in batch if not item.get('is_update', False)]
            updates = [item for item in batch if item.get('is_update', False)]
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    if inserts:
                        logger.info("db_bulk_worker: Executing insert for %d records.", len(inserts))
                        flush_logs()
                        query = """
                        INSERT INTO products (product_link, product_name, product_price, first_seen_date, last_update_date)
                        VALUES (%s, %s, %s, %s, %s) AS new
                        ON DUPLICATE KEY UPDATE 
                            product_price = new.product_price,
                            last_update_date = new.last_update_date
                        """
                        data = [
                            (item['product_link'], item['product_name'], item['product_price'], item['now'], item['now'])
                            for item in inserts
                        ]
                        await cur.executemany(query, data)
                    if updates:
                        logger.info("db_bulk_worker: Executing update for %d records.", len(updates))
                        flush_logs()
                        query = "UPDATE products SET product_price = %s, last_update_date = %s WHERE product_link = %s"
                        data = [
                            (item['product_price'], item['now'], item['product_link'])
                            for item in updates
                        ]
                        await cur.executemany(query, data)
                    await conn.commit()
                    logger.info("db_bulk_worker: Batch operation completed.")
                    flush_logs()
        except Exception as e:
            logger.error("db_bulk_worker: Error occurred: %s", e)
            flush_logs()