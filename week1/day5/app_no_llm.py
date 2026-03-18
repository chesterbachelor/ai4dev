import os
from pathlib import Path

import requests
import time
import json
import calendar

from dotenv import load_dotenv
from openai import OpenAI

###Start setup
load_dotenv(Path(__file__).parent.parent.parent / ".env")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
AGENT_URL = os.getenv("AGENT_URL")
VERIFY_URL = os.getenv("VERIFY_URL")
client = OpenAI(
    base_url='https://openrouter.ai/api/v1',
    api_key=OPENROUTER_API_KEY,
)

# ================= KONGIGURACJA =================
API_KEY = os.getenv("PROJECT_API_KEY")
URL = os.getenv("VERIFY_URL")
ROUTE_NAME = "X-01"

# ================= FUNKCJA WYKONUJĄCA ŻĄDANIA =================
def make_api_call(action_payload):
    payload = {
        "apikey": API_KEY,
        "task": "railway",
        "answer": action_payload
    }

    while True:
        print(f"\n-> Wysyłam akcję: {action_payload.get('action')}")

        try:
            response = requests.post(URL, json=payload)
        except requests.exceptions.RequestException as e:
            print(f"   [Błąd sieci] {e}. Czekam 3 sekundy...")
            time.sleep(3)
            continue

        headers = response.headers
        status = response.status_code

        if status == 503:
            print("   [503] Serwer przeciążony (symulacja). Czekam 2 sekundy i ponawiam...")
            time.sleep(2)
            continue

        if status == 429:
            retry_after = headers.get("Retry-After")
            wait_time = int(retry_after) if retry_after else 10
            print(f"   [429] Przekroczono limit! Czekam {wait_time} sekund...")
            time.sleep(wait_time)
            continue

        remaining = headers.get("X-RateLimit-Remaining")
        reset_time = headers.get("X-RateLimit-Reset")

        if remaining is not None and int(remaining) == 0 and reset_time is not None:
            current_time = calendar.timegm(time.gmtime())
            sleep_time = max(0, int(reset_time) - current_time)
            if sleep_time > 0:
                print(f"   [RateLimit] Wyczerpano pulę zapytań. Grzecznie czekam {sleep_time + 1} s. na reset...")
                time.sleep(sleep_time + 1)

        try:
            data = response.json()
            print(f"<- Odpowiedź ({status}): {json.dumps(data, indent=2)}")

            if data.get("error") == True or data.get("ok") == False:
                print("   [UWAGA] API zwróciło błąd logiczny. Sprawdź logi powyżej.")
            return data

        except ValueError:
            print(f"   [Błąd parsowania JSON] Zwrócono tekst: {response.text[:100]}...")
            time.sleep(2)
            continue


# ================= GŁÓWNA LOGIKA =================
def main():
    print("Rozpoczynam procedurę aktywacji trasy X-01...")

    resp = make_api_call({
        "action": "reconfigure",
        "route": ROUTE_NAME
    })
    if "FLG" in str(resp): print("\n🎉 ZNALEZIONO FLAGĘ!"); return
    resp = make_api_call({
        "action": "setstatus",
        "route": ROUTE_NAME,
        "value": "RTOPEN"
    })
    if "FLG" in str(resp): print("\n🎉 ZNALEZIONO FLAGĘ!"); return
    resp = make_api_call({
        "action": "save",
        "route": ROUTE_NAME
    })
    if "FLG" in str(resp):
        print("\n🎉 ZNALEZIONO FLAGĘ!")
    else:
        print("\nSekwencja zakończona, ale flaga się nie pojawiła. Przeanalizuj odpowiedź API.")

if __name__ == "__main__":
    main()