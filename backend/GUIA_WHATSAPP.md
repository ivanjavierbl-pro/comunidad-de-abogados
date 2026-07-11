# Guía paso a paso: conectar la recepcionista a WhatsApp (gratis)

Esta guía te lleva desde cero hasta tener la recepcionista de **XIX Estudio
Jurídico** respondiendo por WhatsApp, usando el motor gratuito de Google Gemini.

Tiempo estimado: 30–45 minutos. Costo: **$0** para pruebas.

---

## Resumen de lo que vas a hacer

1. Conseguir la clave **gratuita** de Google Gemini (el cerebro).
2. Crear una app en **Meta for Developers** y activar WhatsApp.
3. Poner tu servidor en línea con **ngrok** (URL pública temporal).
4. Conectar el **webhook** de Meta a tu servidor.
5. Enviar un mensaje de prueba y ver a la recepcionista responder.

---

## Parte 0 — Clave gratuita de Google Gemini

1. Entra a <https://aistudio.google.com/> e inicia sesión con tu cuenta de Google.
2. Clic en **Get API key** (Obtener clave de API) → **Create API key**.
3. Copia la clave. La usarás como `GEMINI_API_KEY`.

---

## Parte 1 — Preparar el proyecto en tu computadora

Necesitas **Python 3.10+** instalado.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Abre `.env` y completa por ahora solo esto (el resto lo llenás en la Parte 3):

```
GEMINI_API_KEY=tu-clave-de-gemini
META_VERIFY_TOKEN=xix-verify-token
```

`META_VERIFY_TOKEN` es una contraseña que inventás vos; solo tiene que coincidir
con la que pongas en Meta más adelante.

---

## Parte 2 — Crear la app de Meta y activar WhatsApp

1. Entra a <https://developers.facebook.com/> e inicia sesión con tu cuenta de
   Facebook. Aceptá registrarte como desarrollador si te lo pide.
2. **My Apps → Create App**.
3. Elegí el tipo **Business** (Negocios), poné un nombre (ej. "XIX Recepción") y
   creá la app.
4. En el panel de la app, buscá **WhatsApp** y clic en **Set up** (Configurar).
   - Si te pide un *Meta Business Account*, creá uno (es gratis).
5. Entrá a **WhatsApp → API Setup** (o *Quickstart*). Ahí vas a ver:
   - Un **número de teléfono de prueba** (el "From"), que te da Meta gratis.
   - Un **Access token** temporal (dura 24 h) → será tu `WHATSAPP_TOKEN`.
   - El **Phone number ID** → será tu `WHATSAPP_PHONE_NUMBER_ID`.
6. En la misma pantalla, en **"To"**, agregá tu número de WhatsApp personal como
   destinatario de prueba (Meta permite hasta 5). Confirmá el código que te llega.

> ℹ️ El token temporal vence en 24 h. Para pruebas está bien; para producción se
> genera un token permanente (ver Parte 6).

---

## Parte 3 — Poner el servidor en línea (ngrok)

Meta necesita una URL pública HTTPS para enviarte los mensajes.

1. Completá el `.env` con los datos de la Parte 2:

   ```
   GEMINI_API_KEY=tu-clave-de-gemini
   META_VERIFY_TOKEN=xix-verify-token
   WHATSAPP_TOKEN=el-token-temporal-de-meta
   WHATSAPP_PHONE_NUMBER_ID=el-phone-number-id
   ```

2. Arrancá el servidor:

   ```bash
   uvicorn webhook:app --port 8000
   ```

3. En **otra terminal**, instalá y corré ngrok (<https://ngrok.com/>, plan gratis):

   ```bash
   ngrok http 8000
   ```

   Te va a mostrar una URL como `https://xxxx-xx-xx.ngrok-free.app`.
   Tu webhook será esa URL **+ `/webhook`**, por ejemplo:
   `https://xxxx-xx-xx.ngrok-free.app/webhook`

> Mantené ambas terminales abiertas mientras probás.

---

## Parte 4 — Conectar el webhook en Meta

1. En el panel de la app: **WhatsApp → Configuration** (Configuración).
2. En la sección **Webhook**, clic en **Edit** (Editar):
   - **Callback URL:** la URL de ngrok + `/webhook`.
   - **Verify token:** el mismo valor de tu `META_VERIFY_TOKEN` (`xix-verify-token`).
   - Clic en **Verify and save**. Debe quedar verificado (nuestro servidor
     responde automáticamente al desafío).
3. En **Webhook fields**, clic en **Manage** y **suscribite** al campo
   **`messages`**.

---

## Parte 5 — Probar 🎉

1. Desde tu WhatsApp personal (el que agregaste como destinatario), enviá un
   mensaje al **número de prueba** de Meta. Por ejemplo: *"Hola"*.
2. En unos segundos, la recepcionista debería responder saludando y ofreciendo
   ayuda.
3. Probá agendar: *"Quiero agendar por un juicio sucesorio"*. Al confirmar tus
   datos, la cita queda guardada en `backend/data/citas.json`.

Si algo no responde, mirá la terminal del servidor: ahí aparecen los errores.

---

## Parte 6 — Pasar a producción (cuando estés listo)

Lo anterior es para pruebas. Para uso real:

- **Token permanente:** en *Business Settings → Users → System Users*, creá un
  usuario del sistema y generá un token permanente con permisos de WhatsApp.
  Reemplazá `WHATSAPP_TOKEN` por ese.
- **Tu propio número:** registrá tu número en la WhatsApp Cloud API (no puede
  estar en uso en la app común de WhatsApp Business; hay que migrarlo).
- **Hosting estable:** en lugar de ngrok, subí el servidor a un hosting con plan
  gratuito (Render, Fly.io) para que esté siempre en línea.
- **Firma segura:** completá `META_APP_SECRET` (App Settings → Basic → App
  Secret) para validar la firma de los eventos.
- **Verificación del negocio:** Meta pide verificar tu negocio para levantar los
  límites de mensajería.

---

## Messenger e Instagram (opcional, mismo servidor)

1. En la app de Meta, agregá el producto **Messenger** y conectá tu **Página de
   Facebook**. Generá el **Page Access Token** → `PAGE_ACCESS_TOKEN` en `.env`.
2. Suscribí la página al webhook (mismo Callback URL y Verify token).
3. Para Instagram: vinculá tu cuenta de **Instagram Business** a esa página y
   agregá el producto **Instagram**; el mismo `PAGE_ACCESS_TOKEN` sirve.

El servidor ya distingue automáticamente si el mensaje viene de WhatsApp,
Messenger o Instagram y responde por el canal correcto.

---

## Solución de problemas

| Síntoma | Posible causa |
|---|---|
| "The verification token doesn't match" | El `META_VERIFY_TOKEN` del `.env` no coincide con el de Meta. |
| El webhook verifica pero no llegan mensajes | Falta suscribirse al campo `messages`. |
| Verifica pero la recepcionista no responde | Revisá que `GEMINI_API_KEY` y `WHATSAPP_TOKEN` estén bien; mirá los errores en la terminal. |
| "Falta GEMINI_API_KEY" | No cargaste la clave de Gemini en `.env`. |
| Dejó de responder después de un día | El token temporal de WhatsApp venció (24 h); generá uno nuevo o uno permanente. |
| ngrok cambió de URL | Cada reinicio de ngrok (plan gratis) da una URL nueva; hay que actualizarla en Meta. |
