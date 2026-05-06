import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.middleware.sessions import SessionMiddleware

from app.core.exceptions import validation_exception_handler, generic_exception_handler
from app.api.auth import router as auth_router
from app.api.evaluations import router as evaluations_router
from app.config import get_settings

settings = get_settings()


def _configure_app_logging() -> None:
    """
    Ensure every logger under ``app.*`` and ``eval.*`` writes to stdout.

    Uvicorn adds handlers only to its own ``uvicorn.*`` loggers; app-level
    loggers would otherwise be silently discarded unless the root logger has
    a handler.  We add one here (idempotently) and pin the app namespaces to
    DEBUG so service-level logs are fully visible in the container terminal.
    """
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(fmt)

    root = logging.getLogger()
    # Only add if there is no stdout StreamHandler already
    has_stdout = any(
        isinstance(h, logging.StreamHandler)
        and getattr(h, "stream", None) is sys.stdout
        for h in root.handlers
    )
    if not has_stdout:
        root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    # Pin app namespaces to DEBUG
    logging.getLogger("app").setLevel(logging.DEBUG)
    logging.getLogger("eval").setLevel(logging.DEBUG)

    # Quieten noisy third-party libraries
    for lib in (
        "azure", "urllib3", "httpx", "httpcore",
        "boto3", "botocore", "s3transfer",
        "openai", "deepgram", "asyncio", "multipart",
    ):
        logging.getLogger(lib).setLevel(logging.WARNING)


_configure_app_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="CEFR Oral Expression Evaluator",
    description="Evaluates oral French proficiency and produces CEFR level assessments.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(evaluations_router, prefix="/api/cefr-evaluator", tags=["Evaluations"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
