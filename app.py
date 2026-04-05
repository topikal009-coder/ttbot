111import asyncio
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
    
    # Добавляем user-agent для имитации реального браузера
    options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
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
        
        # Ждем загрузки страницы
        wait = WebDriverWait(driver, 15)
        time.sleep(5)
        
        logger.info(f"Текущий URL после загрузки: {driver.current_url}")
        
        # Сохраняем HTML для отладки
        html_source = driver.page_source[:2000]
        logger.info(f"HTML страницы (первые 2000 символов): {html_source[:500]}...")
        
        # Пробуем найти iframe с формой
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            logger.info(f"Найдено iframe: {len(iframes)}")
            for i, iframe in enumerate(iframes):
                driver.switch_to.frame(iframe)
                inputs_in_iframe = driver.find_elements(By.TAG_NAME, "input")
                if inputs_in_iframe:
                    logger.info(f"В iframe {i} найдено полей: {len(inputs_in_iframe)}")
                    break
                else:
                    driver.switch_to.default_content()
        except Exception as e:
            logger.warning(f"Ошибка при работе с iframe: {e}")
            driver.switch_to.default_content()
        
        # Поиск ВСЕХ полей ввода
        all_inputs = driver.find_elements(By.TAG_NAME, "input")
        logger.info(f"Всего найдено полей ввода: {len(all_inputs)}")
        
        # Логируем все поля для отладки
        for i, inp in enumerate(all_inputs):
            input_type = inp.get_attribute("type")
            input_name = inp.get_attribute("name")
            input_id = inp.get_attribute("id")
            input_placeholder = inp.get_attribute("placeholder")
            input_class = inp.get_attribute("class")
            logger.info(f"Поле {i}: type={input_type}, name={input_name}, id={input_id}, placeholder={input_placeholder}, class={input_class}")
        
        # Поиск поля email
        email_field = None
        
        # Пробуем разные способы найти поле email
        email_selectors = [
            (By.ID, "login"),
            (By.ID, "email"),
            (By.ID, "username"),
            (By.NAME, "login"),
            (By.NAME, "email"),
            (By.NAME, "username"),
            (By.CSS_SELECTOR, "input[name='login']"),
            (By.CSS_SELECTOR, "input[name='email']"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[type='text']"),
            (By.XPATH, "//input[@placeholder='Email']"),
            (By.XPATH, "//input[@placeholder='Логин']"),
            (By.XPATH, "//input[@placeholder='E-mail']"),
            (By.XPATH, "//input[contains(@placeholder, 'mail')]"),
            (By.XPATH, "//input[contains(@placeholder, 'email')]"),
            (By.XPATH, "//label[contains(text(), 'Email')]/following-sibling::input"),
            (By.XPATH, "//label[contains(text(), 'Логин')]/following-sibling::input"),
            (By.XPATH, "//div[contains(@class, 'login')]//input"),
            (By.XPATH, "//div[contains(@class, 'email')]//input"),
        ]
        
        for by, selector in email_selectors:
            try:
                elements = driver.find_elements(by, selector)
                for elem in elements:
                    if elem and elem.is_displayed() and elem.is_enabled():
                        email_field = elem
                        logger.info(f"Найдено поле email по селектору: {selector}")
                        break
                if email_field:
                    break
            except Exception as e:
                continue
        
        # Если не нашли, ищем первое текстовое поле
        if not email_field:
            for inp in all_inputs:
                input_type = inp.get_attribute("type")
                if input_type in ["text", "email"]:
                    email_field = inp
                    logger.info(f"Выбрано первое текстовое поле как email: {inp.get_attribute('name')}")
                    break
        
        if not email_field:
            screenshot_path = f"debug_email_{int(time.time())}.png"
            driver.save_screenshot(screenshot_path)
            logger.error(f"Email поле не найдено. Скриншот: {screenshot_path}")
            return False, f"Поле email не найдено. Скриншот сохранен: {screenshot_path}"
        
        # Вводим email
        email_field.clear()
        email_field.send_keys(email)
        logger.info(f"Email введен: {email}")
        time.sleep(1)
        
        # Поиск поля пароля
        password_field = None
        
        password_selectors = [
            (By.ID, "password"),
            (By.ID, "pass"),
            (By.NAME, "password"),
            (By.NAME, "pass"),
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.XPATH, "//input[@placeholder='Пароль']"),
            (By.XPATH, "//input[@placeholder='Password']"),
            (By.XPATH, "//input[contains(@placeholder, 'парол')]"),
            (By.XPATH, "//label[contains(text(), 'Пароль')]/following-sibling::input"),
            (By.XPATH, "//label[contains(text(), 'Password')]/following-sibling::input"),
            (By.XPATH, "//div[contains(@class, 'password')]//input"),
        ]
        
        for by, selector in password_selectors:
            try:
                elements = driver.find_elements(by, selector)
                for elem in elements:
                    if elem and elem.is_displayed() and elem.is_enabled():
                        password_field = elem
                        logger.info(f"Найдено поле пароля по селектору: {selector}")
                        break
                if password_field:
                    break
            except Exception as e:
                continue
        
        # Если не нашли, ищем поле с type="password"
        if not password_field:
            for inp in all_inputs:
                input_type = inp.get_attribute("type")
                if input_type == "password":
                    password_field = inp
                    logger.info(f"Найдено поле пароля по type='password'")
                    break
        
        if not password_field:
            screenshot_path = f"debug_password_{int(time.time())}.png"
            driver.save_screenshot(screenshot_path)
            logger.error(f"Поле пароля не найдено. Скриншот: {screenshot_path}")
            return False, f"Поле пароля не найдено. Скриншот сохранен: {screenshot_path}"
        
        password_field.clear()
        password_field.send_keys(password)
        logger.info("Пароль введен")
        time.sleep(1)
        
        # Поиск поля подтверждения пароля
        try:
            confirm_selectors = [
                (By.ID, "confirm"),
                (By.ID, "confirm_password"),
                (By.NAME, "confirm"),
                (By.NAME, "confirm_password"),
                (By.CSS_SELECTOR, "input[name='confirm']"),
                (By.CSS_SELECTOR, "input[name='confirm_password']"),
                (By.XPATH, "//input[@placeholder='Подтверждение пароля']"),
                (By.XPATH, "//input[@placeholder='Confirm password']"),
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
        except Exception as e:
            logger.warning(f"Нет поля подтверждения пароля: {e}")
        
        # Поиск кнопки отправки
        submit_button = None
        submit_selectors = [
            (By.XPATH, "//button[@type='submit']"),
            (By.XPATH, "//button[contains(text(), 'Зарегистрироваться')]"),
            (By.XPATH, "//button[contains(text(), 'Регистрация')]"),
            (By.XPATH, "//button[contains(text(), 'Создать')]"),
            (By.XPATH, "//button[contains(text(), 'Зарегистрировать')]"),
            (By.XPATH, "//button[contains(text(), 'Register')]"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "button.submit"),
            (By.CSS_SELECTOR, ".submit-button"),
            (By.CSS_SELECTOR, "input[type='submit']"),
        ]
        
        for by, selector in submit_selectors:
            try:
                elements = driver.find_elements(by, selector)
                for elem in elements:
                    if elem and elem.is_displayed() and elem.is_enabled():
                        submit_button = elem
                        logger.info(f"Найдена кнопка по селектору: {selector}")
                        break
                if submit_button:
                    break
            except Exception as e:
                continue
        
        if not submit_button:
            # Ищем любую кнопку на странице
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if btn.is_displayed() and btn.is_enabled():
                    submit_button = btn
                    logger.info(f"Выбрана кнопка: {btn.text}")
                    break
        
        if not submit_button:
            screenshot_path = f"debug_button_{int(time.time())}.png"
            driver.save_screenshot(screenshot_path)
            logger.error(f"Кнопка отправки не найдена. Скриншот: {screenshot_path}")
            return False, f"Кнопка отправки не найдена. Скриншот сохранен: {screenshot_path}"
        
        submit_button.click()
        logger.info("Форма отправлена")
        
        # Ждем результат
        time.sleep(5)
        
        # Проверяем результат
        current_url = driver.current_url
        logger.info(f"URL после отправки: {current_url}")
        
        if "mail" in current_url or "success" in current_url.lower():
            return True, f"{email}:{password}"
        elif "captcha" in current_url.lower():
            return False, "Требуется решение капчи (автоматическое решение не реализовано)"
        elif "error" in current_url.lower():
            return False, "Ошибка регистрации. Возможно, email уже занят"
        else:
            # Проверяем наличие сообщений об ошибке
            try:
                error_msgs = driver.find_elements(By.CSS_SELECTOR, ".error, .error-message, .alert, .notification")
                for error in error_msgs:
                    error_text = error.text
                    if error_text:
                        return False, f"Ошибка: {error_text[:100]}"
            except:
                pass
            
            return False, "Регистрация не подтверждена. Проверьте вручную"
        
    except Exception as e:
        logger.error(f"Ошибка регистрации: {e}")
        if driver:
            try:
                screenshot_path = f"debug_exception_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                return False, f"Ошибка: {str(e)[:150]}. Скриншот: {screenshot_path}"
            except:
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
                f"• Возможно, сайт изменил форму регистрации\n"
                f"• Проверьте логи в Railway для деталей"
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
