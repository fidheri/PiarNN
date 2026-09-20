
import os
import threading
from flask import Flask
import bot

app = Flask(__name__)

@app.route('/')
def health():
    return "Bot is alive", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
