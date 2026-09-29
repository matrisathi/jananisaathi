from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import auth, people, pregnancies
from app.core.config import settings

app = FastAPI(title="MatriSathi API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_allowed_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", settings.csrf_header_name],
)

app.include_router(auth.router)
app.include_router(people.router)
app.include_router(pregnancies.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
