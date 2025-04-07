import os
import json
import time # Для возможных задержек между запросами
# import openai # Заменяем на google-generativeai
import google.generativeai as genai # Добавляем импорт Google

# --- Настройка ---
# Загрузка API ключа (лучше из переменных окружения)
try:
    # Настраиваем ключ API Google (убедитесь, что переменная окружения установлена)
    google_api_key = os.getenv("GOOGLE_API_KEY_2")
    if not google_api_key:
        raise ValueError("Переменная окружения GOOGLE_API_KEY не установлена.")
    genai.configure(api_key=google_api_key)
except ValueError as ve:
    print(f"Ошибка конфигурации: {ve}")
    exit()
except Exception as e:
    print(f"Неожиданная ошибка при настройке Google API: {e}")
    exit()


SRD_TEXT_FILE = "tg_bot/AI-part/phb_text_final.txt" # Путь к файлу с текстом SRD
OUTPUT_JSONL_FILE = "tg_bot/AI-part/dnd_dataset.jsonl"
# LLM_MODEL_NAME = "gemini-2.5-pro-exp-03-25" # Используем модель Gemini
LLM_MODEL_NAME = "gemini-2.0-flash"
# --- Функция для взаимодействия с LLM ---
def generate_examples_with_llm(text_chunk, model_name):
    # Важно правильно составить промпт!
    prompt = f"""
    На основе следующего текста из правил Dungeons & Dragons 5e:
    --- ТЕКСТ НАЧАЛО ---
    {text_chunk}
    --- ТЕКСТ КОНЕЦ ---

    Сгенерируй 13-15 разнообразных примеров в формате JSON для дообучения ИИ-ассистента Мастера Подземелий.
    Каждый пример должен быть отдельным JSON-объектом на новой строке и содержать ключи "instruction" и "output".
    Примеры должны быть основаны ТОЛЬКО на предоставленном тексте. Они могут включать:
    - Вопросы о правилах, упомянутых в тексте, и ответы на них.
    - Просьбы кратко изложить часть текста.
    - Запросы на объяснение терминов из текста.
    - Инструкции, связанные с механиками, описанными в тексте.
    - Задания на создание персонажа, его класса, расы, уровня и т.д.
    - Задания на создание подземелья, локации, монстров, предметов и т.д.
    - Задания на создание приключения, квеста, испытания и т.д.
    - Задания на создание NPC, их историй, прошлого и т.д.
    - Задания на создание событий, сюжета, развития событий и т.д.

    Пример формата одного JSON-объекта:
    {{"instruction": "...", "output": "..."}}

    Сгенерируй только JSON-объекты, по одному на строку:
    """

    try:
        # Инициализируем модель Gemini
        model = genai.GenerativeModel(model_name)
        # Устанавливаем параметры генерации (опционально)
        generation_config = genai.types.GenerationConfig(
            temperature=0.7
        )
        # Устанавливаем настройки безопасности (можно настроить под себя)
        safety_settings = {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_MEDIUM_AND_ABOVE",
        }

        print(f"Отправка промпта для фрагмента: {text_chunk[:50]}...")
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        # Проверяем, не был ли ответ заблокирован фильтрами безопасности
        # Доступ к `response.text` вызовет ошибку, если кандидатов нет
        if not response.candidates:
            print("Предупреждение: Ответ был заблокирован фильтрами безопасности или пуст.")
            if response.prompt_feedback:
                 print(f"Причина блокировки: {response.prompt_feedback.block_reason}")
            # Возвращаем пустой список, т.к. генерации не было
            return [] # Этот return должен быть здесь

        generated_text = response.text # Получаем сгенерированный текст

        # Очищаем ответ от возможных Markdown-блоков
        cleaned_text = clean_llm_response(generated_text)

        # Используем splitlines() для надежного разделения строк
        json_lines = [line.strip() for line in cleaned_text.strip().splitlines() if line.strip()]
        valid_examples = []
        for line in json_lines:
            try:
                # Проверяем, что это валидный JSON с нужными ключами
                data = json.loads(line)
                if "instruction" in data and "output" in data:
                    valid_examples.append(data)
                else:
                    print(f"Предупреждение: Пропущен невалидный JSON или отсутствуют ключи: {line}")
            except json.JSONDecodeError:
                print(f"Предупреждение: Ошибка декодирования JSON: {line}")
        return valid_examples

    except Exception as e:
        print(f"Ошибка при вызове API Gemini или обработке ответа: {e}")
        # Можно добавить дополнительное логирование, если нужно
        return []

# --- Функция для очистки ответа LLM от Markdown ---
def clean_llm_response(text: str) -> str:
    """Удаляет возможные Markdown-ограждения для JSON."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[len("```json"):]
    if text.endswith("```"):
        text = text[:-len("```")]
    return text.strip()

# --- Основная логика ---
try:
    with open(SRD_TEXT_FILE, 'r', encoding='utf-8') as f_in, \
         open(OUTPUT_JSONL_FILE, 'a', encoding='utf-8') as f_out:

        srd_content = f_in.read()

        # Разделение текста SRD на осмысленные части (чанки)
        # Стратегия разделения важна! Можно делить по параграфам, секциям,
        # или по фиксированному числу символов/токенов,
        # чтобы не превышать лимит контекста LLM.
        # Пример: деление по пустым строкам (параграфам)
        text_chunks = [chunk.strip() for chunk in srd_content.split('\n\n') if chunk.strip()]

        print(f"Найдено {len(text_chunks)} фрагментов текста.")

        for i, chunk in enumerate(text_chunks):
            print(f"\nОбработка фрагмента {i+1}/{len(text_chunks)}...")
            if len(chunk) < 50: # Пропускаем слишком короткие фрагменты
                 print("Фрагмент слишком короткий, пропуск.")
                 continue

            generated_examples = generate_examples_with_llm(chunk, LLM_MODEL_NAME)

            if generated_examples:
                print(f"Сгенерировано {len(generated_examples)} валидных примеров.")
                for example in generated_examples:
                    # Записываем каждый JSON как отдельную строку
                    json.dump(example, f_out, ensure_ascii=False)
                    f_out.write('\n')
            else:
                print("Не удалось сгенерировать примеры для этого фрагмента.")

            # Небольшая задержка, чтобы не превысить лимиты API
            # Для Gemini API лимиты могут отличаться, возможно, можно уменьшить паузу
            # Бесплатный уровень обычно имеет лимит 60 запросов в минуту.
            time.sleep(1.5) # Пауза в 1.5 секунды (можно подстроить)

    print(f"\nГенерация завершена. Примеры сохранены в {OUTPUT_JSONL_FILE}")

except FileNotFoundError:
    print(f"Ошибка: Не найден файл с текстом SRD: {SRD_TEXT_FILE}")
except Exception as e:
    print(f"Произошла непредвиденная ошибка: {e}")
