import requests
from bs4 import BeautifulSoup
import time
import os
from urllib.parse import urljoin, urlparse

# --- Настройки ---
START_URL = "https://longstoryshort.app/srd/races/traits/" # Начальный URL (можно поменять на главный /srd/ если есть)
BASE_URL = "https://longstoryshort.app"
OUTPUT_FILE = "russian_srd123.txt" # Файл для сохранения текста
OUTPUT_DIR = "tg_bot/AI-part" # Папка для сохранения файла

# --- Хранилища ---
visited_urls = set()
urls_to_visit = [START_URL]
all_text_content = [] # Список для хранения текстовых фрагментов

# --- Основная логика --- 
print(f"Начинаем парсинг с: {START_URL}")

while urls_to_visit:
    current_url = urls_to_visit.pop(0) # Берем первый URL из очереди

    if current_url in visited_urls:
        continue # Пропускаем, если уже посещали

    # Проверяем, относится ли URL к разделу /srd/
    parsed_uri = urlparse(current_url)
    if not parsed_uri.path.startswith('/srd/'):
         print(f"Пропуск URL не из SRD: {current_url}")
         visited_urls.add(current_url)
         continue

    print(f"Обрабатывается: {current_url}")
    visited_urls.add(current_url)

    try:
        response = requests.get(current_url, timeout=10) # Загружаем страницу
        response.raise_for_status() # Проверяем на ошибки HTTP (4xx, 5xx)
        response.encoding = 'utf-8' # Устанавливаем кодировку

        soup = BeautifulSoup(response.text, 'html.parser')

        # *** Ключевой момент: Найти правильный контейнер для основного контента ***
        # Нужно будет проверить HTML сайта и адаптировать селектор.
        # Возможные варианты (нужно проверить через инструменты разработчика F12):
        # content_area = soup.find('main') # Если есть тег <main>
        # content_area = soup.find('div', id='content') # Если есть <div id="content">
        # content_area = soup.find('div', class_='main-content') # Если есть <div class="main-content">
        # Пример для longstoryshort.app (НАДО ПРОВЕРИТЬ!):
        content_area = soup.find('section', class_='compendium-main') # Новый вариант на основе скриншота

        if content_area:
            # Извлекаем текст, очищая от лишних пробелов
            text = content_area.get_text(separator='\n', strip=True)
            all_text_content.append(text)
            print(f"  -> Добавлено {len(text)} символов.")

            # Ищем новые ссылки на страницы SRD внутри этой страницы
            # Ищем ссылки внутри навигации или основного контента
            # На longstoryshort навигация слева, попробуем найти ссылки там
            nav_links = soup.select('nav a[href^="/srd/"]') # Ищем ссылки в <nav>, начинающиеся с /srd/
            content_links = content_area.select('a[href^="/srd/"]') # Ищем ссылки в <article>

            for link in nav_links + content_links:
                href = link.get('href')
                if href:
                    # Преобразуем относительные URL в абсолютные
                    absolute_url = urljoin(BASE_URL, href)
                    # Убираем якоря (#...)
                    absolute_url = urlparse(absolute_url)._replace(fragment='').geturl()

                    if absolute_url not in visited_urls and absolute_url not in urls_to_visit:
                        # Добавляем только URL из раздела /srd/
                        if urlparse(absolute_url).path.startswith('/srd/'):
                             urls_to_visit.append(absolute_url)
                             # print(f"    Найдена новая ссылка: {absolute_url}")

        else:
            print("  -> Не найден основной контент на странице.")

        # Пауза, чтобы не нагружать сайт
        time.sleep(1) # Ждем 1 секунду перед следующим запросом

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе {current_url}: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка при обработке {current_url}: {e}")

# --- Сохранение результата ---
print(f"\nПарсинг завершен. Посещено {len(visited_urls)} страниц.")

if all_text_content:
    full_text = "\n\n".join(all_text_content) # Объединяем тексты с двойным переносом строки
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)

    # Создаем директорию, если она не существует
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        print(f"Текст успешно сохранен в файл: {output_path}")
    except IOError as e:
        print(f"Ошибка при сохранении файла {output_path}: {e}")
else:
    print("Не удалось собрать текст.") 