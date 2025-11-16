import os
import requests
from bs4 import BeautifulSoup
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

def get_ruonia_rate():
    """
    Scrape RUONIA rate from CBR website
    """
    try:
        url = 'https://cbr.ru/hd_base/ruonia/dynamics/'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the table with RUONIA rates
        table = soup.find('table', class_='data')
        if table:
            # Get the first data row (most recent rate)
            rows = table.find_all('tr')
            if len(rows) > 1:
                cols = rows[1].find_all('td')
                if len(cols) >= 2:
                    rate = cols[1].text.strip()
                    return float(rate.replace(',', '.'))
        
        return None
    except Exception as e:
        logger.error(f"Error getting RUONIA rate: {e}")
        return None

def get_key_rate():
    """
    Scrape key rate from CBR website
    """
    try:
        url = 'https://cbr.ru/hd_base/KeyRate/'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the table with key rates
        table = soup.find('table', class_='data')
        if table:
            # Get the first data row (most recent rate)
            rows = table.find_all('tr')
            if len(rows) > 1:
                cols = rows[1].find_all('td')
                if len(cols) >= 2:
                    rate = cols[1].text.strip()
                    return float(rate.replace(',', '.'))
        
        return None
    except Exception as e:
        logger.error(f"Error getting key rate: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Send a message when the command /start is issued.
    """
    await update.message.reply_text(
        'Привет! Я бот для мониторинга ставки RUONIA.\n'
        'Используйте /check чтобы получить текущие ставки.'
    )

async def check_rates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Check and display current RUONIA and key rates
    """
    await update.message.reply_text('Получаю данные...')
    
    ruonia = get_ruonia_rate()
    key_rate = get_key_rate()
    
    if ruonia is not None and key_rate is not None:
        difference = ruonia - key_rate
        
        message = (
            f"📊 Текущие ставки:\n\n"
            f"RUONIA: {ruonia}%\n"
            f"Ключевая ставка ЦБ: {key_rate}%\n"
            f"Разница: {difference:+.2f}%"
        )
    else:
        message = "❌ Ошибка при получении данных. Попробуйте позже."
    
    await update.message.reply_text(message)

def main() -> None:
    """
    Start the bot.
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        return
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check", check_rates))
    
    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
