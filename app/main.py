"""AgentResolve API entry point."""

from fastapi import FastAPI
from api.routes import router

app = FastAPI(
    title="AgentResolve Forensic Engine API",
    description="Evidence-first transaction forensics for AI-agent commerce.",
    version="2.3.0",
)
app.include_router(router)


@app.get("/")
def root():
    return {"message":"AgentResolve Forensic Engine API","docs":"/docs","health":"/health","version":"2.3.0"}
