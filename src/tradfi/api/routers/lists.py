"""List management endpoints."""

from fastapi import APIRouter, HTTPException

from tradfi.api.schemas import (
    AddTickerSchema,
    CategorySchema,
    CreateCategorySchema,
    CreateListSchema,
    ListItemSchema,
    ListNoteSchema,
    MessageSchema,
    SavedListSchema,
)
from tradfi.utils.cache import (
    add_list_to_category,
    add_to_saved_list,
    create_category,
    delete_category,
    delete_saved_list,
    get_all_item_notes,
    get_saved_list,
    list_categories,
    list_saved_lists,
    remove_from_saved_list,
    remove_list_from_category,
    save_list,
    set_item_note,
)

router = APIRouter(prefix="/lists", tags=["lists"])


@router.get("", response_model=list[str])
async def get_lists():
    """Get all saved list names."""
    lists = list_saved_lists()
    return [lst["name"] for lst in lists]


@router.post("", response_model=MessageSchema)
async def create_list(request: CreateListSchema):
    """Create a new stock list."""
    save_list(request.name, request.tickers)
    return MessageSchema(message=f"List '{request.name}' created")


@router.get("/{name}", response_model=SavedListSchema)
async def get_list(name: str):
    """Get a saved list by name with all items and notes."""
    tickers = get_saved_list(name)
    if tickers is None:
        raise HTTPException(status_code=404, detail=f"List '{name}' not found")

    # Get notes for all items and convert list to dict keyed by ticker
    notes_list = get_all_item_notes(name)
    notes = {note["ticker"]: note for note in notes_list}
    items = []
    for ticker in tickers:
        note = notes.get(ticker, {})
        items.append(
            ListItemSchema(
                ticker=ticker,
                notes=note.get("notes"),
                thesis=note.get("thesis"),
                entry_price=note.get("entry_price"),
                target_price=note.get("target_price"),
            )
        )

    return SavedListSchema(name=name, tickers=tickers, items=items)


@router.delete("/{name}", response_model=MessageSchema)
async def delete_list(name: str):
    """Delete a saved list."""
    if get_saved_list(name) is None:
        raise HTTPException(status_code=404, detail=f"List '{name}' not found")
    delete_saved_list(name)
    return MessageSchema(message=f"List '{name}' deleted")


@router.post("/{name}/items", response_model=MessageSchema)
async def add_to_list(name: str, request: AddTickerSchema):
    """Add a ticker to a list."""
    if get_saved_list(name) is None:
        raise HTTPException(status_code=404, detail=f"List '{name}' not found")
    add_to_saved_list(name, request.ticker.upper())
    return MessageSchema(message=f"{request.ticker.upper()} added to '{name}'")


@router.delete("/{name}/items/{ticker}", response_model=MessageSchema)
async def remove_from_list(name: str, ticker: str):
    """Remove a ticker from a list."""
    if get_saved_list(name) is None:
        raise HTTPException(status_code=404, detail=f"List '{name}' not found")
    remove_from_saved_list(name, ticker.upper())
    return MessageSchema(message=f"{ticker.upper()} removed from '{name}'")


@router.put("/{name}/items/{ticker}/notes", response_model=MessageSchema)
async def update_item_notes(name: str, ticker: str, request: ListNoteSchema):
    """Update notes for a list item."""
    if get_saved_list(name) is None:
        raise HTTPException(status_code=404, detail=f"List '{name}' not found")
    set_item_note(
        name,
        ticker.upper(),
        notes=request.notes,
        thesis=request.thesis,
        entry_price=request.entry_price,
        target_price=request.target_price,
    )
    return MessageSchema(message=f"Notes updated for {ticker.upper()} in '{name}'")


# Category endpoints


@router.get("/categories", response_model=list[CategorySchema])
async def get_categories():
    """Get all categories."""
    categories = list_categories()
    return [CategorySchema(id=cat["id"], name=cat["name"], icon=cat.get("icon")) for cat in categories]


@router.post("/categories", response_model=MessageSchema)
async def create_new_category(request: CreateCategorySchema):
    """Create a new category."""
    create_category(request.name, request.icon)
    return MessageSchema(message=f"Category '{request.name}' created")


@router.delete("/categories/{category_id}", response_model=MessageSchema)
async def delete_existing_category(category_id: int):
    """Delete a category."""
    delete_category(category_id)
    return MessageSchema(message="Category deleted")


@router.post("/categories/{category_id}/lists/{list_name}", response_model=MessageSchema)
async def add_list_to_cat(category_id: int, list_name: str):
    """Add a list to a category."""
    if get_saved_list(list_name) is None:
        raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")
    add_list_to_category(list_name, category_id)
    return MessageSchema(message=f"List '{list_name}' added to category")


@router.delete(
    "/categories/{category_id}/lists/{list_name}", response_model=MessageSchema
)
async def remove_list_from_cat(category_id: int, list_name: str):
    """Remove a list from a category."""
    remove_list_from_category(list_name, category_id)
    return MessageSchema(message=f"List '{list_name}' removed from category")
