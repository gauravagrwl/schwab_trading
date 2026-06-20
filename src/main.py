import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from requests import RequestException, HTTPError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from src import logger, TOKEN_PATH
from src.schwab_order import Order, place_schwab_order, get_account_balance

# Redirect Uvicorn logs to use the same handlers
uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.handlers = logger.handlers  # use the same console + file handlers
uvicorn_logger.setLevel(logging.DEBUG)


# ----------------- Lifespan (Startup / Shutdown) -----------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the background task
    print("Starting up...")
    try:
        if not os.path.exists(TOKEN_PATH):
            os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        yield
    except Exception as e:
        logger.error(f"Failed to initialize Schwab client: {e}")


app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    swagger_ui_parameters={"syntaxHighlight": {"theme": "obsidian"}},
)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.debug(f"Request: {request.method} {request.url}")
        response = await call_next(request)
        logger.debug(f"Response status: {response.status_code}")
        return response


# ----------------- Exception Handlers -----------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(f"HTTP exception: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch all unhandled exceptions
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


@app.exception_handler(RequestException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(f"HTTP exception: {exc}")
    if isinstance(exc, HTTPError):
        logger.error(exc)
        return JSONResponse(
            status_code=exc.response.status_code, content=json.loads(exc.response.text)
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handle FastAPI / Starlette HTTP exceptions
    """
    logger.warning(f"HTTP exception: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# Custom Swagger page using our CSS
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Dark Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist/swagger-ui-bundle.js",
    )


# ---------------- Root endpoint ----------------


@app.get("/", tags=["Root"])
def read_root():
    return RedirectResponse(url="/docs")

# ---------------- Place Order ----------------
@app.post("/account_balance", status_code=202)
async def account_balance():
    # This will now work!
    account = get_account_balance()
    current_balance = account.get("balance")
    account_id = account.get("securitiesAccount").get("accountNumber")

    return {"status": "Authorized", "id": account_id, "balance": current_balance}

# ---------------- Place Order ----------------
@app.post("/place_two_leg_order", tags=["Schwab Order"])
async def place_two_leg_order_schwab(order: Order):
    if not order.symbol:
        return {"message": "No symbol provided."}
    else:
        return place_schwab_order(order)
