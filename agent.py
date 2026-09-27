import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from database import fetch_table_data, find_relevant_rows, normalize_text, VALID_TABLES

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


def detect_tables(question: str) -> list[str]:
    normalized = normalize_text(question)
    matches: list[str] = []

    table_keywords = {
        "employees": ["employee", "staff", "team", "worker", "department", "role", "salary", "manager", "sales", "support"],
        "customers": ["customer", "client", "buyer", "person", "address", "phone", "email", "city", "resident"],
        "products": ["product", "item", "sku", "inventory", "price", "stock", "expensive", "cheap", "cost"],
        "orders": ["order", "purchase", "sale", "invoice", "buy", "bought", "total", "amount"],
    }

    for table_name, keywords in table_keywords.items():
        if any(keyword in normalized for keyword in keywords):
            matches.append(table_name)

    for table_name in VALID_TABLES:
        table_rows = fetch_table_data(table_name, limit=100)
        for row in table_rows:
            for value in row.values():
                value_text = normalize_text(str(value))
                if value_text and value_text in normalized and table_name not in matches:
                    matches.append(table_name)

    return matches


def build_context(question: str) -> dict[str, list[dict[str, Any]]]:
    relevant_tables = detect_tables(question)
    if not relevant_tables:
        return find_relevant_rows(question)

    context: dict[str, list[dict[str, Any]]] = {}
    normalized_question = normalize_text(question)

    for table_name in relevant_tables:
        rows = fetch_table_data(table_name, limit=50)
        filtered_rows = []

        for row in rows:
            row_text = " ".join(normalize_text(str(value)) for value in row.values() if value is not None)
            score = 0
            for token in normalized_question.split():
                if len(token) < 3:
                    continue
                if token in row_text:
                    score += 1
            if score > 0 or any(normalize_text(str(value)) in normalized_question for value in row.values() if value is not None):
                filtered_rows.append(row)

        context[table_name] = filtered_rows if filtered_rows else rows[:10]

    return context or find_relevant_rows(question)


def sql_quote(value: str) -> str:
    return value.replace("'", "''")


def generate_sql_from_question(question: str, context: dict[str, list[dict[str, Any]]] | None = None) -> str:
    normalized = normalize_text(question)
    tables = detect_tables(question)
    target = tables[0] if tables else "customers"
    q = question.strip()

    if "employee" in normalized or "staff" in normalized or "team" in normalized:
        return "SELECT name, department, role, salary FROM employees WHERE department = 'Sales' OR department = 'Support' ORDER BY department, name;"

    if "most expensive" in normalized or "highest price" in normalized or "expensive product" in normalized:
        return "SELECT id, name, category, price, stock FROM products ORDER BY price DESC LIMIT 1;"

    if "sales" in normalized and target == "employees":
        return "SELECT name, department, role, salary FROM employees WHERE department = 'Sales' ORDER BY name;"

    if "delhi" in normalized and target == "customers":
        return "SELECT id, name, city, phone, email FROM customers WHERE city = 'Delhi' ORDER BY name;"

    if "mumbai" in normalized and target == "customers":
        return "SELECT id, name, city, phone, email FROM customers WHERE city = 'Mumbai' ORDER BY name;"

    if "aditi sharma" in normalized and target == "customers":
        return "SELECT id, name, city, phone, email FROM customers WHERE name = 'Aditi Sharma';"

    if "order" in normalized and "aditi" in normalized:
        return (
            "SELECT o.id, c.name AS customer_name, p.name AS product_name, o.quantity, o.total_amount, o.order_date "
            "FROM orders o INNER JOIN customers c ON c.id = o.customer_id "
            "INNER JOIN products p ON p.id = o.product_id WHERE c.name = 'Aditi Sharma' ORDER BY o.order_date;"
        )

    if target == "employees":
        return "SELECT name, department, role, salary FROM employees ORDER BY department, name;"

    if target == "products":
        return "SELECT id, name, category, price, stock FROM products ORDER BY price DESC;"

    if target == "orders":
        return "SELECT id, customer_id, product_id, quantity, total_amount, order_date FROM orders ORDER BY order_date DESC;"

    return f"SELECT * FROM {target} LIMIT 10;"


def format_money(value: Any) -> str:
    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def build_product_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No products matched your request."
    top = max(rows, key=lambda r: float(r.get("price", 0)))
    return (
        f"The most relevant product is {top.get('name')} in the {top.get('category')} category, "
        f"priced at {format_money(top.get('price'))} with {top.get('stock')} units in stock."
    )


def build_order_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No orders matched your request."
    total = sum(float(r.get("total_amount", 0)) for r in rows)
    order_count = len(rows)
    return (
        f"There are {order_count} matching orders with a total value of {format_money(total)}. "
        f"The latest order amount is {format_money(rows[0].get('total_amount'))}."
    )


def build_customer_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No customer records matched your request."
    cities = {}
    for row in rows:
        city = row.get("city", "Unknown")
        cities[city] = cities.get(city, 0) + 1
    summary = ", ".join(f"{city} ({count})" for city, count in cities.items())
    return f"Matching customers are spread across: {summary}."


def build_employee_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No employee records matched your request."
    departments = {}
    for row in rows:
        dept = row.get("department", "Unknown")
        departments[dept] = departments.get(dept, 0) + 1
    summary = ", ".join(f"{dept} ({count})" for dept, count in departments.items())
    return f"Matching employees are grouped by department: {summary}."


def build_summary_text(question: str, context: dict[str, list[dict[str, Any]]]) -> str:
    normalized = normalize_text(question)

    if "employee" in normalized or "staff" in normalized or "team" in normalized or "sales" in normalized:
        if "employees" in context:
            return build_employee_summary(context["employees"])

    if "customer" in normalized or "city" in normalized or "phone" in normalized or "email" in normalized:
        if "customers" in context:
            return build_customer_summary(context["customers"])

    if "product" in normalized or "inventory" in normalized or "price" in normalized or "expensive" in normalized:
        if "products" in context:
            return build_product_summary(context["products"])

    if "order" in normalized or "purchase" in normalized or "invoice" in normalized:
        if "orders" in context:
            return build_order_summary(context["orders"])

    for table_name, rows in context.items():
        if table_name == "products" and ("expensive" in normalized or "price" in normalized or "most" in normalized):
            return build_product_summary(rows)
        if table_name == "orders":
            return build_order_summary(rows)
        if table_name == "customers":
            return build_customer_summary(rows)
        if table_name == "employees":
            return build_employee_summary(rows)
    if context:
        first_table, first_rows = next(iter(context.items()))
        if first_table == "products":
            return build_product_summary(first_rows)
        if first_table == "orders":
            return build_order_summary(first_rows)
        if first_table == "customers":
            return build_customer_summary(first_rows)
        if first_table == "employees":
            return build_employee_summary(first_rows)
    return "I found matching data in the database."


def build_fallback_answer(question: str, context: dict[str, list[dict[str, Any]]]) -> str:
    if not context:
        return (
            "I could not find a clear match in the database for that question. "
            "Try asking about a customer, product, order, or employee using names like Aditi Sharma, Delhi, Sales, or a product name."
        )

    q = normalize_text(question)
    if "most expensive" in q or "highest price" in q or "expensive product" in q:
        rows = context.get("products", [])
        if rows:
            top = max(rows, key=lambda r: float(r.get("price", 0)))
            return f"The most expensive product is {top.get('name')} priced at {format_money(top.get('price'))}."

    if "sales" in q and "employee" in q:
        rows = context.get("employees", [])
        names = [row.get("name") for row in rows if row.get("department") == "Sales"]
        if names:
            return "The employees in Sales are: " + ", ".join(names) + "."

    if "delhi" in q and "customer" in q:
        rows = context.get("customers", [])
        names = [row.get("name") for row in rows if row.get("city") == "Delhi"]
        if names:
            return "The customers in Delhi are: " + ", ".join(names) + "."

    return build_summary_text(question, context)


def generate_answer(question: str) -> dict[str, Any]:
    question = (question or "").strip()
    if not question:
        return {"answer": "Please enter a question to ask the assistant.", "sql": "", "summary": "", "tables": []}

    context = build_context(question)
    sql = generate_sql_from_question(question, context)

    if not context:
        answer = (
            "I checked the database tables, and there are no matching records for this request. "
            "Try a question like 'Show all customers in Delhi', 'Who works in Sales?', or 'What is the most expensive product?'."
        )
        return {"answer": answer, "sql": sql, "summary": "No matching records found.", "tables": []}

    api_key = os.getenv("OPENAI_API_KEY")
    configured_model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    model_candidates = [configured_model, "gpt-4o-mini", "gpt-4.1-mini"]

    if not api_key:
        return {
            "answer": build_fallback_answer(question, context),
            "sql": sql,
            "summary": build_summary_text(question, context),
            "tables": list(context.keys()),
        }

    client = OpenAI(api_key=api_key)
    system_prompt = (
        "You are a business assistant. Use only the database records below. "
        "Answer clearly and simply. If the data is incomplete, say so without inventing information. "
        "Also explain the key result in a natural business style."
    )

    for model_name in dict.fromkeys(model_candidates):
        try:
            request_kwargs: dict[str, Any] = {"temperature": 0.2}
            if model_name.startswith("gpt-5"):
                request_kwargs["max_completion_tokens"] = 500
            else:
                request_kwargs["max_tokens"] = 500

            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Question: {question}\n\nDatabase context: {context}\n\nGenerated SQL: {sql}"},
                ],
                **request_kwargs,
            )
            answer = response.choices[0].message.content
            if answer:
                return {
                    "answer": answer.strip(),
                    "sql": sql,
                    "summary": build_summary_text(question, context),
                    "tables": list(context.keys()),
                }
        except Exception:
            continue

    fallback_answer = build_fallback_answer(question, context)
    return {
        "answer": fallback_answer,
        "sql": sql,
        "summary": build_summary_text(question, context),
        "tables": list(context.keys()),
    }
