import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import time
import os
from urllib.parse import urljoin, urlparse

# --- Настройки ---
# Начальные точки входа для разделов. Ссылки взяты с главной страницы сайта.
START_URLS = [
    "https://free-dnd.ttrpg.ru/",             # Главная (включает ссылки на разделы Игрокам)
    "https://free-dnd.ttrpg.ru/dms-basics",    # Начало раздела "Мастерам"
    "https://free-dnd.ttrpg.ru/rules-glossary" # Глоссарий
]

BASE_URL = "https://free-dnd.ttrpg.ru"
OUTPUT_FILE = "free_dnd_rules.txt"
OUTPUT_DIR = "tg_bot/AI-part" # Папка для сохранения файла
# Префиксы URL для исключения из парсинга
EXCLUDE_PREFIXES = ["/monsters", "/creatures", "/creature-stat-blocks", "/equipment", "/spells", "/downloads"]

# --- Хранилища ---
visited_urls = set()
urls_to_visit = list(START_URLS) # Начинаем с заданных разделов
all_text_content = [] # Список для хранения текстовых фрагментов

# --- Функции ---
def is_excluded(path):
    """Проверяет, начинается ли путь с одного из исключенных префиксов."""
    for prefix in EXCLUDE_PREFIXES:
        if path.startswith(prefix):
            return True
    return False

def is_heading_tag(tag_name):
    """Проверяет, является ли имя тега заголовком."""
    return tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']

# --- Основная логика ---
print(f"Начинаем парсинг с URL: {', '.join(START_URLS)}")
print(f"Исключаем URL, начинающиеся с: {', '.join(EXCLUDE_PREFIXES)}")

while urls_to_visit:
    current_url = urls_to_visit.pop(0)

    parsed_uri = urlparse(current_url)
    # Проверяем, относится ли URL к нашему сайту
    if not parsed_uri.netloc == urlparse(BASE_URL).netloc:
         print(f"Пропуск URL с другого домена: {current_url}")
         continue

    # Убираем якорь для проверки посещенных и добавления в очередь
    url_without_fragment = parsed_uri._replace(fragment='').geturl()

    if url_without_fragment in visited_urls:
        continue # Пропускаем, если уже посещали (без якоря)

    # Проверяем, не относится ли URL к исключенному разделу
    if is_excluded(parsed_uri.path):
         print(f"Пропуск URL из исключенного раздела: {current_url}")
         visited_urls.add(url_without_fragment)
         continue

    print(f"Обрабатывается: {current_url}")
    visited_urls.add(url_without_fragment)

    try:
        response = requests.get(current_url, timeout=15) # Увеличим таймаут на всякий случай
        response.raise_for_status()
        response.encoding = 'utf-8' # Сайт использует UTF-8

        soup = BeautifulSoup(response.text, 'html.parser')

        # *** Селектор для основного контента на free-dnd.ttrpg.ru ***
        content_area = soup.find('div', class_='p-article-content') # Основной контейнер текста статьи по скриншоту

        if not content_area:
             # Запасной вариант, если это не страница статьи, а, например, страница раздела
             content_area = soup.find('main') or soup.find('article')

        if content_area:
            # Собираем фрагменты вместе с типом тега
            page_fragments_with_tags = []
            for child in content_area.children:
                tag_name = None
                current_text = None
                if isinstance(child, NavigableString):
                    text = child.strip()
                    if text:
                        tag_name = 'text' # Используем 'text' для простого текста
                        current_text = text
                elif isinstance(child, Tag):
                    # Исключаем инлайновые и другие не блочные элементы на этом уровне
                    if child.name not in ['a', 'span', 'b', 'i', 'strong', 'em', 'script', 'style', 'br', 'hr']:
                         text = child.get_text(separator=' ', strip=True)
                         text = ' '.join(text.split())
                         if text:
                             tag_name = child.name
                             current_text = text

                if tag_name and current_text:
                    page_fragments_with_tags.append((tag_name, current_text))

            # Собираем итоговый текст для страницы с умными переносами
            if page_fragments_with_tags:
                page_text_builder = []
                previous_tag_name = None
                for i, (tag_name, text_fragment) in enumerate(page_fragments_with_tags):
                    separator = ""
                    if i > 0: # Не добавляем перенос перед первым фрагментом
                        if is_heading_tag(previous_tag_name) and not is_heading_tag(tag_name):
                            separator = "\n" # Одинарный перенос после заголовка перед НЕ заголовком
                        else:
                            separator = "\n\n" # Двойной перенос в остальных случаях

                    page_text_builder.append(separator)
                    page_text_builder.append(text_fragment)
                    previous_tag_name = tag_name # Обновляем предыдущий тег

                final_page_text = "".join(page_text_builder)
                all_text_content.append(final_page_text)
                print(f"  -> Добавлено ~{len(final_page_text)} символов (с умными переносами).")

            # Ищем новые ссылки на страницы ЭТОГО ЖЕ сайта внутри найденного контента
            # Важно: Искать ссылки нужно в исходном content_area, а не в собранных фрагментах
            internal_links = content_area.find_all('a', href=True) if content_area else []

            for link in internal_links:
                href = link.get('href')
                # Преобразуем в абсолютный URL относительно текущей страницы
                absolute_url = urljoin(current_url, href)
                parsed_new_uri = urlparse(absolute_url)

                # Проверяем, что ссылка ведет на тот же сайт
                if parsed_new_uri.netloc == parsed_uri.netloc:
                    # Убираем якорь
                    url_clean = parsed_new_uri._replace(fragment='').geturl()

                    # Проверяем, что не посещали, не в очереди и не исключена
                    if url_clean not in visited_urls and \
                       url_clean not in urls_to_visit and \
                       not is_excluded(parsed_new_uri.path):

                        urls_to_visit.append(url_clean)
                        # print(f"    Найдена новая ссылка: {url_clean}")
        else:
            print(f"  -> Не найден целевой контент (`div.p-article-content` или `main`/`article`) на странице: {current_url}")

        # Пауза, чтобы не перегружать сайт
        time.sleep(0.5) # 0.5 секунды должно быть достаточно для статического сайта

    except requests.exceptions.Timeout:
        print(f"Таймаут при запросе {current_url}")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе {current_url}: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка при обработке {current_url}: {e}")

# --- Сохранение результата ---
print(f"\nПарсинг завершен. Посещено {len(visited_urls)} уникальных URL (без якорей).")
print(f"Собрано {len(all_text_content)} текстовых блоков со страниц.")

if all_text_content:
    # Объединяем тексты со страниц с двойным переносом строки
    # Логика переносов внутри страницы уже обработана
    full_text = "\n\n".join(all_text_content)
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)

    # Создаем директорию, если она не существует
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        print(f"Текст успешно сохранен в файл: {output_path}")
        print(f"Размер файла: {os.path.getsize(output_path) / 1024:.2f} KB")
    except IOError as e:
        print(f"Ошибка при сохранении файла {output_path}: {e}")
else:
    print("Не удалось собрать текст. Проверьте начальные URL и селектор контента.")
