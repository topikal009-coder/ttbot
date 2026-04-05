import asyncio
import logging
import random
import string
import time
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium_stealth import stealth

TELEGRAM_BOT_TOKEN = "8710933878:AAHhqav-ZPa6OIXb5rRIcWH1Wj-dViw2Xgs"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_random_email() -> str:
    prefixes = ["user", "mail", "hello", "world", "test", "student"]
    return f"{random.choice(prefixes)}{random.randint(1000, 9999)}@rambler.ru"

def generate_random_password() -> str:
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(random.choices(chars, k=12))

def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--remote-debugging-port=9222")
    
    options.binary_location = "/usr/bin/google-chrome"
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        stealth(driver, languages=["ru-RU", "ru"], vendor="Google Inc.", platform="Linux")
    except:
        pass
    
    return driver

def register_rambler_email(email: str, password: str):
    driver = None
    try:
        driver = create_driver()
        driver.get("https://id.rambler.ru/registration")
        time.sleep(5)
        
        email_field = None
        for selector in ["#login", "input[name='login']", "input[type='email']"]:
            try:
                email_field = driver.find_element(By.CSS_SELECTOR, selector)
                if email_field:
                    break
            except:
                continue
        
        if not email_field:
            return False, "Не найдено поле email"
        
        email_field.send_keys(email)
        time.sleep(1)
        
        password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_field.send_keys(password)
        time.sleep(1)
        
        submit = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit.click()
        time.sleep(5)
        
        return True, f"{email}:{password}"
        
    except Exception as e:
        return False, str(e)[:200]
    finally:
        if driver:
            driver.quit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎓 Бот работает!\n\n/register - начать регистрацию\n/check - проверить Selenium")

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Проверка Selenium...")
    try:
        driver = create_driver()
        await update.message.reply_text("✅ Selenium работает!")
        driver.quit()
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:200]}")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🚀 Начать", callback_data="reg")]]
    await update.message.reply_text("🔐 Начать регистрацию?", reply_markup=InlineKeyboardMarkup(keyboard))

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "reg":
        email = generate_random_email()
        password = generate_random_password()
        
        await query.edit_message_text(f"🔄 Регистрация {email}...\n⏳ Подождите до 60 секунд...")
        
        success, result = await asyncio.get_event_loop().run_in_executor(
            None, register_rambler_email, email, password
        )
        
        if success:
            await query.message.reply_text(f"✅ Готово!\n📧 {email}\n🔑 {password}")
        else:
            await query.message.reply_text(f"❌ Ошибка: {result}")

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CallbackQueryHandler(callback))
    
    print("🤖 Бот запущен и слушает сообщения...")
    app.run_polling()

if __name__ == "__main__":
    main()
