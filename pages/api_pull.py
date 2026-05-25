import requests
import json

# Your session token
SESSION_TOKEN = "YOUR_SESSION_TOKEN"

# API URL
url = f"https://api.gpsinsight.com/v2/vehicle/getattributes?session_token={SESSION_TOKEN}"

try:
    # Send request
    response = requests.get(url)

    # Raise error if request failed
    response.raise_for_status()

    # Convert response to JSON
    data = response.json()

    # Save locally
    with open("vehicles.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print("All vehicle data saved successfully.")

except requests.exceptions.RequestException as e:
    print("Request failed:")
    print(e)

except json.JSONDecodeError:
    print("Response was not valid JSON.")
    print(response.text)