from fastapi import FastAPI

from app.api.endpoints import router

app = FastAPI(
    title="Cloud2BIM Service",
    description="A web service for converting 3D point cloud files into IFC BIM models",
    version="1.0.0",
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
