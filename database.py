import os
import sqlite3
from typing import Any

DB_PATH = os.path.join(os.path.dirname(__file__), "app_data.db")
VALID_TABLES = ["customers", "products", "orders", "employees"]


def normalize_text(value: str) -> str:
    return " ".join(str(value).lower().replace("-", " ").replace("_", " ").split())


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            phone TEXT,
            email TEXT
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            order_date TEXT NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            role TEXT NOT NULL,
            salary REAL NOT NULL
        );
        """
    )

    customer_rows = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    if customer_rows == 0:
        conn.executemany(
            "INSERT INTO customers (name, city, phone, email) VALUES (?, ?, ?, ?)",
            [
                ("Aditi Sharma", "Delhi", "9876543210", "aditi@example.com"),
                ("Rahul Verma", "Mumbai", "9812345678", "rahul@example.com"),
                ("Sonia Nair", "Bengaluru", "9988776655", "sonia@example.com"),
                ("Vikram Singh", "Hyderabad", "9123456789", "vikram@example.com"),
                ("Neha Rao", "Delhi", "9345678901", "neha@example.com"),
            ],
        )

    product_rows = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if product_rows == 0:
        conn.executemany(
            "INSERT INTO products (name, category, price, stock) VALUES (?, ?, ?, ?)",
            [
                ("Laptop Pro 14", "Electronics", 95000.0, 20),
                ("Wireless Mouse", "Accessories", 1200.0, 100),
                ("Office Chair", "Furniture", 6500.0, 40),
                ("Smart Speaker", "Electronics", 7800.0, 60),
                ("Notebook Set", "Stationery", 450.0, 150),
            ],
        )

    order_rows = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    if order_rows == 0:
        conn.executemany(
            "INSERT INTO orders (customer_id, product_id, quantity, total_amount, order_date) VALUES (?, ?, ?, ?, ?)",
            [
                (1, 1, 1, 95000.0, "2026-09-01"),
                (1, 5, 3, 1350.0, "2026-09-03"),
                (2, 2, 2, 2400.0, "2026-09-04"),
                (3, 3, 1, 6500.0, "2026-09-06"),
                (5, 4, 2, 15600.0, "2026-09-08"),
                (4, 1, 1, 95000.0, "2026-09-10"),
            ],
        )

    employee_rows = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    if employee_rows == 0:
        conn.executemany(
            "INSERT INTO employees (name, department, role, salary) VALUES (?, ?, ?, ?)",
            [
                ("Meera Iyer", "Sales", "Sales Lead", 980000.0),
                ("Arjun Patel", "Support", "Customer Success", 760000.0),
                ("Priya Shah", "Engineering", "Product Engineer", 1200000.0),
                ("Karan Gupta", "Marketing", "Campaign Manager", 890000.0),
                ("Nisha Menon", "Sales", "Account Manager", 850000.0),
            ],
        )

    conn.commit()
    conn.close()


def all_table_names() -> list[str]:
    return VALID_TABLES.copy()


def fetch_table_data(table_name: str, limit: int = 10, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    table_name = table_name.lower().strip()
    if table_name not in VALID_TABLES:
        raise ValueError(f"Unsupported table: {table_name}")

    conn = get_connection()
    query = f"SELECT * FROM {table_name}"
    params: list[Any] = []

    if filters:
        clauses = []
        for key, value in filters.items():
            if value is None:
                continue
            clauses.append(f"{key} = ?")
            params.append(value)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)

    query += " LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def find_relevant_rows(question: str, limit: int = 25) -> dict[str, list[dict[str, Any]]]:
    normalized_question = normalize_text(question)
    matches: dict[str, list[dict[str, Any]]] = {}

    for table_name in VALID_TABLES:
        rows = fetch_table_data(table_name, limit=200)
        relevant: list[dict[str, Any]] = []

        for row in rows:
            row_text = " ".join(
                normalize_text(str(value))
                for value in row.values()
                if value is not None
            )
            score = 0
            for token in normalized_question.split():
                if len(token) < 3:
                    continue
                if token in row_text:
                    score += 3
            if score == 0:
                for key, value in row.items():
                    if value is None:
                        continue
                    label = normalize_text(str(value))
                    if label and label in normalized_question:
                        score += 5
            if score > 0:
                relevant.append(row)

        if relevant:
            matches[table_name] = relevant[:limit]

    if not matches:
        fallback = {}
        for table_name in VALID_TABLES:
            rows = fetch_table_data(table_name, limit=limit)
            if rows:
                fallback[table_name] = rows
        return fallback

    return matches
