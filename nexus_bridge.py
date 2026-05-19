# nexus_bridge.py
# Puente entre WhatsApp (via n8n) y NexusNetflixBot usando cuenta personal de Telegram
# Instalar: pip install telethon

import asyncio
import logging
import os
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#  CONFIGURACIÓN — variables de entorno en Railway
# ══════════════════════════════════════════════
API_ID         = int(os.environ.get("API_ID", "32612495"))
API_HASH       = os.environ.get("API_HASH", "678d81b676317cf854133c9f5dfd9cbb")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

GRUPO_ID          = int(os.environ.get("GRUPO_ID", "-5282560412"))
NEXUS_BOT_USERNAME = os.environ.get("NEXUS_BOT_USERNAME", "NexusNetflixBot")
BRIDGE_BOT_ID     = int(os.environ.get("BRIDGE_BOT_ID", "8567373005"))

# ══════════════════════════════════════════════
#  CLIENTE TELETHON (cuenta personal)
# ══════════════════════════════════════════════
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# Diccionario para rastrear: mensaje_id_en_bot → numero_wa_cliente
sesiones_pendientes = {}

# ══════════════════════════════════════════════
#  ESCUCHA MENSAJES DEL BOT PUENTE EN EL GRUPO
# ══════════════════════════════════════════════
@client.on(events.NewMessage(chats=GRUPO_ID))
async def handler_grupo(event):
    sender = await event.get_sender()
    
    # Solo procesar mensajes del NexusBridgeBot
    if sender.id != BRIDGE_BOT_ID:
        return
    
    text = event.raw_text.strip()
    logger.info(f"Mensaje de NexusBridgeBot: {text}")
    
    # Detectar formato SOPORTE:51XXXXXXXXX
    match = re.match(r"SOPORTE:(\d+)", text)
    if not match:
        return
    
    numero_wa = match.group(1)
    logger.info(f"Procesando soporte para WA: {numero_wa}")
    
    # Enviar comando al NexusNetflixBot como si fuera el usuario
    nexus_bot = await client.get_entity(NEXUS_BOT_USERNAME)
    msg_enviado = await client.send_message(nexus_bot, f"/soporte {numero_wa}")
    
    # Guardar el numero_wa asociado al mensaje enviado
    sesiones_pendientes[msg_enviado.id] = numero_wa
    logger.info(f"Comando enviado al bot. msg_id={msg_enviado.id}, wa={numero_wa}")

# ══════════════════════════════════════════════
#  ESCUCHA RESPUESTA DEL NEXUSNETFLIXBOT (chat privado)
# ══════════════════════════════════════════════
@client.on(events.NewMessage(from_users=NEXUS_BOT_USERNAME))
async def handler_respuesta_bot(event):
    text = event.raw_text.strip()
    logger.info(f"Respuesta de NexusNetflixBot: {text[:100]}...")
    
    # Verificar si la respuesta contiene WA:51XXXXXXXXX
    if not text.startswith("WA:"):
        return
    
    lines = text.split("\n")
    numero_wa = lines[0].replace("WA:", "").strip()
    respuesta_cliente = "\n".join(lines[1:]).strip()
    
    logger.info(f"Reenviando respuesta al grupo para WA: {numero_wa}")
    
    # Reenviar la respuesta al grupo de Telegram
    await client.send_message(
        GRUPO_ID,
        f"📱 Respuesta para {numero_wa}:\n\n{respuesta_cliente}"
    )

# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════
async def main():
    logger.info("🚀 NexusBridge iniciando...")
    await client.start()
    me = await client.get_me()
    logger.info(f"✅ Conectado como: {me.first_name} (@{me.username})")
    logger.info(f"👂 Escuchando grupo: {GRUPO_ID}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
