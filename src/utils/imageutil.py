"""本地生成发送用的 JPEG 数据，保留无损缓存与原始分辨率。"""

import asyncio
from io import BytesIO
from pathlib import Path

from PIL import Image as PillowImage
from pkg.platform.types import Image

JPEG_QUALITY = 85


def encode_image_for_send(file_path: str, quality: int = JPEG_QUALITY) -> tuple:
    """尝试一次 JPEG 压缩；只有体积更小时采用，返回内容和真实扩展名。"""
    original = Path(file_path).read_bytes()
    with PillowImage.open(BytesIO(original)) as image:
        suffix = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}.get(
            image.format, Path(file_path).suffix,
        )
        if image.mode in ("RGBA", "LA") or "transparency" in image.info:
            rgba = image.convert("RGBA")
            rgb = PillowImage.new("RGB", image.size, "white")
            rgb.paste(rgba, mask=rgba.getchannel("A"))
        else:
            rgb = image.convert("RGB")
        with BytesIO() as buffer:
            # 不缩放；4:4:4 保留谱面彩色线条和文字的色彩细节。
            rgb.save(buffer, format="JPEG", quality=quality, subsampling=0, optimize=True)
            compressed = buffer.getvalue()
    return (compressed, ".jpg") if len(compressed) < len(original) else (original, suffix)


async def image_for_send(file_path: str) -> Image:
    content, _ = await asyncio.to_thread(encode_image_for_send, file_path)
    return await Image.from_local(content=content)
