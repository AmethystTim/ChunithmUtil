from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *
import os
import requests

cover_cache_dir = os.path.join(os.path.dirname(__file__), '../cache/covers')

def checkIsHit(coverUrl, imageName):
    if os.path.exists(os.path.join(cover_cache_dir, imageName)):
        return
    else:
        response = requests.get(coverUrl + imageName)
        if response.status_code == 200:
            with open(os.path.join(cover_cache_dir, imageName), 'wb') as f:
                f.write(response.content)
        return