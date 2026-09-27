import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from agent import generate_answer, generate_sql_from_question
from database import VALID_TABLES, fetch_table_data

app = FastAPI(title="AI MCP REST API", version="1.0.0")


class AskRequest(BaseModel):
    question: str


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "tables": VALID_TABLES}


@app.get("/api/tables")
def list_tables() -> dict[str, Any]:
    return {"tables": VALID_TABLES}


@app.get("/api/data/{table_name}")
def get_table_data(
    table_name: str,
    limit: int = Query(default=10, ge=1, le=100),
) -> dict[str, Any]:
    table_name = table_name.lower()
    if table_name not in VALID_TABLES:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    rows = fetch_table_data(table_name, limit=limit)
    return {"table": table_name, "count": len(rows), "rows": rows}


@app.get("/api/search")
def search_table(
    table: str,
    field: str,
    value: str,
    limit: int = Query(default=10, ge=1, le=100),
) -> dict[str, Any]:
    table = table.lower()
    if table not in VALID_TABLES:
        raise HTTPException(status_code=404, detail=f"Table '{table}' not found")

    rows = fetch_table_data(table, limit=limit, filters={field: value})
    return {"table": table, "count": len(rows), "rows": rows}


@app.post("/api/sql")
def build_sql(payload: AskRequest) -> dict[str, Any]:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    sql = generate_sql_from_question(question)
    return {"question": question, "sql": sql}


@app.post("/api/ask")
def ask_question(payload: AskRequest) -> dict[str, Any]:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    result = generate_answer(question)
    return {"question": question, **result}
