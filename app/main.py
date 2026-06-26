from fastapi import FastAPI
from app.api_routes.vehicles import router
from app.config import APP_HOST, APP_PORT

app = FastAPI()

app.include_router(router, prefix="/vehicles", tags=["vehicles"])



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
    