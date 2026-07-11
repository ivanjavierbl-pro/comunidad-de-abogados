"""Recepcionista virtual de XIX Estudio Jurídico (interfaz de línea de comandos).

Uso:
    python recepcion.py

Inicia una conversación: la recepcionista saluda, responde dudas, toma tus datos
y agenda citas o deja recados. Las citas se guardan en backend/data/citas.json y
los recados en backend/data/mensajes.json.
"""

from __future__ import annotations

from dotenv import load_dotenv

from xix_agents.legal_research_agent import _require_api_key
from xix_agents.receptionist_agent import ReceptionistAgent


def main() -> None:
    load_dotenv()
    _require_api_key()

    agent = ReceptionistAgent()

    print("── Recepción · XIX Estudio Jurídico ──")
    print("(escribe 'salir' para terminar)\n")

    # Turno de apertura: la recepcionista saluda primero.
    saludo, messages = agent.chat(
        "Un visitante acaba de abrir el chat. Salúdalo y ofrécele ayuda."
    )
    print(f"Recepción: {saludo}\n")

    while True:
        try:
            user = input("Usted: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nRecepción: ¡Que tenga buen día!")
            break
        if not user:
            continue
        if user.lower() in {"salir", "exit", "quit"}:
            print("Recepción: ¡Que tenga buen día!")
            break

        respuesta, messages = agent.chat(user, messages)
        print(f"\nRecepción: {respuesta}\n")


if __name__ == "__main__":
    main()
