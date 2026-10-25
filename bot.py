import os
import time
import shutil
import asyncio
import nest_asyncio
from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.types import Message

nest_asyncio.apply()

API_ID = 34306836
API_HASH = "cbd074ed691206582e91a694e3a641cf"
BOT_TOKEN = "8879377072:AAGNLORZNlvL3kPMt4aFtmTiKeyBBAEK67U"

app = Client("my_koyeb_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DOWNLOAD_DIR = "/app/downloads/"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

TRACKERS = (
    "udp://tracker.opentrackr.org:1337/announce,"
    "udp://open.stealth.si:80/announce,"
    "udp://tracker.torrent.eu.org:451/announce,"
    "udp://tracker.bittor.pw:1337/announce,"
    "udp://public.tracker.vraphim.com:6969/announce"
)

ARIA2_TORRENT_FLAGS = (
    f'--bt-tracker="{TRACKERS}" '
    '--enable-dht=true '
    '--enable-peer-exchange=true '
    '--bt-max-peers=80 '
    '--bt-request-peer-speed-limit=50M '
    '--max-connection-per-server=16 '
    '--split=16 '
    '--min-split-size=1M '
    '--seed-time=0 '
    '--summary-interval=0'
)

# Render Web Service-க்கான Health Server
async def handle_ping(request):
    return web.Response(text="Bot is running smoothly 24/7!")

async def start_web_server():
    server = web.Application()
    server.router.add_get("/", handle_ping)
    runner = web.AppRunner(server)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def upload_directory(client, chat_id, target_dir, status_msg):
    found_files = []
    for root, _, files in os.walk(target_dir):
        for f in files:
            if not f.endswith(".aria2"):
                found_files.append(os.path.join(root, f))
    
    if not found_files:
        await status_msg.edit_text("❌ கோப்புகள் எதுவும் பதிவிறக்கம் செய்யப்படவில்லை.")
        return

    for file_path in found_files:
        file_name = os.path.basename(file_path)
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        if file_size_mb > 2000:
            await client.send_message(chat_id, f"⚠️ கோப்பு அளவு 2GB-க்கு மேல் உள்ளது ({file_size_mb:.2f} MB): `{file_name}`")
            continue

        await status_msg.edit_text(f"📤 **அப்லோட் ஆகிறது...**\n`{file_name}` ({file_size_mb:.1f} MB)")
        try:
            await client.send_document(
                chat_id=chat_id,
                document=file_path,
                caption=f"✅ `{file_name}`"
            )
        except Exception as e:
            await client.send_message(chat_id, f"⚠️ அப்லோட் பிழை ({file_name}): `{str(e)}`")

    await status_msg.delete()

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(
        "⚡ **24/7 Cloud Leech Bot தயாராக உள்ளது!**\n\n"
        "🧲 **Magnet Link:** `/magnet <link>`\n"
        "🔗 **Direct URL:** `/leech <url>`\n"
        "📂 **Torrent File:** கோப்பை நேரடியாக அனுப்பவும்."
    )

@app.on_message((filters.command("leech") | filters.command("magnet")) & filters.private)
async def handle_url(client, message):
    if len(message.command) < 2:
        await message.reply_text("❌ லிங்கை சேர்த்து அனுப்பவும்!")
        return

    link = message.text.split(None, 1)[1].strip()
    session_id = str(int(time.time()))
    task_dir = os.path.join(DOWNLOAD_DIR, session_id)
    os.makedirs(task_dir, exist_ok=True)

    status_msg = await message.reply_text("🚀 **பதிவிறக்கம் தொடங்குகிறது...**")

    cmd = f'aria2c --dir="{task_dir}" {ARIA2_TORRENT_FLAGS} "{link}"'
    proc = await asyncio.create_subprocess_shell(cmd)
    await proc.communicate()

    if proc.returncode == 0:
        await status_msg.edit_text("📤 **பதிவிறக்கம் முடிந்தது! அப்லோட் ஆகிறது...**")
        await upload_directory(client, message.chat.id, task_dir, status_msg)
    else:
        await status_msg.edit_text("❌ பதிவிறக்கம் தோல்வியடைந்தது.")

    shutil.rmtree(task_dir, ignore_errors=True)

@app.on_message(filters.document & filters.private)
async def handle_torrent_doc(client, message):
    if not message.document.file_name.endswith(".torrent"):
        return

    session_id = str(int(time.time()))
    task_dir = os.path.join(DOWNLOAD_DIR, session_id)
    os.makedirs(task_dir, exist_ok=True)

    status_msg = await message.reply_text("📥 `.torrent` பெறப்பட்டது. பதிவிறக்கம் தொடங்குகிறது...")
    torrent_path = await message.download(file_name=os.path.join(task_dir, message.document.file_name))

    cmd = f'aria2c --dir="{task_dir}" {ARIA2_TORRENT_FLAGS} "{torrent_path}"'
    proc = await asyncio.create_subprocess_shell(cmd)
    await proc.communicate()

    if os.path.exists(torrent_path):
        os.remove(torrent_path)

    if proc.returncode == 0:
        await status_msg.edit_text("📤 **பதிவிறக்கம் முடிந்தது! அப்லோட் ஆகிறது...**")
        await upload_directory(client, message.chat.id, task_dir, status_msg)
    else:
        await status_msg.edit_text("❌ பதிவிறக்கம் தோல்வியடைந்தது.")

    shutil.rmtree(task_dir, ignore_errors=True)

async def main():
    await start_web_server()
    await app.start()
    print("✅ Render Cloud-ல் பாட் வெற்றிகரமாக Live ஆகிவிட்டது!")
    await idle()

asyncio.run(main())
    
