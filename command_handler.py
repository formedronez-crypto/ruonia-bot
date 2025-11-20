#
#!usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime
from telegram import Bot
import asyncio
import json
import time

# Получаем токен и chat_id из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("Ошибка: Не указаны TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
    exit(1)

def get_ruonia_rate(max_retries=2, retry_delay=30):
    """Получение текущей ставки RUONIA с повторными попытками"""
    for attempt in range(max_retries):
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
                        rate_str = cells[1].get_text(strip=True)
                        return float(rate_str.replace(',', '.'))
            
            return None
        
        except Exception as e:
            print(f"Ошибка при получении RUONIA (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Повторная попытка через {retry_delay} секунд...")
                time.sleep(retry_delay)
            else:
                return None
    
    return None

def get_key_rate(max_retries=2, retry_delay=30):
    """Получение ключевой ставки ЦБ РФ с повторными попытками"""
    for attempt in range(max_retries):
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
            print(f"Ошибка при получении ключевой ставки (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Повторная попытка через {retry_delay} секунд...")
                time.sleep(retry_delay)
            else:
                return None
    
    return None

def get_key_rate_history():
    """Получение истории изменений ключевой ставки"""
    try:
        url = 'https://cbr.ru/hd_base/keyrate/'
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', class_='data')
        
        if table:
            rows = table.find_all('tr')[1:]  # Пропускаем заголовок
            history = []
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    date_str = cells[0].get_text(strip=True)
                    rate_str = cells[1].get_text(strip=True)
                    history.append({
                        'date': datetime.strptime(date_str, '%d.%m.%Y'),
                        'rate': float(rate_str.replace(',', '.'))
                    })
            return history
        return []
    except Exception as e:
        print(f"Ошибка при получении истории ключевой ставки: {e}")
        return []

def get_ruonia_history(start_date, end_date):
    """Получение истории RUONIA за период"""
    try:
        url = 'https://cbr.ru/hd_base/ruonia/dynamics/'
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', class_='data')
        
        if table:
            rows = table.find_all('tr')[1:]  # Пропускаем заголовок
            history = []
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    date_str = cells[0].get_text(strip=True)
                    rate_str = cells[1].get_text(strip=True)
                    date = datetime.strptime(date_str, '%d.%m.%Y')
                    
                    if start_date <= date <= end_date:
                        history.append({
                            'date': date,
                            'rate': float(rate_str.replace(',', '.'))
                        })
            return history
        return []
    except Exception as e:
        print(f"Ошибка при получении истории RUONIA: {e}")
        return []

def get_next_meeting_date():
    """Получение даты следующего заседания по ключевой ставке"""
    try:
        url = 'https://cbr.ru/DKP/cal_mp/'
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        today = datetime.now()
        
        # Ищем все даты заседаний
        date_elements = soup.find_all('h3')
        for elem in date_elements:
            text = elem.get_text(strip=True)
            # Пытаемся найти дату в формате "DD месяца YYYY года"
            match = re.search(r'(\d+)\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})', text)
            if match:
                day = int(match.group(1))
                month_name = match.group(2)
                year = int(match.group(3))
                
                months = {
                    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
                    'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
                    'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
                }
                month = months.get(month_name)
                
                if month:
                    meeting_date = datetime(year, month, day)
                    if meeting_date > today:
                        return meeting_date
        
        return None
    except Exception as e:
        print(f"Ошибка при получении даты следующего заседания: {e}")
        return None

def calculate_average_diff(ruonia_history, key_rate):
    """Расчет средней разницы между RUONIA и ключевой ставкой"""
    if not ruonia_history:
        return None
    
    diffs = [entry['rate'] - key_rate for entry in ruonia_history]
    avg_diff = sum(diffs) / len(diffs)
    return avg_diff

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
                    
                    # Получаем данные о ставках с retry логикой
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
                        
                        await bot.send_message(chat_id=chat_id, text=message_text)
                       with open('last_update_id.txt', 'w') as f:
                            f.write(str(update_id))
                           print(f"Сохранен update_id: {update_id}")
                        print(f"Сообщение отправлено в чат {chat_id}")
                    else:
                        await bot.send_message(chat_id=chat_id, text="Ошибка при получении данных о ставках. Попробуйте позже.")
                           with open('last_update_id.txt', 'w') as f:
                        f.write(str(update_id))                        print(f"Не удалось получить данные после повторных попыток")
                
                # Обработка команды /prog
                elif text.strip().lower() in ['/prog', '/прогноз']:
                    print(f"Получена команда {text} от {chat_id}")
                    
                    # Получаем историю ключевой ставки
                    key_rate_history = get_key_rate_history()
                    
                    if not key_rate_history or len(key_rate_history) < 2:
                        await bot.send_message(chat_id=chat_id, text="Не удалось получить данные об истории ключевой ставки.")
                        continue
                    
                    # Текущая ключевая ставка
                    current_key_rate = key_rate_history[0]['rate']
                    
                    # Дата последнего изменения (когда ставка была другой)
                    last_change_date = None
                    for i in range(1, len(key_rate_history)):
                        if key_rate_history[i]['rate'] != current_key_rate:
                            last_change_date = key_rate_history[i-1]['date']
                            break
                    
                    if not last_change_date:
                        last_change_date = key_rate_history[-1]['date']
                    
                    # Получаем историю RUONIA с момента последнего изменения
                    today = datetime.now()
                    ruonia_history = get_ruonia_history(last_change_date, today)
                    
                    # Рассчитываем среднюю разницу
                    avg_diff = calculate_average_diff(ruonia_history, current_key_rate)
                    
                    # Получаем дату следующего заседания
                    next_meeting = get_next_meeting_date()
                    
                    if avg_diff is not None and next_meeting:
                        # Форматируем сообщение
                        comparison = "ниже" if avg_diff < 0 else "выше"
                        
                        message_text = f"""📊 Прогноз и статистика:

С последнего изменения ключевой ставки от {last_change_date.strftime('%d.%m.%Y')} до {today.strftime('%d.%m.%Y')} ставка RUONIA была в среднем на {abs(avg_diff):.2f}% {comparison}, чем ключевая ставка.

Следующее заседание по ключевой ставке: {next_meeting.strftime('%d.%m.%Y')}"""
                        
                        await bot.send_message(chat_id=chat_id, text=message_text)
                           with open('last_update_id.txt', 'w') as f:
                            f.write(str(update_id))
                        print(f"Прогноз отправлен в чат {chat_id}")
                    else:
                        await bot.send_message(chat_id=chat_id, text="Не удалось получить данные для прогноза. Попробуйте позже.")
                        with open('last_update_id.txt', 'w') as f:
                         f.write(str(update_id))
        
        # Сохраняем максимальный ID обработанного апдейта
   
if __name__ == '__main__':
    asyncio.run(check_for_commands())
