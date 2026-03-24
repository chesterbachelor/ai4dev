import os
from pathlib import Path

import requests
import csv
import io

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")
API_KEY = os.getenv("PROJECT_API_KEY")
BASE_URL = os.getenv("AGENT_URL")

def solve():
    requests.post(f"{BASE_URL}/verify", json={"apikey": API_KEY, "task": "categorize", "answer": {"prompt": "reset"}})
    res = requests.get(f"{BASE_URL}/data/{API_KEY}/categorize.csv")
    items = [row for row in csv.reader(io.StringIO(res.text)) if row and row[0] != 'code']

    print(f"🚀 Startujemy. Próbujemy bezbłędnej klasyfikacji 10 towarów...")
    prefix = "Rules: Weapons=DNG. Reactor/Tools/Parts/Electronics=NEU. Answer only 1 word: DNG or NEU. Item "

    for item_id, description in items:
        short_desc = description.strip()[:60]
        prompt = f"{prefix}{item_id}: {short_desc}"
        print(prompt, end="\r")
        payload = {
            "apikey": API_KEY,
            "task": "categorize",
            "answer": { "prompt": prompt }
        }

        r = requests.post(f"{BASE_URL}/verify", json=payload)
        response = r.json()
        msg = str(response.get("message", ""))

        if "{FLG:" in msg:
            print(f"\n\n🏆 MAMY FLAGĘ! {msg}")
            return

        if "NOT ACCEPTED" in msg.upper():
            print(f"❌ {item_id} REJECTED (Błąd klasyfikacji).")
            return

        if response.get("code") == 0 or "ACCEPTED" in msg.upper():
            bal = response.get("balance", "N/A")
            print(f"✅ {item_id} | OK | Bal: {bal} PP")
        else:
            print(f"❌ {item_id} ERROR: {msg}")
            return

if __name__ == "__main__":
    solve()