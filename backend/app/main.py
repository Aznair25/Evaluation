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
