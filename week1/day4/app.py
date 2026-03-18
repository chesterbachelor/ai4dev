import json
import os
from pathlib import Path
from dotenv import load_dotenv
import requests
import re
import base64
from openai import OpenAI

###Start setup
load_dotenv(Path(__file__).parent.parent.parent / ".env")
PROJECT_API_KEY = os.getenv("PROJECT_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
AGENT_URL = os.getenv("AGENT_URL")
VERIFY_URL = os.getenv("VERIFY_URL")
client = OpenAI(
    base_url='https://openrouter.ai/api/v1',
    api_key=OPENROUTER_API_KEY,
)

BASE_DOC_URL = f"{AGENT_URL}/dane/doc/"
INDEX_URL = f"{BASE_DOC_URL}index.md"

####
def fetch_file(url):
    response = requests.get(url)
    response.raise_for_status()
    return response

def encode_image_to_base64(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

def download_documentation():
    """Pobiera index.md i szuka linków do innych plików (.md, .png, .jpg)."""
    print("Pobieranie index.md...")
    index_content = fetch_file(INDEX_URL).text

    docs = {"text": [f"--- INDEX.MD ---\n{index_content}"], "images": []}

    # Proste wyszukiwanie linków w formacie markdown: [tekst](plik.ext)
    # Wyłapujemy pliki .md, .png, .jpg
    links = re.findall(r'\[include file="([^"]+\.(?:md|png|jpg))"\]', index_content)
    print(links)
    for link in set(links): # set() usuwa duplikaty
        file_url = BASE_DOC_URL + link
        print(f"Pobieranie załącznika: {link}...")

        try:
            response = fetch_file(file_url)
            if link.endswith('.md'):
                docs["text"].append(f"--- {link.upper()} ---\n{response.text}")
            elif link.endswith(('.png', '.jpg')):
                b64_image = encode_image_to_base64(response.content)
                docs["images"].append({
                    "name": link,
                    "data": b64_image,
                    "mime_type": "image/png" if link.endswith('.png') else "image/jpeg"
                })
        except Exception as e:
            print(f"Błąd podczas pobierania {link}: {e}")

    return docs

def ask_llm(docs, error_feedback=None):
    """Buduje prompt i wysyła zapytanie do LLM (z obsługą Vision)."""

    # Połączone teksty z dokumentacji
    all_text_docs = "\n\n".join(docs["text"])

    # Konstrukcja System Promptu
    system_prompt = f"""Jesteś zaawansowanym asystentem logistycznym.
Twoim zadaniem jest wypełnienie deklaracji transportu w Systemie Przesyłek Konduktorskich.

Oto dokumentacja (Regulaminy, cenniki, wzory):
{all_text_docs}

DANE PRZESYŁKI:
- Nadawca: 450202122
- Punkt nadawczy: Gdańsk
- Punkt docelowy: Żarnowiec
- Waga: 2800 kg
- Zawartość: kasety z paliwem do reaktora
- Uwagi specjalne: BRAK (absolutnie puste pole, nie dodawaj nic)
- Budżet: 0 PP (musisz wydedukować z dokumentacji jak zaklasyfikować przesyłkę by była darmowa/dla Systemu).
- Trasa zamknięta: Zignoruj to, wpisz poprawny kod trasy.

ZASADY ZWROTU:
1. Zwróć TYLKO i WYŁĄCZNIE surowy tekst wypełnionej deklaracji.
2. Musi on być formacie DOKŁADNIE odpowiadającym wzorowi z dokumentacji (odpowiednie spacje, myślniki itp.).
3. Żadnego wstępu, żadnych bloków kodu markdown (```). Po prostu sam tekst deklaracji.
4. Wszystko musi byc uzupelnione. Data musi byc aktulna w dobry m formacie.
5. Zwroc uwage na podstawowa dostepna wage dla wagonow, dodaj tylko tyle ile jest potrzebnych
"""

    if error_feedback:
        system_prompt += f"\n\nUWAGA! Poprzednia próba została odrzucona przez system z błędem:\n{error_feedback}\nZidentyfikuj swój błąd na podstawie dokumentacji i popraw deklarację!"

    # Przygotowanie wiadomości dla modelu (wsparcie dla tekstu + obrazów)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": [{"type": "text", "text": "Przeanalizuj również załączone obrazy dokumentacji (jeśli są) i wygeneruj poprawną deklarację."}]}
    ]

    # Dodawanie obrazów do promptu użytkownika
    for img in docs["images"]:
        messages[1]["content"].append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{img['mime_type']};base64,{img['data']}",
                "detail": "high"
            }
        })

    print("Wysyłanie zapytania do LLM...")
    response = client.chat.completions.create(
        model="gpt-4o", # Używamy modelu multimodalnego
        messages=messages,
        temperature=0.1 # Niska temperatura dla precyzyjnych zadań
    )

    return response.choices[0].message.content.strip()

def send_to_hub(declaration):
    """Wysyła deklarację do weryfikacji w API Hub."""
    payload = {
        "apikey": PROJECT_API_KEY,
        "task": "sendit",
        "answer": {
            "declaration": declaration
        }
    }

    print("Wysyłanie deklaracji do weryfikacji...")
    response = requests.post(VERIFY_URL, json=payload)
    return response.json()


def main():
    # 1. Pobierz wiedzę
    docs = download_documentation()
    print(json.dumps(docs, indent=2))
    error_feedback = None
    max_retries = 2

    # 2. Pętla prób i błędów
    for attempt in range(1, max_retries + 1):
        print(f"\n--- Próba {attempt}/{max_retries} ---")

        # Generowanie deklaracji
        declaration = ask_llm(docs, error_feedback)
        print("\nWygenerowana deklaracja:\n", declaration, "\n")

        # Weryfikacja
        result = send_to_hub(declaration)
        print("Odpowiedź z API:", result)

        # Sprawdzanie sukcesu
        if result.get("code") == 0 or "FLG" in str(result):
            print("\n🎉 SUKCES! Flaga zdobyta:")
            print(result.get("message", result))
            break
        else:
            # Pobranie komunikatu błędu do kolejnego promptu
            error_feedback = result.get("message", str(result))
            print(f"❌ Odrzucono. Błąd: {error_feedback}")

    else:
        print("\nPrzekroczono maksymalną liczbę prób. Przeanalizuj logi ręcznie.")

if __name__ == "__main__":
    main()