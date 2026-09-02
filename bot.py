import asyncio
import imaplib
import email
from email.header import decode_header
import html
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from flask import Flask
import threading
import os

# ================= НАЛАШТУВАННЯ =================
EMAIL = "iasa-kn61@ukr.net"  # <--- ВПИШИ СВОЮ ПОШТУ
PASSWORD = "avuGkSlgPL3LLovt"
BOT_TOKEN = "8924622903:AAEsi6layYVKC5cLoH2-5fqnmIO5d1kLpVI"
CHAT_ID = "-1004391355458"
MAIL_THREAD_ID = 7161
# ================================================

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
LAST_SEEN_UID = None

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("Привіт! Я бот групи. Поки що я пересилаю пошту, але скоро буду знати розклад!")

@dp.message(Command("time"))
async def cmd_time(message: Message):
    await message.reply("Ця функція в розробці. Але я тебе чую!")

def get_email_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                charset = part.get_content_charset() or 'utf-8'
                try:
                    return part.get_payload(decode=True).decode(charset, errors="ignore")
                except Exception:
                    pass
    else:
        charset = msg.get_content_charset() or 'utf-8'
        try:
            return msg.get_payload(decode=True).decode(charset, errors="ignore")
        except Exception:
            pass
    return "Зміст листа недоступний (можливо, містить лише картинки)."

def check_email_sync():
    global LAST_SEEN_UID
    new_emails = []
    try:
        mail = imaplib.IMAP4_SSL("imap.ukr.net")
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")

        status, messages = mail.uid('SEARCH', None, "ALL")

        if status == "OK" and messages[0]:
            uids = messages[0].split()

            if not uids:
                mail.logout()
                return []

            if LAST_SEEN_UID is None:
                LAST_SEEN_UID = int(uids[-1])
                mail.logout()
                return []

            for uid in uids:
                current_uid = int(uid)
                if current_uid > LAST_SEEN_UID:
                    res, msg_data = mail.uid('FETCH', uid, "(RFC822)")

                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])

                            subject, encoding = decode_header(msg.get("Subject", "Без теми"))[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(encoding if encoding else "utf-8", errors="ignore")

                            sender, encoding = decode_header(msg.get("From", "Невідомий"))[0]
                            if isinstance(sender, bytes):
                                sender = sender.decode(encoding if encoding else "utf-8", errors="ignore")

                            body = get_email_body(msg)
                            new_emails.append({"sender": sender, "subject": subject, "body": body})

                    LAST_SEEN_UID = max(LAST_SEEN_UID, current_uid)

        mail.logout()
    except Exception as e:
        print(f"Помилка перевірки пошти: {e}")

    return new_emails

async def email_worker():
    while True:
        await asyncio.sleep(30)
        new_emails = await asyncio.to_thread(check_email_sync)
        for mail in new_emails:
            safe_sender = html.escape(mail['sender'])
            safe_subject = html.escape(mail['subject'])
            safe_body = html.escape(mail['body'].strip())
            if len(safe_body) > 3500:
                safe_body = safe_body[:3500] + "\n\n<i>[...Текст обрізано...]</i>"

            text = f"📧 <b>Новий лист!</b>\n\n<b>Від:</b> {safe_sender}\n<b>Тема:</b> {safe_subject}\n\n<b>Текст:</b>\n{safe_body}"

            try:
                await bot.send_message(
                    chat_id=CHAT_ID,
                    message_thread_id=MAIL_THREAD_ID,
                    text=text,
                    disable_web_page_preview=True
                )
                print(f"✅ Успішно переслано лист від {safe_sender}")
            except Exception as e:
                print(f"Помилка відправки в Telegram: {e}")

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

async def main():
    print("Запуск фонової перевірки пошти (кожні 30 сек)...")
    asyncio.create_task(email_worker())
    print("Бот готовий приймати команди!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Запускаємо веб-сервер у фоновому потоці
    threading.Thread(target=run_web, daemon=True).start()
    # Запускаємо телеграм-бота
    asyncio.run(main())
