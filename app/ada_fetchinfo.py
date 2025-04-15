import requests
from app.core.config import settings

Ada_username = settings.ADAFRUIT_IO_USERNAME
Ada_key = settings.ADAFRUIT_IO_KEY

def get_last_value(feed_key: str): 
    url = f"https://io.adafruit.com/api/v2/{Ada_username}/feeds/{feed_key}/data/last"
    headers = {
        "X-AIO-Key": Ada_key,
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        print("Last Value:", data["value"])
        print("Timestamp:", data["created_at"])
        return data
    else:
        print("Error:", response.status_code, response.text)
        return None