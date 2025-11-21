#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
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

def get_key_rate_from_main_page(max_retries=2, retry_delay=30):
    """Получение ключевой ставки и даты установления с главной страницы ЦБ"""
    for attempt in range(max_retries):
        try:
            url = 'https://www.cbr.ru/key-indicators/'
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ищем ключевую ставку и дату
            key_rate = None
            key_rate_date = None
            
            # Поиск текста "с 27.10.2025" и "16,50%"
            text = soup.get_text()
            
            # Ищем паттерн "с ДД.ММ.ГГГГ"
            date_match = re.search(r'с\s+(\d{2}\.\d{2}\.\d{4})', text)
            if date_match:
                key_rate_date_str = date_match.group(1)
                key_rate_date = datetime.strptime(key_rate_date_str, '%d.%m.%Y')
            
            # Ищем ключевую ставку после даты
            rate_match = re.search(r'с\s+\d{2}\.\d{2}\.\d{4}\s+([\d,]+)%', text)
            if rate_match:
                key_rate = float(rate_match.group(1).replace(',', '.'))
            
            if key_rate and key_rate_date:
                return key_rate, key_rate_date
            
            return None, None
        
        except Exception as e:
            print(f"Ошибка при получении ключевой ставки с главной (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Повторная попытка через {retry_delay} секунд...")
                time.sleep(retry_delay)
            else:
                return None, None
    
    return None, None

def get_ruonia_rate_from_main_page(max_retries=2, retry_delay=30):
    """Получение текущей ставки RUONIA с главной страницы"""
    for attempt in range(max_retries):
        try:
            url = 'https://www.cbr.ru/key-indicators/'
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text()
            
            # Ищем "RUONIA за ДД.ММ.ГГГГ|XX,XX"
            ruonia_match = re.search(r'RUONIA\s+за\s+\d{2}\.\d{2}\.\d{4}\s+([\d,]+)', text)
            if ruonia_match:
                return float(ruonia_match.group(1).replace(',', '.'))
            
            return None
        
        except Exception as e:
            print(f"Ошибка при получении RUONIA с главной (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Повторная попытка через {retry_delay} секунд...")
                time.sleep(retry_delay)
            else:
                return None
    
    return None

def get_ruonia_rate(max_retries=2, retry_delay=30):
    """Получение текущей ставки RUONIA со страницы динамики (запасной вариант)"""
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

def get_next_meeting_date(max_retries=2, retry_delay=30):
    """Получение даты следующего заседания по ключевой ставке"""
    for attempt in range(max_retries):
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
            print(f"Ошибка при получении даты следующего заседания (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Повторная попытка через {retry_delay} секунд...")
                time.sleep(retry_delay)
            else:
                return None
    
    return None

def get_ruonia_history_parametrized(start_date, end_date, max_retries=2, retry_delay=30):
    """Получение истории RUONIA за период с использованием параметров в URL"""
    for attempt in range(max_retries):
        try:
            # Форматируем даты в формат ДД.ММ.ГГГГ для URL
            start_str = start_date.strftime('%d.%m.%Y')
            end_str = end_date.strftime('%d.%m.%Y')
            
            url = f'https://cbr.ru/hd_base/ruonia/dynamics/?UniDbQuery.Posted=True&UniDbQuery.From={start_str}&UniDbQuery.To={end_str}'
            
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
                        try:
                            date = datetime.strptime(date_str, '%d.%m.%Y')
                            rate = float(rate_str.replace(',', '.'))
                            history.append({
                                'date': date,
                                'rate': rate
                            })
                        except ValueError:
                            continue
                return history
            return []
        except Exception as e:
            print(f"Ошибка при получении истории RUONIA (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Повторная попытка через {retry_delay} секунд...")
                time.sleep(retry_delay)
            else:
                return []
    
    return []

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
                    
                    # Получаем текущие данные
                    ruonia = get_ruonia_rate_from_main_page()
                    key_rate, key_rate_date = get_key_rate_from_main_page()
                    
                    # Если не получилось, пробуем старый метод
                    if not ruonia:
                        ruonia = get_ruonia_rate()
                    
                    if ruonia and key_rate:
                        diff = ruonia - key_rate
                        today = datetime.now()
                        today_str = today.strftime('%d.%m.%Y')
                        
                        # Формируем базовое сообщение
                        if diff > 0:
                            emoji = '✅'
                            comparison = 'RUONIA выше ключевой ставки.'
                        elif diff < 0:
                            emoji = '⚠️'
                            comparison = 'RUONIA ниже ключевой ставки.'
                        else:
                            emoji = '🔵'
                            comparison = 'RUONIA равна ключевой ставке.'
                        
                        message_text = f"""📊 Ежедневный отчет по ставкам {today_str}:

📈 RUONIA: {ruonia:.2f}%
🏦 Ключевая ставка ЦБ: {key_rate:.2f}%
💡 Разница сегодня: {diff:+.2f}%
{emoji} {comparison}"""
                        
                        # Добавляем статистику с последнего заседания
                        if key_rate_date:
                            ruonia_history = get_ruonia_history_parametrized(key_rate_date, today)
                            
                            if ruonia_history:
                                avg_diff = calculate_average_diff(ruonia_history, key_rate)
                                
                                if avg_diff is not None:
                                    comparison_avg = "ниже" if avg_diff < 0 else "выше"
                                    days_count = len(ruonia_history)
                                    
                                    message_text += f"""

📅 Статистика с {key_rate_date.strftime('%d.%m.%Y')}:
📊 Средняя разница: {abs(avg_diff):.2f}% {comparison_avg}
📆 Торговых дней: {days_count}"""
                        
                        # Добавляем дату следующего заседания
                        next_meeting = get_next_meeting_date()
                        if next_meeting:
                            days_until = (next_meeting - today).days
                            message_text += f"""

🗓 Следующее заседание: {next_meeting.strftime('%d.%m.%Y')}
⏳ Осталось дней: {days_until}"""
                        
                        await bot.send_message(chat_id=chat_id, text=message_text)
                        with open('last_update_id.txt', 'w') as f:
                            f.write(str(update_id))
                            print(f"Сохранен update_id: {update_id}")
                        print(f"Сообщение отправлено в чат {chat_id}")
                    else:
                        await bot.send_message(chat_id=chat_id, text="Ошибка при получении данных о ставках. Попробуйте позже.")
                        with open('last_update_id.txt', 'w') as f:
                            f.write(str(update_id))
                            print("Не удалось получить данные после повторных попыток")

                # Обработка команды /prog
                elif text.strip().lower() in ['/prog', '/прогноз']:
                    print(f"Получена команда {text} от {chat_id}")
                    
                    # Получаем ключевую ставку и дату установления с главной страницы
                    current_key_rate, last_change_date = get_key_rate_from_main_page()
                    
                    if not current_key_rate or not last_change_date:
                        await bot.send_message(chat_id=chat_id, text="Не удалось получить данные о ключевой ставке.")
                        with open('last_update_id.txt', 'w') as f:
                            f.write(str(update_id))
                        continue
                    
                    # Получаем историю RUONIA с момента последнего изменения
                    today = datetime.now()
                    ruonia_history = get_ruonia_history_parametrized(last_change_date, today)
                    
                    if not ruonia_history:
                        await bot.send_message(chat_id=chat_id, text="Не удалось получить историю RUONIA. Попробуйте позже.")
                        with open('last_update_id.txt', 'w') as f:
                            f.write(str(update_id))
                        continue
                    
                    # Рассчитываем среднюю разницу
                    avg_diff = calculate_average_diff(ruonia_history, current_key_rate)
                    
                    # Получаем дату следующего заседания
                    next_meeting = get_next_meeting_date()
                    
                    if avg_diff is not None:
                        # Форматируем сообщение
                        comparison = "ниже" if avg_diff < 0 else "выше"
                        
                        message_text = f"""📊 Прогноз и статистика:

С последнего изменения ключевой ставки от {last_change_date.strftime('%d.%m.%Y')} до {today.strftime('%d.%m.%Y')} ставка RUONIA была в среднем на {abs(avg_diff):.2f}% {comparison}, чем ключевая ставка.

Количество торговых дней в анализе: {len(ruonia_history)}"""
                        
                        if next_meeting:
                            days_until = (next_meeting - today).days
                            message_text += f"\n\nСледующее заседание по ключевой ставке: {next_meeting.strftime('%d.%m.%Y')}"
                            message_text += f"\nОсталось дней до заседания: {days_until}"
                        
                        await bot.send_message(chat_id=chat_id, text=message_text)
                        with open('last_update_id.txt', 'w') as f:
                            f.write(str(update_id))
                        print(f"Прогноз отправлен в чат {chat_id}")
                    else:
                        await bot.send_message(chat_id=chat_id, text="Не удалось рассчитать прогноз. Попробуйте позже.")
                        with open('last_update_id.txt', 'w') as f:
                            f.write(str(update_id))

if __name__ == '__main__':
    asyncio.run(check_for_commands())
