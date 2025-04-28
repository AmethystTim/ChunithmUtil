import requests
import json
import os
url_zetaraku = "https://dp4p6x0xfi5o9.cloudfront.net/chunithm/data.json"
url_sega = "https://chunithm.sega.jp/storage/json/music.json"
json_path_zetaraku = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'data.json')
json_path_sega = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'data_new.json')

def songMeta():
    # zetaraku
    response = requests.get(url_zetaraku)
    data = json.loads(response.text)
    
    # 捕获新数据
    diff = []
    
    if os.path.exists(json_path_zetaraku):
        with open(json_path_zetaraku, "r", encoding="utf-8") as f:
            old_songs = json.load(f).get("songs")
            diff = [x for x in data.get('songs') if x not in old_songs]
    
    with open(json_path_zetaraku, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    # sega
    response = requests.get(url_sega)
    data = json.loads(response.text)
    with open(json_path_sega, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    return diff

if __name__ == "__main__":
    songMeta()