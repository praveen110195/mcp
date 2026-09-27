import os

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
mcp = FastMCP("ai-data-mcp")


@mcp.tool()
def fetch_database_data(table: str, limit: int = 10) -> dict:
    """Fetch rows from the FastAPI database table."""
    response = httpx.get(
        f"{API_BASE_URL}/api/data/{table.lower()}",
        params={"limit": limit},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
def generate_sql_for_question(question: str) -> dict:
    """Translate a natural-language question into a likely SQL query for the sample database."""
    response = httpx.post(
        f"{API_BASE_URL}/api/sql",
        json={"question": question},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
def ask_database_question(question: str) -> dict:
    """Send a natural-language question to the API and return the model answer plus SQL."""
    response = httpx.post(
        f"{API_BASE_URL}/api/ask",
        json={"question": question},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    mcp.run(transport="stdio")
