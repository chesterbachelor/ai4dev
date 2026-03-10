import csv
import io
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from openai import OpenAI
import json

load_dotenv()

CURRENT_YEAR = 2026
PROJECT_API_KEY = os.getenv('PROJECT_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
VERIFY_URL = os.getenv('VERIFY_URL')
TEMPLATE_FOR_DATA = os.environ["FIRST_TASK_URL"]

client = OpenAI(
    base_url='https://openrouter.ai/api/v1',
    api_key=OPENROUTER_API_KEY,
)

format_response = {
    'type': 'json_schema',
    'json_schema': {
        'name': 'people',
        'strict': True,
        'schema': {
            'type': 'object',
            'properties': {
                'description': {'type': 'string', 'description': 'description provided by me'},
                'tags': {'type': 'array', 'items': {'type': 'string'}, 'description': 'list of tags that describe the job'},
            },
            'required': ['description', 'tags'],
            'additionalProperties': False
        }
    }
}

url = TEMPLATE_FOR_DATA.format(PROJECT_API_KEY=PROJECT_API_KEY)
response = requests.get(url)
reader = csv.DictReader(io.StringIO(response.text))
rows = list(reader)

aged_males = [
    row for row in rows
    if row['gender'] == 'M'
    and row['birthPlace'] == 'Grudziądz'
    and CURRENT_YEAR - 40 <= int(row['birthDate'].split('-')[0]) <= CURRENT_YEAR - 20
]

content = """
You will receive a job description. Return a short description and tag or list of thas that best categorises the job.  
One person can have more than one tag (for example person can have tag "IT" and "transport").
You can only use this tags :
IT - which is about a person working in computer department,
transport - which is a person which works include transportation, moving stuff around,
edukacja - which is a person who teaches something,
medycyna - which is a person who works in medical department or is a doctor, or works in a drug store,
praca z ludźmi - work which includes working with people, for example in a shop, or in a restaurant, or in a hotel,
praca z pojazdami - work which includes driving, or working with a car, or working with a motorcycle, or working with a bicycle,
praca fizyczna - work which manual labor, or work which includes working with a machine, or work which includes working with a tool
"""

def classify_job(person: dict) -> dict:
    completion = client.chat.completions.create(
        model='openai/gpt-4o-mini',
        response_format=format_response,
        messages=[
            {
                'role': 'system',
                'content': content
            },
            {
                'role': 'user',
                'content': person['job']
            }
        ]
    )
    return {
        'person': f"{person['name']} {person['surname']}",
        'birthDate': person['birthDate'],
        'city': person['birthPlace'],
        'job': person['job'],
        'result': completion.choices[0].message.content
    }


results = []
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(classify_job, person): person for person in aged_males}
    for future in as_completed(futures):
        try:
            results.append(future.result())
        except Exception as e:
            person = futures[future]
            print(f"Error processing {person['name']} {person['surname']}: {e}")


final_answer = []
transport_workers = [
    r for r in results
    if 'transport' in json.loads(r['result'])['tags']
]
for r in results:
    print(r)
for r in transport_workers:
    name = r['person'].split(' ')
    result = json.loads(r['result'])
    worker = {
        'name': name[0],
        'surname': name[1],
        'gender': 'M',
        'born': r['birthDate'].split('-')[0],
        'city': 'Grudziądz',
        'tags': result['tags']
    }
    final_answer.append(worker)

answer = {
    "apikey": PROJECT_API_KEY,
    "task": 'people',
    'answer': final_answer,
}

verify_response = requests.post(VERIFY_URL, json=answer)
print(verify_response.status_code)
print(verify_response.json())

