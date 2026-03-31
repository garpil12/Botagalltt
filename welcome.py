import os
import json
import asyncio
import time
from telethon import events, Button, functions

DB_FILE = "welcome_db.json"

# ================= DATABASE =================
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

db = load_db()

# ================= JUALAN CONTROL =================
user_cooldown = {}
global_cooldown = 0

USER_DELAY = 300      # 5 menit per user
GLOBAL_DELAY = 10     # delay global biar ga spam

# ================= DEFAULT =================
DEFAULT_CAPTION = (
    "👋 WELCOME TO {group}\n\n"
    "❏ ɴᴀᴍᴇ ➠ {mention}\n"
    "❏ ɪᴅ ᴜsᴇʀ ➠ {id}\n"
    "❏ ᴜsᴇʀɴᴀᴍᴇ ➠ @{username}"
)

AUTO_DELETE = 120

# ================= FORMAT =================
def format_caption(text, user, chat):
    mention = f"{user.first_name}"
    return text.format(
        mention=mention,
        id=user.id,
        username=user.username or "-",
        group=chat.title or "-"
    )

# ================= BUILD BUTTON =================
def build_buttons(buttons_data):
    buttons = []

    temp = []
    for b in buttons_data or []:
        if b["type"] == "url":
            temp.append(Button.url(b["text"], b["url"]))
        elif b["type"] == "vip":
            temp.append(Button.inline(b["text"], b"vip"))

        if len(temp) == 2:
            buttons.append(temp)
            temp = []

    if temp:
        buttons.append(temp)

    buttons.append([
        Button.url("⚡ Creator by", "https://t.me/Brsik23")
    ])

    return buttons

# ================= PARSE BUTTON =================
def parse_buttons(text):
    result = []
    pairs = text.split(" - ")

    for i in range(0, len(pairs), 2):
        try:
            name = pairs[i].strip()
            url = pairs[i+1].strip()

            if "vip" in name.lower():
                result.append({"text": "👑 VVIP", "type": "vip"})
            else:
                result.append({"text": name, "url": url, "type": "url"})
        except:
            continue

    return result

# ================= REGISTER =================
def register(client):

    # ===== AUTO WELCOME =====
    @client.on(events.ChatAction)
    async def welcome_handler(event):
        if not (event.user_joined or event.user_added):
            return

        chat_id = str(event.chat_id)

        if chat_id not in db:
            db[chat_id] = {
                "enabled": True,
                "text": DEFAULT_CAPTION,
                "media": None,
                "buttons": [],
                "clean": False
            }
            save_db(db)

        data = db.get(chat_id, {})

        if not data.get("enabled", True):
            return

        try:
            user = await event.get_user()
            chat = await event.get_chat()

            caption = format_caption(data.get("text", DEFAULT_CAPTION), user, chat)

            media = data.get("media")
            if media and not os.path.exists(media):
                media = None

            buttons = build_buttons(data.get("buttons"))

            if media:
                msg = await event.reply(caption, file=media, buttons=buttons)
            else:
                msg = await event.reply(caption, buttons=buttons)

            if data.get("clean"):
                old = data.get("last_msg")
                if old:
                    try:
                        await client.delete_messages(event.chat_id, old)
                    except:
                        pass

                db[chat_id]["last_msg"] = msg.id
                save_db(db)

            async def auto_delete():
                await asyncio.sleep(AUTO_DELETE)
                try:
                    await msg.delete()
                except:
                    pass

            asyncio.create_task(auto_delete())

        except Exception as e:
            print("ERROR WELCOME:", e)

    # ===== AUTO REPLY JUALAN =====
    @client.on(events.NewMessage)
    async def auto_jualan(event):
        global global_cooldown

        if event.is_group:
            text = event.raw_text.lower()
            user_id = event.sender_id
            now = time.time()

            keywords = [
                "jajanan",
                "jualan",
                "ready",
                "open order",
                "open po",
                "murah",
                "stok",
                "sale"
            ]

            if any(k in text for k in keywords):

                # cek cooldown global
                if now - global_cooldown < GLOBAL_DELAY:
                    return

                # cek cooldown user
                if user_id in user_cooldown:
                    if now - user_cooldown[user_id] < USER_DELAY:
                        return

                # simpan waktu
                user_cooldown[user_id] = now
                global_cooldown = now

                await event.reply(
                    "🔥 Mending cek store keren gua dah!!",
                    buttons=[
                        [Button.url("🛒 Kunjungi Store", "https://t.me/storegarf")]
                    ]
                )

    # ===== ON/OFF =====
    @client.on(events.NewMessage(pattern="^/welcome (on|off)$"))
    async def toggle(event):
        chat_id = str(event.chat_id)
        state = event.pattern_match.group(1)

        db.setdefault(chat_id, {})
        db[chat_id]["enabled"] = state == "on"

        save_db(db)
        await event.reply(f"✅ Welcome {'aktif' if state=='on' else 'mati'}")

    # ===== CLEAN =====
    @client.on(events.NewMessage(pattern="^/cleanwelcome (on|off)$"))
    async def clean(event):
        chat_id = str(event.chat_id)
        state = event.pattern_match.group(1)

        db.setdefault(chat_id, {})
        db[chat_id]["clean"] = state == "on"

        save_db(db)
        await event.reply(f"🧹 Clean welcome {'aktif' if state=='on' else 'mati'}")

    # ===== SET WELCOME =====
    @client.on(events.NewMessage(pattern="^/setwelcome$"))
    async def set_welcome(event):
        chat_id = str(event.chat_id)

        if not event.is_reply:
            return await event.reply("Reply foto/video + teks!")

        msg = await event.get_reply_message()

        db.setdefault(chat_id, {})

        custom = msg.message or ""
        db[chat_id]["text"] = custom + "\n\n" + DEFAULT_CAPTION

        if msg.media:
            path = await msg.download_media()
            db[chat_id]["media"] = path

        save_db(db)
        await event.reply("✅ Welcome diset!")

    # ===== GET WELCOME =====
    @client.on(events.NewMessage(pattern="^/getwelcome$"))
    async def get_welcome(event):
        chat_id = str(event.chat_id)

        data = db.get(chat_id)
        if not data:
            return await event.reply("Belum ada setting")

        user = await event.get_sender()
        chat = await event.get_chat()

        caption = format_caption(data.get("text", DEFAULT_CAPTION), user, chat)
        buttons = build_buttons(data.get("buttons"))
        media = data.get("media")

        if media and os.path.exists(media):
            await event.reply(caption, file=media, buttons=buttons)
        else:
            await event.reply(caption, buttons=buttons)

    # ===== RESET =====
    @client.on(events.NewMessage(pattern="^/resetwelcome$"))
    async def reset(event):
        chat_id = str(event.chat_id)

        db[chat_id] = {
            "enabled": True,
            "text": DEFAULT_CAPTION,
            "media": None,
            "buttons": [],
            "clean": False
        }

        save_db(db)
        await event.reply("♻️ Welcome direset!")

    # ===== SET BUTTON =====
    @client.on(events.NewMessage(pattern=r"^/setbutton (.+)$"))
    async def set_button(event):
        chat_id = str(event.chat_id)
        raw = event.pattern_match.group(1)

        db.setdefault(chat_id, {})
        db.setdefault(chat_id, {}).setdefault("buttons", [])

        new_buttons = parse_buttons(raw)
        db[chat_id]["buttons"].extend(new_buttons)

        save_db(db)
        await event.reply("✅ Button ditambah!")

    # ===== CLEAR BUTTON =====
    @client.on(events.NewMessage(pattern="^/clearbutton$"))
    async def clear_button(event):
        chat_id = str(event.chat_id)

        if chat_id in db:
            db[chat_id]["buttons"] = []

        save_db(db)
        await event.reply("🗑 Button dihapus!")

    # ===== RELOAD DATABASE =====
    @client.on(events.NewMessage(pattern="^/reload$"))
    async def reload_db(event):
        global db
        try:
            db = load_db()
            await event.reply("♻️ Database berhasil di-reload!")
        except Exception as e:
            await event.reply(f"❌ Gagal reload:\n{e}")

    # ===== VIP BUTTON =====
    @client.on(events.CallbackQuery(data=b"vip"))
    async def vip_handler(event):
        user = await event.get_sender()

        try:
            await client.send_message(
                user.id,
                "👑 **VVIP ACCESS**\n\nHubungi 👉 @Brsik23"
            )
            await event.answer("Cek DM lu!", alert=True)
        except:
            await event.answer("Gagal kirim DM", alert=True)

    # ===== GET GROUP LINK =====
    @client.on(events.NewMessage(pattern="^/getlink$"))
    async def get_link(event):
        try:
            chat = await event.get_chat()

            if getattr(chat, "username", None):
                link = f"https://t.me/{chat.username}"
            else:
                result = await client(functions.messages.ExportChatInviteRequest(
                    peer=event.chat_id
                ))
                link = result.link

            await event.reply(f"🔗 Link Grup:\n{link}")

        except Exception as e:
            await event.reply(f"❌ Gagal ambil link:\n{e}")
