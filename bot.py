
import telebot
from telebot import types
import uuid
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
MODERATOR_ID = int(os.environ.get("MODERATOR_ID"))
CHANNEL_NN_ID = os.environ.get("CHANNEL_NN_ID")
CHANNEL_MSK_ID = os.environ.get("CHANNEL_MSK_ID")
CHANNEL_SPB_ID = os.environ.get("CHANNEL_SPB_ID")
PIAR_NINO_BOT_LINK = os.environ.get("PIAR_NINO_BOT_LINK")
FDKAHF_LINK = os.environ.get("FDKAHF_LINK")


bot = telebot.TeleBot(BOT_TOKEN)

# Хранение постов в формате {post_id: post_data}
posts_waiting_moderation = {}

# Хранение состояния пользователя: в каком шаге он находится и к какому post_id относится
user_states = {}  # {user_id: {'step': str, 'post_id': str, 'city': str}}

def start_post_creation(message):
    user_id = message.from_user.id
    post_id = str(uuid.uuid4())
    user_states[user_id] = {'step': 'city', 'post_id': post_id}
    posts_waiting_moderation[post_id] = {'user_id': user_id}

    # Предлагаем выбрать город
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    nn_button = types.KeyboardButton("Нижний Новгород")
    msk_button = types.KeyboardButton("Москва")
    spb_button = types.KeyboardButton("СПБ")
    markup.add(nn_button, msk_button, spb_button)
    bot.send_message(message.chat.id, "Выберите город для публикации:", reply_markup=markup)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
                     "Привет! 🍎🍏\nЯ помогу тебе опубликовать пост в барахолку ПиарНН\n"
                     "Для связи и рекламы писать: @Fdkahf")
    start_post_creation(message)

@bot.message_handler(content_types=['photo', 'text'])
def handle_messages(message):
    user_id = message.from_user.id

    if user_id not in user_states:
        bot.send_message(message.chat.id, "Чтобы начать, напишите /start")
        return

    state = user_states[user_id]
    step = state['step']
    post_id = state['post_id']

    if step == 'city':
        city = message.text
        if city not in ["Нижний Новгород", "Москва", "СПБ"]:
            bot.send_message(message.chat.id, "Пожалуйста, выберите город из предложенных вариантов.")
            return  # Остаемся на шаге выбора города

        user_states[user_id]['city'] = city
        posts_waiting_moderation[post_id]['city'] = city
        user_states[user_id]['step'] = 'photo'  # Переходим к следующему шагу

        #Убираем клавиатуру выбора города
        markup = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, "Пришлите фотографию товара.", reply_markup=markup)  # Переходим к запросу фото


    elif step == 'photo':
        if message.content_type != 'photo':
            bot.send_message(message.chat.id, "Пожалуйста, отправьте фотографию товара.")
            return
        photo_id = message.photo[-1].file_id
        posts_waiting_moderation[post_id]['photo_id'] = photo_id
        user_states[user_id]['step'] = 'description'
        bot.send_message(message.chat.id, "Отлично! Теперь пришлите описание товара.")

    elif step == 'description':
        if message.content_type != 'text':
            bot.send_message(message.chat.id, "Пожалуйста, отправьте текст с описанием товара.")
            return
        posts_waiting_moderation[post_id]['description'] = message.text
        user_states[user_id]['step'] = 'price'
        bot.send_message(message.chat.id, "Теперь укажите цену товара цифрами.")

    elif step == 'price':
        if message.content_type != 'text' or not message.text.isdigit():
            bot.send_message(message.chat.id, "Пожалуйста, укажите цену цифрами.")
            return
        posts_waiting_moderation[post_id]['price'] = message.text
        user_states[user_id]['step'] = 'done'
        username = message.from_user.username if message.from_user.username else message.from_user.first_name
        posts_waiting_moderation[post_id]['username'] = username
        posts_waiting_moderation[post_id]['user_id'] = user_id

        # Отправляем модератору
        send_to_moderator(post_id)

        bot.send_message(message.chat.id, "Ваш пост отправлен на модерацию. Ожидайте решения.\n"
                                          "Если хотите, можете сразу отправить следующий пост — напишите /start")
        # Убираем пользователя из состояния, чтобы он мог начать новый пост
        del user_states[user_id]

def send_to_moderator(post_id):
    post = posts_waiting_moderation[post_id]
    city = post['city']
    post_text = (f"Город: {city}\n"
                 f"Описание: {post['description']}\n"
                 f"Цена: {post['price']}\n"
                 f"Автор: @{post['username']}\n"
                 f"ID пользователя: {post['user_id']}\n\n"
                 f"Опубликовать? (+/-)")

    markup = types.InlineKeyboardMarkup()
    btn_approve = types.InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{post_id}")
    btn_reject = types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{post_id}")
    markup.add(btn_approve, btn_reject)

    try:
        bot.send_photo(MODERATOR_ID, post['photo_id'], caption=post_text, reply_markup=markup)
    except Exception as e:
        print(f"Ошибка при отправке модератору: {e}")

# --- Добавляем функцию для отправки поста в канал с кнопками ---
def send_to_channel(post_id):
    post = posts_waiting_moderation[post_id]
    city = post['city']

    if city == "Нижний Новгород":
        channel_id = CHANNEL_NN_ID
    elif city == "Москва":
        channel_id = CHANNEL_MSK_ID
    elif city == "СПБ":
        channel_id = CHANNEL_SPB_ID
    else:
        print(f"Ошибка: Неизвестный город {city}")
        return  # Прекращаем выполнение функции, если город неизвестен

    post_text = (f"Описание: {post['description']}\n"
                 f"Цена: {post['price']}\n"
                 f"Автор: @{post['username']}\n\n"
                 f"__________\n\n"
                 f"Внимние! Не переводите деньги за предоплату, бронь и тп! Будьте бдительны!")

    # Создаем клавиатуру с кнопками (одна под другой)
    markup = types.InlineKeyboardMarkup()
    btn_add_ad = types.InlineKeyboardButton("Добавить объявление", url=f"https://t.me/{PIAR_NINO_BOT_LINK.replace('@', '')}")
    btn_ads = types.InlineKeyboardButton("Реклама", url=f"https://t.me/{FDKAHF_LINK.replace('@', '')}")
    markup.add(btn_add_ad)
    markup.add(btn_ads)

    try:
        bot.send_photo(channel_id, post['photo_id'], caption=post_text, reply_markup=markup)
    except Exception as e:
        print(f"Ошибка при отправке в канал: {e}")

# --- Обработчик callback query (нажатий на кнопки) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data.startswith("approve_"):
        post_id = call.data.split("_")[1]
        send_to_channel(post_id)  # Отправляем в канал с кнопками
        bot.answer_callback_query(call.id, "Пост опубликован в канале.")
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id) # Удаляем сообщение у модератора
        del posts_waiting_moderation[post_id] # Удаляем пост из очереди

    elif call.data.startswith("reject_"):
        post_id = call.data.split("_")[1]
        user_id = posts_waiting_moderation[post_id]['user_id']
        # Запрашиваем причину отклонения у модератора
        msg = bot.send_message(call.message.chat.id, f"Укажите причину отклонения поста {post_id}:")
        bot.register_next_step_handler(msg, get_rejection_reason, post_id)
        bot.answer_callback_query(call.id, "Запрошена причина отклонения.")
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id) # Удаляем сообщение у модератора

def get_rejection_reason(message, post_id):
    rejection_reason = message.text
    user_id = posts_waiting_moderation[post_id]['user_id']

    # Отправляем причину отклонения пользователю
    bot.send_message(user_id, f"Ваш пост был отклонен модератором по причине: {rejection_reason}")

    # Удаляем пост из очереди после обработки
    del posts_waiting_moderation[post_id]

def run_bot():
    bot.remove_webhook()
    bot.infinity_polling()
