from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine

from app.auth.routes import router as auth_router
from app.hr.routes import router as hr_router
from app.user.routes import router as user_router
from app.chat.routes import router as chat_router


app = FastAPI(title="AI HR Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(hr_router)
app.include_router(user_router)
app.include_router(chat_router)


@app.get("/")
def root():
    return {"message": "AI HR Bot Running"}
