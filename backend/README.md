# Agentes de IA de SUILEX

Backend en Python con agentes de inteligencia artificial (Claude) para la
comunidad de abogados **SUILEX**.

## Agente incluido

### 🔎 Asistente de Investigación Jurídica

Responde consultas de **derecho mexicano** verificando en fuentes oficiales
(SCJN, DOF, leyes federales y estatales) mediante búsqueda web, y devuelve la
respuesta **con sus citas**.

- Modelo: **Claude Opus 4.8** (`claude-opus-4-8`)
- Herramienta: búsqueda web con citas (`web_search_20260209`)
- Pensamiento adaptativo + esfuerzo alto
- Respuesta en streaming (token por token)

## Instalación

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # y coloca tu ANTHROPIC_API_KEY
```

Obtén tu clave en <https://console.anthropic.com/>.

## Uso

### Línea de comandos

```bash
# Consulta única
python cli.py "¿Cómo aplica la reforma laboral 2025 a contratos vigentes?"

# Modo interactivo (mantiene el contexto de la conversación)
python cli.py
```

### Como servidor web (para integrar con el sitio de SUILEX)

```bash
uvicorn server:app --reload
```

Endpoints:

| Método | Ruta                     | Descripción                             |
| ------ | ------------------------ | --------------------------------------- |
| GET    | `/api/health`            | Verificación de estado                  |
| POST   | `/api/research`          | Respuesta completa en JSON              |
| POST   | `/api/research/stream`   | Respuesta en streaming (SSE)            |

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Qué es el amparo directo y cuándo procede?"}'
```

### Desde Python

```python
from suilex_agents import LegalResearchAgent

agent = LegalResearchAgent()
resultado = agent.research("¿Qué establece el artículo 123 constitucional?")

print(resultado.answer)
for cita in resultado.citations:
    print(cita.title, "->", cita.url)
```

## Estructura

```
backend/
├── requirements.txt
├── .env.example
├── cli.py                        # interfaz de línea de comandos
├── server.py                     # API FastAPI (JSON + SSE)
└── suilex_agents/
    ├── __init__.py
    ├── config.py                 # modelo, prompt de sistema, parámetros
    └── legal_research_agent.py   # el agente
```

## Advertencia

Esta es una herramienta de **apoyo a la investigación jurídica**. No sustituye el
criterio profesional ni constituye asesoría legal formal.
