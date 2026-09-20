import os
import threading
from flask import Flask
import bot

app = Flask(__name__)

@app.route('/')
def health():
    return "Bot is alive", 200

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке, чтобы он не мешал Flask
    bot_thread = threading.Thread(target=bot.run_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # Запускаем веб-сервер (открываем порт для Render)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
