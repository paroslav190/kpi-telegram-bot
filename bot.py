import asyncio
import imaplib
import email
from email.header import decode_header
import html
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from flask import Flask
import threading
import os
from datetime import datetime, timedelta
import pytz

# ================= НАЛАШТУВАННЯ =================
EMAIL = "iasa-kn61@ukr.net" 
PASSWORD = "avuGkSlgPL3LLovt"
BOT_TOKEN = "8924622903:AAFAHYG3zD36C3_zJs8-dAD30PrShQPiJGo"
CHAT_ID = "-1004391355458"
MAIL_THREAD_ID = 7161
KYIV_TZ = pytz.timezone('Europe/Kyiv')
# ================================================

# === ДАНІ РОЗКЛАДУ ТА ПОСИЛАНЬ ===
LINKS = {
    "algo": [
        ("Лекція", "https://us02web.zoom.us/j/84261573579?pwd=2vcfLaachCLF5dbuAfHi3n9NVvZrYk.1"), 
        ("Безнос", "https://us02web.zoom.us/j/88258710884?pwd=RzdqZTg5clhNTWltRGFQOTRmUFFuQT09"), 
        ("Корнач", "https://us04web.zoom.us/j/78663748130")
    ],
    "physics": [
        ("Калита", "https://us02web.zoom.us/j/84191489478?pwd=ALoGHLau6caqKIPwaU3UMdbTKTqmL7.1"),
        ("Лаби",   "https://us05web.zoom.us/j/83481750583?pwd=nLxCZtmlRKaub328S4kaOevUvoB3rb.1")
    ],
    "matan": [("Матан", "https://us04web.zoom.us/j/5044819147?pwd=GpZr4xSe2mYxg30pTFgvgRYEg8HmOZ.1")],
    "linal": [("Лінал", "https://us05web.zoom.us/j/3362272501?pwd=Vm42cEVNQVBrcUlhYWpzdnYwOUNMQT09")],
    "discrete": [("Дискретка", "https://us04web.zoom.us/j/78663748130")],
    "rhetoric": [
        ("Лекція", "https://meet.google.com/ubf-mpzs-pbv"), 
        ("Практика", "https://us04web.zoom.us/j/78663748130")
    ],
    "english": [("Англійська", "https://us04web.zoom.us/j/78663748130")]
}

# Красиві назви предметів для меню
SUBJECT_NAMES = {
    "algo": "Алгоритмізація та програмування",
    "physics": "Фізика",
    "matan": "Матан",
    "linal": "Лінал",
    "discrete": "Дискретна мат.",
    "rhetoric": "Риторика",
    "english": "🇬🇧 Англійська"
}

BELLS = {
    1: ("08:30", "10:05"),
    2: ("10:25", "12:00"),
    3: ("12:20", "13:55"),
    4: ("14:15", "15:50"),
    5: ("16:10", "17:45")
}

SCHEDULE = {
    1: { # ПЕРШИЙ ТИЖДЕНЬ
        0: {
            2: {"name": "Лабораторна, Алгоритмізація та програмування", "type": "algo"},
            3: {"name": "Практика, Культура усного професійного мовлення (риторика)", "type": "rhetoric"},
            4: {"name": "Практика, Англійська мова", "type": "english"},
            5: {"name": "Практика, Англійська мова", "type": "english"}
        },
        1: {}, 
        2: {
            1: {"name": "Лекція, Алгебра та аналітична геометрія", "type": "linal"},
            2: {"name": "Лекція, Дискретна математика", "type": "discrete"},
            3: {"name": "Лекція, Математичний аналіз", "type": "matan"},
            4: {"name": "Лекція, Математичний аналіз", "type": "matan"}
        },
        3: {
            2: {"name": "Лекція, Алгоритмізація та програмування", "type": "algo"},
            3: {"name": "Лекція, Культура усного професійного мовлення (риторика)", "type": "rhetoric"},
            4: {"name": "Лекція, Фізика", "type": "physics"}
        },
        4: {
            1: {"name": "Практика, Математичний аналіз", "type": "matan"},
            2: {"name": "Практика, Дискретна математика", "type": "discrete"},
            3: {"name": "Лабораторна, Фізика", "type": "physics"},
            4: {"name": "Практика, Алгебра та аналітична геометрія", "type": "linal"}
        }
    },
    2: { # ДРУГИЙ ТИЖДЕНЬ
        0: {
            2: {"name": "Лабораторна, Алгоритмізація та програмування", "type": "algo"},
            4: {"name": "Практика, Англійська мова", "type": "english"},
            5: {"name": "Практика, Алгоритмізація та програмування", "type": "algo"}
        },
        1: {},
        2: {
            1: {"name": "Лекція, Алгебра та аналітична геометрія", "type": "linal"},
            2: {"name": "Лекція, Дискретна математика", "type": "discrete"},
            3: {"name": "Лекція, Математичний аналіз", "type": "matan"}
        },
        3: {
            2: {"name": "Лекція, Алгоритмізація та програмування", "type": "algo"},
            3: {"name": "Лекція, Автоматизація та програмування", "type": "algo"}
        },
        4: {
            1: {"name": "Практика, Математичний аналіз", "type": "matan"},
            2: {"name": "Практика, Дискретна математика", "type": "discrete"},
            4: {"name": "Практика, Алгебра та аналітична геометрія", "type": "linal"}
        }
    }
}

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
LAST_SEEN_UID = None

# === ДОПОМІЖНІ ФУНКЦІЇ РОЗКЛАДУ ===
def get_current_week():
    now = datetime.now(KYIV_TZ)
    week_num = now.isocalendar()[1]
    return 1 if (week_num - 36) % 2 == 0 else 2

def get_keyboard(subject_type):
    if subject_type not in LINKS: return None
    buttons = []
    for btn_name, url in LINKS[subject_type]:
        buttons.append([InlineKeyboardButton(text=btn_name, url=url)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# === ЛОГІКА МЕНЮ /ZOOM ===
def get_zoom_main_keyboard():
    all_buttons = []
    for subj_key, links in LINKS.items():
        subj_name = SUBJECT_NAMES.get(subj_key, "Предмет")
        if len(links) == 1:
            all_buttons.append(InlineKeyboardButton(text=subj_name, url=links[0][1]))
        else:
            all_buttons.append(InlineKeyboardButton(text=subj_name, callback_data=f"zoom_{subj_key}"))
    
    # Додаємо кнопку закриття
    all_buttons.append(InlineKeyboardButton(text="❌ Закрити меню", callback_data="zoom_close"))
    
    # Розбиваємо всі зібрані кнопки по 2 в один ряд
    buttons = [all_buttons[i:i + 2] for i in range(0, len(all_buttons), 2)]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_zoom_sub_keyboard(subj_key):
    buttons = []
    for btn_name, url in LINKS[subj_key]:
        buttons.append([InlineKeyboardButton(text=btn_name, url=url)])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="zoom_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("zoom"))
async def cmd_zoom(message: Message):
    await message.reply("🔗 <b>Виберіть предмет:</b>", reply_markup=get_zoom_main_keyboard())

@dp.callback_query(F.data.startswith("zoom_"))
async def process_zoom_callback(callback: CallbackQuery):
    action = callback.data.split("_")[1]
    
    if action == "close":
        await callback.message.delete()
    elif action == "main":
        await callback.message.edit_text("🔗 <b>Виберіть предмет:</b>", reply_markup=get_zoom_main_keyboard())
    elif action in LINKS:
        subj_name = SUBJECT_NAMES.get(action, "Предмет")
        await callback.message.edit_text(f"🔗 <b>{subj_name}</b>\nВиберіть посилання:", reply_markup=get_zoom_sub_keyboard(action))
    
    await callback.answer()

# === ХЕНДЛЕРИ КОМАНД ===
@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    text = (
        "📚 <b>Меню команд:</b>\n"
        "/now - Що зараз (яка пара/перерва і коли наступна)\n"
        "/time_left - Час до кінця поточної пари\n"
        "/schedule - Розклад пар на сьогодні\n"
        "/time_schedule - Розклад дзвінків\n"
        "/zoom - Кнопки з усіма посиланнями на предмети\n"
        "/mute - Замутити когось на 10 хвилин\n"
        "/kurator_pidor - а ви спробуйте, ризикніть"
    )
    await message.reply(text)

@dp.message(Command("time_schedule"))
async def cmd_time_schedule(message: Message):
    text = "🔔 <b>Розклад дзвінків:</b>\n"
    for i, (start, end) in BELLS.items():
        text += f"{i} пара: {start} - {end}\n"
    await message.reply(text)

@dp.message(Command("schedule"))
async def cmd_schedule(message: Message):
    now = datetime.now(KYIV_TZ)
    day = now.weekday()
    week = get_current_week()
    
    if day > 4: 
        await message.reply("Сьогодні вихідний! Пар немає. 🍻")
        return
        
    todays_schedule = SCHEDULE[week].get(day, {})
    if not todays_schedule:
        await message.reply("На сьогодні пар немає, відпочиваємо!")
        return

    text = f"📅 <b>Розклад на сьогодні ({week}-й тиждень):</b>\n\n"
    for pair_num, data in sorted(todays_schedule.items()):
        start, end = BELLS[pair_num]
        text += f"<b>{pair_num} пара ({start}-{end})</b>\n{data['name']}\n\n"
    
    await message.reply(text)

@dp.message(Command("time_left"))
async def cmd_time_left(message: Message):
    now = datetime.now(KYIV_TZ)
    current_time = now.strftime("%H:%M")
    
    # 1. Перевіряємо, чи зараз йде якась пара
    for pair_num, (start, end) in BELLS.items():
        if start <= current_time <= end:
            end_dt = now.replace(hour=int(end.split(':')[0]), minute=int(end.split(':')[1]), second=0)
            left = end_dt - now
            mins_left = int(left.total_seconds() / 60)
            await message.reply(f"⏳ До кінця {pair_num} пари залишилось {mins_left} хв.")
            return
            
    # 2. Якщо пари зараз немає, шукаємо найближчу наступну (перерва або ранок)
    for pair_num, (start, end) in BELLS.items():
        if current_time < start:
            start_dt = now.replace(hour=int(start.split(':')[0]), minute=int(start.split(':')[1]), second=0)
            left = start_dt - now
            mins_left = int(left.total_seconds() / 60)
            
            # Додаємо умову, щоб гарно звучало, якщо до пари ще довго (наприклад, зранку)
            if mins_left > 60:
                hours = mins_left // 60
                mins = mins_left % 60
                time_str = f"{hours} год {mins} хв"
            else:
                time_str = f"{mins_left} хв"
                
            await message.reply(f"☕ До початку {pair_num} пари залишилось {time_str}.")
            return
            
    # 3. Якщо час більший за початок останньої пари (всі пари вже пройшли)
    await message.reply("На сьогодні всі пари вже закінчились! Відпочиваємо 🍻")
@dp.message(Command("now"))
async def cmd_now(message: Message):
    now = datetime.now(KYIV_TZ)
    current_time = now.strftime("%H:%M")
    day = now.weekday()
    week = get_current_week()
    
    if day > 4:
        await message.reply("Сьогодні вихідний! 🎉")
        return
        
    todays_schedule = SCHEDULE[week].get(day, {})
    
    for pair_num, (start, end) in BELLS.items():
        if start <= current_time <= end:
            if pair_num in todays_schedule:
                subject = todays_schedule[pair_num]
                text = f"🟢 <b>Зараз іде {pair_num} пара (до {end}):</b>\n{subject['name']}"
                kb = get_keyboard(subject['type'])
                
                next_pairs = [p for p in todays_schedule.keys() if p > pair_num]
                if next_pairs:
                    next_p = min(next_pairs)
                    text += f"\n\n▶️ Наступна {next_p} пара о {BELLS[next_p][0]}: {todays_schedule[next_p]['name']}"
                
                await message.reply(text, reply_markup=kb)
                return
            else:
                await message.reply("Зараз за розкладом у вас \"вікно\" (пари немає).")
                return

    future_pairs = [p for p, (start, end) in BELLS.items() if current_time < start and p in todays_schedule]
    if future_pairs:
        next_p = min(future_pairs)
        subj = todays_schedule[next_p]
        text = f"☕ <b>Зараз перерва.</b>\n\n▶️ {next_p} пара почнеться о {BELLS[next_p][0]}:\n{subj['name']}"
        kb = get_keyboard(subj['type'])
        await message.reply(text, reply_markup=kb)
    else:
        await message.reply("На сьогодні пари вже закінчились (або їх взагалі не було). Відпочиваємо! 🍻")

@dp.message(Command("mute"))
async def cmd_mute(message: Message):
    until_date = datetime.now(KYIV_TZ) + timedelta(minutes=10)
    try:
        await bot.restrict_chat_member(
            chat_id=message.chat.id, 
            user_id=message.from_user.id, 
            permissions=ChatPermissions(can_send_messages=False), 
            until_date=until_date
        )
        await message.reply(f"🤐 Користувач {message.from_user.first_name} самозамутився на 10 хвилин.")
    except Exception as e:
        await message.reply("Не можу видати мут. Бот повинен мати права адміністратора (Обмеження користувачів)!")

@dp.message(Command("kurator_pidor"))
async def cmd_kurator(message: Message):
    until_date = datetime.now(KYIV_TZ) + timedelta(minutes=30)
    try:
        await bot.restrict_chat_member(
            chat_id=message.chat.id, 
            user_id=message.from_user.id, 
            permissions=ChatPermissions(can_send_messages=False), 
            until_date=until_date
        )
        await message.reply(f"🚨 {message.from_user.first_name} отримав мут на 30 хвилин за таку команду.")
    except Exception as e:
        await message.reply("Не можу видати мут. Бот повинен мати права адміністратора (Обмеження користувачів)!")

# === ЛОГІКА ПЕРЕВІРКИ ПОШТИ (БЕЗ ЗМІН) ===
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

# === ВЕБ-СЕРВЕР ДЛЯ RENDER ===
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
    threading.Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
