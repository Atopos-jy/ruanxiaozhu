from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_database
from routers import auth, chat


app = FastAPI(title="软小助 AI 管家 API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_database()


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(chat.router)
