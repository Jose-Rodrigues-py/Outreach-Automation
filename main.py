from fastapi import FastAPI
from app.api.routes import router as clients_router
from app.api.web import router as web_router

app = FastAPI(title="Client Outreach Dashboard")

app.include_router(clients_router, prefix="/api")
app.include_router(web_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)