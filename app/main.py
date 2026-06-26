from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api_routes.vehicles import router
from app.config import APP_HOST, APP_PORT
from app.utils.logging_config import configure_logging

logger = configure_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API started")
    yield
    logger.info("API shutting down")


app = FastAPI(lifespan=lifespan)
app.include_router(router, prefix="/vehicles", tags=["vehicles"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)