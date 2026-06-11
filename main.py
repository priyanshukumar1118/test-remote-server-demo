import aiosqlite
from pathlib import Path
import json
from fastmcp import FastMCP

DB_PATH = Path("expense2.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("""
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
            for row in await (
                await conn.execute("PRAGMA table_info(expenses)")
            ).fetchall()
        }

        if "category" not in columns:
            await conn.execute("""
                ALTER TABLE expenses
                ADD COLUMN category TEXT NOT NULL
                DEFAULT 'uncategorized'
            """)

        await conn.commit()


mcp = FastMCP(name="expense_tracker_server")


@mcp.tool
async def add_expense(
    item_name: str,
    date: str,
    price: float,
    category: str
) -> str:
    """
    Add an expense to the database.
    """
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            """
            INSERT INTO expenses(date,item_name,price,category)
            VALUES (?,?,?,?)
            """,
            (date, item_name, price, category),
        )
        await conn.commit()

    return f"{item_name} with price {price} added successfully."


@mcp.tool
async def get_all_expenses():
    """
    Get all expenses.
    """
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("""
            SELECT *
            FROM expenses
            ORDER BY id ASC
        """) as cursor:
            return await cursor.fetchall()


@mcp.tool
async def get_expenses_in_date_range(
    start_date: str,
    end_date: str
):
    """
    Get expenses between start_date and end_date.
    """
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute(
            """
            SELECT *
            FROM expenses
            WHERE date >= ?
            AND date <= ?
            ORDER BY id ASC
            """,
            (start_date, end_date),
        ) as cursor:
            return await cursor.fetchall()


@mcp.tool
async def summarize(
    start_date: str,
    end_date: str,
    category: str | None = None
):
    """
    Summarize expenses between dates.

    If category is provided,
    only summarize that category.
    """
    async with aiosqlite.connect(DB_PATH) as conn:
        if category:
            async with conn.execute(
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
            ) as cursor:
                return await cursor.fetchall()
        else:
            async with conn.execute(
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
            ) as cursor:
                return await cursor.fetchall()


@mcp.resource(
    uri="docs://categories",
    name="CategoriesList",
    description=(
        "Returns a JSON list of all available "
        "expense categories."
    ),
    mime_type="application/json",
)
async def get_categories():
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
    import asyncio

    async def main():
        await init_db()
        await mcp.run_async(
            transport="streamable-http",
            host="0.0.0.0",
            port=8000,
        )

    asyncio.run(main())