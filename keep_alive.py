from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return 'Bot is alive!'

def run():
    # Use Render’s assigned PORT, fallback to 5000 locally
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
