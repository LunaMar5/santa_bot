import telebot
from telebot import types
import random
import json
import os
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("Не задана переменная окружения BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

DATA_FILE = 'games.json'

# ---------- Загрузка и сохранение ----------
def load_games():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_games():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(games, f, ensure_ascii=False, indent=2)

games = load_games()

def main_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton('🎄 Создать игру', callback_data='menu_newgame'),
        types.InlineKeyboardButton('📊 Статус игры', callback_data='menu_status')
    )
    kb.add(
        types.InlineKeyboardButton('🎁 Мой результат', callback_data='menu_myresult'),
        types.InlineKeyboardButton('❓ Помощь', callback_data='menu_help')
    )
    return kb
# ---------- Создание игры ----------
@bot.message_handler(commands=['newgame'])
def new_game(message):
    code = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=4))
    while code in games:
        code = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=4))

    user_id = str(message.from_user.id)
    name = message.from_user.first_name

    games[code] = {
        'organizer_id': message.from_user.id,
        'participants': {user_id: name},  # организатор сразу в игре
        'results': {}
    }
    save_games()

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton('📊 Статус игры', callback_data=f'org_status:{code}'))
    kb.add(types.InlineKeyboardButton('🚀 Запустить жеребьёвку', callback_data=f'org_start:{code}'))
    kb.add(types.InlineKeyboardButton('🔗 Показать ссылку', callback_data=f'org_link:{code}'))

    bot.reply_to(
        message,
        f"🎄 Игра создана!\n\nКод игры: `{code}`\n\n"
        f"Ты уже в игре как **{name}** (участников: 1).\n\n"
        f"Ссылка для друзей:\n"
        f"`https://t.me/Bot672_bot?start={code}`\n\n"
        f"Или пусть напишут вручную:\n`/join {code}`",
        parse_mode='Markdown',
        reply_markup=kb
    )
# ---------- Присоединение ----------
@bot.message_handler(commands=['join'])
def join_game(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Напиши код игры. Пример: `/join A7F9`", parse_mode='Markdown')
        return

    code = parts[1].strip().upper()
    if code not in games:
        bot.reply_to(message, f"Игра `{code}` не найдена. Проверь код.", parse_mode='Markdown')
        return

    user_id = str(message.from_user.id)
    if user_id in games[code]['participants']:
        bot.reply_to(message, "Ты уже участвуешь в этой игре!")
        return

    # Запоминаем код и просим имя
    msg = bot.reply_to(
        message,
        f"Как тебя зовут? Напиши имя, которое увидят другие участники игры `{code}`.",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, save_name, code)

# ---------- Присоединение: шаг 2 — сохраняем имя ----------
def save_name(message, code):
    user_id = str(message.from_user.id)
    name = message.text.strip()

    if code not in games:
        bot.reply_to(message, "Игра не найдена. Начни заново: /join КОД")
        return
    if user_id in games[code]['participants']:
        bot.reply_to(message, "Ты уже участвуешь в этой игре!")
        return
    if not name or len(name) > 50:
        bot.reply_to(message, "Имя должно быть от 1 до 50 символов. Попробуй ещё раз: /join " + code)
        return

    games[code]['participants'][user_id] = name
    save_games()

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton('📊 Статус игры', callback_data=f'org_status:{code}'))
    kb.add(types.InlineKeyboardButton('🎁 Мой результат', callback_data='menu_myresult'))

    bot.reply_to(
        message,
        f"✅ Ты в игре `{code}` как **{name}**.\n"
        f"Участников: {len(games[code]['participants'])}",
        parse_mode='Markdown',
        reply_markup=kb
    )
# ---------- Запуск жеребьёвки: показываем список ----------
@bot.message_handler(commands=['startgame'])
def start_game(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Напиши код игры. Пример: `/startgame A7F9`", parse_mode='Markdown')
        return

    code = parts[1].strip().upper()
    if code not in games:
        bot.reply_to(message, "Игра не найдена.")
        return

    game = games[code]
    if str(message.from_user.id) != str(game['organizer_id']):
        bot.reply_to(message, "Только создатель игры может её запустить.")
        return

    participants = list(game['participants'].values())
    if len(participants) < 2:
        bot.reply_to(message, "Нужно хотя бы 2 участника.")
        return

    names_list = '\n'.join(f"• {name}" for name in participants)
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton('✅ Да, запустить', callback_data=f'confirm:{code}'),
        types.InlineKeyboardButton('❌ Отмена', callback_data='cancel')
    )
    bot.reply_to(
        message,
        f"🎄 В игре {len(participants)} участник(ов):\n\n{names_list}\n\n"
        f"⚠️ **Важно:** те, кто не зашёл, не будут участвовать.\n"
        f"Запустить жеребьёвку?",
        parse_mode='Markdown',
        reply_markup=kb
    )

# ---------- Подтверждение или отмена ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm:') or call.data == 'cancel')
def handle_confirm(call):
    if call.data == 'cancel':
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="❌ Жеребьёвка отменена. Можно подождать ещё участников и запустить снова.",
        )
        bot.answer_callback_query(call.id)
        return

    code = call.data.split(':')[1]
    if code not in games:
        bot.answer_callback_query(call.id, "Игра не найдена", show_alert=True)
        return

    game = games[code]
    if str(call.from_user.id) != str(game['organizer_id']):
        bot.answer_callback_query(call.id, "Только создатель игры может её запустить", show_alert=True)
        return

    participants = list(game['participants'].keys())
    if len(participants) < 2:
        bot.answer_callback_query(call.id, "Нужно хотя бы 2 участника", show_alert=True)
        return

    # Честная жеребьёвка
    result = None
    for _ in range(1000):
        shuffled = participants[:]
        random.shuffle(shuffled)
        if all(shuffled[i] != participants[i] for i in range(len(participants))):
            result = shuffled
            break

    if result is None:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Не удалось провести жеребьёвку. Попробуй ещё раз.",
        )
        bot.answer_callback_query(call.id)
        return

    for giver_id, recipient_id in zip(participants, result):
        game['results'][giver_id] = game['participants'][recipient_id]
    save_games()

    # Рассылка
    failed = []
    for giver_id, recipient_name in game['results'].items():
        try:
            bot.send_message(
                int(giver_id),
                f"🎅 Ты — Тайный Санта для: **{recipient_name}**\n\n"
                f"Не забудь подготовить подарок! 🎁",
                parse_mode='Markdown'
            )
        except Exception:
            failed.append(giver_id)

    text = f"✅ Жеребьёвка проведена! Участников: {len(participants)}."
    if failed:
        text += f"\n\n⚠️ Не удалось написать {len(failed)} участник(ам). Возможно, они не нажали /start у бота."

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
    )
    bot.answer_callback_query(call.id)

# ---------- Справка и старт ----------
@bot.message_handler(commands=['start'])
def start(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) >= 2:
        code = parts[1].strip().upper()
        if code in games:
            user_id = str(message.from_user.id)
            if user_id in games[code]['participants']:
                bot.reply_to(message, "Ты уже участвуешь в этой игре!")
                return
            msg = bot.reply_to(
                message,
                f"Ты пришёл по приглашению в игру `{code}`.\n\n"
                f"Как тебя зовут? Напиши имя, которое увидят другие участники.",
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(msg, save_name, code)
            return
        else:
            bot.reply_to(message, f"Игра `{code}` не найдена. Проверь ссылку.", parse_mode='Markdown')
            return

    bot.reply_to(
        message,
        "🎄 **Тайный Санта**\n\nВыбери действие:",
        parse_mode='Markdown',
        reply_markup=main_menu()
    )

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(
        message,
        "🎄 **Тайный Санта**\n\n"
        "`/newgame` — создать игру\n"
        "`/join КОД` — присоединиться\n"
        "`/startgame КОД` — запустить жеребьёвку (только создатель)\n\n"
        "**Важно:** каждый участник должен нажать /start у бота, иначе не получит имя в личку.",
        parse_mode='Markdown'
    )

# ---------- /myresult — кому я дарю ----------
@bot.message_handler(commands=['myresult'])
def my_result(message):
    user_id = str(message.from_user.id)
    found = False

    for code, game in games.items():
        if user_id in game['results']:
            recipient = game['results'][user_id]
            bot.reply_to(
                message,
                f"🎅 В игре `{code}` ты — Тайный Санта для: **{recipient}**\n\n"
                f"Не забудь подготовить подарок! 🎁",
                parse_mode='Markdown'
            )
            found = True

    if not found:
        bot.reply_to(
            message,
            "Ты пока не участвуешь ни в одной завершённой жеребьёвке.\n"
            "Если игра ещё не запущена — дождись, когда организатор нажмёт /startgame."
        )

# ---------- /status КОД — кто уже зашёл ----------
@bot.message_handler(commands=['status'])
def status(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Напиши код игры. Пример: `/status A7F9`", parse_mode='Markdown')
        return

    code = parts[1].strip().upper()
    if code not in games:
        bot.reply_to(message, f"Игра `{code}` не найдена.", parse_mode='Markdown')
        return

    game = games[code]
    participants = game['participants']

    if not participants:
        bot.reply_to(message, f"В игре `{code}` пока никто не зашёл.", parse_mode='Markdown')
        return

    names_list = '\n'.join(f"• {name}" for name in participants.values())
    text = f"🎄 Игра `{code}`\n\nУчастников: {len(participants)}\n\n{names_list}"

    if game['results']:
        text += "\n\n✅ Жеребьёвка уже проведена."
    else:
        text += "\n\n⏳ Жеребьёвка ещё не запущена."

    bot.reply_to(message, text, parse_mode='Markdown')
@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_'))
def handle_menu(call):
    if call.data == 'menu_newgame':
        bot.send_message(call.message.chat.id, "Напиши /newgame, чтобы создать игру.")
        bot.answer_callback_query(call.id)

    elif call.data == 'menu_status':
        msg = bot.send_message(
            call.message.chat.id,
            "Напиши код игры, чтобы посмотреть статус. Пример: `A7F9`",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(msg, status_by_code)
        bot.answer_callback_query(call.id)

    elif call.data == 'menu_myresult':
        # Создаём «поддельное» сообщение с правильным from_user
        fake_message = call.message
        fake_message.from_user = call.from_user
        my_result(fake_message)
        bot.answer_callback_query(call.id)

    elif call.data == 'menu_help':
        bot.send_message(
            call.message.chat.id,
            "🎄 **Тайный Санта**\n\n"
            "`/newgame` — создать игру\n"
            "`/join КОД` — присоединиться\n"
            "`/startgame КОД` — запустить жеребьёвку (только создатель)\n"
            "`/status КОД` — статус игры\n"
            "`/myresult` — кому я дарю\n\n"
            "**Важно:** каждый участник должен нажать /start у бота.",
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)

# ---------- Статус по коду (для кнопки) ----------
def status_by_code(message):
    code = message.text.strip().upper()
    if code not in games:
        bot.reply_to(message, f"Игра `{code}` не найдена.", parse_mode='Markdown')
        return

    game = games[code]
    participants = game['participants']
    if not participants:
        bot.reply_to(message, f"В игре `{code}` пока никто не зашёл.", parse_mode='Markdown')
        return

    names_list = '\n'.join(f"• {name}" for name in participants.values())
    text = f"🎄 Игра `{code}`\n\nУчастников: {len(participants)}\n\n{names_list}"
    if game['results']:
        text += "\n\n✅ Жеребьёвка уже проведена."
    else:
        text += "\n\n⏳ Жеребьёвка ещё не запущена."

    bot.reply_to(message, text, parse_mode='Markdown')
@bot.callback_query_handler(func=lambda call: call.data.startswith('org_'))
def handle_org(call):
    action, code = call.data.split(':')
    if code not in games:
        bot.answer_callback_query(call.id, "Игра не найдена", show_alert=True)
        return

    game = games[code]

    if action == 'org_status':
        participants = game['participants']
        if not participants:
            bot.answer_callback_query(call.id, "В игре пока никто не зашёл", show_alert=True)
            return
        names_list = '\n'.join(f"• {name}" for name in participants.values())
        text = f"🎄 Игра `{code}`\n\nУчастников: {len(participants)}\n\n{names_list}"
        if game['results']:
            text += "\n\n✅ Жеребьёвка уже проведена."
        else:
            text += "\n\n⏳ Жеребьёвка ещё не запущена."
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
        bot.answer_callback_query(call.id)

    elif action == 'org_link':
        bot.send_message(
            call.message.chat.id,
            f"🔗 Ссылка для друзей:\n"
            f"`https://t.me/Bot672_bot?start={code}`\n\n"
            f"Или пусть напишут:\n`/join {code}`",
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)

    elif action == 'org_start':
        if str(call.from_user.id) != str(game['organizer_id']):
            bot.answer_callback_query(call.id, "Только создатель игры может её запустить", show_alert=True)
            return
        participants = list(game['participants'].values())
        if len(participants) < 2:
            bot.answer_callback_query(call.id, "Нужно хотя бы 2 участника", show_alert=True)
            return
        names_list = '\n'.join(f"• {name}" for name in participants)
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton('✅ Да, запустить', callback_data=f'confirm:{code}'),
            types.InlineKeyboardButton('❌ Отмена', callback_data='cancel')
        )
        bot.send_message(
            call.message.chat.id,
            f"🎄 В игре {len(participants)} участник(ов):\n\n{names_list}\n\n"
            f"⚠️ **Важно:** те, кто не зашёл, не будут участвовать.\n"
            f"Запустить жеребьёвку?",
            parse_mode='Markdown',
            reply_markup=kb
        )
        bot.answer_callback_query(call.id)
@bot.message_handler(func=lambda m: True)
def echo(message):
    bot.reply_to(message, f"Ты написал: {message.text}")

print("Бот запущен...")
bot.infinity_polling()