from agno.agent import Agent
#from agno.models.google import Gemini
from agno.models.groq import Groq
from agno.db.sqlite import SqliteDb
from .tools import create_book_tool, search_book_tool, my_loans_tool
from ..config import settings, BACKEND_DIR

#model = Gemini(id="gemini-flash-latest", api_key=settings.google_api_key)
model = Groq(id="openai/gpt-oss-120b", api_key=settings.groq_api_key)

db = SqliteDb(db_file=str(BACKEND_DIR / "agent_sessions.db"))

agent = Agent(
    model = model,
    db=db,
    add_history_to_context=True,
    num_history_runs=5,
    instructions="You are an AI librarian. Help users manage their personal library. When a user wants to add a book, use the create_book_tool, no need to ask for confirmation. When a user wants to search for a book, use the search_book_tool. If required information is missing, ask the user before calling the tool. Use my_loans_tool for current loans and due dates. Preserve the exact book links returned by tools in your replies so the reader can open the book card. Never invent book IDs or availability. For borrowing, returning, or deleting a book, provide its book link and ask the reader to use the action button and confirmation there; you cannot perform those actions yourself.",
    tools=[create_book_tool, search_book_tool, my_loans_tool]
)
