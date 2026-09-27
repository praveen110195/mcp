# AI MCP Application

This project includes a database-backed AI workflow built with:

- FastAPI REST API for database access
- MCP server that calls the API as a tool
- Streamlit UI for user prompts
- OpenAI model integration using the configured model name `gpt-5.6-luna`

## Project structure

- `database.py` — SQLite database with sample tables and seed data
- `api_app.py` — REST API that exposes table data and chat-answer route
- `mcp_server.py` — MCP tool server that calls the API
- `streamlit_app.py` — user interface for asking questions
- `agent.py` — prompt-to-data-to-LLM logic

## Database tables

- customers
- products
- orders
- employees

## Example prompt inputs and expected responses

### Input 1

`Show all customers in Delhi`

Expected response:

- A list of customers living in Delhi
- Their names, contact details, and email addresses

### Input 2

`What is the most expensive product?`

Expected response:

- The product name and price
- A short explanation based on database data

### Input 3

`Which employees work in Sales?`

Expected response:

- Names of Sales team employees
- Their role and department information

### Input 4

`List all orders placed by Aditi Sharma`

Expected response:

- Orders linked to that customer
- Product information and total amounts

## How to run

1. Create a virtual environment and install dependencies:
   `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and add your OpenAI API key.
3. Start the API server:
   `uvicorn api_app:app --host 0.0.0.0 --port 8000`
4. Start the Streamlit app:
   `streamlit run streamlit_app.py --server.port 8501`
5. Optional: run the MCP server:
   `python mcp_server.py`

## Notes

If your OpenAI account uses a different deployment name than `gpt-5.6-luna`, update `OPENAI_MODEL` in the environment before running the app.
