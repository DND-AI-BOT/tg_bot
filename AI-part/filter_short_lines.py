import os

# --- Настройки ---
INPUT_FILE = "russian_srd.txt" # Имя исходного файла
OUTPUT_FILE = "russian_srd_filtered.txt" # Имя файла после фильтрации
MIN_LINE_LENGTH = 4 # Минимальная длина НЕПУСТОЙ строки (после strip)

# Определяем пути относительно папки скрипта
script_dir = os.path.dirname(os.path.abspath(__file__))
input_path = os.path.join(script_dir, INPUT_FILE)
output_path = os.path.join(script_dir, OUTPUT_FILE)

# --- Логика фильтрации ---
lines_read = 0
lines_written = 0

print(f"Начинаем фильтрацию файла: {input_path}")

try:
    with open(input_path, 'r', encoding='utf-8') as infile, \
         open(output_path, 'w', encoding='utf-8') as outfile:

        for line in infile:
            lines_read += 1
            # Проверяем строку после удаления пробелов по краям
            stripped_line = line.strip()
            # Сохраняем строку, если она пустая ИЛИ если она непустая и ее длина >= MIN_LINE_LENGTH
            if not stripped_line or len(stripped_line) >= MIN_LINE_LENGTH:
                outfile.write(line) # Записываем исходную строку (с пробелами/пустую)
                lines_written += 1

    print("\nФильтрация завершена.")
    print(f"Прочитано строк: {lines_read}")
    print(f"Записано строк (длиной >= {MIN_LINE_LENGTH}): {lines_written}")
    print(f"Результат сохранен в: {output_path}")

except FileNotFoundError:
    print(f"Ошибка: Не найден исходный файл: {input_path}")
except IOError as e:
    print(f"Ошибка при чтении/записи файла: {e}")
except Exception as e:
    print(f"Произошла непредвиденная ошибка: {e}") 