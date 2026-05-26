import sqlite3


def init_db():
    conn   = sqlite3.connect("crosscart.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT,
            price        TEXT,
            app_name     TEXT,
            product_url  TEXT,
            timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("Database ready!")


def save_price(product_name, price, app_name, product_url):
    conn   = sqlite3.connect("crosscart.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO prices (product_name, price, app_name, product_url)
        VALUES (?, ?, ?, ?)
    """, (product_name, price, app_name, product_url))
    conn.commit()
    conn.close()


def get_prices(product_name):
    conn   = sqlite3.connect("crosscart.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT app_name, price, product_url
        FROM prices
        WHERE product_name LIKE ?
        ORDER BY timestamp DESC
        LIMIT 20
    """, ('%' + product_name + '%',))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_price_history(product_name):
    conn   = sqlite3.connect("crosscart.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT app_name, price, timestamp
        FROM prices
        WHERE product_name LIKE ?
        ORDER BY timestamp DESC
        LIMIT 50
    """, ('%' + product_name + '%',))
    rows = cursor.fetchall()
    conn.close()
    return rows


if __name__ == "__main__":
    init_db()