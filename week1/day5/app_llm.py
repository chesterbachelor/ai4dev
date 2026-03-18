import os
from pathlib import Path

import requests
import time
import json
import calendar

from dotenv import load_dotenv
from openai import OpenAI

# ================= KONGIGURACJA =================
load_dotenv(Path(__file__).parent.parent.parent / ".env")
URL = os.getenv("VERIFY_URL")
AG3NTS_API_KEY = os.getenv("PROJECT_API_KEY")

###Start setup
OPENAI_API_KEY = os.getenv("OPENROUTER_API_KEY")
AGENT_URL = os.getenv("AGENT_URL")
VERIFY_URL = os.getenv("VERIFY_URL")
client = OpenAI(
    base_url='https://openrouter.ai/api/v1',
    api_key=OPENAI_API_KEY,
)

# ================= 1. OBSŁUGA SIECI  =================
def make_api_call(action_payload):
    payload = {
        "apikey": AG3NTS_API_KEY,
        "task": "railway",
        "answer": action_payload
    }

    print(payload)
    while True:
        try:
            response = requests.post(URL, json=payload)
        except requests.exceptions.RequestException as e:
            print(f"   [Sieć] {e}. Czekam...")
            time.sleep(3)
            continue
        status = response.status_code
        if status == 503:
            print("   [Sieć] 503 - Czekam 2 sekundy...")
            time.sleep(2)
            continue
        if status == 429:
            wait_time = int(response.headers.get("Retry-After", 10))
            print(f"   [Sieć] 429 - Limit! Czekam {wait_time} s...")
            time.sleep(wait_time)
            continue

        remaining = response.headers.get("X-RateLimit-Remaining")
        reset_time = response.headers.get("X-RateLimit-Reset")
        if remaining is not None and int(remaining) == 0 and reset_time is not None:
            sleep_time = max(0, int(reset_time) - calendar.timegm(time.gmtime()))
            if sleep_time > 0:
                print(f"   [Sieć] Chłodzenie limitów... Czekam {sleep_time + 1} s.")
                time.sleep(sleep_time + 1)
        return response.json()

# ================= LLM =================
def get_next_action_from_llm(conversation_history):
    system_prompt = """Jesteś autonomicznym agentem integrującym się z nieznanym API.
Twoim celem jest aktywacja trasy o nazwie 'X-01'.
Zaczynasz bez wiedzy o API. Twoją pierwszą akcją zawsze powinno być 'help'.
Analizuj dokładnie odpowiedzi z API i na ich podstawie generuj kolejne żądania.

ZASADY ZWROTU:
1. Zwracasz WYŁĄCZNIE obiekt JSON, który zostanie wstawiony w pole 'answer' w żądaniu do API.
2. Zwrócony JSON musi zawierać pole 'action' i ewentualne inne parametry wymagane przez API.
3. Nie dodawaj żadnego tekstu pobocznego, tylko poprawny JSON.

Przykład pierwszej akcji:
{
  "action": "help"
}
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)

    print("   [LLM] Zastanawiam się nad kolejnym krokiem...")
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={ "type": "json_object" },
        messages=messages,
        temperature=0.1
    )
    llm_output = response.choices[0].message.content
    return json.loads(llm_output)

# ================= 3. GŁÓWNA PĘTLA AGENTA =================
def main():
    print("🤖 Uruchamiam agenta autonomicznego dla zadania railway...")
    conversation_history = []
    step = 1
    while True:
        print(f"\n--- KROK {step} ---")
        try:
            next_action = get_next_action_from_llm(conversation_history)
        except Exception as e:
            print(f"Błąd przy odpytywaniu LLM: {e}")
            break
        print(f"➡️ LLM wygenerował payload: {json.dumps(next_action)}")
        conversation_history.append({
            "role": "assistant",
            "content": json.dumps(next_action)
        })
        print("➡️ Wysyłam do API...")
        api_response = make_api_call(next_action)
        print(f"⬅️ Odpowiedź API: {json.dumps(api_response, indent=2)}")
        if "FLG" in str(api_response):
            print("\n🎉 ZNALEZIONO FLAGĘ! Zadanie wykonane.")
            break
        if step >= 10:
            print("\n⚠️ Agent wykonał zbyt wiele kroków. Przerywam, żeby nie zużyć limitów.")
            break
        conversation_history.append({
            "role": "user",
            "content": f"Odpowiedź z serwera:\n{json.dumps(api_response)}"
        })
        step += 1

if __name__ == "__main__":
    main()