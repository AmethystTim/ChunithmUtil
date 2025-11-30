import requests
import json
import os

url_reiwa = "https://reiwa.f5.si/chunithm_record.json"
url_zetaraku = "https://dp4p6x0xfi5o9.cloudfront.net/chunithm/data.json"
url_sega = "https://chunithm.sega.jp/storage/json/music.json"

json_path_zetaraku = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'data.json')
json_path_sega = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'sega.json')
json_path_reiwa = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'songs.json')

def songMeta():
    # reiwa
    response = requests.get(url_reiwa)
    data = json.loads(response.content.decode('utf-8-sig'))
    
    # 捕获新数据
    diff = []
    
    # if os.path.exists(json_path_reiwa):
    #     with open(json_path_reiwa, "r", encoding="utf-8-sig") as f:
    #         old_songs = json.load(f).get("songs")
    #         diff = [x for x in data.get('songs') if x not in old_songs]
    
    with open(json_path_reiwa, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    # sega
    response = requests.get(url_sega)
    data = json.loads(response.text)
    with open(json_path_sega, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    # 去重
    exist = []
    for diff_song in diff:
        if diff_song.get('title') in exist:
            diff.remove(diff_song)
        else:
            exist.append(diff_song.get('title'))
    
    return diff

if __name__ == "__main__":
    songMeta()