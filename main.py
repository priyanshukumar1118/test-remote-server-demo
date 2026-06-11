import sqlite3
from pathlib import Path
import json
from fastmcp import FastMCP

DB_PATH = Path("expense2.db")

def init_db():
    DB_PATH.touch(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            item_name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL
        )
    """)

    columns = {
        row[1]
        for row in cur.execute(
            "PRAGMA table_info(expenses)"
        ).fetchall()
    }

    if "category" not in columns:
        cur.execute("""
            ALTER TABLE expenses
            ADD COLUMN category TEXT NOT NULL
            DEFAULT 'uncategorized'
        """)

    conn.commit()
    conn.close()


def get_connection():
    init_db()
    return sqlite3.connect(DB_PATH)


# Initialize database on startup
init_db()

mcp = FastMCP(name="expense_tracker_server")


@mcp.tool
def add_expense(
    item_name: str,
    date: str,
    price: float,
    category: str
) -> str:
    """
    Add an expense to the database.
    """

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO expenses(date,item_name,price,category)
        VALUES (?,?,?,?)
        """,
        (date, item_name, price, category),
    )

    conn.commit()
    conn.close()

    return f"{item_name} with price {price} added successfully."


@mcp.tool
def get_all_expenses():
    """
    Get all expenses.
    """

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM expenses
        ORDER BY id ASC
    """)

    result = cur.fetchall()

    conn.close()

    return result


@mcp.tool
def get_expenses_in_date_range(
    start_date: str,
    end_date: str
):
    """
    Get expenses between start_date and end_date.
    """

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM expenses
        WHERE date >= ?
          AND date <= ?
        ORDER BY id ASC
        """,
        (start_date, end_date),
    )

    result = cur.fetchall()

    conn.close()

    return result


@mcp.tool
def summarize(
    start_date: str,
    end_date: str,
    category: str | None = None
):
    """
    Summarize expenses between dates.

    If category is provided,
    only summarize that category.
    """

    conn = get_connection()
    cur = conn.cursor()

    if category:
        cur.execute(
            """
            SELECT
                category,
                COUNT(*) as total_items,
                SUM(price) as total_spent
            FROM expenses
            WHERE date >= ?
              AND date <= ?
              AND category = ?
            GROUP BY category
            """,
            (start_date, end_date, category),
        )
    else:
        cur.execute(
            """
            SELECT
                category,
                COUNT(*) as total_items,
                SUM(price) as total_spent
            FROM expenses
            WHERE date >= ?
              AND date <= ?
            GROUP BY category
            ORDER BY category
            """,
            (start_date, end_date),
        )

    result = cur.fetchall()

    conn.close()

    return result


@mcp.resource(
    uri="docs://categories",
    name="CategoriesList",
    description=(
        "Returns a JSON list of all available "
        "expense categories."
    ),
    mime_type="application/json",
)
def get_categories():
    """
    Return supported categories.
    """

    categories = [
        "clothing",
        "food",
        "education",
        "travel",
        "electronics",
    ]

    return json.dumps(categories)


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
    )