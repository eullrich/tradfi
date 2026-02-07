"""Stock screening endpoints."""

from fastapi import APIRouter, HTTPException

from tradfi.api.converters import (
    schema_to_screen_criteria,
    screen_criteria_to_schema,
    stock_to_schema,
)
from tradfi.api.schemas import (
    PresetSchema,
    ScreenCriteriaSchema,
    ScreenRequestSchema,
    ScreenResultSchema,
    UniverseSchema,
)
from tradfi.core.data import fetch_stock
from tradfi.core.screener import (
    PRESET_SCREENS,
    get_preset_screen,
    list_available_universes,
    load_tickers,
    screen_stock,
)

router = APIRouter(prefix="/screening", tags=["screening"])


@router.get("/universes", response_model=list[UniverseSchema])
async def get_universes():
    """
    List all available stock universes.

    Returns universe name, description, and number of stocks.
    """
    universes = list_available_universes()
    return [
        UniverseSchema(name=name, description=desc, count=count)
        for name, (desc, count) in universes.items()
    ]


@router.get("/presets", response_model=list[PresetSchema])
async def get_presets():
    """
    List all available screening presets.

    Returns preset name and its criteria.
    """
    return [
        PresetSchema(name=name, criteria=screen_criteria_to_schema(criteria))
        for name, criteria in PRESET_SCREENS.items()
    ]


@router.get("/presets/{name}", response_model=PresetSchema)
async def get_preset(name: str):
    """Get a specific preset by name."""
    try:
        criteria = get_preset_screen(name)
        return PresetSchema(name=name, criteria=screen_criteria_to_schema(criteria))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/run", response_model=ScreenResultSchema)
async def run_screen(request: ScreenRequestSchema):
    """
    Run a stock screen with specified criteria.

    You can use a preset name OR provide custom criteria (or both to combine).
    """
    # Load tickers from universe
    try:
        tickers = load_tickers(request.universe)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Get screening criteria
    if request.preset:
        try:
            criteria = get_preset_screen(request.preset)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif request.criteria:
        criteria = schema_to_screen_criteria(request.criteria)
    else:
        # Default: basic value criteria
        criteria = schema_to_screen_criteria(ScreenCriteriaSchema(pe_max=20, pb_max=3, roe_min=5))

    # Screen stocks
    results = []
    for ticker in tickers:
        if len(results) >= request.limit:
            break

        stock = fetch_stock(ticker, use_cache=True)
        if stock is None:
            continue

        if screen_stock(stock, criteria):
            results.append(stock_to_schema(stock))

    return ScreenResultSchema(
        universe=request.universe,
        preset=request.preset,
        total_screened=len(tickers),
        matches=len(results),
        stocks=results,
    )
