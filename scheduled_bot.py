#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
from bs4 import BeautifulSoup
from telegram import Bot
import asyncio
from datetime import datetime

# Получаем токен и chat_id из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("Ошибка: Не указаны TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
    exit(1)

def get_ruonia_rate():
    """Получение текущей ставки RUONIA"""
    try:
        url = 'https://cbr.ru/hd_base/ruonia/dynamics/'
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', class_='data')
        
        if table:
            rows = table.find_all('tr')
            if len(rows) > 1:
                cells = rows[1].find_all('td')
                if len(cells) >= 2:
                    rate_text = cells[1].get_text(strip=True)
                    return float(rate_text.replace(',', '.'))
        return None
    except Exception as e:
        print(f"Ошибка при получении RUONIA: {e}")
        return None

def get_key_rate():
    """Получение ключевой ставки ЦБ РФ"""
    try:
        url = 'https://cbr.ru/hd_base/KeyRate/'
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', class_='data')
        
        if table:
            rows = table.find_all('tr')
            if len(rows) > 1:
                cells = rows[1].find_all('td')
                if len(cells) >= 2:
                    rate_text = cells[1].get_text(strip=True)
                    return float(rate_text.replace(',', '.'))
        return None
    except Exception as e:
        print(f"Ошибка при получении ключевой ставки: {e}")
        return None

async def send_daily_report():
    """Отправка ежедневного отчета"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # Получаем ставки
    ruonia = get_ruonia_rate()
    key_rate = get_key_rate()
    
    if ruonia is None or key_rate is None:
        message = "⚠️ Ошибка получения данных о ставках"
    else:
        difference = ruonia - key_rate
        current_date = datetime.now().strftime('%d.%m.%Y')
        
        message = f"""
📈 <b>Ежедневный отчет по ставкам ({current_date})</b>

📊 RUONIA: <b>{ruonia:.2f}%</b>
🏦 Ключевая ставка ЦБ: <b>{key_rate:.2f}%</b>

🔄 Разница: <b>{difference:+.2f}%</b>
        """.strip()
        
        if difference > 0:
            message += "\n\nℹ️ RUONIA <b>выше</b> ключевой ставки"
        elif difference < 0:
            message += "\n\nℹ️ RUONIA <b>ниже</b> ключевой ставки"
        else:
            message += "\n\nℹ️ RUONIA <b>равна</b> ключевой ставке"
    
    # Отправляем сообщение
    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode='HTML'
        )
        print(f"Сообщение успешно отправлено в chat_id: {TELEGRAM_CHAT_ID}")
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")

if __name__ == '__main__':
    asyncio.run(send_daily_report())
