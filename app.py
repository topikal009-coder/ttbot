import asyncio
import logging
import random
import string
import time
import os
from flask import Flask, request, jsonify
from threading import Thread

# Импорты для Telegram бота
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, filters, ContextTypes

# Импорты для Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from selenium_stealth import stealth

# ========== НАСТРОЙКИ ==========
TELEGRAM_BOT_TOKEN = "8710933878:AAHhqav-ZPa6OIXb5rRIcWH1Wj-dViw2Xgs"
WEBHOOK_URL = os.environ.get("RAILWAY_STATIC_URL", "https://your-app.up.railway.app")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask приложение для Railway
app = Flask(__name__)

# Глобальная переменная для бота
telegram_app = None

# ========== ФУНКЦИИ БОТА ==========
def generate_random_email() -> str:
    prefixes = ["user", "mail", "hello", "world", "test", "student"]
    prefix = random.choice(prefixes)
    numbers = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}{numbers}@rambler.ru"

def generate_random_password(length: int = 12) -> str:
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%^&*"
    all_chars = lowercase + uppercase + digits + symbols
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(symbols)
    ]
    password += random.choices(all_chars, k=length - 4)
    random.shuffle(password)
    return ''.join(password)

def create_stealth_driver() -> webdriver.Chrome:
    chrome_options = Options()
    # Важно для Railway — headless режим
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        from selenium_stealth import stealth
        stealth(driver, languages=["ru-RU", "ru"], vendor="Google Inc.", platform="Win32")
    except:
        pass
    
    return driver

def register_rambler_email(email: str, password: str, user_id: int = None):
    driver = None
    try:
        driver = create_stealth_driver()
        logger.info(f"Chrome драйвер создан для {email}")
        
        driver.get("https://id.rambler.ru/registration")
        time.sleep(3)
        
        email_selectors = [
            (By.ID, "login"), (By.NAME, "login"),
            (By.CSS_SELECTOR, "input[name='login']"),
            (By.XPATH, "//input[@placeholder*='Email']")
        ]
        
        email_field = None
        for by, selector in email_selectors:
            try:
                email_field = driver.find_element(by, selector)
                if email_field:
                    break
            except:
                continue
        
        if not email_field:
            return False, "Не найдено поле для ввода email"
        
        email_field.clear()
        email_field.send_keys(email)
        time.sleep(1)
        
        password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_field.clear()
        password_field.send_keys(password)
        time.sleep(1)
        
        submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        submit_button.click()
        time.sleep(5)
        
        current_url = driver.current_url
        if "mail" in current_url or "success" in current_url.lower():
            return True, f"{email}:{password}"
        elif "captcha" in current_url.lower():
            return False, "Требуется решение капчи"
        else:
            return False, "Ошибка регистрации"
            
    except Exception as e:
        logger.error(f"Ошибка регистрации: {e}")
        return False, f"Ошибка: {str(e)[:200]}"
    finally:
        if driver:
            driver.quit()

# ========== ОБРАБОТЧИКИ TELEGRAM ==========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎓 Добро пожаловать!\n\n/register - начать регистрацию\n/check - проверить Selenium"
    )

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Проверяю Selenium...")
    try:
        loop = asyncio.get_event_loop()
        driver = await loop.run_in_executor(None, create_stealth_driver)
        await update.message.reply_text("✅ Selenium работает!")
        driver.quit()
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:200]}")

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🚀 Стандартная регистрация", callback_data="reg_standard")],
                [InlineKeyboardButton("❌ Отмена", callback_data="reg_cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔐 Автоматическая регистрация", reply_markup=reply_markup)

async def register_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "reg_cancel":
        await query.edit_message_text("❌ Отменено.")
        return
    
    email = generate_random_email()
    password = generate_random_password()
    
    await query.edit_message_text(f"🔄 Регистрация {email}...\n⏳ Подождите...")
    
    loop = asyncio.get_event_loop()
    success, result = await loop.run_in_executor(None, register_rambler_email, email, password, query.from_user.id)
    
    if success:
        await context.bot.send_message(query.from_user.id, f"✅ Готово!\n📧 {email}\n🔑 {password}")
    else:
        await context.bot.send_message(query.from_user.id, f"❌ Ошибка: {result}")

# ========== ЗАПУСК БОТА В ОТДЕЛЬНОМ ПОТОКЕ ==========
def run_telegram_bot():
    global telegram_app
    telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("check", check_command))
    telegram_app.add_handler(CommandHandler("register", register_command))
    telegram_app.add_handler(CallbackQueryHandler(register_callback))
    
    # Установка webhook для Railway
    telegram_app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=f"{WEBHOOK_URL}/webhook"
    )

# ========== FLASK ЭНДПОИНТЫ ==========
@app.route("/")
def home():
    return {"status": "Бот работает!", "webhook_url": WEBHOOK_URL}

@app.route("/webhook", methods=["POST"])
def webhook():
    if telegram_app:
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        telegram_app.process_update(update)
    return "ok", 200

@app.route("/health")
def health():
    return {"status": "healthy"}, 200

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    # Запускаем Telegram бота в отдельном потоке
    bot_thread = Thread(target=run_telegram_bot)
    bot_thread.start()
    
    # Запускаем Flask для Railway
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))