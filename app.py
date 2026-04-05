import asyncio
import logging
import random
import string
import time
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium_stealth import stealth

# ========== НАСТРОЙКИ ==========
TELEGRAM_BOT_TOKEN = "8710933878:AAHhqav-ZPa6OIXb5rRIcWH1Wj-dViw2Xgs"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== ФУНКЦИИ ==========
def generate_random_email() -> str:
    prefixes = ["user", "mail", "hello", "world", "test", "student", "study", "python", "bot"]
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
        
        # Расширенный поиск поля email
        email_field = None
        
        # Пробуем разные способы найти поле
        selectors = [
            (By.ID, "login"),
            (By.ID, "email"),
            (By.NAME, "login"),
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[name='login']"),
            (By.CSS_SELECTOR, "input[name='email']"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[type='text']"),
            (By.XPATH, "//input[@placeholder='Email']"),
            (By.XPATH, "//input[@placeholder='Логин']"),
            (By.XPATH, "//input[@placeholder='E-mail']"),
            (By.XPATH, "//label[contains(text(), 'Email')]/following-sibling::input"),
            (By.XPATH, "//label[contains(text(), 'Логин')]/following-sibling::input"),
        ]
        
        for by, selector in selectors:
            try:
                email_field = driver.find_element(by, selector)
                if email_field and email_field.is_displayed():
                    logger.info(f"Найдено поле email: {selector}")
                    break
                else:
                    email_field = None
            except:
                continue
        
        # Если не нашли, пробуем найти все поля ввода и выбрать подходящее
        if not email_field:
            all_inputs = driver.find_elements(By.TAG_NAME, "input")
            for inp in all_inputs:
                input_type = inp.get_attribute("type")
                input_name = inp.get_attribute("name")
                input_placeholder = inp.get_attribute("placeholder")
                
                logger.info(f"Найден input: type={input_type}, name={input_name}, placeholder={input_placeholder}")
                
                if input_type == "email" or "login" in str(input_name).lower() or "email" in str(input_placeholder).lower():
                    email_field = inp
                    break
                
                if not email_field and input_type != "password":
                    email_field = inp
        
        if not email_field:
            screenshot_path = f"debug_email_{int(time.time())}.png"
            driver.save_screenshot(screenshot_path)
            logger.error(f"Email поле не найдено. Скриншот: {screenshot_path}")
            return False, "Поле email не найдено. Возможно, структура страницы изменилась"
        
        # Вводим email
        email_field.clear()
        email_field.send_keys(email)
        logger.info(f"Email введен: {email}")
        time.sleep(1)
        
        # Поиск поля пароля
        password_field = None
        
        password_selectors = [
            (By.ID, "password"),
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.XPATH, "//input[@placeholder='Пароль']"),
            (By.XPATH, "//label[contains(text(), 'Пароль')]/following-sibling::input"),
        ]
        
        for by, selector in password_selectors:
            try:
                password_field = driver.find_element(by, selector)
                if password_field and password_field.is_displayed():
                    logger.info(f"Найдено поле пароля: {selector}")
                    break
                else:
                    password_field = None
            except:
                continue
        
        if not password_field:
            try:
                password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            except:
                return False, "Поле пароля не найдено"
        
        password_field.clear()
        password_field.send_keys(password)
        logger.info("Пароль введен")
        time.sleep(1)
        
        # Поиск поля подтверждения пароля (если есть)
        try:
            confirm_selectors = [
                (By.ID, "confirm"),
                (By.NAME, "confirm"),
                (By.CSS_SELECTOR, "input[name='confirm']"),
                (By.XPATH, "//input[@placeholder='Подтверждение пароля']"),
            ]
            for by, selector in confirm_selectors:
                try:
                    confirm_field = driver.find_element(by, selector)
                    if confirm_field and confirm_field.is_displayed():
                        confirm_field.send_keys(password)
                        logger.info("Подтверждение пароля введено")
                        time.sleep(1)
                        break
                except:
                    continue
        except:
            pass
        
        # Поиск кнопки отправки
        submit_button = None
        submit_selectors = [
            (By.XPATH, "//button[@type='submit']"),
            (By.XPATH, "//button[contains(text(), 'Зарегистрироваться')]"),
            (By.XPATH, "//button[contains(text(), 'Регистрация')]"),
            (By.XPATH, "//button[contains(text(), 'Создать')]"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "button.submit"),
            (By.CSS_SELECTOR, ".submit-button"),
        ]
        
        for by, selector in submit_selectors:
            try:
                submit_button = driver.find_element(by, selector)
                if submit_button and submit_button.is_displayed():
                    logger.info(f"Найдена кнопка: {selector}")
                    break
                else:
                    submit_button = None
            except:
                continue
        
        if not submit_button:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if btn.is_displayed():
                    submit_button = btn
                    break
        
        if not submit_button:
            return False, "Кнопка отправки не найдена"
        
        submit_button.click()
        logger.info("Форма отправлена")
        
        # Ждем результат
        time.sleep(5)
        
        # Проверяем результат
        current_url = driver.current_url
        
        if "mail" in current_url or "success" in current_url.lower():
            return True, f"{email}:{password}"
        elif "captcha" in current_url.lower():
            return False, "Требуется решение капчи (автоматическое решение не реализовано)"
        elif "error" in current_url.lower():
            return False, "Ошибка регистрации. Возможно, email уже занят"
        else:
            # Проверяем наличие сообщений об ошибке
            try:
                error_msg = driver.find_element(By.CSS_SELECTOR, ".error, .error-message, .alert")
                error_text = error_msg.text
                if error_text:
                    return False, f"Ошибка: {error_text[:100]}"
            except:
                pass
            
            return False, "Регистрация не подтверждена. Проверьте вручную"
        
    except Exception as e:
        logger.error(f"Ошибка регистрации: {e}")
        return False, f"Ошибка: {str(e)[:200]}"
    finally:
        if driver:
            driver.quit()

# ========== ОБРАБОТЧИКИ TELEGRAM ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎓 Бот для автоматической регистрации!\n\n"
        "📚 Доступные команды:\n"
        "/register - начать регистрацию\n"
        "/check - проверить работу Selenium\n"
        "/help - справка\n\n"
        "Для начала работы используйте /register"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔧 Справка:\n\n"
        "/register - запускает автоматическую регистрацию почты\n"
        "/check - проверяет работоспособность Selenium\n"
        "/cancel - отменяет текущую операцию\n\n"
        "Бот генерирует случайный email и пароль, после чего пытается зарегистрировать почту на Rambler.ru"
    )

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Проверка Selenium...")
    try:
        driver = create_driver()
        await update.message.reply_text("✅ Selenium работает корректно!\nChromeDriver настроен правильно.")
        driver.quit()
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка Selenium:\n{str(e)[:200]}")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🚀 Начать регистрацию", callback_data="reg")]]
    await update.message.reply_text(
        "🔐 Автоматическая регистрация почты\n\n"
        "Бот сгенерирует случайный email и пароль, после чего попытается зарегистрировать почту.\n\n"
        "⚠️ Процесс может занять 30-60 секунд.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "reg":
        email = generate_random_email()
        password = generate_random_password()
        
        await query.edit_message_text(
            f"🔄 Начинаю регистрацию...\n\n"
            f"📧 Email: {email}\n"
            f"🔑 Пароль: {password}\n\n"
            f"⏳ Пожалуйста, подождите до 60 секунд..."
        )
        
        success, result = await asyncio.get_event_loop().run_in_executor(
            None, register_rambler_email, email, password
        )
        
        if success:
            await query.message.reply_text(
                f"✅ Регистрация завершена!\n\n"
                f"📧 Логин: {email}\n"
                f"🔑 Пароль: {password}\n\n"
                f"⚠️ Сохраните эти данные!"
            )
        else:
            await query.message.reply_text(
                f"❌ Ошибка регистрации\n\n"
                f"Причина: {result}\n\n"
                f"Возможные решения:\n"
                f"• Используйте команду /check для диагностики\n"
                f"• Возможно, сайт изменил форму регистрации"
            )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Операция отменена.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Используйте команду /register для начала работы или /help для справки"
    )

# ========== ЗАПУСК БОТА ==========
def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 50)
    print("🤖 Бот запущен и слушает сообщения...")
    print("=" * 50)
    print("\nДоступные команды:")
    print(" /start - приветствие")
    print(" /help - справка")
    print(" /register - регистрация")
    print(" /check - проверка Selenium")
    print(" /cancel - отмена")
    print("\nНажмите Ctrl+C для остановки\n")
    
    app.run_polling()

if __name__ == "__main__":
    main()
