import os
import time
from collections import deque
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Класс для генерации случайных чисел
class SimpleRNG:
    def __init__(self):
        self.seed = int(time.time() * 1000)
    
    def next(self):
        """Генерация следующего случайного числа"""
        self.seed = (1664525 * self.seed + 1013904223) & 0xFFFFFFFF
        return self.seed / 4294967296.0
    
    def choice(self, items):
        """Случайный выбор элемента из списка"""
        if not items:
            return None
        index = int(self.next() * len(items))
        return items[index]

# Класс для управления мемами и историей показов
class MemeManager:
    def __init__(self, max_global_history=5):
        self.rng = SimpleRNG()
        self.global_history = deque(maxlen=max_global_history)  # Глобальная история
        self.user_histories = {}  # Персональные истории пользователей
    
    def get_random_meme(self, memes_list, user_id):
        """Получение случайного мема с учетом истории"""
        # Получаем историю пользователя или создаем новую
        user_history = self.user_histories.get(user_id, set())
        
        # Доступные мемы (не в глобальной истории и не в истории пользователя)
        available_memes = [
            m for m in memes_list 
            if m not in self.global_history and 
            m not in user_history
        ]
        
        # Если все мемы были показаны, сбрасываем историю пользователя
        if not available_memes:
            available_memes = memes_list
            user_history = set()
        
        # Выбираем случайный мем
        chosen_meme = self.rng.choice(available_memes)
        
        # Обновляем истории
        self.global_history.append(chosen_meme)
        user_history.add(chosen_meme)
        self.user_histories[user_id] = user_history
        
        return chosen_meme

# Инициализация менеджера мемов
meme_manager = MemeManager(max_global_history=5)

# Настройки бота
TOKEN = "7554249769:AAEkxlkFaQS6RYNcDGaFIJVVeC8NvtKHTOw"  # Замените на ваш токен
MEMES_DIR = "memes"

# Клавиатура с категориями
keyboard = [
    ["Грустные", "Про работу", "Про учебу"],
    ["Глупые", "Котики", "Любые"]
]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Соответствие русских названий папкам
category_mapping = {
    "Грустные": "sad",
    "Про работу": "work",
    "Про учебу": "study",
    "Глупые": "stupid",
    "Котики": "cats"
}

def load_memes():
    """Загрузка мемов из папок"""
    memes = {}
    for russian_name, english_name in category_mapping.items():
        path = os.path.join(MEMES_DIR, english_name)
        if os.path.exists(path):
            memes[russian_name] = [
                os.path.join(path, file) 
                for file in os.listdir(path) 
                if file.lower().endswith(('.jpg', '.jpeg', '.png'))
            ]
            print(f"Загружено {len(memes[russian_name])} мемов из категории '{russian_name}'")
    return memes

# Загрузка мемов при старте
memes_db = load_memes()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "Выбери категорию мемов:",
        reply_markup=reply_markup
    )

async def send_meme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка случайного мема"""
    user_id = update.message.from_user.id
    chosen_category = update.message.text
    
    if chosen_category == "Любые":
        # Собираем все мемы из всех категорий
        all_memes = []
        for category in memes_db.values():
            all_memes.extend(category)
        
        if not all_memes:
            await update.message.reply_text("Нет доступных мемов")
            return
            
        meme_path = meme_manager.get_random_meme(all_memes, user_id)
        # Определяем категорию мема
        selected_category = next(
            (name for name, memes in memes_db.items() 
             if meme_path in memes),
            "Неизвестная категория"
        )
    else:
        # Проверяем существование категории
        if chosen_category not in memes_db or not memes_db[chosen_category]:
            await update.message.reply_text("В этой категории пока нет мемов")
            return
            
        selected_category = chosen_category
        meme_path = meme_manager.get_random_meme(memes_db[selected_category], user_id)

    # Отправка мема
    try:
        with open(meme_path, 'rb') as photo:
            await update.message.reply_photo(
                photo,
                caption=f"Категория: {selected_category}"
            )
    except Exception as e:
        print(f"Ошибка при отправке мема: {e}")
        await update.message.reply_text("Произошла ошибка при отправке мема")

def main():
    """Запуск бота"""
    print("Запуск мем-бота...")
    print("Доступные категории:", [cat for cat in memes_db.keys() if memes_db[cat]])
    
    app = Application.builder().token(TOKEN).build()
    
    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_meme))
    
    # Запуск бота
    app.run_polling()

if __name__ == "__main__":
    main()