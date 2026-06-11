import sqlite3
from pathlib import Path
import json
from fastmcp import FastMCP

mcp=FastMCP(name="expense_tracker_server")
DB_PATH = Path(__file__).resolve().with_name("expense2.db")

def init_db():
    conn=sqlite3.connect(DB_PATH)
    cur=conn.cursor()

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
        row[1] for row in cur.execute("PRAGMA table_info(expenses)").fetchall()
    }
    if "category" not in columns:
        cur.execute(
            """
            ALTER TABLE expenses
            ADD COLUMN category TEXT NOT NULL DEFAULT 'uncategorized'
            """
        )

    conn.commit()
    conn.close()


@mcp.tool
def add_expense(item_name:str,date:str,price:float,category:str)->str:
    ''''this tool helps the user to add a expense in the expenses table of the expense database'''
    conn=sqlite3.connect(DB_PATH)
    cur=conn.cursor()
    cur.execute('''
            INSERT INTO expenses(date,item_name,price,category)
                VALUES (?,?,?,?)''',
            (date,item_name,price,category))
    conn.commit()
    conn.close()
    return f"{item_name} with price: {price} is added"

@mcp.tool
def get_all_expenses():
    '''this tool helps the user to get all the expenses'''
    conn=sqlite3.connect(DB_PATH)
    cur=conn.cursor()
    cur.execute('''SELECT * 
                FROM expenses''')
    result=cur.fetchall()
    conn.close()
    return result

@mcp.tool
def get_expenses_in_date_range(start_date,end_date):
    '''this tool helps the user to get all the expenses from start_date to end_date'''
    conn=sqlite3.connect(DB_PATH)
    cur=conn.cursor()
    cur.execute('''SELECT *
                FROM expenses
                WHERE date>= ? AND date<= ?
                ORDER BY id ASC''',(start_date,end_date))
    result=cur.fetchall()
    conn.close()
    return result

@mcp.tool
def summarize(start_date,end_date,category):
    """
    Summarize expenses between start_date and end_date.
    start_date and end_date are inclusive.

    If category is provided, summarize only that category.
    If category is not provided, summarize expenses across all categories.
    """
    conn=sqlite3.connect(DB_PATH)
    cur=conn.cursor()
    if category!=None:
        cur.execute('''SELECT * 
                    FROM expenses
                    WHERE date>= ? AND date<= ?
                    GROUP BY category
                    HAVING category= ?
                    ORDER BY category ASC''',(start_date,end_date,category))
        result=cur.fetchall()
        conn.close()
        return result

@mcp.resource(uri="docs://categories",
            name="CategoriesList",
            description="Returns a JSON list of all available expense categories such as clothing, food, education, travel, and electronics.",
            mime_type="application/json")
def get_categories():
    '''use this function to get the list of categories '''
    categories=["clothing","food","education","travel","electronics"]
    return json.dumps(categories)

if __name__=="__main__":
    init_db()
    mcp.run(transport="streamable-http",host="0.0.0.0",port=8000)
