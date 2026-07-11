"""Interfaz de línea de comandos para el Asistente de Investigación Jurídica.

Uso:
    python cli.py "¿Cómo aplica la reforma laboral 2025 a contratos vigentes?"

O de forma interactiva (mantiene el contexto de la conversación):
    python cli.py
"""

from __future__ import annotations

import sys

from dotenv import load_dotenv

from suilex_agents.legal_research_agent import LegalResearchAgent, _require_api_key


def _run_query(agent: LegalResearchAgent, query: str, history):
    """Ejecuta una consulta mostrando la salida en streaming. Devuelve el result."""
    result = None
    printed_search = False
    for event in agent.stream_events(query, history):
        if event["type"] == "search_start" and not printed_search:
            print("\n🔎 Buscando en fuentes jurídicas…\n", flush=True)
            printed_search = True
        elif event["type"] == "text":
            print(event["text"], end="", flush=True)
        elif event["type"] == "done":
            result = event["result"]

    print()  # salto de línea final

    if result and result.citations:
        print("\n📚 Fuentes:")
        for i, cita in enumerate(result.citations, 1):
            print(f"  [{i}] {cita.title}\n      {cita.url}")

    return result


def main() -> None:
    load_dotenv()
    _require_api_key()

    agent = LegalResearchAgent()

    # Modo de una sola consulta (argumento en la línea de comandos).
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        _run_query(agent, query, history=None)
        return

    # Modo interactivo.
    print("Asistente de Investigación Jurídica de SUILEX")
    print("Escribe tu consulta (o 'salir' para terminar).\n")

    history: list = []
    while True:
        try:
            query = input("⚖️  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHasta luego.")
            break
        if not query:
            continue
        if query.lower() in {"salir", "exit", "quit"}:
            print("Hasta luego.")
            break

        result = _run_query(agent, query, history)
        if result:
            history = result.messages
        print()


if __name__ == "__main__":
    main()
