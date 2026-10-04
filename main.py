#!/usr/bin/env python3
"""
Apostado Play Bot — Entry Point for Railway/Render/Heroku
This file redirects to the main bot file.
"""
import subprocess
import sys
import os

# Run the actual bot
if __name__ == "__main__":
    bot_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "freefire-bot-main.py")
    # exec the bot file in the current process so signals work correctly
    with open(bot_file, "r", encoding="utf-8") as f:
        code = compile(f.read(), bot_file, "exec")
        exec(code)
