import fitz # PyMuPDF
import os
import re

# --- Настройки ---
INPUT_PDF = "5e Players Handbook - Книга игрока RUS.pdf" # Имя PDF файла
OUTPUT_TXT = "phb_extracted_text.txt" # Имя выходного текстового файла

# --- Параметры фильтрации (МОГУТ ПОТРЕБОВАТЬ НАСТРОЙКИ!) ---
# Определяем границы страницы для фильтрации колонтитулов (в % от высоты)
# Например, игнорировать текст в верхних 5% и нижних 5% страницы
HEADER_MARGIN_PERCENT = 5
FOOTER_MARGIN_PERCENT = 5
MIN_BLOCK_TEXT_LENGTH = 10 # Минимальная длина текста в блоке (для отсева мусора)

# Определяем пути
script_dir = os.path.dirname(os.path.abspath(__file__))
pdf_path = os.path.join(script_dir, INPUT_PDF)
output_path = os.path.join(script_dir, OUTPUT_TXT)

all_extracted_text = []

print(f"Начинаем обработку PDF: {pdf_path}")

try:
    doc = fitz.open(pdf_path)
    print(f"PDF открыт. Всего страниц: {doc.page_count}")

    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        page_height = page.rect.height
        header_limit = page_height * (HEADER_MARGIN_PERCENT / 100.0)
        footer_limit = page_height * (1 - FOOTER_MARGIN_PERCENT / 100.0)

        # Получаем текстовые блоки с координатами
        # Формат блока: (x0, y0, x1, y1, text, block_no, block_type)
        blocks = page.get_text("blocks")

        # Фильтруем блоки
        filtered_blocks = []
        for b in blocks:
            x0, y0, x1, y1, text, block_no, block_type = b
            # Оставляем только текстовые блоки (type 0)
            if block_type != 0:
                continue
            # Удаляем лишние пробелы и переносы внутри блока
            cleaned_text = re.sub(r'\s+', ' ', text).strip()
            # Фильтруем по длине
            if len(cleaned_text) < MIN_BLOCK_TEXT_LENGTH:
                continue
            # Фильтруем колонтитулы по Y-координате
            # Учитываем, что y0 - это верхняя граница блока
            if y0 < header_limit or y1 > footer_limit:
                 # print(f"  >> Фильтр колонтитула (Y={y0:.1f}-{y1:.1f}): {cleaned_text[:50]}...")
                 continue

            # Добавляем блок с его верхней координатой для сортировки
            filtered_blocks.append((y0, cleaned_text))

        # Сортируем оставшиеся блоки по вертикали (сверху вниз)
        filtered_blocks.sort(key=lambda item: item[0])

        # Собираем текст со страницы, разделяя блоки ОДНИМ переносом
        page_text = "\n".join([block_text for y_coord, block_text in filtered_blocks])
        all_extracted_text.append(page_text)

        if (page_num + 1) % 10 == 0:
             print(f"Обработано страниц: {page_num + 1}/{doc.page_count}")

    doc.close()
    print("\nОбработка PDF завершена.")

    # --- Сохранение результата ---
    if all_extracted_text:
        # full_text = "\n\n---\n\n".join(all_extracted_text) # Убираем разделитель страниц ---
        full_text = "\n\n".join(all_extracted_text) # Соединяем страницы двойным переносом

        # Попытка убрать дублирующиеся пустые строки (оставляем)
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            print(f"Извлеченный текст успешно сохранен в: {output_path}")
        except IOError as e:
            print(f"Ошибка при сохранении файла {output_path}: {e}")
    else:
        print("Не удалось извлечь текст из PDF.")

except FileNotFoundError:
    print(f"Ошибка: Не найден PDF файл: {pdf_path}")
except Exception as e:
    print(f"Произошла ошибка при обработке PDF: {e}") 