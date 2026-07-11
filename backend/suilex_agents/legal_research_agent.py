"""Asistente de Investigación Jurídica de SUILEX.

Agente que responde consultas de derecho paraguayo usando Claude Opus 4.8 con la
herramienta de búsqueda web (con citas). Verifica en fuentes oficiales de la
República del Paraguay (BACN, Gaceta Oficial, Corte Suprema de Justicia, leyes
nacionales) y devuelve la respuesta junto con las fuentes citadas.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Iterator

import anthropic

from . import config


@dataclass
class Citation:
    """Una fuente citada por el agente durante la investigación."""

    title: str
    url: str
    cited_text: str = ""


@dataclass
class ResearchResult:
    """Resultado completo de una consulta de investigación jurídica."""

    answer: str
    citations: list[Citation] = field(default_factory=list)
    searches: list[str] = field(default_factory=list)
    stop_reason: str | None = None
    # Historial actualizado (para continuar la conversación en siguientes turnos).
    messages: list[dict[str, Any]] = field(default_factory=list)


class LegalResearchAgent:
    """Agente de investigación jurídica sobre derecho paraguayo.

    Uso básico::

        agent = LegalResearchAgent()
        resultado = agent.research("¿Qué plazos de prescripción establece el "
                                   "Código Civil paraguayo para la acción laboral?")
        print(resultado.answer)
        for cita in resultado.citations:
            print(cita.title, cita.url)
    """

    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        model: str = config.MODEL,
        max_tokens: int = config.MAX_TOKENS,
        max_search_uses: int = config.MAX_SEARCH_USES,
        system_prompt: str = config.SYSTEM_PROMPT,
    ) -> None:
        # El cliente resuelve la credencial desde ANTHROPIC_API_KEY (o un perfil
        # de `ant auth login`). No codifiques la clave en el código.
        self.client = client or anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens
        self.max_search_uses = max_search_uses
        self.system_prompt = system_prompt

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    def research(
        self, query: str, history: list[dict[str, Any]] | None = None
    ) -> ResearchResult:
        """Ejecuta la consulta completa y devuelve el resultado (bloqueante)."""
        result: ResearchResult | None = None
        for event in self.stream_events(query, history):
            if event["type"] == "done":
                result = event["result"]
        assert result is not None  # stream_events siempre emite un "done"
        return result

    def stream_events(
        self, query: str, history: list[dict[str, Any]] | None = None
    ) -> Iterator[dict[str, Any]]:
        """Ejecuta la consulta emitiendo eventos incrementales.

        Emite diccionarios con estos ``type``:
          - ``"thinking"``     -> {text}   fragmento del razonamiento (resumido)
          - ``"search_start"`` -> {}       el agente inició una búsqueda web
          - ``"text"``         -> {text}   fragmento de la respuesta final
          - ``"done"``         -> {result} ResearchResult completo (último evento)
        """
        messages = self._init_messages(query, history)

        answer_parts: list[str] = []
        citations: list[Citation] = []
        searches: list[str] = []
        stop_reason: str | None = None

        # Los tools del lado del servidor (búsqueda web) corren en un bucle en
        # Anthropic; si alcanza su límite interno de iteraciones devuelve
        # stop_reason == "pause_turn" y reenviamos para que continúe.
        for _ in range(config.MAX_CONTINUATIONS):
            with self.client.messages.stream(**self._request_params(messages)) as stream:
                for event in stream:
                    if event.type == "content_block_start":
                        block = event.content_block
                        if getattr(block, "type", None) == "server_tool_use":
                            yield {"type": "search_start"}
                    elif event.type == "content_block_delta":
                        delta = event.delta
                        if delta.type == "text_delta":
                            answer_parts.append(delta.text)
                            yield {"type": "text", "text": delta.text}
                        elif delta.type == "thinking_delta":
                            yield {"type": "thinking", "text": delta.thinking}

                final = stream.get_final_message()

            messages.append({"role": "assistant", "content": final.content})
            citations.extend(self._extract_citations(final))
            searches.extend(self._extract_searches(final))
            stop_reason = final.stop_reason

            if stop_reason != "pause_turn":
                break

        result = ResearchResult(
            answer="".join(answer_parts).strip(),
            citations=self._dedupe_citations(citations),
            searches=searches,
            stop_reason=stop_reason,
            messages=messages,
        )
        yield {"type": "done", "result": result}

    # ------------------------------------------------------------------ #
    # Internos
    # ------------------------------------------------------------------ #
    def _init_messages(
        self, query: str, history: list[dict[str, Any]] | None
    ) -> list[dict[str, Any]]:
        messages = list(history or [])
        messages.append({"role": "user", "content": query})
        return messages

    def _request_params(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": self.system_prompt,
            # Pensamiento adaptativo: Claude decide cuánto razonar; "summarized"
            # nos deja mostrar un resumen del razonamiento en la interfaz.
            "thinking": {"type": "adaptive", "display": "summarized"},
            "output_config": {"effort": "high"},
            "tools": [
                {
                    "type": config.WEB_SEARCH_TOOL_TYPE,
                    "name": "web_search",
                    "max_uses": self.max_search_uses,
                }
            ],
            "messages": messages,
        }

    @staticmethod
    def _extract_citations(message: Any) -> list[Citation]:
        found: list[Citation] = []
        for block in message.content:
            if getattr(block, "type", None) != "text":
                continue
            for citation in getattr(block, "citations", None) or []:
                url = getattr(citation, "url", None)
                if not url:
                    continue
                found.append(
                    Citation(
                        title=getattr(citation, "title", None) or url,
                        url=url,
                        cited_text=getattr(citation, "cited_text", "") or "",
                    )
                )
        return found

    @staticmethod
    def _extract_searches(message: Any) -> list[str]:
        queries: list[str] = []
        for block in message.content:
            if getattr(block, "type", None) != "server_tool_use":
                continue
            if getattr(block, "name", None) != "web_search":
                continue
            block_input = getattr(block, "input", None) or {}
            query = block_input.get("query")
            if query:
                queries.append(query)
        return queries

    @staticmethod
    def _dedupe_citations(citations: list[Citation]) -> list[Citation]:
        seen: set[str] = set()
        unique: list[Citation] = []
        for citation in citations:
            if citation.url in seen:
                continue
            seen.add(citation.url)
            unique.append(citation)
        return unique


def _require_api_key() -> None:
    """Aviso temprano si falta la credencial, con un mensaje claro."""
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        raise SystemExit(
            "Falta ANTHROPIC_API_KEY. Copia backend/.env.example a backend/.env y "
            "coloca tu clave, o expórtala en el entorno."
        )
