import telebot
import requests
import jsons
from Class_ModelResponse import ModelResponse

API_TOKEN = '8016831180:AAERjYdFLRRXSU1ZDrgBDkkC3-J_EAkH9xY'
bot = telebot.TeleBot(API_TOKEN)

user_contexts = {}
MAX_HISTORY_LENGTH = 10


def limit_context_length(context_list, max_length=MAX_HISTORY_LENGTH):
    if len(context_list) > max_length * 2:  # пара user/assistant
        return context_list[-(max_length * 2):]
    return context_list


def get_or_create_context(user_id):
    if user_id not in user_contexts:
        user_contexts[user_id] = []
    return user_contexts[user_id]


def clear_context(user_id):
    user_contexts[user_id] = []


# Команды
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "Привет! Я ваш Telegram бот.\n"
        "Доступные команды:\n"
        "/start - вывод всех доступных команд\n"
        "/model - выводит название используемой языковой модели\n"
        "/clear - очищает историю нашего диалога\n"
        "Отправьте любое сообщение, и я отвечу с помощью LLM модели."
    )
    bot.reply_to(message, welcome_text)


@bot.message_handler(commands=['model'])
def send_model_name(message):
    # Отправляем запрос к LM Studio для получения информации о модели
    response = requests.get('http://localhost:1234/v1/models')

    if response.status_code == 200:
        model_info = response.json()
        model_name = model_info['data'][0]['id']
        bot.reply_to(message, f"Используемая модель: {model_name}")
    else:
        bot.reply_to(message, 'Не удалось получить информацию о модели.')


@bot.message_handler(commands=['clear'])
def clear_context_command(message):
    """Обработчик команды /clear"""
    user_id = message.from_user.id

    if user_id in user_contexts and user_contexts[user_id]:
        clear_context(user_id)
        bot.reply_to(message, "История диалога очищена! Начинаем новый разговор.")
    else:
        bot.reply_to(message, "У вас еще нет истории диалога для очистки.")


@bot.message_handler(commands=['context'])
def show_context(message):
    """Показывает текущую длину контекста (для отладки)"""
    user_id = message.from_user.id
    context = get_or_create_context(user_id)
    bot.reply_to(message, f"Текущая длина контекста: {len(context)} сообщений")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    user_query = message.text

    context = get_or_create_context(user_id)

    context.append({
        "role": "user",
        "content": user_query
    })

    # Ограничение длины контекста
    context = limit_context_length(context)
    user_contexts[user_id] = context

    # запрос с полной историей диалога
    request = {
        "messages": context,
        "temperature": 0.7,
        "max_tokens": -1
    }

    response = requests.post(
        'http://localhost:1234/v1/chat/completions',
        json=request
    )

    if response.status_code == 200:
        model_response: ModelResponse = jsons.loads(response.text, ModelResponse)
        bot_response = model_response.choices[0].message.content

        context.append({
            "role": "assistant",
            "content": bot_response
        })

        context = limit_context_length(context)
        user_contexts[user_id] = context

        bot.reply_to(message, bot_response)
    else:
        bot.reply_to(message, 'Произошла ошибка при обращении к модели.')


# Запуск бота
if __name__ == '__main__':
    print("Бот запущен")
    bot.polling(none_stop=True)