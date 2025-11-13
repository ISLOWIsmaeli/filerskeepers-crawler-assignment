from fastapi import FastAPI
from db.books import BookSelector
app = FastAPI()

@app.get("/GET/books")
async def get_books(skip: int = 0, limit: int = 20):
    selector = BookSelector()
    books = await selector.get_books(
        category="", max_price=0, min_price=0, skip=skip, limit=limit
    )
    return books

@app.get("/GET/books/{book_id}")
async def get_book(book_id: str):
    selector = BookSelector()
    book = await selector.get_book_by_id(book_id)
    if book is None:
        return {"error": "Book not found"}
    return book

@app.get("/GET/changes")
async def get_changes(skip: int = 0, limit: int = 20):
    selector = BookSelector()
    changes = await selector.get_recent_changes(skip=skip, limit=limit)
    if not changes:
        return {"message": "No changes found", "changes": []}
    return {"total": len(changes), "changes": changes}