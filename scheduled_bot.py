#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import re
from bs4 import BeautifulSoup
from telegram import Bot
import asyncio
from datetime import datetime
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
            text = soup.get_text()
            
            # Ищем паттерн "с ДД.ММ.ГГГГ"
            date_match = re.search(r'с\s+(\d{2}\.\d{2}\.\d{4})', text)
            if date_match:
                key_rate_date_str = date_match.group(1)
                key_rate_date = datetime.strptime(key_rate_date_str, '%d.%m.%Y')
            else:
                return None, None
            
            # Ищем ключевую ставку после даты
            rate_match = re.search(r'с\s+\d{2}\.\d{2}\.\d{4}\s+([\d,]+)%', text)
            if rate_match:
                key_rate = float(rate_match.group(1).replace(',', '.'))
            else:
                return None, None
            
            return key_rate, key_rate_date
        
        except Exception as e:
            print(f"Ошибка при получении ключевой ставки (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Повторная попытка через {retry_delay} секунд...")
                time.sleep(retry_delay)
            else:
                return None, None
    
    return None, None

def get_ruonia_rate(max_retries=2, retry_delay=30):
    """Получение текущей ставки RUONIA со страницы динамики"""
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
            
            # Ищем все даты заседаний — ищем в h3 и в тексте страницы
            date_elements = soup.find_all(['h3', 'p', 'div'])
            meeting_dates = []
            
            for elem in date_elements:
                text = elem.get_text(strip=True)
                # Ищем даты в формате "19 декабря 2025 года" или "19 декабря 2025"
                match = re.search(r'(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})(?:\s+года)?', text)
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
                        try:
                            meeting_date = datetime(year, month, day)
                            if meeting_date > today:
                                meeting_dates.append(meeting_date)
                                print(f"✅ Найдено заседание: {meeting_date.strftime('%d.%m.%Y')}")
                        except ValueError:
                            continue
            
            # Возвращаем ближайшую дату
            if meeting_dates:
                next_meeting = min(meeting_dates)
                print(f"📅 Ближайшее заседание: {next_meeting.strftime('%d.%m.%Y')}")
                return next_meeting
            
            print("❌ Не найдено будущих заседаний")
            return None
        except Exception as e:
            print(f"❌ Ошибка при получении даты следующего заседания (попытка {attempt + 1}/{max_retries}): {e}")
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
                
                # Подсчитываем только реальные торговые дни из истории
                print(f"📊 Получено {len(history)} торговых дней из истории RUONIA")
                for entry in history[:5]:  # Выводим первые 5 для проверки
                    print(f"  {entry['date'].strftime('%d.%m.%Y')} ({entry['date'].strftime('%A')}): {entry['rate']:.2f}%")
                
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

async def send_daily_report():
    """Отправка ежедневного отчета"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # Получаем данные о ставках
    ruonia = get_ruonia_rate()
    key_rate, key_rate_date = get_key_rate_from_main_page()
    
    if not ruonia or not key_rate or not key_rate_date:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, 
            text="Ошибка при получении данных о ставках. Попробуйте позже."
        )
        print("Не удалось получить данные после повторных попыток")
        return
    
    # Получаем дополнительные данные
    today = datetime.now()
    today_str = today.strftime('%d.%m.%Y')
    diff = ruonia - key_rate
    
    # Получаем историю RUONIA с даты установления ключевой ставки
    ruonia_history = get_ruonia_history_parametrized(key_rate_date, today)
    avg_diff = calculate_average_diff(ruonia_history, key_rate) if ruonia_history else None
    
    # Получаем дату следующего заседания
    next_meeting = get_next_meeting_date()
    
    # Формируем сообщение в нужном формате
    message_text = f"📊 Ежедневный отчет по ставкам ({today_str}):\n\n"
    message_text += f"📈 RUONIA: {ruonia:.2f}%\n"
    message_text += f"🏦 Ключевая ставка ЦБ: {key_rate:.2f}%\n"
    message_text += f"💡 Разница: {diff:+.2f}%\n"
    
    # Добавляем статистику
    if avg_diff is not None and ruonia_history:
        message_text += f"\n🔢 Средняя разница с {key_rate_date.strftime('%d.%m.%Y')} {avg_diff:.2f}% "
        message_text += "ниже\n" if avg_diff < 0 else "выше\n"
        # Используем реальное количество торговых дней из истории
        message_text += f"🔴 Количество торговых дней в анализе: {len(ruonia_history)}\n"
    
    # Добавляем дату следующего заседания (ИСПРАВЛЕНО!)
    if next_meeting:
        days_until = (next_meeting - today).days
        message_text += f"📆 Следующее заседание по ключевой ставке: {next_meeting.strftime('%d.%m.%Y')}\n"
        message_text += f"⏳ Осталось дней: {days_until}\n"
    
    # Добавляем статус
    if diff < 0 and avg_diff is not None and avg_diff < 0:
        message_text += f"\n⚠️ RUONIA сегодня и в среднем ниже ключевой ставки."
    elif diff > 0 and avg_diff is not None and avg_diff > 0:
        message_text += f"\n✅ RUONIA сегодня и в среднем выше ключевой ставки."
    elif diff < 0:
        message_text += f"\n⚠️ RUONIA сегодня ниже ключевой ставки."
    elif diff > 0:
        message_text += f"\n✅ RUONIA сегодня выше ключевой ставки."
    else:
        message_text += f"\n🔵 RUONIA равна ключевой ставке."
    
    # Добавляем галочку и время
    message_text += f" {today.strftime('%H:%M')} ✓"
    
    # Отправляем сообщение
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message_text)
    print(f"Ежедневный отчет отправлен: RUONIA={ruonia:.2f}%, Ключевая ставка={key_rate:.2f}%, Разница={diff:+.2f}%")
    print(f"Торговых дней: {len(ruonia_history) if ruonia_history else 0}")

if __name__ == '__main__':
    asyncio.run(send_daily_report())
