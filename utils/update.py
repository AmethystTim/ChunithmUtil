import requests
import json
import os
url = "https://dp4p6x0xfi5o9.cloudfront.net/chunithm/data.json"
json_path = os.path.join(os.path.dirname(__file__), "../data", "data.json")

if __name__ == "__main__":
    response = requests.get(url)
    data = json.loads(response.text)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)