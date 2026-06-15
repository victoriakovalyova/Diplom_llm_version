import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from llm_engine import LLMEngine

app = FastAPI(title="LLM Service")
llm_engine = None

class CorrectionRequest(BaseModel):
    rows: Dict[int, Dict[str, str]]

@app.on_event("startup")
async def startup():
    global llm_engine
    llm_engine = LLMEngine()

@app.post("/correct")
async def correct(request: CorrectionRequest):
    if not llm_engine:
        raise HTTPException(500, "LLM not ready")
    try:
        corrected = llm_engine.correct_table(request.rows)
        return {"status": "success", "corrected_rows": corrected}
    except Exception as e:
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8001)