import asyncio
import os
import os.path as osp
import json
import dotenv
import numpy as np
import requests
import zlib
import base64
import socket
import binascii
from urllib.parse import urlparse, urlencode, parse_qs, unquote
from Crypto.Cipher import AES
from typing import Optional, Any

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .query_song import searchSong
from .utils.songutil import *
from .utils.recorddb import record_flags, save_record

dotenv.load_dotenv()
SONGS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("SONG_PATH"))
DB_PATH = os.path.join(os.path.dirname(__file__), "..", 'data', 'data.db')
LX_JSON_PATH = osp.join(osp.dirname(__file__), '..', 'data', 'lx.json')
RIN_JSON_PATH = osp.join(osp.dirname(__file__), '..', 'data', 'rin.json')
SHIRO_JSON_PATH = osp.join(osp.dirname(__file__), '..', 'data','shiro.json')
HELP_API_IMG_PATH = osp.join(osp.dirname(__file__), '..', 'images', 'api.png')

# ========= 落雪查分器 =========
class LXHandler:
    def __init__(self, ctx: EventContext):
        self.ctx = ctx
        self.user_id = str(ctx.event.sender_id)
        self.song_url = "https://maimai.lxns.net/api/v0/chunithm/song/list"
        self.record_url = "https://maimai.lxns.net/api/v0/user/chunithm/player/scores"

    async def readUsersJson(self):
        users = {}
        with open(LX_JSON_PATH, 'r') as f:
            users = json.load(f).get('users', {})
        return users

    async def writeUsersJson(self, users: dict):
        try:
            with open(LX_JSON_PATH, 'w') as f:
                json.dump({'users': users}, f, indent=4)
            return 0
        except Exception as e:
            await self.ctx.reply([Plain(f'写入用户信息失败：{e}')])
            return -1

    def checkIsBind(self, users: dict):
        return self.user_id in users.keys()

    def getSongs(self) -> list:
        response = requests.get(self.song_url)
        data = response.json()
        songs = data.get('songs', [])
        return songs

    def updateRecord(self, user_id: str, cid: str, score: int, difficulty: int, record=None):
        fc, aj = record_flags(record or {}, "lx")
        return save_record(
            DB_PATH, user_id, cid, score, difficulty, "lx", only_if_higher=True,
            is_full_combo=fc, is_all_justice=aj,
        )

    async def copyLXRecord(self):
        users = await self.readUsersJson()
        if not self.checkIsBind(users):
            img = await Image.from_local(HELP_API_IMG_PATH)
            await self.ctx.reply([
                Plain('你还没有绑定账号，请先使用“chubind [服务器] [TOKEN]”绑定账号\n· rin: TOKEN为20位卡号\n· shiro: TOKEN为20位卡号\n· lx: 落雪查分器TOKEN获取地址：https://maimai.lxns.net/user/profile?tab=thirdparty'),
                img
            ])
            return
        new_records = 0
        # 请求记录
        headers = {
            "X-User-Token": users[self.user_id],
        }

        try:
            response = await asyncio.to_thread(
                requests.get, self.record_url, headers=headers, timeout=15
            )
        except requests.RequestException:
            await self.ctx.reply([Plain('获取落雪成绩失败：连接查分器时出错，请稍后重试')])
            return
        try:
            data = response.json()
        except ValueError:
            await self.ctx.reply([Plain('获取落雪成绩失败：查分器返回了无效响应，请稍后重试')])
            return
        if not isinstance(data, dict):
            await self.ctx.reply([Plain('获取落雪成绩失败：查分器返回了无效响应，请稍后重试')])
            return
        if response.status_code == 401 or data.get('code') == 401:
            await self.ctx.reply([Plain('落雪个人 API 密钥无效或已过期，请使用 chubind lx [TOKEN] 更新绑定')])
            return
        if response.status_code != 200 or data.get('code') != 200 or data.get('success') is False:
            await self.ctx.reply([Plain(f'获取落雪成绩失败（HTTP {response.status_code}，接口代码 {data.get("code")}）')])
            return
        try:
            records = data.get('data', [])
            for record in records:
                new_records += self.updateRecord(self.user_id, str(record.get('id')), record.get('score'), record.get('level_index'), record)
            await self.ctx.reply([Plain(f'迁移LX查分器数据成功，更新了{new_records}条记录')])
        except Exception as e:
            await self.ctx.reply([Plain(f'迁移LX查分器数据失败，{e}')])

class ChuniNetRinClient:
    AES_KEY = b'Copyright(C)SEGA'  # 16 bytes

    def __init__(self, access_code: str, raw_key_chip_id: str, host: str = "ea.naominet.live"):
        # keep same behavior: remove dashes
        self.access_code = access_code.replace('-', '')
        self.raw_key_chip_id = raw_key_chip_id
        self.clean_key_chip_id = raw_key_chip_id.replace('-', '')
        self.host = host
        self.server_uri: Optional[str] = None

        if len(self.access_code) != 20:
            raise ValueError("Access Code 长度必须为20位")

    def _deflate_base64(self, payload: bytes) -> str:
        # 使用 zlib.compress 生成带 zlib header 的压缩数据（与 node zlib.deflate 行为非常相近）
        compressed = zlib.compress(payload)
        return base64.b64encode(compressed).decode('ascii')

    def _ensure_initialized(self) -> None:
        if self.server_uri:
            return

        print("正在执行 PowerOn 请求...")
        payload_str = f"game_id=SDHD&ver=2.20&serial={self.raw_key_chip_id}"
        compressed_b64 = self._deflate_base64(payload_str.encode('utf-8'))

        base_url = self.host if "://" in self.host else f"http://{self.host}"
        power_on_url = base_url.rstrip("/") + "/sys/servlet/PowerOn"

        try:
            resp = requests.post(power_on_url, data=compressed_b64, headers={'Content-Type': 'text/plain'}, timeout=10)
            resp.raise_for_status()
            response_data = resp.text
            print(f"PowerOn 响应: {response_data}")
            # 在响应中寻找 uri= 部分
            parts = response_data.split('&')
            uri_part = next((p for p in parts if p.startswith('uri=')), None)
            if not uri_part:
                raise RuntimeError("PowerOn 响应中未找到 'uri'")

            server_uri = uri_part.split('=', 1)[1].strip()
            parsed_uri = urlparse(server_uri)
            if parsed_uri.scheme not in ('http', 'https') or not parsed_uri.hostname:
                raise RuntimeError("PowerOn 响应中的游戏 API 地址无效")
            self.server_uri = server_uri.rstrip('/') + '/'
            print(f"PowerOn 成功, 获取到 API 基地址: {self.server_uri}")
        except requests.Timeout as e:
            raise RuntimeError(f"PowerOn 连接或响应超时：{power_on_url}，请检查地址、端口及网络连接。") from e
        except requests.ConnectionError as e:
            raise RuntimeError(f"无法连接 PowerOn：{power_on_url}，请检查地址、端口及网络连接。") from e
        except RuntimeError:
            raise
        except Exception as e:
            err_msg = getattr(e, 'response', None)
            print("PowerOn 请求失败:", getattr(e, 'args', e))
            raise RuntimeError("PowerOn 请求失败，请检查服务器地址和 KeyChip ID。") from e

    def _aes_encrypt(self, data: bytes) -> bytes:
        if len(data) % 16 != 0:
            # JS 版在调用前已经填充到 48 字节；在此再做保险（不自动填充原始逻辑，但保持对齐）
            padded = data + b'\x00' * (16 - (len(data) % 16))
        else:
            padded = data
        cipher = AES.new(self.AES_KEY, AES.MODE_ECB)
        return cipher.encrypt(padded)

    def _aes_decrypt(self, data: bytes) -> bytes:
        cipher = AES.new(self.AES_KEY, AES.MODE_ECB)
        return cipher.decrypt(data)

    def _generate_tcp_request_bytes(self) -> bytes:
        # keychipHex = Buffer.from(this.cleanKeyChipId, 'ascii').toString('hex').padStart(30, '0');
        keychip_hex = binascii.hexlify(self.clean_key_chip_id.encode('ascii')).decode('ascii').rjust(30, '0')

        access_code_string = self.access_code  # 已去掉 '-'

        # 与 TS 原始拼接保持一致
        request_hex = f"3ea1ab150f003000000153444844000005{keychip_hex}{access_code_string}000000000000"

        request_payload = binascii.unhexlify(request_hex)
        # 创建 48 字节 buffer 并拷贝
        padded_payload = bytearray(48)
        padded_payload[:len(request_payload)] = request_payload

        print(f"生成的请求体原始长度: {len(request_payload)}, 填充后长度: {len(padded_payload)}")
        return self._aes_encrypt(bytes(padded_payload))

    def _send_tcp_data(self, data: bytes, host: str, port: int) -> bytes:
        # 同步 socket 写法，和 JS 的行为一致：connect -> write -> 等待 data -> close
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10.0)
        try:
            s.connect((host, port))
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.sendall(data)
            # 读取响应（一次 read 即可，和 JS 里 on('data') 一样）
            recv = s.recv(8192)
            return recv
        except Exception as e:
            raise
        finally:
            try:
                s.close()
            except Exception:
                pass

    def get_user_id(self) -> int:
        # 主流程：保证初始化 -> 生成 tcp 请求 -> 发往 PowerOn 返回的 server uri 的主机 22345 端口 -> 解密 -> 提取 userId
        self._ensure_initialized()
        request_bytes = self._generate_tcp_request_bytes()

        # server_uri 可能是类似 http://xxx:yyyy/ 的字符串，解析 host
        parsed = urlparse(self.server_uri)  # type: ignore[arg-type]
        tcp_host = parsed.hostname
        tcp_port = 22345

        if not tcp_host:
            raise RuntimeError("无法从 serverUri 解析到主机名")

        response_bytes = self._send_tcp_data(request_bytes, tcp_host, tcp_port)
        decrypted = self._aes_decrypt(response_bytes)

        # 从响应的固定位置提取UserID
        # TS: const userIdHex = decryptedResponse.subarray(32, 45).reverse().toString('hex');
        # Python 等价：
        if len(decrypted) < 45:
            raise RuntimeError("解密后的响应长度不足以提取 UserID")

        user_id_hex = decrypted[32:45][::-1].hex()
        try:
            user_id = int(user_id_hex, 16)
        except ValueError:
            raise RuntimeError("从服务器获取 UserID 失败（hex 解析错误）")

        if user_id <= 0:
            raise RuntimeError("从服务器获取 UserID 失败，可能是卡片未注册或 Access Code 错误。")

        return user_id

    def _api_request(self, api_endpoint: str, payload: dict) -> Any:
        self._ensure_initialized()
        # TS: const apiUrl = `${this.serverUri}ChuniServlet/${apiEndpoint}`;
        api_url = f"{self.server_uri}ChuniServlet/{api_endpoint}"  # type: ignore[arg-type]
        try:
            resp = requests.post(api_url, json=payload, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            status = getattr(e, 'response', None)
            print(f"API 请求 to {api_endpoint} 失败:", getattr(e, 'args', e))
            raise

    def get_user_data(self, user_id: int) -> Any:
        return self._api_request("GetUserDataApi", {"userId": str(user_id)})

    def get_user_music(self, user_id: int) -> Any:
        return self._api_request("GetUserMusicApi", {
            "userId": str(user_id),
            "nextIndex": "0",
            "maxCount": "2147483647"
        })

class ChuniNetShiroClient(ChuniNetRinClient):
    """复用 Rin 的 PowerOn、Aime 查询及成绩 API 请求流程。"""

    def __init__(self, access_code: str, raw_key_chip_id: str, host: str = "aime.shiroaura.top"):
        if not isinstance(raw_key_chip_id, str) or not raw_key_chip_id.strip():
            raise ValueError("未配置 KEYCHIP_SHIRO，请先配置 Shiro 服机台号")
        if not isinstance(access_code, str):
            raise ValueError("Access Code 必须为20位数字，请重新绑定卡号")
        access_code = access_code.strip().replace('-', '')
        if len(access_code) != 20 or not access_code.isascii() or not access_code.isdigit():
            raise ValueError("Access Code 必须为20位数字，请重新绑定卡号")
        # Shiro 可单独指定 ALL.Net 地址（含协议和端口），不影响 Rin。
        base_url = host if "://" in host else f"https://{host}"
        parsed = urlparse(base_url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.query or parsed.fragment:
            raise ValueError("SHIRO_BASE_URL 必须是有效的 HTTP/HTTPS 服务基地址")
        super().__init__(access_code, raw_key_chip_id.strip(), base_url)
        proxy = os.getenv("SHIRO_PROXY")
        if proxy is None:
            proxy = dotenv.dotenv_values(osp.join(osp.dirname(__file__), '..', '.env')).get("SHIRO_PROXY")
        self.proxy = (proxy or "").strip()
        self.proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        if self.proxy:
            try:
                address = urlparse(self.proxy)
                if address.scheme not in ('socks5', 'socks5h') or not address.hostname or not address.port:
                    raise ValueError
            except ValueError:
                raise ValueError("SHIRO_PROXY 必须是含端口的 SOCKS5 地址") from None
            try:
                import socks
            except ImportError:
                raise RuntimeError("请在机器人 Python 环境安装 PySocks 依赖") from None

    def _generate_tcp_request_bytes(self) -> bytes:
        # Aime header: game @ 0x0a, store @ 0x10, keychip @ 0x14, card @ 0x20.
        # 完整机台号包含尾部校验段，Aime 使用前11位短号。
        keychip = self.clean_key_chip_id[:11].encode('ascii')
        if len(keychip) != 11:
            raise ValueError("Shiro Aime 短机台号必须为11位")
        packet = bytearray(48)
        packet[0:2] = (0xa13e).to_bytes(2, 'little')
        packet[2:4] = (0x3087).to_bytes(2, 'little')
        packet[4:6] = (0x0f).to_bytes(2, 'little')
        packet[6:8] = len(packet).to_bytes(2, 'little')
        packet[10:14] = b'SDHD'
        packet[16:20] = getattr(self, 'place_id', 0).to_bytes(4, 'little')
        packet[20:20 + len(keychip)] = keychip
        packet[32:42] = bytes.fromhex(self.access_code)
        return self._aes_encrypt(bytes(packet))

    def get_user_id(self) -> int:
        self._ensure_initialized()
        host = urlparse(self.server_uri).hostname
        response = self._send_tcp_data(self._generate_tcp_request_bytes(), host, 22345)
        if not response or len(response) % 16:
            raise RuntimeError("Shiro Aime 返回了不完整的加密响应")
        data = self._aes_decrypt(response)
        if data[:2] != b'\x3e\xa1' or int.from_bytes(data[4:6], 'little') != 0x10:
            raise RuntimeError("Shiro Aime 拒绝了卡号查询，请检查机台号授权")
        if len(data) < 36:
            raise RuntimeError("Shiro Aime 响应缺少用户 ID")
        user_id = int.from_bytes(data[32:36], 'little')
        if user_id in (0, 0xffffffff):
            raise RuntimeError("Shiro 未找到该卡号，请确认卡号正确且已在 Shiro 注册")
        return user_id

    def _api_request(self, api_endpoint: str, payload: dict) -> Any:
        self._ensure_initialized()
        try:
            # Shiro 游戏 API 要求 zlib 压缩 JSON；普通 JSON 只返回 stat=0。
            body = zlib.compress(json.dumps(payload).encode('utf-8'))
            with requests.post(f"{self.server_uri}ChuniServlet/{api_endpoint}",
                               data=body, timeout=10, proxies=self.proxies,
                               headers={"User-Agent": "SDHD", "Content-Type": "application/json"}) as resp:
                resp.raise_for_status()
                try:
                    result = resp.json()
                except ValueError:
                    result = json.loads(zlib.decompress(resp.content))
            if not isinstance(result, dict) or result.get('stat') == 0:
                raise RuntimeError(f"Shiro 成绩 API 返回失败状态（{api_endpoint}）")
            if api_endpoint == 'GetUserMusicApi' and not isinstance(result.get('userMusicList'), list):
                raise RuntimeError("Shiro 成绩响应缺少 userMusicList，未导入任何记录")
            return result
        except requests.RequestException as e:
            raise RuntimeError(f"Shiro 成绩 API 请求失败（{api_endpoint}），请检查代理和服务连接") from e
        except (ValueError, zlib.error) as e:
            raise RuntimeError(f"Shiro 成绩 API 响应解码失败（{api_endpoint}）") from e

    def _send_tcp_data(self, data: bytes, host: str, port: int) -> bytes:
        if not self.proxy:
            return super()._send_tcp_data(data, host, port)
        import socks
        proxy = urlparse(self.proxy)
        try:
            with socks.create_connection(
                (host, port), timeout=10, proxy_type=socks.SOCKS5,
                proxy_addr=proxy.hostname, proxy_port=proxy.port,
                proxy_rdns=proxy.scheme == 'socks5h',
                proxy_username=unquote(proxy.username) if proxy.username else None,
                proxy_password=unquote(proxy.password) if proxy.password else None,
            ) as conn:
                conn.sendall(data)
                response = bytearray()
                expected = 16
                while len(response) < expected:
                    chunk = conn.recv(expected - len(response))
                    if not chunk:
                        raise RuntimeError("Shiro Aime 响应提前结束")
                    response.extend(chunk)
                    if len(response) == 16:
                        header = self._aes_decrypt(bytes(response))
                        size = int.from_bytes(header[6:8], 'little')
                        if size < 16 or size > 8192:
                            raise RuntimeError("Shiro Aime 响应长度无效")
                        expected = (size + 15) // 16 * 16
                return bytes(response)
        except OSError as e:
            raise RuntimeError("Shiro Aime TCP 查询失败，请检查代理是否能连接服务器 22345 端口") from e


    def _ensure_initialized(self) -> None:
        if self.server_uri:
            return
        power_on_url = self.host.rstrip('/') + '/sys/servlet/PowerOn'
        payload = urlencode({
            "game_id": "SDHD", "ver": "2.20", "serial": self.raw_key_chip_id,
            "ip": "127.0.0.1", "firm_ver": "60001", "boot_ver": "0000",
            "encode": "UTF-8", "format_ver": "3", "hops": "1", "token": "0",
        }) + "\r\n"
        try:
            # Shiro 的 DFI 响应是 base64(zlib)，但声明 Content-Encoding: deflate。
            # 必须读取原始字节，避免 requests 按 HTTP 头自动解压失败。
            with requests.post(
                power_on_url, data=self._deflate_base64(payload.encode('utf-8')),
                headers={"Content-Type": "application/x-www-form-urlencoded",
                         "User-Agent": "ALL.Net", "Pragma": "DFI"},
                timeout=10, stream=True, proxies=self.proxies,
            ) as resp:
                resp.raise_for_status()
                raw = resp.raw.read(65537, decode_content=False)
                if len(raw) > 65536:
                    raise RuntimeError("Shiro PowerOn 响应过大")
                if resp.headers.get('Pragma', '').upper() == 'DFI':
                    raw = zlib.decompress(base64.b64decode(raw.strip(), validate=True))
                elif resp.headers.get('Content-Encoding', '').lower() == 'deflate':
                    raw = zlib.decompress(raw)
                fields = parse_qs(raw.decode('utf-8').strip())
            if fields.get('stat') != ['1']:
                raise RuntimeError("Shiro PowerOn 握手失败，请检查机台号授权及游戏版本")
            uri = fields.get('uri', [''])[0].strip()
            parsed = urlparse(uri)
            if parsed.scheme not in ('http', 'https') or not parsed.hostname:
                raise RuntimeError("Shiro PowerOn 未返回有效的游戏 API 地址")
            self.place_id = int(fields.get('place_id', ['0'])[0])
            self.server_uri = uri.rstrip('/') + '/'
        except requests.Timeout as e:
            raise RuntimeError(f"Shiro PowerOn 连接或响应超时：{power_on_url}") from e
        except requests.RequestException as e:
            raise RuntimeError(f"Shiro PowerOn 网络请求失败：{power_on_url}") from e
        except (ValueError, zlib.error) as e:
            raise RuntimeError("Shiro PowerOn 响应解码失败") from e


# ========= Rin服 =========
class RinHandler:
    def __init__(self, ctx: EventContext):
        self.ctx = ctx
        self.user_id = str(ctx.event.sender_id)
        self.keychip = os.getenv("KEYCHIP_RIN")

    async def readUsersJson(self):
        users = {}
        with open(RIN_JSON_PATH, 'r') as f:
            users = json.load(f).get('users', {})
        return users

    async def writeUsersJson(self, users: dict):
        try:
            with open(RIN_JSON_PATH , 'w') as f:
                json.dump({'users': users}, f, indent=4)
            return 0
        except Exception as e:
            await self.ctx.reply([Plain(f'写入用户信息失败：{e}')])
            return -1

    def checkIsBind(self, users: dict):
        return self.user_id in users.keys()

    def getSongs(self) -> list:
        response = requests.get(self.song_url)
        data = response.json()
        songs = data.get('songs', [])
        return songs

    def updateRecord(self, user_id: str, cid: str, score: int, difficulty: int, record=None):
        fc, aj = record_flags(record or {}, "rin")
        return save_record(
            DB_PATH, user_id, cid, score, difficulty, "rin", only_if_higher=True,
            is_full_combo=fc, is_all_justice=aj,
        )

    def get_rin_user_music(self, access_code: str):
        KeyChipId = os.getenv("KEYCHIP_RIN")
        Host = "ea.naominet.live"

        client = ChuniNetRinClient(access_code, KeyChipId, Host)
        try:
            user_id = client.get_user_id()
            user_music = client.get_user_music(user_id)

            print("玩家音乐列表获取成功! 歌曲数量:", len(user_music.get('userMusicList', [])))
            return {
                "status": 200,
                "message": "Player music list obtained successfully!",
                "data": user_music
            }
        except Exception as e:
            print("在获取用户音乐列表时发生错误:", e)
            return {
                "status": 500,
                "message": "An error occurred while obtaining player music list.",
                "data": None
            }

    async def copyRinRecord(self):
        users = await self.readUsersJson()
        if not self.checkIsBind(users):
            img = await Image.from_local(HELP_API_IMG_PATH)
            await self.ctx.reply([
                Plain('你还没有绑定账号，请先使用“chubind [服务器] [TOKEN]”绑定账号\n· rin: TOKEN为20位卡号\n· shiro: TOKEN为20位卡号\n· lx: 落雪查分器TOKEN获取地址：https://maimai.lxns.net/user/profile?tab=thirdparty'),
                img
            ])
            return
        new_records = 0
        # 请求记录
        data = self.get_rin_user_music(users.get(self.user_id))
        match data.get('status'):
            case 200:
                try:
                    records = data.get('data', {}).get('userMusicList', [])
                    for record in records:
                        for musicdata in record.get('userMusicDetailList', []):
                            new_records += self.updateRecord(self.user_id, str(musicdata.get('musicId')), musicdata.get('scoreMax'), musicdata.get('level'), musicdata)
                    await self.ctx.reply([Plain(f'迁移Rin服数据成功，更新了{new_records}条记录')])
                    return
                except Exception as e:
                    await self.ctx.reply([Plain(f'迁移Rin服数据失败，{e}')])
                    return
            case 500:
                await self.ctx.reply([Plain(f'获取Rin服数据失败，{data.get("message")}')])
                return
            case _:
                await self.ctx.reply([Plain(f'获取失败，请检查TOKEN是否正确')])
                return

# ========= Shiro服 =========
class ShiroHandler:
    def __init__(self, ctx: EventContext):
        self.ctx = ctx
        self.user_id = str(ctx.event.sender_id)
        self.keychip = os.getenv("KEYCHIP_SHIRO")

    async def readUsersJson(self):
        users = {}
        with open(SHIRO_JSON_PATH, 'r') as f:
            users = json.load(f).get('users', {})
        return users

    async def writeUsersJson(self, users: dict):
        try:
            with open(SHIRO_JSON_PATH, 'w') as f:
                json.dump({'users': users}, f, indent=4)
            return 0
        except Exception as e:
            await self.ctx.reply([Plain(f'写入用户信息失败：{e}')])
            return -1

    def checkIsBind(self, users: dict):
        return self.user_id in users.keys()

    def updateRecord(self, user_id: str, cid: str, score: int, difficulty: int, record=None):
        fc, aj = record_flags(record or {}, "shiro")
        return save_record(
            DB_PATH, user_id, cid, score, difficulty, "shiro", only_if_higher=True,
            is_full_combo=fc, is_all_justice=aj,
        )

    def get_shiro_user_music(self, access_code: str):
        KeyChipId = os.getenv("KEYCHIP_SHIRO")
        Host = os.getenv("SHIRO_BASE_URL", "https://aime.shiroaura.top").strip()

        try:
            client = ChuniNetShiroClient(access_code, KeyChipId, Host)
            user_id = client.get_user_id()
            user_music = client.get_user_music(user_id)

            print("玩家音乐列表获取成功! 歌曲数量:", len(user_music.get('userMusicList', [])))
            return {
                "status": 200,
                "message": "Player music list obtained successfully!",
                "data": user_music
            }
        except (ValueError, RuntimeError) as e:
            return {"status": 500, "message": str(e), "data": None}
        except Exception as e:
            print("在获取用户音乐列表时发生错误:", e)
            return {
                "status": 500,
                "message": "请求失败，请检查 Shiro 服务连接、机台号及卡片注册状态；详细原因见机器人日志。",
                "data": None
            }

    async def copyShiroRecord(self):
        users = await self.readUsersJson()
        if not self.checkIsBind(users):
            img = await Image.from_local(HELP_API_IMG_PATH)
            await self.ctx.reply([
                Plain('你还没有绑定账号，请先使用“chubind [服务器] [TOKEN]”绑定账号\n· rin: TOKEN为20位卡号\n· shiro: TOKEN为20位卡号\n· lx: 落雪查分器TOKEN获取地址：https://maimai.lxns.net/user/profile?tab=thirdparty'),
                img
            ])
            return
        new_records = 0
        data = self.get_shiro_user_music(users.get(self.user_id))
        # DEBUG shiro
        with open(osp.join(osp.dirname(__file__), "..", "data", "shiro_music_record.json"), "w", encoding='utf-8') as f:
            json.dump(data, f)
        match data.get('status'):
            case 200:
                try:
                    records = data.get('data', {}).get('userMusicList', [])
                    for record in records:
                        for musicdata in record.get('userMusicDetailList', []):
                            difficulty = int(musicdata.get('level'))
                            if difficulty not in range(5):
                                continue
                            new_records += self.updateRecord(
                                self.user_id,
                                str(musicdata.get('musicId')),
                                musicdata.get('scoreMax'),
                                difficulty,
                                musicdata,
                            )
                    await self.ctx.reply([Plain(f'迁移Shiro服数据成功，更新了{new_records}条记录')])
                except Exception as e:
                    await self.ctx.reply([Plain(f'迁移Shiro服数据失败，{e}')])
            case 500:
                await self.ctx.reply([Plain(f'获取Shiro服数据失败，{data.get("message")}')])
            case _:
                await self.ctx.reply([Plain(f'获取失败，请检查TOKEN是否正确')])

async def queryCopy(ctx: EventContext, args: list, **kwargs) -> None:
    '''查询最佳

    Args:
        ctx (EventContext): 事件上下文
        args (list): 参数列表
    Returns:
        None: 无返回值
    '''
    server = args[0] if args else None
    if not server:
        await ctx.reply([Plain("请在命令后添加服务器名称：目前支持服务器：lx（落雪查分器）、rin（Rin服）、shiro（Shiro服），例如：chucopy lx")])
        return
    match server:
        case 'lx':
            lx = LXHandler(ctx)
            await lx.copyLXRecord()
        case 'rin':
            rin = RinHandler(ctx)
            await rin.copyRinRecord()
        case 'shiro':
            shiro = ShiroHandler(ctx)
            await shiro.copyShiroRecord()
        case _:
            await ctx.reply(MessageChain([Plain(f"未知服务器{server}")]))
            return
