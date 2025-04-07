import os
import re

# --- Настройки ---
INPUT_FILE = "phb_extracted_text.txt" # Исходный файл с текстом из PDF
OUTPUT_FILE = "phb_text_final.txt" # Итоговый файл после исправления переносов

# Определяем пути
script_dir = os.path.dirname(os.path.abspath(__file__))
input_path = os.path.join(script_dir, INPUT_FILE)
output_path = os.path.join(script_dir, OUTPUT_FILE)

print(f"Начинаем исправление переносов в файле: {input_path}")

try:
    # Читаем весь контент исходного файла
    with open(input_path, 'r', encoding='utf-8') as infile:
        content = infile.read()

    # Заменяем дефис + перенос строки (Windows и Unix) на пустую строку
    # Ищем дефис, за которым могут следовать пробелы, а затем перенос строки
    # \s* - ноль или больше пробельных символов
    # \r? - необязательный символ возврата каретки (для Windows)
    # \n - обязательный символ новой строки
    # \s* - ноль или больше пробельных символов (в начале следующей строки)
    corrected_content = re.sub(r'-\s*\r?\n\s*', '', content)

    lines_before = len(content.splitlines())
    lines_after = len(corrected_content.splitlines())
    chars_before = len(content)
    chars_after = len(corrected_content)

    print(f"Предварительные статистики:")
    print(f"  Строк до: {lines_before}, Символов до: {chars_before}")
    print(f"  Строк после: {lines_after}, Символов после: {chars_after}")

    # Записываем исправленный контент в новый файл
    with open(output_path, 'w', encoding='utf-8') as outfile:
        outfile.write(corrected_content)

    print(f"\nИсправление переносов завершено.")
    print(f"Результат сохранен в: {output_path}")

except FileNotFoundError:
    print(f"Ошибка: Не найден исходный файл: {input_path}")
except IOError as e:
    print(f"Ошибка при чтении/записи файла: {e}")
except Exception as e:
    print(f"Произошла непредвиденная ошибка: {e}") 