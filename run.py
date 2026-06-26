import subprocess
import time
import sys

# GitHub Actions timeout is 58 min = 3480 seconds
# We restart bot every 55 min = 3300 seconds
# This gives 3 min overlap before next workflow kicks in

RUN_DURATION = 3300  # 55 minutes

while True:
    print(f"Starting bot... will restart in {RUN_DURATION//60} minutes")
    process = subprocess.Popen([sys.executable, "bot.py"])
    time.sleep(RUN_DURATION)
    print("Restarting bot now...")
    process.terminate()
    time.sleep(5)
    process.kill()
