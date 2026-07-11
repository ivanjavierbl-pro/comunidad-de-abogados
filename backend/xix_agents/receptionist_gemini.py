"""Recepcionista virtual de XIX Estudio Jurídico con Google Gemini (nivel gratuito).

Misma persona y mismas herramientas (agendar cita / dejar recado) que la versión
con Claude, pero usando la API de Google Gemini, que tiene un nivel gratuito.
Expone la misma interfaz `chat(mensaje, historial)` para que el webhook y la CLI
funcionen sin cambios.
"""

from __future__ import annotations

import os

from google import genai
from google.genai import types

from . import config

# Reutilizamos la persistencia (citas.json / mensajes.json) de la versión Claude.
from .receptionist_agent import _append_record, _confirmation_code, _now_iso


# ---------------------------------------------------------------------- #
# Herramientas: funciones que Gemini puede llamar automáticamente.
# El esquema se infiere de la firma y el docstring.
# ---------------------------------------------------------------------- #
def agendar_cita(
    nombre_cliente: str,
    contacto: str,
    area: str,
    motivo: str,
    fecha_hora_preferida: str = "",
    urgencia: str = "normal",
) -> dict:
    """Agenda una cita del cliente con el despacho.

    Úsala solo después de haber confirmado con la persona su nombre, un contacto
    y el motivo de la consulta.

    Args:
        nombre_cliente: Nombre completo del cliente.
        contacto: Teléfono o correo electrónico del cliente.
        area: Área jurídica del caso (civil, sucesiones, contratos, etc.).
        motivo: Descripción breve del motivo de la consulta.
        fecha_hora_preferida: Fecha y hora que prefiere el cliente, en texto libre.
        urgencia: Nivel de urgencia, "normal" o "alta".
    """
    code = _confirmation_code()
    _append_record(
        "citas.json",
        {
            "codigo": code,
            "creado": _now_iso(),
            "nombre_cliente": nombre_cliente,
            "contacto": contacto,
            "area": area,
            "motivo": motivo,
            "fecha_hora_preferida": fecha_hora_preferida,
            "urgencia": urgencia,
        },
    )
    return {
        "estado": "agendada",
        "codigo": code,
        "nota": "Un abogado del área confirmará la cita.",
    }


def dejar_mensaje(
    nombre_cliente: str,
    contacto: str,
    mensaje: str,
    urgencia: str = "normal",
) -> dict:
    """Registra un recado cuando la persona no agenda una cita en el momento.

    También se usa para consultas que NO son de derecho civil, para que el
    abogado contacte a la persona y la derive personalmente.

    Args:
        nombre_cliente: Nombre completo del cliente.
        contacto: Teléfono o correo electrónico del cliente.
        mensaje: Contenido del recado o motivo de la consulta.
        urgencia: Nivel de urgencia, "normal" o "alta".
    """
    code = _confirmation_code()
    _append_record(
        "mensajes.json",
        {
            "codigo": code,
            "creado": _now_iso(),
            "nombre_cliente": nombre_cliente,
            "contacto": contacto,
            "mensaje": mensaje,
            "urgencia": urgencia,
        },
    )
    return {"estado": "registrado", "codigo": code}


class GeminiReceptionistAgent:
    """Recepcionista virtual conversacional basada en Google Gemini.

    Uso::

        agent = GeminiReceptionistAgent()
        texto, chat = agent.chat("Hola, necesito ayuda con una sucesión")
        print(texto)
        # ... siguiente turno reutilizando `chat` para mantener el contexto
    """

    def __init__(
        self,
        model: str = config.GEMINI_MODEL,
        despacho_info: dict | None = None,
    ) -> None:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.system_prompt = config.build_receptionist_prompt(
            despacho_info or config.DESPACHO_INFO
        )
        # Gemini llama a las herramientas automáticamente (automatic function calling).
        self._config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            tools=[agendar_cita, dejar_mensaje],
        )

    def chat(self, user_message: str, history=None):
        """Procesa un turno y devuelve (respuesta, sesión_de_chat).

        La "sesión_de_chat" se devuelve como historial: pásala de nuevo en el
        siguiente turno para mantener el contexto de la conversación.
        """
        chat = history or self.client.chats.create(
            model=self.model, config=self._config
        )
        response = chat.send_message(user_message)
        return (response.text or "").strip(), chat


def _require_gemini_key() -> None:
    """Aviso temprano si falta la credencial de Gemini."""
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        raise SystemExit(
            "Falta GEMINI_API_KEY. Consíguela gratis en https://aistudio.google.com/ "
            "y colócala en backend/.env (o expórtala en el entorno)."
        )
