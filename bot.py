import asyncio
import json
import os
from collections import defaultdict
import random
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode

# ===== КОНФИГУРАЦИЯ =====
BOT_TOKEN = "8989900194:AAFNG9gHkvCgy0LC76jsNB9pMOwgYUM-FzM"

# ТВОЙ ID (правильный)
ADMIN_IDS = [1087968824]
STATE_FILE = "game_state.json"
USER_BALANCE_FILE = "user_balances.json"
LAST_DAILY_FILE = "last_daily.json"
PRIZE_IMAGE = "prize.png"

# Глобальные переменные
game_active = True
winner_announced = False
user_attempts = defaultdict(int)
user_balances = defaultdict(int)
last_daily_bonus = defaultdict(lambda: None)
last_bank_message_time = None
current_prize_name = None
current_prize_url = None
reset_task = None

WIN_JACKPOT = 64

WIN_VALUES = {
    1: {"name": "три бара", "multiplier": 2, "emoji": "®️®️®️"},
    22: {"name": "три винограда", "multiplier": 2, "emoji": "🍇🍇🍇"},
    43: {"name": "три лимона", "multiplier": 2, "emoji": "🍋🍋🍋"},
    64: {"name": "ДЖЕКПОТ! три семёрки", "multiplier": 10, "emoji": "7️⃣7️⃣7️⃣"}
}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== РАБОТА С БАЛАНСАМИ =====
def load_balances():
    global user_balances
    if os.path.exists(USER_BALANCE_FILE):
        with open(USER_BALANCE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            user_balances = defaultdict(int, {int(k): v for k, v in data.items()})

def save_balances():
    with open(USER_BALANCE_FILE, "w", encoding="utf-8") as f:
        json.dump(dict(user_balances), f, ensure_ascii=False, indent=2)

def load_daily():
    global last_daily_bonus
    if os.path.exists(LAST_DAILY_FILE):
        with open(LAST_DAILY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            last_daily_bonus = defaultdict(lambda: None, {int(k): datetime.fromisoformat(v) if v else None for k, v in data.items()})

def save_daily():
    data = {uid: dt.isoformat() if dt else None for uid, dt in last_daily_bonus.items()}
    with open(LAST_DAILY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_stars(user_id: int, amount: int):
    user_balances[user_id] += amount
    save_balances()

def remove_stars(user_id: int, amount: int) -> bool:
    if user_balances[user_id] >= amount:
        user_balances[user_id] -= amount
        save_balances()
        return True
    return False

def get_balance(user_id: int) -> int:
    return user_balances[user_id]

async def check_daily_bonus(user_id: int, chat_id: int = None):
    now = datetime.now()
    last = last_daily_bonus[user_id]
    
    if last is None or (now - last) >= timedelta(hours=24):
        last_daily_bonus[user_id] = now
        add_stars(user_id, 1)
        save_daily()
        
        if chat_id:
            try:
                await bot.send_message(
                    chat_id,
                    f"⭐ **Ежедневный бонус!** +1⭐\n💰 Баланс: {get_balance(user_id)}⭐",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        return True
    return False

# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С ПРИЗАМИ =====
def extract_prize_name_from_url(url: str) -> str:
    match = re.search(r'/([A-Za-z0-9]+)-?\d*$', url)
    if match:
        return match.group(1)
    return "NFT"

def load_state():
    global game_active, winner_announced, user_attempts, last_bank_message_time, current_prize_name, current_prize_url
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            game_active = data.get("game_active", True)
            winner_announced = data.get("winner_announced", False)
            user_attempts = defaultdict(int, {int(k): v for k, v in data.get("user_attempts", {}).items()})
            last_bank_message_time = data.get("last_bank_message_time", None)
            if last_bank_message_time:
                last_bank_message_time = datetime.fromisoformat(last_bank_message_time)
            current_prize_name = data.get("current_prize_name", "NFT")
            current_prize_url = data.get("current_prize_url", None)
    
    load_balances()
    load_daily()

def save_state():
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "game_active": game_active,
            "winner_announced": winner_announced,
            "user_attempts": dict(user_attempts),
            "last_bank_message_time": last_bank_message_time.isoformat() if last_bank_message_time else None,
            "current_prize_name": current_prize_name,
            "current_prize_url": current_prize_url
        }, f, ensure_ascii=False, indent=2)

async def auto_reset_after_win(chat_id: int):
    global game_active, winner_announced, reset_task
    await asyncio.sleep(180)
    
    if not game_active or winner_announced:
        game_active = True
        winner_announced = False
        save_state()
        
        try:
            await bot.send_message(
                chat_id,
                f"🔄 **АВТОМАТИЧЕСКИЙ СБРОС** 🔄\n\n"
                f"🎰 Новый розыгрыш начат!\n"
                f"🎁 Приз: {current_prize_name}\n"
                f"🔗 {current_prize_url}\n\n"
                f"🍀 Удачи всем!",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
    
    reset_task = None

async def send_bank_message(chat_id: int):
    global last_bank_message_time
    current_time = datetime.now()
    
    if last_bank_message_time and (current_time - last_bank_message_time) < timedelta(hours=2):
        return
    
    last_bank_message_time = current_time
    save_state()
    
    prize_info = f"{current_prize_name}" if current_prize_name else "NFT"
    
    await bot.send_message(
        chat_id,
        f"🎁 **Банк подарков в профиле у @hazed_q!** 🎁\n\n"
        f"📦 Сейчас в розыгрыше: **{prize_info}**\n"
        f"🎰 Выбей 777 и забери его!\n\n"
        f"Все выигрыши выдаются через @hazed_q.",
        parse_mode=ParseMode.MARKDOWN
    )

# ===== КОМАНДА ДЛЯ ПРОВЕРКИ ID =====
@dp.message(Command("id"))
async def show_id(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    is_admin = user_id in ADMIN_IDS
    await message.answer(
        f"🆔 **Твой ID:** `{user_id}`\n"
        f"👤 **Имя:** {username}\n"
        f"👑 **Админ:** {'✅ Да' if is_admin else '❌ Нет'}",
        parse_mode=ParseMode.MARKDOWN
    )

# ===== КЛАВИАТУРЫ =====
def balance_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 15 звёзд", callback_data="withdraw_15")],
        [InlineKeyboardButton(text="⭐ 25 звёзд", callback_data="withdraw_25")],
        [InlineKeyboardButton(text="⭐ 50 звёзд", callback_data="withdraw_50")],
        [InlineKeyboardButton(text="⭐ 100 звёзд", callback_data="withdraw_100")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])

def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Вывести звёзды", callback_data="withdraw_menu")],
        [InlineKeyboardButton(text="🎁 Текущий приз", callback_data="current_prize")],
        [InlineKeyboardButton(text="📊 Топ игроков", callback_data="show_top")]
    ])

# ===== ОБРАБОТЧИКИ ЛС =====
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.first_name
    
    if get_balance(user_id) == 0:
        add_stars(user_id, 5)
    
    prize_info = f"{current_prize_name}" if current_prize_name else "?"
    
    await message.answer(
        f"🎰 **Здравствуйте, {username}!** 🎰\n\n"
        f"💰 **Баланс:** {get_balance(user_id)}⭐\n\n"
        f"🎁 **Текущий приз:** {prize_info}\n\n"
        f"👇 **Выбери действие:**",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

@dp.callback_query(lambda c: c.data == "withdraw_menu")
async def withdraw_menu(call: CallbackQuery):
    user_id = call.from_user.id
    await call.message.edit_text(
        f"💸 **Вывод звёзд**\n\n💰 Баланс: {get_balance(user_id)}⭐\n\nВыбери сумму:",
        reply_markup=balance_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    await call.answer()

@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(call: CallbackQuery):
    user_id = call.from_user.id
    username = call.from_user.first_name
    prize_info = f"{current_prize_name}" if current_prize_name else "?"
    
    await call.message.edit_text(
        f"🎰 **{username}**\n\n💰 Баланс: {get_balance(user_id)}⭐\n\n🎁 Приз: {prize_info}",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    await call.answer()

@dp.callback_query(lambda c: c.data == "current_prize")
async def show_current_prize(call: CallbackQuery):
    if current_prize_url:
        await call.message.answer(
            f"🎁 **Текущий розыгрыш:**\n\n"
            f"🏆 **{current_prize_name}**\n"
            f"🔗 {current_prize_url}\n\n"
            f"🎰 Выбей 777 в чате и забери его!"
        )
    else:
        await call.message.answer("🎁 Розыгрыш не запущен. Дождитесь команды /reset от администратора.")
    await call.answer()

@dp.callback_query(lambda c: c.data == "show_top")
async def show_top(call: CallbackQuery):
    sorted_users = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)[:5]
    if not sorted_users:
        await call.message.answer("📊 Пока нет игроков!")
        await call.answer()
        return
    
    text = "🏆 **ТОП ПО БАЛАНСУ** 🏆\n━━━━━━━━━━━━━━━\n"
    for i, (uid, balance) in enumerate(sorted_users, 1):
        try:
            user = await bot.get_chat(uid)
            name = user.first_name or str(uid)
            text += f"{i}. {name} — {balance}⭐\n"
        except:
            text += f"{i}. ID{uid} — {balance}⭐\n"
    
    await call.message.answer(text, parse_mode=ParseMode.MARKDOWN)
    await call.answer()

@dp.callback_query(lambda c: c.data.startswith("withdraw_"))
async def handle_withdraw(call: CallbackQuery):
    user_id = call.from_user.id
    username = call.from_user.first_name
    amount = int(call.data.split("_")[1])
    
    if remove_stars(user_id, amount):
        await call.message.edit_text(
            f"✅ **Заявка на вывод {amount}⭐ принята!**\n\n"
            f"💰 Новый баланс: {get_balance(user_id)}⭐\n\n"
            f"Ожидайте вывода от @hazed_q.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"💸 **ЗАЯВКА НА ВЫВОД**\n\n"
                    f"👤 {username}\n"
                    f"🆔 ID: {user_id}\n"
                    f"⭐ Сумма: {amount} звёзд\n\n"
                    f"Ссылка: tg://user?id={user_id}"
                )
            except:
                pass
    else:
        await call.message.edit_text(
            f"❌ **Ошибка!**\n\n"
            f"Не хватает {amount}⭐!\n"
            f"💰 Твой баланс: {get_balance(user_id)}⭐\n\n"
            f"Продолжай крутить 🎰, чтобы заработать больше!",
            reply_markup=balance_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    await call.answer()

# ===== АДМИНСКАЯ КОМАНДА /reset =====
@dp.message(Command("reset"))
async def cmd_reset(message: Message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer(f"❌ Ты не админ!")
        return
    
    global game_active, winner_announced, user_attempts, reset_task, current_prize_name, current_prize_url
    
    if reset_task:
        reset_task.cancel()
        reset_task = None
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❌ **Ошибка!**\n\n"
            "Использование: `/reset ссылка_на_предмет`\n\n"
            "Пример: `/reset https://t.me/nft/SwagBag-13848`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    prize_url = args[1].strip()
    prize_name = extract_prize_name_from_url(prize_url)
    
    # ⚠️ ГЛАВНОЕ: сбрасываем счётчики ВСЕХ игроков
    game_active = True
    winner_announced = False
    user_attempts.clear()  # ← ВОТ ЭТО ВАЖНО!
    current_prize_name = prize_name
    current_prize_url = prize_url
    save_state()
    
    try:
        if os.path.exists(PRIZE_IMAGE):
            photo = FSInputFile(PRIZE_IMAGE)
            await message.answer_photo(
                photo=photo,
                caption=(
                    f"🔄 **РОЗЫГРЫШ ПЕРЕЗАПУЩЕН!** 🔄\n\n"
                    f"🎁 **Приз:** {prize_name}\n"
                    f"🔗 {prize_url}\n\n"
                    f"🎰 **Задача:** выбить 777\n"
                    f"📊 Счётчики всех игроков обнулены!\n"
                    f"🍀 Удачи всем!"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await message.answer(
                f"🔄 **РОЗЫГРЫШ ПЕРЕЗАПУЩЕН!** 🔄\n\n"
                f"🎁 **Приз:** {prize_name}\n"
                f"🔗 {prize_url}\n\n"
                f"🎰 **Задача:** выбить 777\n"
                f"📊 Счётчики всех игроков обнулены!\n"
                f"🍀 Удачи всем!"
            )
    except Exception as e:
        await message.answer(
            f"🔄 **РОЗЫГРЫШ ПЕРЕЗАПУЩЕН!** 🔄\n\n"
            f"🎁 **Приз:** {prize_name}\n"
            f"🔗 {prize_url}\n\n"
            f"🎰 **Задача:** выбить 777\n"
            f"🍀 Удачи всем!"
        )
        print(f"Ошибка: {e}")

# ===== ОБРАБОТЧИК СЛОТА В ЧАТЕ =====
@dp.message(F.dice & F.dice.emoji == "🎰")
async def handle_slot(message: Message):
    global game_active, winner_announced, user_attempts, reset_task
    
    await send_bank_message(message.chat.id)
    
    if message.forward_date:
        return
    
    # Если игра остановлена (кто-то уже выиграл приз)
    if not game_active or winner_announced:
        await message.reply("⛔ Розыгрыш завершён! Дождитесь /reset от администратора.")
        return
    
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    result = message.dice.value
    
    await check_daily_bonus(user_id, message.chat.id)
    
    # Увеличиваем счётчик игрока
    user_attempts[user_id] += 1
    attempts = user_attempts[user_id]
    
    # Малые выигрыши (1, 22, 43)
    if result in WIN_VALUES and result != WIN_JACKPOT:
        win_info = WIN_VALUES[result]
        win_amount = win_info["multiplier"]
        add_stars(user_id, win_amount)
        await message.reply(
            f"🎉 {win_info['emoji']} **{win_info['name']}**! +{win_amount}⭐\n"
            f"💰 Баланс: {get_balance(user_id)}⭐",
            parse_mode=ParseMode.MARKDOWN
        )
        save_state()
    
    # ДЖЕКПОТ 777
    if result == WIN_JACKPOT:
        prize_name = current_prize_name if current_prize_name else "NFT"
        prize_url = current_prize_url if current_prize_url else "#"
        
        # Логика удаления/выдачи приза
        if attempts <= 100:
            # ДО 100 прокрутов: 100% удаление
            try:
                await message.delete()
                await message.answer("🚫 **Спам! Удаляю.**")
                print(f"🗑️ УДАЛЕНО: {username} выбил 777 на {attempts} попытке")
                
                # ⚠️ ОБНУЛЯЕМ СЧЁТЧИК ТОЛЬКО ЭТОГО ИГРОКА
                user_attempts[user_id] = 0
                save_state()
            except:
                pass
            
        else:
            # ПОСЛЕ 100 прокрутов: 25% удаление, 75% выдача приза
            should_delete = random.random() < 0.25
            
            if should_delete:
                # 25% - удаляем, приз НЕ выдаём
                try:
                    await message.delete()
                    await message.answer("🚫 **Спам! Удаляю.**")
                    print(f"🗑️ УДАЛЕНО: {username} выбил 777 на {attempts} попытке (25% шанс)")
                    
                    # ⚠️ ОБНУЛЯЕМ СЧЁТЧИК ТОЛЬКО ЭТОГО ИГРОКА
                    user_attempts[user_id] = 0
                    save_state()
                except:
                    pass
            else:
                # 75% - НЕ удаляем, ВЫДАЁМ ПРИЗ
                await message.reply(
                    f"🎉🎉🎉 **{username} ВЫБИЛ 777!** 🎉🎉🎉\n\n"
                    f"🎁 Ты выиграл: **{prize_name}**\n"
                    f"🔗 {prize_url}\n\n"
                    f"🎁 **За призом обращайся к @hazed_q**\n"
                    f"👑 Админам нужно написать: `/reset {prize_url}` для нового розыгрыша.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                print(f"🏆 ВЫИГРЫШ: {username} выбил 777 на {attempts} попытке! Выдан приз {prize_name}")
                print(f"   Счётчик {username} НЕ обнулён (осталось {user_attempts[user_id]})")
                
                # Останавливаем игру до команды /reset
                game_active = False
                winner_announced = True
                save_state()
                
                # Автосброс через 3 минуты
                if reset_task:
                    reset_task.cancel()
                reset_task = asyncio.create_task(auto_reset_after_win(message.chat.id))
                return
    
    # Подбадривание
    if user_attempts[user_id] >= 10 and user_attempts[user_id] % 5 == 0:
        encouragement = [
            f"💪 {username}, уже {user_attempts[user_id]} ставок! Додепай до 777!",
            f"🔥 {username}, {user_attempts[user_id]} прокрутов — твой час близок!",
        ]
        await message.reply(random.choice(encouragement))
    
    save_state()

# ===== ЗАПУСК =====
async def main():
    load_state()
    
    global game_active, winner_announced
    game_active = True
    winner_announced = False
    save_state()
    
    print("✅ Бот запущен!")
    print(f"👥 Админы: {ADMIN_IDS}")
    print(f"💰 Балансов: {len(user_balances)}")
    print(f"🎁 Текущий приз: {current_prize_name}")
    print("📊 Логика 777:")
    print("   - До 100 прокрутов: 100% удаление, приз НЕ выдаётся")
    print("   - После 100 прокрутов: 25% удаление, 75% выдача приза")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())