from aiogram import Bot, Dispatcher, F
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardRemove, KeyboardButton, Message, ReplyKeyboardMarkup
from config import BOT_TOKEN
import logging
import asyncio
import json
import os  # Добавим os для работы с путями
import torch  # Добавим torch
from peft import PeftModel
from transformers import (AutoModelForCausalLM, AutoTokenizer,
                          BitsAndBytesConfig, pipeline)
from huggingface_hub import login # Добавим login


logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Авторизация в Hugging Face Hub ---
try:
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        logging.warning("Переменная окружения HF_TOKEN не установлена. Загрузка некоторых моделей может не работать.")
    else:
        login(token=hf_token)
        logging.info("Успешная авторизация в Hugging Face Hub.")
except Exception as e:
    logging.error(f"Ошибка авторизации в Hugging Face Hub: {e}")

# --- Конфигурация модели ---
base_model_name = "IlyaGusev/saiga_mistral_7b_lora"
# Используем относительный путь, предполагая запуск из корня проекта
adapter_path = "AI-part/saiga_mistral_dnd_lora_colab"

# Глобальные переменные для модели и генератора
llm_pipeline = None
# Словарь для хранения истории диалогов (ключ: chat_id, значение: список сообщений)
conversation_history = {}
MAX_HISTORY_TURNS = 5 # Хранить примерно 5 последних пар "вопрос-ответ"

# --- Функция загрузки модели ---
async def load_llm():
    """Загружает базовую модель, адаптер и создает pipeline."""
    global llm_pipeline
    if llm_pipeline:
        logging.info("Модель уже загружена.")
        return

    logging.info("Начало загрузки LLM...")
    try:
        # Конфигурация для 4-битной загрузки (Возвращено)
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=False,
        )

        logging.info(f"Загрузка базовой модели: {base_model_name}")
        # Возвращен параметр quantization_config=bnb_config
        # Убран параметр offload_folder
        model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            quantization_config=bnb_config, # <-- Возвращено
            device_map="auto",  # Автоматический выбор устройства (GPU/CPU)
            # offload_folder="offload", # <-- Убрано
            trust_remote_code=True,
            torch_dtype=torch.bfloat16 # Оставляем, т.к. используется в bnb_config
        )
        logging.info("Базовая модель загружена.")

        tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
        tokenizer.pad_token = tokenizer.eos_token # Установка pad_token
        tokenizer.padding_side = "right"
        logging.info("Токенизатор загружен.")

        # --- Загрузка адаптера D&D (ВРЕМЕННО ОТКЛЮЧЕНО ДЛЯ ТЕСТА) ---
        # Проверяем и загружаем адаптер, используя абсолютный путь
        # if os.path.exists(absolute_adapter_path) and os.path.isdir(absolute_adapter_path):
        #     logging.info(f"Загрузка LoRA адаптера из: {absolute_adapter_path}")
        #     model = PeftModel.from_pretrained(model, absolute_adapter_path) # <-- Используем абсолютный путь
        #     logging.info("LoRA адаптер применен.")
        #     # Опционально: слияние адаптера для ускорения инференса (Закомментировано по запросу)
        #     # try:
        #     #     logging.info("Попытка слияния адаптера...")
        #     #     model = model.merge_and_unload()
        #     #     logging.info("Адаптер успешно слит с базовой моделью.")
        #     # except Exception as merge_exc:
        #     #     logging.warning(f"Не удалось слить адаптер: {merge_exc}. Используем модель без слияния.")
        # else:
        #     logging.warning(f"Папка с адаптером не найдена по пути: {absolute_adapter_path}. Используется базовая модель Saiga.") # Используем абсолютный путь в логе
        logging.info("ЗАГРУЗКА АДАПТЕРА D&D ОТКЛЮЧЕНА. Используется базовая модель Saiga.") # Добавим лог
        # ----------------------------------------------------------------

        # Создаем pipeline для генерации текста
        # Pipeline будет использовать модель БЕЗ D&D адаптера
        llm_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            torch_dtype=torch.bfloat16, # Тип данных для вычислений
            device_map="auto"
        )
        logging.info("Pipeline для генерации текста создан.")

    except Exception as e:
        logging.error(f"Ошибка при загрузке LLM: {e}", exc_info=True)
        llm_pipeline = None # Оставляем None в случае ошибки


@dp.message(Command("start"))
async def process_start_command(msg: Message):
    kb = [[KeyboardButton(text="Создать персонажа"), KeyboardButton(text="Погнали сразу в приключение")]]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True,
                                         input_field_placeholder="Выбери, че будешь делать")
    await msg.reply("Здарова, го в днд", reply_markup=keyboard)


@dp.message(F.text.lower() == "создать персонажа")
async def with_puree(msg: Message):
    await msg.reply("Создадим же легенду Фаэруна", reply_markup=ReplyKeyboardRemove())

@dp.message(F.text.lower() == "Погнали сразу в приключение")
async def without_puree(msg: Message):
    await msg.reply("Ладно, будешь играть за орка", reply_markup=ReplyKeyboardRemove())


@dp.message(F.text)
async def handle_text_message(msg: Message):
    """Обрабатывает текстовые сообщения с помощью LLM."""
    if not llm_pipeline:
        await msg.answer("Извините, Мастер сейчас размышляет над сюжетом (модель загружается или не загружена). Попробуйте позже.")
        return

    user_text = msg.text
    logging.info(f"Получен текст от {msg.from_user.id}: {user_text}")

    # --- Работа с историей (Временно отключено для теста) ---
    chat_id = msg.chat.id
    history = conversation_history.get(chat_id, [])
    # Добавляем текущее сообщение пользователя в историю
    history.append({"role": "user", "content": user_text})

    # --- Формирование промпта (формат Saiga) ---
    # Шаблоны из документации Saiga
    message_template = "<s>{role}\n{content}</s>"
    response_template = "<s>bot\n" # Маркер начала ответа бота
    system_prompt_content = "Ты — ИИ-ассистент, который ведет игру в Dungeons & Dragons 5-й редакции. Ты - мастер этой игры, именно ты должен генерировать конкретных персонажей и конкретные ситуации. Отвечай на вопросы о правилах, самой игре, генерируй описания и помогай с игровыми ситуациями. "

    # Собираем промпт
    prompt_parts = []
    # Добавляем системный промпт в правильном формате
    prompt_parts.append(message_template.format(role="system", content=system_prompt_content))

    # Добавляем последние сообщения из истории (пропуская системный, если он там был бы)
    # Берем последние N * 2 сообщений (N пар user/bot)
    recent_history = history[-(MAX_HISTORY_TURNS * 2):]
    for message in recent_history:
        prompt_parts.append(message_template.format(**message)) # Передаем весь словарь message

    # Добавляем маркер для ответа бота
    prompt_parts.append(response_template)
    prompt = "".join(prompt_parts) # Соединяем без дополнительных переносов строки
    logging.info(f"--- Полный промпт ---\n{prompt}\n--------------------") # Изменим лог для отладки

    try:
        # Используем pipeline для генерации
        logging.info("Генерация ответа...")
        # Настройте параметры генерации по необходимости

        # --- Определяем правильный ID стоп-токена ---
        stop_token = "<|im_end|>"
        try:
            stop_token_id = llm_pipeline.tokenizer.convert_tokens_to_ids(stop_token)
            logging.info(f"Используем ID токена '{stop_token}' ({stop_token_id}) как EOS.")
        except KeyError:
            stop_token_id = llm_pipeline.tokenizer.eos_token_id # Fallback на стандартный
            logging.warning(f"Токен '{stop_token}' не найден, используем стандартный eos_token_id ({stop_token_id}) как EOS.")
        # Стандартный EOS ID для padding
        pad_token_id = llm_pipeline.tokenizer.eos_token_id
        if pad_token_id is None: # На случай если у токенизатора совсем нет eos_token
            pad_token_id = llm_pipeline.tokenizer.pad_token_id
        # ----------------------------------------------

        sequences = llm_pipeline(
            prompt,
            max_new_tokens=350,       # Максимальная длина нового текста
            do_sample=True,          # Включаем сэмплирование обратно
            temperature=0.7,        # Снижаем температуру еще немного
            top_p=0.95,             # Возвращаем top_p
            num_return_sequences=1,   # Генерировать одну последовательность
            eos_token_id=stop_token_id, # <-- Используем ID для <|im_end|>
            pad_token_id=pad_token_id   # Используем стандартный для padding
        )

        # Извлекаем сгенерированный текст из результата pipeline
        raw_response = sequences[0]['generated_text']

        # --- Извлекаем ТОЛЬКО сгенерированную часть ---
        generated_response = "" # Инициализируем
        # Важно: т.к. pipeline возвращает и промпт, и ответ,
        # а мы знаем точный формат промпта, ищем начало ответа ПОСЛЕ промпта.
        if raw_response.startswith(prompt):
            generated_response = raw_response[len(prompt):].strip()
        else:
            # Fallback, если что-то пошло не так
            generated_response = raw_response # Берем все, очистка ниже должна помочь
            logging.warning("Вывод модели не начинался с промпта. Используется сырой вывод.")

        # Логируем ответ ДО финальной очистки
        logging.info(f"Ответ модели до очистки спец.токенов: {generated_response}")

        # --- Улучшенная очистка ответа ---
        # 1. Убираем все после первого </s> или <|im_end|>
        #    (Saiga может использовать и то, и другое, возьмем то, что раньше)
        stop_tokens = ["</s>", "<|im_end|>"]
        first_stop_pos = -1
        for token in stop_tokens:
            pos = generated_response.find(token)
            if pos != -1:
                if first_stop_pos == -1 or pos < first_stop_pos:
                    first_stop_pos = pos

        if first_stop_pos != -1:
            generated_response = generated_response[:first_stop_pos].strip()

        # 2. Дополнительно убираем стандартный eos_token, если он вдруг остался
        if llm_pipeline.tokenizer.eos_token and generated_response.endswith(llm_pipeline.tokenizer.eos_token):
             generated_response = generated_response[:-len(llm_pipeline.tokenizer.eos_token)].strip()

        # 3. Убираем слово "bot" из конца строки, если оно там есть
        if generated_response.endswith(" bot"):
            generated_response = generated_response[:-len(" bot")]

        logging.info(f"Очищенный ответ: {generated_response}")
        if not generated_response: # Если ответ пустой после очистки
            await msg.answer("Мастер задумался и не смог сформулировать ответ...")
        else:
            await msg.answer(generated_response)
            # Добавляем ответ бота в историю (Временно отключено, т.к. история не используется)
            history.append({"role": "bot", "content": generated_response})
            conversation_history[chat_id] = history[-(MAX_HISTORY_TURNS * 2):]

    except Exception as e:
        logging.error(f"Ошибка во время генерации ответа: {e}", exc_info=True)
        await msg.answer("Упс! Кажется, вдохновение покинуло Мастера (ошибка генерации).")


async def main():
    # Загружаем модель перед стартом бота
    await load_llm()
    if not llm_pipeline:
        logging.warning("LLM не загружена! Бот будет работать с ограниченной функциональностью (без ответов LLM).")

    # Запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
