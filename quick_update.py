import json
import os
import difflib
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import dotenv
import PIL.Image
import requests


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "cache"
CHART_CACHE_DIR = CACHE_DIR / "charts"
COVER_CACHE_DIR = CACHE_DIR / "covers"
SONGS_PATH = DATA_DIR / "songs.json"
MAPPING_SCRIPT = BASE_DIR / "src" / "utils" / "mapping.py"
SONGMETA_SCRIPT = BASE_DIR / "src" / "utils" / "songmeta.py"

CHART_DIFFS = {
    "EXP": "exp",
    "MAS": "mas",
    "ULT": "ult",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    ),
}


def load_songs() -> list[dict]:
    if not SONGS_PATH.exists():
        return []
    with SONGS_PATH.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("songs", [])
    return data


def song_id(song: dict) -> str:
    return str(song.get("idx", ""))


def song_key(song: dict) -> tuple[str, str]:
    return song_id(song), str(song.get("title", ""))


def unique_songs(songs: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for song in songs:
        key = song_id(song)
        if key in seen:
            continue
        seen.add(key)
        result.append(song)
    return result


def start_vpn() -> subprocess.Popen | None:
    print("[ChunithmUtil] 启动代理：vpn")
    try:
        proc = subprocess.Popen(
            ["bash", "-lc", "vpn"],
            cwd=BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except FileNotFoundError:
        print("[ChunithmUtil] 未找到 bash，跳过自动启动代理")
        return None
    except Exception as e:
        print(f"[ChunithmUtil] 启动代理失败：{type(e).__name__}: {e}")
        return None

    time.sleep(3)
    if proc.poll() is not None:
        print("[ChunithmUtil] vpn 命令已退出，若代理未生效请先手动启动")
        return None
    return proc


def stop_vpn(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    print("[ChunithmUtil] 关闭本脚本启动的代理进程")
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except ProcessLookupError:
        return
    except Exception as e:
        print(f"[ChunithmUtil] 关闭代理失败：{type(e).__name__}: {e}")


def run_update_script(script: Path) -> None:
    print(f"[ChunithmUtil] 执行 {script.relative_to(BASE_DIR)}")
    subprocess.run([sys.executable, str(script)], cwd=BASE_DIR, check=True)


def load_chart_maps() -> tuple[dict, dict]:
    id2name_path = DATA_DIR / "chartId2Name.json"
    id2gen_path = DATA_DIR / "chartId2Gen.json"
    with id2name_path.open("r", encoding="utf-8") as f:
        id2name = json.load(f)
    with id2gen_path.open("r", encoding="utf-8") as f:
        id2gen = json.load(f)
    return id2name, id2gen


def find_chart_id(song: dict, id2name: dict) -> str | None:
    title = song.get("title")
    if not title:
        return None

    names = [name for name in id2name.values() if name is not None]
    lowercase_names = [name.lower() for name in names]
    title_lower = title.lower()

    if title_lower in lowercase_names:
        matched_name = names[lowercase_names.index(title_lower)]
        return list(id2name.keys())[list(id2name.values()).index(matched_name)]

    print(f"[ChunithmUtil] 精确标题未命中谱面 ID，尝试兜底匹配：c{song_id(song)} {title}")
    results = difflib.get_close_matches(title_lower, lowercase_names, n=10, cutoff=0.8)
    for name in names:
        if re.fullmatch("[A-Za-z]+", title) and len(title) <= 1:
            continue
        if title_lower in name.lower():
            results.append(name.lower())

    if results:
        matched_name = names[lowercase_names.index(results[0])]
        return list(id2name.keys())[list(id2name.values()).index(matched_name)]
    return None


def chart_cache_path(chart_id: str, diff: str) -> Path:
    suffix = "" if diff == "mas" else diff
    return CHART_CACHE_DIR / f"{chart_id}_{suffix}.png"


def chart_urls(chart_id: str, gen: str, diff: str) -> list[str]:
    chart_url = os.getenv("CHART_URL", "").replace("<chartid>", chart_id)
    bg_url = os.getenv("CHART_BG_URL", "").replace("<chartid>", chart_id)
    bar_url = os.getenv("CHART_BAR_URL", "").replace("<chartid>", chart_id)

    if diff == "ult":
        chart_url = chart_url.replace("mst.png", "ult.png").replace("<gen>", "ult")
        bg_url = bg_url.replace("<gen>", "ult")
        bar_url = bar_url.replace("<gen>", "ult")
    else:
        chart_url = chart_url.replace("<gen>", gen)
        bg_url = bg_url.replace("<gen>", gen)
        bar_url = bar_url.replace("<gen>", gen)
    if diff != "mas":
        chart_url = chart_url.replace("mst.png", f"{diff}.png")

    return [chart_url, bg_url, bar_url]


def download_file(url: str, save_path: Path) -> bool:
    try:
        response = requests.get(url, headers=HEADERS, timeout=120)
    except requests.RequestException as e:
        print(f"[ChunithmUtil] 下载失败：{url} - {type(e).__name__}: {e}")
        return False
    if response.status_code != 200:
        print(f"[ChunithmUtil] 请求失败：{response.status_code} {url}")
        return False
    save_path.write_bytes(response.content)
    return True


def process_chart(save_path: Path) -> bool:
    imgs = []
    temp_paths = [Path(str(save_path).replace(".png", f"_{i}.png")) for i in range(3)]
    for img_path in temp_paths:
        if not img_path.exists():
            print(f"[ChunithmUtil] 图片不存在：{img_path}")
            return False
        imgs.append(PIL.Image.open(img_path).convert("RGBA"))

    min_width = min(img.size[0] for img in imgs)
    min_height = min(img.size[1] for img in imgs)
    imgs = [img.crop((0, 0, min_width, min_height)) for img in imgs]

    new_image = PIL.Image.new("RGBA", (min_width, min_height), color=(0, 0, 0, 255))
    new_image = PIL.Image.alpha_composite(new_image, imgs[1])
    new_image = PIL.Image.alpha_composite(new_image, imgs[0])
    new_image = PIL.Image.alpha_composite(new_image, imgs[2])
    new_image.save(save_path)

    for img_path in temp_paths:
        img_path.unlink(missing_ok=True)
    return True


def cache_chart(song: dict, chart_id: str, gen: str, diff: str) -> bool:
    save_path = chart_cache_path(chart_id, diff)
    if save_path.exists():
        return True

    urls = chart_urls(chart_id, gen, diff)
    if not all(urls):
        print("[ChunithmUtil] 谱面 URL 环境变量不完整，跳过谱面缓存")
        return False

    print(f"[ChunithmUtil] 缓存谱面：{song.get('title')} {diff}")
    for i, url in enumerate(urls):
        temp_path = Path(str(save_path).replace(".png", f"_{i}.png"))
        if not download_file(url, temp_path):
            return False
    return process_chart(save_path)


def cache_cover(song: dict) -> bool:
    image_name = song.get("img")
    cover_url = os.getenv("COVER_URL", "")
    if not image_name:
        return False
    if not cover_url:
        print("[ChunithmUtil] COVER_URL 未配置，跳过曲绘缓存")
        return False

    save_path = COVER_CACHE_DIR / f"{image_name}.webp"
    if save_path.exists():
        return True

    print(f"[ChunithmUtil] 缓存曲绘：{song.get('title')}")
    return download_file(f"{cover_url}{image_name}.webp", save_path)


def cache_new_song_assets(new_songs: list[dict]) -> None:
    if not new_songs:
        print("[ChunithmUtil] 没有检测到新歌，跳过预缓存")
        return

    id2name, id2gen = load_chart_maps()
    cover_ok = chart_ok = chart_total = 0

    for song in unique_songs(new_songs):
        if cache_cover(song):
            cover_ok += 1

        chart_id = find_chart_id(song, id2name)
        if chart_id is None:
            print(f"[ChunithmUtil] 未找到谱面 ID：{song.get('title')}")
            continue
        gen = id2gen.get(chart_id)
        if gen is None:
            print(f"[ChunithmUtil] 未找到谱面版本：{song.get('title')} ({chart_id})")
            continue

        song_diffs = {
            CHART_DIFFS[s.get("diff")]
            for s in new_songs
            if song_id(s) == song_id(song) and s.get("diff") in CHART_DIFFS
        }
        for diff in sorted(song_diffs):
            chart_total += 1
            if cache_chart(song, chart_id, gen, diff):
                chart_ok += 1

    print(
        f"[ChunithmUtil] 预缓存完成：曲绘 {cover_ok}/{len(unique_songs(new_songs))}，"
        f"谱面 {chart_ok}/{chart_total}"
    )


def main() -> None:
    dotenv.load_dotenv(BASE_DIR / ".env")
    CHART_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    COVER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    old_ids = {song_id(song) for song in load_songs()}
    vpn_proc = start_vpn()
    try:
        run_update_script(MAPPING_SCRIPT)
        run_update_script(SONGMETA_SCRIPT)

        updated_songs = load_songs()
        new_songs = [song for song in updated_songs if song_id(song) not in old_ids]
        new_unique = unique_songs(new_songs)
        print(f"[ChunithmUtil] 检测到新歌 {len(new_unique)} 首")
        for song in new_unique[:20]:
            print(f"  - c{song.get('idx')} {song.get('title')}")
        if len(new_unique) > 20:
            print(f"  ... 还有 {len(new_unique) - 20} 首")

        cache_new_song_assets(new_songs)
    finally:
        stop_vpn(vpn_proc)


if __name__ == "__main__":
    main()
