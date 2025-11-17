#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from telegram import Bot
import asyncio
import json

# Получаем токен и chat_id из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("Ошибка: Не указаны TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
    exit(1)

def get_ruonia_rate():
    """Получение текущей ставки RUONIA"""
    try:
        url = 'https://cbr.ru/hd_base/ruonia/'
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', class_='data')
        
        if table:
            rows = table.find_all('tr')
            if len(rows) > 1:
                cells = rows[1].find_all('td')
                if len(cells) >= 2:
                    rate_str = cells[1].get_text(strip=True)
                    return float(rate_str.replace(',', '.'))
        
        return None
        
    except Exception as e:
        print(f"Ошибка при получении RUONIA: {e}")
        return None

def get_key_rate():
    """Получение ключевой ставки ЦБ РФ"""
    try:
        url = 'https://cbr.ru/hd_base/keyrate/'
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', class_='data')
        
        if table:
            rows = table.find_all('tr')
            if len(rows) > 1:
                cells = rows[1].find_all('td')
                if len(cells) >= 2:
                    rate_column = cells[1].get_text(strip=True)
                    rate_str = rate_column.split()[0] if rate_column else None
                    return float(rate_str.replace(',', '.')) if rate_str else None
        
        return None
        
    except Exception as e:
        print(f"Ошибка при получении ключевой ставки: {e}")
        return None

async def check_for_commands():
    """Проверка новых команд от пользователя"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # Получаем ID последнего обработанного сообщения
    try:
        with open('last_update_id.txt', 'r') as f:
            last_update_id = int(f.read().strip())
    except FileNotFoundError:
        last_update_id = 0
    
    # Получаем новые сообщения
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates'
    params = {'offset': last_update_id + 1, 'limit': 10}
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if data.get('ok') and data.get('result'):
        for update in data['result']:
            update_id = update['update_id']
            
            if 'message' in update:
                message = update['message']
                chat_id = message['chat']['id']
                text = message.get('text', '')
                
                # Обработка команды /check
                if text.strip().lower() in ['/check', '/проверить']:
                    print(f"Получена команда {text} от {chat_id}")
                    
                    # Получаем данные о ставках
                    ruonia = get_ruonia_rate()
                    key_rate = get_key_rate()
                    
                    if ruonia and key_rate:
                        diff = ruonia - key_rate
                        today = datetime.now().strftime('%d.%m.%Y')
                        
                        # Формируем сообщение
                        if diff > 0:
                            emoji = '✅'
                            comparison = 'RUONIA выше ключевой ставки.'
                        elif diff < 0:
                            emoji = '⚠️'
                            comparison = 'RUONIA ниже ключевой ставки.'
                        else:
                            emoji = '🔵'
                            comparison = 'RUONIA равна ключевой ставке.'
                        
                        message_text = f"""📊 Ежедневный отчет по ставкам {today}:

📈 RUONIA: {ruonia:.2f}%
🏦 Ключевая ставка ЦБ: {key_rate:.2f}%

💡 Разница: {diff:+.2f}%

{emoji} {comparison}"""
                        
                        # Отправляем сообщение
                        await bot.send_message(chat_id=chat_id, text=message_text)
                        print(f"Сообщение отправлено в чат {chat_id}")
                    else:
                        await bot.send_message(chat_id=chat_id, text="Ошибка при получении данных о ставках.")
            
            # Сохраняем ID последнего обработанного сообщения
            with open('last_update_id.txt', 'w') as f:
                f.write(str(update_id))
    
    print("Проверка команд завершена")

if __name__ == '__main__':
    asyncio.run(check_for_commands())
