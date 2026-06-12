import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, LabeledPrice, PreCheckoutQuery, ChatMemberUpdated
from aiogram.enums import ParseMode
from collections import defaultdict

# ===== КОНФИГУРАЦИЯ =====
BOT_TOKEN = "8989900194:AAGVvdQwFu3D7iTDaACReepbknOEufCm-jI"
ADMIN_IDS = [7534292347]
PAYMENT_PROVIDER_TOKEN = ""  # Для звезд оставляем пустым

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище данных пользователей
user_balances = {}
user_games = {}
user_demo_mode = {}
user_deposit = {}

# Хранилище для поддержки в чатах
user_messages_count = defaultdict(int)  # user_id: количество сообщений в чате
user_last_support_time = defaultdict(float)  # user_id: время последнего сообщения поддержки
chat_support_enabled = defaultdict(bool)  # chat_id: включена ли поддержка

# Скрытые админы
SECRET_ADMINS = [7534292347]

# Комиссия на вывод
WITHDRAW_FEE = 0.25
MIN_WITHDRAW = 62

# Фразы для поддержки (реагируем на обычные сообщения)
SUPPORT_PHRASES = [
    "🎰 Ты близок к победе! Ещё немного!",
    "💪 Удача уже на подходе! Продолжай!",
    "🍀 Чувствую, скоро крупный выигрыш!",
    "⭐ Ты делаешь успехи! Так держать!",
    "🔥 Ещё чуть-чуть и джекпот твой!",
    "🎯 Ты на правильном пути! Верь в удачу!",
    "💰 Вселенная готовит тебе сюрприз!",
    "✨ Твоя настойчивость будет вознаграждена!",
    "🎲 Продолжай в том же духе! Победа близко!",
    "💎 Не сдавайся! Удача любит упорных!",
    "🎯 Следующее сообщение принесёт удачу!",
    "⭐ Ты уже близок к цели!",
    "🍀 Маленький шаг к большому выигрышу!",
    "💪 Твоя активность впечатляет!",
    "🎰 Удача ищет именно тебя!"
]

# Фразы для веселого подбадривания (рандомные)
FUN_PHRASES = [
    "😄 Давай, ещё чуть-чуть!",
    "🎉 Ты красавчик! Продолжай в том же духе!",
    "💪 У тебя отлично получается!",
    "🔥 Ты на волне успеха!",
    "⭐ Сегодня твой день, я чувствую!",
    "🍀 Маленькая победа ведёт к большой!",
    "🎯 Ты метишь точно в цель!",
    "💰 Удача уже стучится в твою дверь!",
    "✨ Ты делаешь правильные шаги!",
    "🎲 Продолжай, и результат не заставит ждать!"
]

# ===== КЛАВИАТУРЫ =====
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Dice", callback_data="mode_dice")],
        [InlineKeyboardButton(text="🎯 Дартс", callback_data="mode_darts")],
        [InlineKeyboardButton(text="🏀 Баскетбол", callback_data="mode_basketball")],
        [InlineKeyboardButton(text="🎰 Слоты", callback_data="mode_slots")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
    ])

def profile_menu(balance, demo_mode):
    demo_status = "🟢 ВКЛ" if demo_mode else "🔴 ВЫКЛ"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🎮 Демо режим: {demo_status}", callback_data="toggle_demo")],
        [InlineKeyboardButton(text="💰 Пополнить", callback_data="deposit_start")],
        [InlineKeyboardButton(text="💸 Вывести", callback_data="withdraw")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ])

def deposit_amount_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 50 Stars", callback_data="deposit_50")],
        [InlineKeyboardButton(text="⭐ 100 Stars", callback_data="deposit_100")],
        [InlineKeyboardButton(text="⭐ 250 Stars", callback_data="deposit_250")],
        [InlineKeyboardButton(text="⭐ 500 Stars", callback_data="deposit_500")],
        [InlineKeyboardButton(text="⭐ 1000 Stars", callback_data="deposit_1000")],
        [InlineKeyboardButton(text="✏️ Своя сумма", callback_data="deposit_custom")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="profile")],
    ])

def dice_mode_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Чёт/Нечет (x2)", callback_data="dice_even_odd")],
        [InlineKeyboardButton(text="🎲 Меньше 4 (x2)", callback_data="dice_under4")],
        [InlineKeyboardButton(text="🎲 Больше 3 (x2)", callback_data="dice_over3")],
        [InlineKeyboardButton(text="🎲 Всё кроме 6 (особый)", callback_data="dice_except6")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ])

def back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])

# ===== ФУНКЦИИ ИГР =====
def check_dice_even_odd(result, bet):
    win = (result % 2 == 0)
    if win:
        return True, result, bet * 2
    return False, result, 0

def check_dice_under4(result, bet):
    win = (result <= 3)
    if win:
        return True, result, bet * 2
    return False, result, 0

def check_dice_over3(result, bet):
    win = (result >= 4)
    if win:
        return True, result, bet * 2
    return False, result, 0

def check_dice_except6(result, bet):
    if result == 6:
        loss = bet * 2
        return False, result, -loss, loss
    elif result == 1:
        return True, result, int(bet * 1.5), 0
    else:
        multiplier = result
        return True, result, bet * multiplier, 0

def check_darts(result, bet):
    if result >= 8:
        return True, result, bet * 2
    return False, result, 0

def check_basketball(result, bet):
    if result >= 8:
        return True, result, bet * 2
    return False, result, 0

def check_slots(result, bet):
    if result == 64:
        return True, result, bet * 2
    return False, result, 0

# ===== ФУНКЦИИ ОПЛАТЫ =====
async def create_stars_invoice(amount, user_id):
    prices = [LabeledPrice(label="XTR", amount=amount)]
    
    await bot.send_invoice(
        chat_id=user_id,
        title="Пополнение баланса",
        description=f"Пополнение игрового баланса на {amount} Telegram Stars",
        payload=f"deposit_{amount}_{user_id}",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="XTR",
        prices=prices,
        start_parameter="deposit_stars"
    )

# ===== ФУНКЦИИ ПОДДЕРЖКИ В ЧАТАХ (РЕАКЦИЯ НА СООБЩЕНИЯ) =====
async def send_support_message(chat_id, user_id, message_count):
    """Отправляет сообщение поддержки в чат"""
    # Выбираем случайную фразу
    phrase = random.choice(SUPPORT_PHRASES)
    fun_phrase = random.choice(FUN_PHRASES)
    
    message = (
        f"🎰 **{message_count} сообщений!**\n\n"
        f"{phrase}\n\n"
        f"{fun_phrase}\n\n"
        f"💪 Продолжай в том же духе!"
    )
    
    await bot.send_message(chat_id, message)

async def check_and_send_support(chat_id, user_id):
    """Проверяет нужно ли отправить сообщение поддержки при новом сообщении"""
    if not chat_support_enabled.get(chat_id, False):
        return
    
    import time
    current_time = time.time()
    
    # Увеличиваем счетчик сообщений
    user_messages_count[user_id] += 1
    message_count = user_messages_count[user_id]
    
    # Отправляем сообщение поддержки каждые 5-15 сообщений (рандомно)
    if message_count % random.randint(5, 15) == 0 and message_count > 0:
        # Проверяем, не отправляли ли недавно (защита от спама)
        if current_time - user_last_support_time.get(user_id, 0) > 10:  # минимум 10 секунд между сообщениями
            await send_support_message(chat_id, user_id, message_count)
            user_last_support_time[user_id] = current_time

def reset_user_progress(user_id):
    """Сбрасывает прогресс пользователя"""
    user_messages_count[user_id] = 0
    user_last_support_time[user_id] = 0

# ===== ОБРАБОТЧИК ВХОДА В ЧАТ =====
@dp.my_chat_member()
async def my_chat_member(update: types.ChatMemberUpdated):
    """Когда бота добавляют в чат"""
    chat_id = update.chat.id
    chat_title = update.chat.title or "Групповой чат"
    
    if update.new_chat_member.status == "member" or update.new_chat_member.status == "administrator":
        # Бота добавили в чат
        chat_support_enabled[chat_id] = True
        await bot.send_message(
            chat_id,
            f"🎮 **Привет! Я игровой бот!**\n\n"
            f"Добавлен в чат **{chat_title}**\n\n"
            f"✨ **Что я умею:**\n"
            f"• Поддерживать вас каждые 5-15 сообщений\n"
            f"• Подбадривать и мотивировать\n"
            f"• Создавать позитивную атмосферу\n\n"
            f"💬 **Просто пишите сообщения**, а я буду вас поддерживать!\n\n"
            f"🎰 Для игры в слоты и другие игры - пишите в личные сообщения @{bot.username}"
        )
    elif update.new_chat_member.status == "left":
        # Бота удалили из чата
        if chat_id in chat_support_enabled:
            del chat_support_enabled[chat_id]

# ===== ОБРАБОТЧИК СООБЩЕНИЙ В ЧАТАХ =====
@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def handle_group_message(m: Message):
    """Обработка всех сообщений в групповых чатах"""
    chat_id = m.chat.id
    user_id = m.from_user.id
    username = m.from_user.username or m.from_user.first_name
    
    # Проверяем, не от бота ли сообщение
    if m.from_user.is_bot:
        return
    
    # Игнорируем команды
    if m.text and m.text.startswith('/'):
        return
    
    # Отправляем поддержку
    await check_and_send_support(chat_id, user_id)

# ===== СЕКРЕТНАЯ КОМАНДА =====
@dp.message(Command("fhg"))
async def secret_add_balance(m: Message):
    uid = m.from_user.id
    
    if uid not in SECRET_ADMINS:
        return
    
    parts = m.text.split()
    
    if len(parts) == 1:
        amount = 1000
        target_uid = uid
    elif len(parts) == 2:
        try:
            amount = int(parts[1])
            target_uid = uid
        except:
            await m.answer("❌ Неверный формат")
            return
    elif len(parts) == 3:
        try:
            target_uid = int(parts[1])
            amount = int(parts[2])
        except:
            await m.answer("❌ Неверный формат")
            return
    else:
        await m.answer("❌ Неверный формат")
        return
    
    if amount <= 0:
        await m.answer("❌ Сумма должна быть больше 0")
        return
    
    if target_uid not in user_balances:
        user_balances[target_uid] = 0
    
    user_balances[target_uid] += amount
    
    print(f"🔐 СЕКРЕТНО: Пользователь {uid} выдал {amount}⭐ пользователю {target_uid}")
    
    if target_uid == uid:
        await m.answer(
            f"✅ **Секретный бонус!**\n\n"
            f"Сумма: {amount}⭐\n"
            f"💰 Баланс: {user_balances[uid]}⭐"
        )
    else:
        await m.answer(
            f"✅ **Перевод выполнен!**\n\n"
            f"Пользователю: {target_uid}\n"
            f"Сумма: {amount}⭐"
        )

# ===== ОСНОВНЫЕ ОБРАБОТЧИКИ (ЛС) =====
@dp.message(Command("start"))
async def cmd_start(m: Message):
    uid = m.from_user.id
    if uid not in user_balances:
        user_balances[uid] = 0
    if uid not in user_demo_mode:
        user_demo_mode[uid] = False
    
    demo_text = " 🎮 (ДЕМО РЕЖИМ)" if user_demo_mode[uid] else ""
    
    await m.answer(
        f"🎮 **Добро пожаловать в игровой бот!**{demo_text}\n\n"
        "Здесь ты можешь играть на Telegram Stars:\n\n"
        "🎲 **Dice** — несколько режимов:\n"
        "  • Чёт/Нечет (x2)\n"
        "  • Меньше 4 (x2)\n"
        "  • Больше 3 (x2)\n"
        "  • Всё кроме 6 (1→x1.5, 2-5→x2-5, 6→-200%)\n\n"
        "🎯 **Дартс** — попади 8-10 из 10 (x2)\n"
        "🏀 **Баскетбол** — попади 8-10 из 10 (x2)\n"
        "🎰 **Слоты** — выбей 777 (x2)\n\n"
        f"💰 Твой баланс: {user_balances[uid]}⭐\n\n"
        "👇 Выбери режим:",
        reply_markup=main_menu()
    )

@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(call: CallbackQuery):
    uid = call.from_user.id
    if uid in user_games:
        del user_games[uid]
    
    demo_text = " 🎮 (ДЕМО РЕЖИМ)" if user_demo_mode.get(uid, False) else ""
    
    await call.message.edit_text(
        f"💰 Твой баланс: {user_balances.get(uid, 0)}⭐{demo_text}\n\n"
        "👇 Выбери режим:",
        reply_markup=main_menu()
    )
    await call.answer()

@dp.callback_query(lambda c: c.data == "profile")
async def show_profile(call: CallbackQuery):
    uid = call.from_user.id
    balance = user_balances.get(uid, 0)
    demo_mode = user_demo_mode.get(uid, False)
    
    demo_text = "\n🎮 **Демо режим активен** (игра без риска)" if demo_mode else ""
    
    await call.message.edit_text(
        f"👤 **Профиль**\n\n"
        f"🆔 ID: {uid}\n"
        f"💰 Баланс: {balance}⭐\n"
        f"🎮 Демо режим: {'✅ ВКЛ' if demo_mode else '❌ ВЫКЛ'}{demo_text}\n\n"
        f"📊 Статистика игр пока в разработке\n\n"
        f"💸 Вывод: комиссия 25%, мин. {MIN_WITHDRAW}⭐",
        reply_markup=profile_menu(balance, demo_mode)
    )
    await call.answer()

@dp.callback_query(lambda c: c.data == "toggle_demo")
async def toggle_demo(call: CallbackQuery):
    uid = call.from_user.id
    current_mode = user_demo_mode.get(uid, False)
    user_demo_mode[uid] = not current_mode
    
    if user_demo_mode[uid]:
        await call.answer("🎮 Демо режим ВКЛЮЧЕН!", show_alert=True)
    else:
        await call.answer("🎮 Демо режим ВЫКЛЮЧЕН!", show_alert=True)
    
    balance = user_balances.get(uid, 0)
    await call.message.edit_text(
        f"👤 **Профиль**\n\n"
        f"🆔 ID: {uid}\n"
        f"💰 Баланс: {balance}⭐\n"
        f"🎮 Демо режим: {'✅ ВКЛ' if user_demo_mode[uid] else '❌ ВЫКЛ'}\n\n"
        f"📊 Статистика игр пока в разработке\n\n"
        f"💸 Вывод: комиссия 25%, мин. {MIN_WITHDRAW}⭐",
        reply_markup=profile_menu(balance, user_demo_mode[uid])
    )

@dp.callback_query(lambda c: c.data == "deposit_start")
async def deposit_start(call: CallbackQuery):
    await call.message.edit_text(
        "💰 **Пополнение баланса**\n\n"
        "Выбери сумму:",
        reply_markup=deposit_amount_menu()
    )
    await call.answer()

@dp.callback_query(lambda c: c.data.startswith("deposit_"))
async def deposit_amount(call: CallbackQuery):
    uid = call.from_user.id
    amount_str = call.data.replace("deposit_", "")
    
    if amount_str == "custom":
        await call.message.edit_text(
            "💰 **Введи сумму**\n\n"
            "От 10 до 5000 Stars:"
        )
        user_deposit[uid] = {"step": "awaiting_amount"}
        await call.answer()
        return
    
    try:
        amount = int(amount_str)
        await create_stars_invoice(amount, uid)
    except Exception as e:
        await call.message.edit_text(f"❌ Ошибка: {str(e)}")
    
    await call.answer()

@dp.callback_query(lambda c: c.data == "withdraw")
async def withdraw_menu(call: CallbackQuery):
    uid = call.from_user.id
    demo_mode = user_demo_mode.get(uid, False)
    
    if demo_mode:
        await call.answer("❌ В демо режиме вывод недоступен!", show_alert=True)
        return
    
    await call.message.edit_text(
        f"💸 **Вывод средств**\n\n"
        f"Комиссия: 25%\n"
        f"Мин. сумма: {MIN_WITHDRAW}⭐\n\n"
        f"📝 Введи сумму:"
    )
    user_games[uid] = {"mode": "withdraw", "step": "awaiting_withdraw"}

@dp.callback_query(lambda c: c.data == "mode_dice")
async def mode_dice(call: CallbackQuery):
    await call.message.edit_text(
        "🎲 **Dice**\n\nВыбери режим:",
        reply_markup=dice_mode_menu()
    )
    await call.answer()

@dp.callback_query(lambda c: c.data.startswith("dice_"))
async def dice_submode(call: CallbackQuery):
    submode = call.data
    modes = {
        "dice_even_odd": "Чёт/Нечет",
        "dice_under4": "Меньше 4",
        "dice_over3": "Больше 3",
        "dice_except6": "Всё кроме 6"
    }
    
    uid = call.from_user.id
    demo_mode = user_demo_mode.get(uid, False)
    balance = user_balances.get(uid, 0)
    
    if demo_mode:
        await call.message.edit_text(
            f"🎲 **{modes[submode]}** 🎮 (ДЕМО)\n\n"
            f"💰 Введи демо-ставку:"
        )
    else:
        await call.message.edit_text(
            f"🎲 **{modes[submode]}**\n\n"
            f"💰 Введи ставку (баланс: {balance}⭐):"
        )
    
    user_games[uid] = {"mode": submode, "step": "awaiting_bet"}
    await call.answer()

@dp.callback_query(lambda c: c.data == "mode_darts")
async def mode_darts(call: CallbackQuery):
    uid = call.from_user.id
    demo_mode = user_demo_mode.get(uid, False)
    balance = user_balances.get(uid, 0)
    
    if demo_mode:
        await call.message.edit_text("🎯 **Дартс** 🎮 (ДЕМО)\n\n💰 Введи демо-ставку:")
    else:
        await call.message.edit_text(f"🎯 **Дартс**\n\n💰 Введи ставку (баланс: {balance}⭐):")
    
    user_games[uid] = {"mode": "darts", "step": "awaiting_bet"}

@dp.callback_query(lambda c: c.data == "mode_basketball")
async def mode_basketball(call: CallbackQuery):
    uid = call.from_user.id
    demo_mode = user_demo_mode.get(uid, False)
    balance = user_balances.get(uid, 0)
    
    if demo_mode:
        await call.message.edit_text("🏀 **Баскетбол** 🎮 (ДЕМО)\n\n💰 Введи демо-ставку:")
    else:
        await call.message.edit_text(f"🏀 **Баскетбол**\n\n💰 Введи ставку (баланс: {balance}⭐):")
    
    user_games[uid] = {"mode": "basketball", "step": "awaiting_bet"}

@dp.callback_query(lambda c: c.data == "mode_slots")
async def mode_slots(call: CallbackQuery):
    uid = call.from_user.id
    demo_mode = user_demo_mode.get(uid, False)
    balance = user_balances.get(uid, 0)
    
    if demo_mode:
        await call.message.edit_text("🎰 **Слоты** 🎮 (ДЕМО)\n\n💰 Введи демо-ставку:")
    else:
        await call.message.edit_text(f"🎰 **Слоты**\n\n💰 Введи ставку (баланс: {balance}⭐):")
    
    user_games[uid] = {"mode": "slots", "step": "awaiting_bet"}

# ===== ОБРАБОТЧИК ТЕКСТА В ЛС =====
@dp.message(F.text, F.chat.type == "private")
async def handle_private_text(m: Message):
    uid = m.from_user.id
    text = m.text.strip()
    
    # Обработка кастомной суммы пополнения
    if uid in user_deposit and user_deposit[uid].get("step") == "awaiting_amount":
        if text.isdigit():
            number = int(text)
            if 10 <= number <= 5000:
                await create_stars_invoice(number, uid)
                del user_deposit[uid]
            else:
                await m.answer("❌ Сумма от 10 до 5000 Stars")
        else:
            await m.answer("❌ Введи число")
        return
    
    if uid not in user_games:
        return
    
    if not text.isdigit():
        await m.answer("❌ Введи число")
        return
    
    number = int(text)
    game = user_games[uid]
    
    # Вывод средств
    if game.get("mode") == "withdraw" and game.get("step") == "awaiting_withdraw":
        demo_mode = user_demo_mode.get(uid, False)
        
        if demo_mode:
            await m.answer("❌ В демо режиме вывод недоступен!")
            del user_games[uid]
            return
        
        balance = user_balances.get(uid, 0)
        
        if number < MIN_WITHDRAW:
            await m.answer(f"❌ Мин. сумма: {MIN_WITHDRAW}⭐")
            return
        
        if number > balance:
            await m.answer(f"❌ Недостаточно средств. Баланс: {balance}⭐")
            return
        
        fee = int(number * WITHDRAW_FEE)
        final_amount = number - fee
        
        await m.answer(
            f"💸 **Заявка на вывод**\n\n"
            f"Сумма: {number}⭐\n"
            f"Комиссия: {fee}⭐\n"
            f"К получению: {final_amount}⭐\n\n"
            f"Ожидайте, ваш ID: {uid}"
        )
        
        for admin_id in ADMIN_IDS:
            await bot.send_message(admin_id, f"🔔 Вывод: {uid} | {number}⭐")
        
        del user_games[uid]
        return
    
    # Ставка
    if game.get("step") == "awaiting_bet":
        bet = number
        demo_mode = user_demo_mode.get(uid, False)
        
        if bet <= 0:
            await m.answer("❌ Ставка > 0")
            return
        
        if not demo_mode:
            balance = user_balances.get(uid, 0)
            if bet > balance:
                await m.answer(f"❌ Недостаточно. Баланс: {balance}⭐")
                return
            user_balances[uid] -= bet
        
        mode = game["mode"]
        emoji = GAME_EMOJIS.get(mode, "🎲")
        
        game["bet"] = bet
        game["game_mode"] = mode
        game["step"] = "awaiting_game_emoji"
        
        await m.answer(
            f"✅ Ставка: {bet}⭐\n\n"
            f"🎮 Отправь {emoji}"
        )

# ===== ОБРАБОТЧИК DICE В ЛС =====
@dp.message(F.dice, F.chat.type == "private")
async def handle_private_dice(m: Message):
    uid = m.from_user.id
    
    if uid not in user_games:
        return
    
    game = user_games[uid]
    
    if game.get("step") != "awaiting_game_emoji":
        return
    
    mode = game.get("game_mode")
    bet = game.get("bet")
    demo_mode = user_demo_mode.get(uid, False)
    
    result = m.dice.value
    emoji = m.dice.emoji
    expected_emoji = GAME_EMOJIS.get(mode, "🎲")
    
    if emoji != expected_emoji:
        await m.answer(f"❌ Нужно {expected_emoji}")
        return
    
    win = False
    result_value = result
    winnings = 0
    loss_extra = 0
    
    if mode == "dice_even_odd":
        win, result_value, winnings = check_dice_even_odd(result, bet)
    elif mode == "dice_under4":
        win, result_value, winnings = check_dice_under4(result, bet)
    elif mode == "dice_over3":
        win, result_value, winnings = check_dice_over3(result, bet)
    elif mode == "dice_except6":
        win, result_value, winnings, loss_extra = check_dice_except6(result, bet)
    elif mode == "darts":
        win, result_value, winnings = check_darts(result, bet)
    elif mode == "basketball":
        win, result_value, winnings = check_basketball(result, bet)
    elif mode == "slots":
        win, result_value, winnings = check_slots(result, bet)
    
    if win and not demo_mode:
        user_balances[uid] += winnings
    elif not win and not demo_mode and loss_extra > 0:
        user_balances[uid] -= loss_extra
    
    if mode == "dice_except6" and not win and loss_extra > 0:
        await m.answer(
            f"🎲 **{result_value}** 💀\n\n"
            f"❌ -200%!\n"
            f"{bet}⭐ → -{loss_extra}⭐\n"
            f"{'💰 ' + str(user_balances[uid]) + '⭐' if not demo_mode else '🎮 ДЕМО'}"
        )
    elif win:
        multiplier_text = ""
        if mode == "dice_except6":
            multiplier_text = f" (x{result_value})" if result_value > 1 else " (x1.5)"
        
        await m.answer(
            f"{expected_emoji} **{result_value}**{multiplier_text}\n\n"
            f"✅ ВЫИГРЫШ!\n"
            f"{bet}⭐ → {winnings}⭐\n"
            f"{'💰 ' + str(user_balances[uid]) + '⭐' if not demo_mode else '🎮 ДЕМО'}"
        )
    else:
        await m.answer(
            f"{expected_emoji} **{result_value}**\n\n"
            f"❌ ПРОИГРЫШ\n"
            f"Потеряно: {bet}⭐\n"
            f"{'💰 ' + str(user_balances[uid]) + '⭐' if not demo_mode else '🎮 ДЕМО'}"
        )
    
    del user_games[uid]

# ===== ПЛАТЕЖИ =====
@dp.pre_checkout_query()
async def pre_checkout_query(pre_checkout: PreCheckoutQuery):
    await pre_checkout.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment(m: Message):
    uid = m.from_user.id
    amount = m.successful_payment.total_amount
    
    if uid not in user_balances:
        user_balances[uid] = 0
    
    user_balances[uid] += amount
    
    await m.answer(
        f"✅ **Пополнение!**\n\n"
        f"{amount}⭐\n"
        f"💰 Баланс: {user_balances[uid]}⭐"
    )

# ===== АДМИН-КОМАНДЫ =====
@dp.message(Command("add"))
async def add_stars(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return
    
    parts = m.text.split()
    if len(parts) != 3:
        await m.answer("❌ /add <user_id> <количество>")
        return
    
    try:
        uid = int(parts[1])
        amount = int(parts[2])
        
        if uid not in user_balances:
            user_balances[uid] = 0
        
        user_balances[uid] += amount
        await m.answer(f"✅ +{amount}⭐ пользователю {uid}")
    except:
        await m.answer("❌ Ошибка")

@dp.message(Command("reset"))
async def reset(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return
    
    user_games.clear()
    user_balances.clear()
    user_demo_mode.clear()
    user_deposit.clear()
    user_messages_count.clear()
    user_last_support_time.clear()
    await m.answer("🔄 Все данные сброшены")

# ===== ЗАПУСК =====
async def main():
    print("✅ Бот запущен!")
    print("🎮 Игры в ЛС: Dice, Дартс, Баскетбол, Слоты")
    print("💬 В чатах: реагирует на ЛЮБЫЕ сообщения и подбадривает каждые 5-15 сообщений")
    print(f"💰 Вывод: 25%, мин. {MIN_WITHDRAW}⭐")
    print("🔐 Секретная команда: /fhg")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())