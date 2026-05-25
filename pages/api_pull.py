import requests
import json

url = "https://api.gpsinsight.com/v2/vehicle/getattributes?session_token=YOUR_TOKEN&vehicle=12345"

response = requests.get(url)

# Check if request worked
if response.status_code == 200:
    data = response.json()

    # Save locally
    with open("vehicles.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    print("Saved successfully.")
else:
    print("Error:", response.status_code)
    print(response.text)