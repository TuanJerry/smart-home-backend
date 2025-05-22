import requests
from requests.exceptions import RequestException
from app.core.config import settings

Ada_username = settings.ADAFRUIT_IO_USERNAME
Ada_key = settings.ADAFRUIT_IO_KEY

def get_last_value(feed_key: str): 
    try:    
        url = f"https://io.adafruit.com/api/v2/{Ada_username}/feeds/{feed_key}/data/last"
        headers = {
            "X-AIO-Key": Ada_key,
        }

        response = requests.get(url, headers=headers)
    except RequestException as e:
        print("Data fetch error because data in Ada was deleted:", e)

    if response.status_code == 200:
        data = response.json()
        print("Last Value:", data["value"])
        print("Timestamp:", data["created_at"])
        return data
    else:
        print("Error:", response.status_code, response.text)
        return None
    
def get_all_value(feed_key: str): 
    url = f"https://io.adafruit.com/api/v2/{Ada_username}/feeds/{feed_key}/data"
    headers = {
        "X-AIO-Key": Ada_key,
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        # print("Last Value:", data["value"])
        # print("Timestamp:", data["created_at"])
        data_created : list[dict] = [{
            "created_at": x["created_at"],
            "value": x["value"]
        } for x in data]
        print("All Values:", data_created)
        return data_created
    else:
        print("Error:", response.status_code, response.text)
        return None