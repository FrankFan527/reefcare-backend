from fastapi import FastAPI

app = FastAPI(
    title="ReefCare MY API",
    description="Backend API for ReefCare MY",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "message": "ReefCare MY backend is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }