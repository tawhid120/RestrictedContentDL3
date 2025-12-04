import os
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Restricted Content DL Bot is Running Successfully! 🚀"

def run():
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    # ১. ওয়েব সার্ভার ব্যাকগ্রাউন্ডে চালু করা হচ্ছে
    t = Thread(target=run)
    t.start()

    # ২. এরপর আপনার মেইন বট বা start.sh রান করা হচ্ছে
    # এটি main.py ফাইলে হাত না দিয়েই বট চালু করে দেবে
    os.system("bash start.sh")
