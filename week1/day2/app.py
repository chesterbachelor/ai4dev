import json
import os
import time
from pathlib import Path
import requests
from openai import OpenAI
from dotenv import load_dotenv
from math import radians, cos, sin, asin, sqrt

load_dotenv(Path(__file__).parent.parent.parent / ".env")
PROJECT_API_KEY = os.getenv("PROJECT_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
AGENT_URL = os.getenv("AGENT_URL")
client = OpenAI(
    base_url='https://openrouter.ai/api/v1',
    api_key=OPENROUTER_API_KEY,
)
data = json.loads((Path(__file__).parent.parent.parent / "classified_people.json").read_text())

def extract_function_call(message) -> str | None:
    if message.finish_reason == "tool_calls":
        return message.message.tool_calls[0].function.name
    return None

def requestResponse(input) -> object:
    request = {
        "model": 'openai/gpt-4o-mini',
        "tools": tools,
        "messages": input
    }
    response = client.chat.completions.create(**request)
    return response.choices[0]


tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate_distance",
            "description": "Calculate the distance between selected place (specified in decimal degrees)",
            "parameters": {
                "type": "object",
                "properties": {
                    "locationLatituide": {
                        "type": "number",
                        "description": "Place latitude",
                    },
                    "locationLongitude": {
                        "type": "number",
                        "description": "Place longitude",
                    },
                },
                "required": [
                    "locationLatituide",
                    "locationLongitude"
                ],
                "additionalProperties": False,
            },
        },
    },
]

def tools_function(args, locations):
    return calculate_distance(**args, locationsToCompare=locations)

def calculate_distance(locationLatituide: float,
    locationLongitude: float,
    locationsToCompare: list,
) -> float:
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    min_dist = float('inf')
    for loc in locationsToCompare:
        lon = loc['longitude']
        lat = loc['latitude']
        lon1, lat1, lon, lat = map(radians, [locationLatituide, locationLongitude, lon, lat])

        # haversine formula
        dlon = lon - lon1
        dlat = lat - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371 # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.
        dist =  c * r
        if dist < min_dist:
            min_dist = dist

        return min_dist

def get_power_plants():
    while True:
        power_plant = requests.get(f'{AGENT_URL}/data/{PROJECT_API_KEY}/findhim_locations.json')
        if power_plant.status_code == 200:
            locations = power_plant.json()
            return locations
        print("Waiting for power plants...")
        print(f"Status code: {power_plant.status_code}, Response: {power_plant.text}")
        time.sleep(10)

closest_person = None
min_distance = float('inf')
power_plant_locations = get_power_plants()

for people in data:
    distances = []
    request = {
        "name": people["name"],
        "surname": people["surname"],
        "apikey": PROJECT_API_KEY
    }
    place = requests.post(f'{AGENT_URL}/api/location', json=request)
    person_locations = place.json() # List of locations visited by this person
    for city_name, plant_data in power_plant_locations['power_plants'].items():
        max_attempts = 2
        starting_message = (
            "I want to find who was the closest person to the power plant. "
            "I will provide the city in which power plant is, give me its location in decimal degrees. "
            f"Power plant city: {city_name}\n"
        )
        messages =  [
            {
                "role": "user",
                "content": starting_message
            }
        ]

        while max_attempts > 0:
            max_attempts -= 1

            response = requestResponse(messages)
            if extract_function_call(response) == None:
                break
            tool_call = response.message.tool_calls[0]
            #messages.append({"role": "assistant", "content": None, "function": tool_call.function})
            tools_response = tools_function(json.loads(tool_call.function.arguments), person_locations)
           # messages.append({
           #     "role": "tool",
           #     "tool_call_id": tool_call.id,
           #     "content": json.dumps(tools_response),
           # })
        distances.append({ 'city': city_name, 'distance': tools_response })
    if distances:
        closest_city = min(distances, key=lambda d: d['distance'])
        print(f"{people['name']} {people['surname']} closest to {closest_city['city']} at {closest_city['distance']:.2f} km")

        close_power_plant = power_plant_locations['power_plants'][closest_city['city']]
        request_for_level = {
            "name": people["name"],
            "surname": people["surname"],
            "birthYear": people["born"],
            "apikey": PROJECT_API_KEY
        }
        level = requests.post(f'{AGENT_URL}/api/accesslevel', json=request_for_level)
        request_for_flag = {
            "apikey": PROJECT_API_KEY,
            'task': 'findhim',
            'answer': {
                "name": people["name"],
                "surname": people["surname"],
                "accessLevel": level.json()['accessLevel'],
                "powerPlant": close_power_plant['code']
            }
        }
    flag = requests.post(f'{AGENT_URL}/verify', json=request_for_flag)

    print(flag.json())
