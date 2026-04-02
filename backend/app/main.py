from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.infrastructure.database.config import init_db
from app.interfaces.api.routers import auth, gallery


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="RobertGate API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(gallery.router, prefix="/api/v1")


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    first_error = exc.errors()[0]
    return JSONResponse(
        content={"code": 2000, "data": None, "message": first_error.get("msg", "参数错误")},
    )


@app.get("/api/v1/health")
async def health():
    return {"code": 0, "data": {"status": "ok"}, "message": "ok"}
