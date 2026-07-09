import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator


DB_PATH = os.path.join(os.path.dirname(__file__), "store.db")


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def search_products(query: str, max_price: float | None = None, is_organic: bool | None = None) -> list[dict]:
    sql = "SELECT id, name, category, price, description, is_organic FROM products WHERE 1=1"
    params: list = []

    if query:
        sql += " AND (name LIKE ? OR description LIKE ? OR category LIKE ?)"
        like = f"%{query}%"
        params.extend([like, like, like])

    if max_price is not None:
        sql += " AND price <= ?"
        params.append(max_price)

    if is_organic is not None:
        sql += " AND is_organic = ?"
        params.append(1 if is_organic else 0)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "name": row[1],
            "category": row[2],
            "price": row[3],
            "description": row[4],
            "is_organic": bool(row[5]),
        }
        for row in rows
    ]


def get_product_name_and_price(product_id: int) -> tuple[str, float] | None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, price FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()

    if not row:
        return None

    return row[0], row[1]


def create_order(product_id: int) -> int | None:
    product = get_product_name_and_price(product_id)
    if not product:
        return None

    name, price = product
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO orders (product_id, product_name, price) VALUES (?, ?, ?)",
            (product_id, name, price),
        )
        order_id = cursor.lastrowid
        conn.commit()

    return order_id