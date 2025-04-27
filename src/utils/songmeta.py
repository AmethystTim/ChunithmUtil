import requests
import json
import os
url_zetaraku = "https://dp4p6x0xfi5o9.cloudfront.net/chunithm/data.json"
url_sega = "https://chunithm.sega.jp/storage/json/music.json"
json_path_zetaraku = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'data.json')
json_path_sega = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'data_new.json')

if __name__ == "__main__":
    # zetaraku
    response = requests.get(url_zetaraku)
    data = json.loads(response.text)
    with open(json_path_zetaraku, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    # sega
    response = requests.get(url_sega)
    data = json.loads(response.text)
    with open(json_path_sega, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)