#!/usr/bin/env python3
"""
Apostado Play Bot — Entry Point for Railway/Render/Heroku
Forces pip install then runs the bot.
"""
import subprocess
import sys
import os

def ensure_dependencies():
    """Install dependencies if discord.py is not available."""
    try:
        import discord
    except ImportError:
        print("⚠️ discord.py not found — installing dependencies...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "-r", os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
        ])
        print("✅ Dependencies installed successfully")

if __name__ == "__main__":
    ensure_dependencies()
    bot_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "freefire-bot-main.py")
    with open(bot_file, "r", encoding="utf-8") as f:
        code = compile(f.read(), bot_file, "exec")
        exec(code)
