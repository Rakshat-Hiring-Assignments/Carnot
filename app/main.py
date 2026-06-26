from fastapi import FastAPI
from app.api_routes.vehicles import router

app = FastAPI()

app.include_router(router, prefix="/vehicles", tags=["vehicles"])



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    