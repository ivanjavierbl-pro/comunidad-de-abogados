"""Servidor FastAPI que expone el Asistente de Investigación Jurídica al frontend.

Arranque:
    cd backend
    uvicorn server:app --reload

Endpoints:
    POST /api/research         -> respuesta completa en JSON
    POST /api/research/stream  -> respuesta en streaming (Server-Sent Events)
"""

from __future__ import annotations

import json
from dataclasses import asdict

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from xix_agents.legal_research_agent import LegalResearchAgent, _require_api_key

load_dotenv()
_require_api_key()

app = FastAPI(title="XIX Estudio Jurídico — Agentes")

# Permitir que el sitio estático (index.html) consuma la API desde el navegador.
# En producción, restringe allow_origins a tu dominio real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

agent = LegalResearchAgent()


class ResearchRequest(BaseModel):
    query: str


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/research")
def research(req: ResearchRequest) -> dict:
    """Devuelve la respuesta completa con sus citas en un solo JSON."""
    result = agent.research(req.query)
    return {
        "answer": result.answer,
        "citations": [asdict(c) for c in result.citations],
        "searches": result.searches,
    }


@app.post("/api/research/stream")
def research_stream(req: ResearchRequest) -> StreamingResponse:
    """Transmite la respuesta token por token vía Server-Sent Events (SSE)."""

    def event_stream():
        for event in agent.stream_events(req.query):
            if event["type"] == "text":
                yield _sse({"type": "text", "text": event["text"]})
            elif event["type"] == "search_start":
                yield _sse({"type": "search"})
            elif event["type"] == "done":
                result = event["result"]
                yield _sse(
                    {
                        "type": "done",
                        "citations": [asdict(c) for c in result.citations],
                        "searches": result.searches,
                    }
                )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
