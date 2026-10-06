"""从 ChuProg 合并的等级成绩表与牌子进度图片绘制。"""

import os.path as osp
import os
import hashlib
from pathlib import Path
from uuid import uuid4

import PIL.Image
import PIL.ImageDraw
import PIL.ImageFilter
import PIL.ImageFont

PLUGIN_DIR = Path(__file__).resolve().parents[2]
ASSET_DIR = PLUGIN_DIR / "assets" / "progress"
OUTPUT_DIR = PLUGIN_DIR / "cache" / "progress"
NOTFOUND_COVER_PATH = PLUGIN_DIR / "images" / "notfound.jpg"


class ProgressRenderer:
    def getRank(self, score: int) -> str:
        if score >= 1009000:
            return "SSS+"
        elif score >= 1007500:
            return "SSS"
        elif score >= 1005000:
            return "SS+"
        elif score >= 1000000:
            return "SS"
        elif score >= 990000:
            return "S+"
        elif score >= 975000:
            return "S"
        return "S-"


    def getRankStatistcs(self, data: list):
        sssp = f"SSS+ {len([song for song in data if song.get('score') >= 1009000])}"
        sss = f"SSS {len([song for song in data if song.get('score') >= 1007500 and song.get('score') < 1009000])}"
        ssp = f"SS+ {len([song for song in data if song.get('score') >= 1005000 and song.get('score') < 1007500])}"
        ss = f"SS {len([song for song in data if song.get('score') >= 1000000 and song.get('score') < 1005000])}"
        sp = f"S+ {len([song for song in data if song.get('score') >= 990000 and song.get('score') < 1000000])}"
        s = f"S {len([song for song in data if song.get('score') >= 975000 and song.get('score') < 990000])}"
        sm = f"S- {len([song for song in data if song.get('score') < 975000])}"
        fc = f"FC {len([song for song in data if song.get('full_combo') == 'fullcombo'])}"
        aj = f"AJ {len([song for song in data if song.get('full_combo') == 'alljustice'])}"
        return f"Total {len(data)} | {sssp} | {sss} | {ssp} | {ss} | {sp} | {s} | {sm} | {fc} | {aj}"


    def getRankColor(self, rank: str):
        rank = rank.upper()
        if "SSS+" in rank:
            return (255, 255, 204, 255) # 铂金
        elif "SSS" in rank:
            return (255, 223, 100, 255) # 金黄
        elif "SS+" in rank:
            return (200, 230, 255, 255) # 淡蓝
        elif "SS" in rank:
            return (200, 230, 255, 255)
        else:
            return (221, 221, 221, 255) # 淡灰


    def getFCAJ(self, full_combo: str):
        if full_combo == 'fullcombo':
            return "FC"
        elif full_combo == 'alljustice':
            return "AJ"
        else:
            return ""


    def drawImg(self, data: list, header: str, user_id: str, mode: str):
        level_groups = {}
        for song in data:
            level_value = str(song.get('level_value'))
            if level_value not in level_groups.keys():
                level_groups[level_value] = []
            level_groups[level_value].append(song)

        # 根据得分降序排序
        for level_value in level_groups.keys():
            level_groups[level_value] = sorted(level_groups[level_value], key=lambda x: x.get('score'), reverse=True)

        # 获取曲绘

        # Drawing settings

        NUM_PER_ROW = 12

        header_font = PIL.ImageFont.truetype(osp.join(ASSET_DIR, 'font', 'SJ-Narrow-Bold-2.ttf'), 72)
        font = PIL.ImageFont.truetype(osp.join(ASSET_DIR, 'font', 'sjnarrow.ttf'), 38)
        small_font = PIL.ImageFont.truetype(osp.join(ASSET_DIR, 'font', 'simhei.ttf'), 28)
        very_small_font = PIL.ImageFont.truetype(osp.join(ASSET_DIR, 'font', 'simhei.ttf'), 20)

        levels_sorted = sorted(level_groups, key=lambda value: float(value) if value != "None" else 0.0, reverse=True)
        row_height = 100
        margin = 20
        img_width = NUM_PER_ROW * 100 + (NUM_PER_ROW + 1) * margin
        probe = PIL.ImageDraw.Draw(PIL.Image.new("RGB", (1, 1)))
        img_height = row_height + margin
        for level in levels_sorted:
            level_text = f"[ {float(level if level != 'None' else 0.0):.1f} ]"
            stats_text = self.getRankStatistcs(level_groups[level])
            boxes = [probe.textbbox((0, 0), text, font=font) for text in (level_text, stats_text)]
            stats_height = max(box[3] - box[1] for box in boxes) + 20
            rows = (len(level_groups[level]) + NUM_PER_ROW - 1) // NUM_PER_ROW
            img_height += stats_height + int(row_height * 0.5) + rows * row_height * 2

        canvas = PIL.Image.new("RGBA", (img_width, img_height), (255, 255, 255, 0))
        draw = PIL.ImageDraw.Draw(canvas)

        heading = f"CHUNITHM {mode.upper()} {header.upper()}"
        while draw.textbbox((0, 0), heading, font=header_font)[2] > img_width - margin * 2 and header_font.size > 28:
            header_font = PIL.ImageFont.truetype(osp.join(ASSET_DIR, 'font', 'SJ-Narrow-Bold-2.ttf'), header_font.size - 2)

        # Draw each level block
        y = 0
        # 大标题
        draw.text((margin, y), heading, font=header_font, fill="black")
        y += row_height
        for level in levels_sorted:
            songs = level_groups[level]

            # 解析等级和rank统计内容
            level_text = f"[ {float(level if not level == 'None' else 0.0):.1f} ]"
            stats_text = self.getRankStatistcs(songs)

            level_box_size = draw.textbbox((0, 0), level_text, font=font)
            stats_box_size = draw.textbbox((0, 0), stats_text, font=font)

            level_text_width = level_box_size[2] - level_box_size[0]
            level_text_height = level_box_size[3] - level_box_size[1]

            stats_text_width = stats_box_size[2] - stats_box_size[0]
            stats_text_height = stats_box_size[3] - stats_box_size[1]

            stats_height = max(level_text_height, stats_text_height) + 20  # 文字高度 + 内边距
            box_padding_x = 20

            # 第一个色块：[等级定数]
            draw.rounded_rectangle(
                [(margin, y), (margin + level_text_width + box_padding_x * 2, y + stats_height + margin // 2)],
                radius=16,
                fill=(255, 255, 204, 255)
            )
            draw.text(
                (margin + box_padding_x, y + 10),
                level_text,
                font=font,
                fill="black"
            )

            # 第二个色块：[rank统计]

            # 拆分 rank 统计和 FC/AJ
            rank_stats_text = " | ".join(stats_text.split(" | ")[1:8])  # SSS+ ~ S-
            extra_stats_text = " | ".join(stats_text.split(" | ")[8:])  # FC 和 AJ

            # rank 色块
            rank_stats_box_size = draw.textbbox((0, 0), rank_stats_text, font=font)
            rank_stats_width = rank_stats_box_size[2] - rank_stats_box_size[0]
            rank_stats_x = margin + level_text_width + box_padding_x * 2 + margin

            draw.rounded_rectangle(
                [(rank_stats_x, y), (rank_stats_x + rank_stats_width + box_padding_x * 2, y + stats_height + margin // 2)],
                radius=16,
                fill=(220, 235, 250, 255)  # 淡蓝色
            )
            draw.text(
                (rank_stats_x + box_padding_x, y + 10),
                rank_stats_text,
                font=font,
                fill="black"
            )

            # FC/AJ 色块
            extra_stats_box_size = draw.textbbox((0, 0), extra_stats_text, font=font)
            extra_stats_width = extra_stats_box_size[2] - extra_stats_box_size[0]
            extra_stats_x = rank_stats_x + rank_stats_width + box_padding_x * 2 + margin

            draw.rounded_rectangle(
                [(extra_stats_x, y), (extra_stats_x + extra_stats_width + box_padding_x * 2, y + stats_height + margin // 2)],
                radius=16,
                fill=(255, 255, 204, 255)  # 铂金
            )
            draw.text(
                (extra_stats_x + box_padding_x + 2, y + 10),
                extra_stats_text,
                font=font,
                fill="black"
            )

            # 更新 y
            y += stats_height + int(row_height * 0.5)

            # 绘制歌曲列表
            for i, song in enumerate(songs):
                x = margin + (i % NUM_PER_ROW) * (100 + margin)
                row_offset = (i // NUM_PER_ROW) * (row_height * 2)
                box_y = y + row_offset

                padding = 6
                score_font_height = 28
                rank_font_height = 24

                # 绘制整体色块背景（封面+分数+评级）
                total_height = 100 + score_font_height + rank_font_height
                rank = f'(#{i+1})' + str(self.getRank(song['score']))
                color = self.getRankColor(rank)

                draw.rounded_rectangle(
                    [(x - padding, box_y - padding), (x + 100 + padding, box_y + total_height + padding)],
                    radius=12,
                    fill=color
                )

                # 曲绘
                try:
                    song_cover = PIL.Image.open(song.get("cover_path") or NOTFOUND_COVER_PATH).resize((100, 100))
                except Exception as e:
                    print(f"Failed to load cover for {song.get('id')}: {e}")
                    # song_cover = PIL.Image.new("RGB", (100, 100), (255, 255, 255))
                    song_cover = PIL.Image.new("RGB", (100, 100), (230, 230, 230))
                # 绘制斜条带表示难度
                level_index = song.get("level_index", 3)
                difficulty_colors = [
                    (102, 204, 0, 220),
                    (255, 204, 0, 220),
                    (255, 51, 51, 220),
                    (153, 51, 255, 220),
                    (0, 0, 0, 220),
                ]
                band_color = difficulty_colors[level_index]
                band_overlay = PIL.Image.new("RGBA", (100, 100), (255, 255, 255, 0))
                band_draw = PIL.ImageDraw.Draw(band_overlay)
                band_draw.polygon([(0, 0), (30, 0), (0, 30), (0, 0)], fill=band_color)

                border_thickness = 1
                border_box = [
                    x - border_thickness,
                    box_y - border_thickness,
                    x + 100 + border_thickness,
                    box_y + 100 + border_thickness
                ]
                draw.rectangle(border_box, fill="black")

                canvas.paste(song_cover, (x, box_y), mask=song_cover if song_cover.mode == 'RGBA' else None)
                canvas.alpha_composite(band_overlay, (x, box_y))

                # 绘制fc/aj
                fullcombo = self.getFCAJ(song.get('full_combo', ''))
                fullcombo_colors = {
                    'FC': (255, 223, 100, 255),
                    'AJ': (255, 255, 204, 255)
                }
                band_color = fullcombo_colors.get(fullcombo, (0, 0, 0, 0))
                # band_overlay = PIL.Image.new("RGBA", (100, 100), (255, 255, 255, 0))
                band_draw = PIL.ImageDraw.Draw(band_overlay)
                band_draw.polygon([(100, 70), (100, 100), (70, 100), (100, 70)], fill=band_color)

                canvas.paste(song_cover, (x, box_y), mask=song_cover if song_cover.mode == 'RGBA' else None)
                canvas.alpha_composite(band_overlay, (x, box_y))

                # 分数
                score_str = str(song['score'])
                score_text_size = draw.textbbox((0, 0), score_str, font=small_font)
                score_text_width = score_text_size[2] - score_text_size[0]
                score_x = x + (100 - score_text_width) // 2
                score_y = box_y + 100
                draw.text((score_x, score_y), score_str, font=small_font, fill="black")

                # 评级
                rank = f'(#{i+1})' + str(self.getRank(song['score']))
                rank_text_size = draw.textbbox((0, 0), rank, font=very_small_font)
                rank_text_width = rank_text_size[2] - rank_text_size[0]
                rank_box_width = rank_text_width + 16  # 给左右边留些空

                rank_x = x + (100 - rank_box_width) // 2
                rank_y = box_y + 100 + score_font_height

                # 评级文字
                draw.text((rank_x + 8, rank_y), rank, font=very_small_font, fill="black")

            y += ((len(songs) - 1) // NUM_PER_ROW + 1) * row_height * 2

        bg_path = osp.join(ASSET_DIR, 'bg', 'bg.webp')

        # 旋转背景后按画布宽度等比缩放，避免将原图在纵向过度拉伸。
        # 画布高度不足时居中裁剪，过高时在竖直方向交替使用镜像图平铺。
        with PIL.Image.open(bg_path) as bg_image:
            background = bg_image.convert('RGBA').rotate(-90, expand=True)

        background_height = round(background.height * canvas.width / background.width)
        background = background.resize(
            (canvas.width, background_height),
            PIL.Image.Resampling.LANCZOS
        )

        if background.height >= canvas.height:
            crop_top = (background.height - canvas.height) // 2
            background = background.crop(
                (0, crop_top, canvas.width, crop_top + canvas.height)
            )
        else:
            tiled_background = PIL.Image.new('RGBA', canvas.size)
            y = 0
            tile_index = 0
            while y < canvas.height:
                tile = background
                if tile_index % 2:
                    tile = background.transpose(PIL.Image.Transpose.FLIP_TOP_BOTTOM)
                tile_height = min(tile.height, canvas.height - y)
                tiled_background.alpha_composite(
                    tile.crop((0, 0, canvas.width, tile_height)),
                    (0, y)
                )
                y += tile_height
                tile_index += 1
            background = tiled_background

        background = background.filter(PIL.ImageFilter.GaussianBlur(radius=8))
        final_image = PIL.Image.alpha_composite(background, canvas)

        final_image = final_image.convert("RGB")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cache_key = hashlib.sha256(f"{user_id}\0{mode}\0{header}".encode("utf-8")).hexdigest()[:24]
        output = OUTPUT_DIR / f"{cache_key}.png"
        temporary = OUTPUT_DIR / f".{cache_key}-{uuid4().hex}.png"
        try:
            final_image.save(temporary)
            os.replace(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)
        return str(output)
