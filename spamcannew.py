# language: Python, file: spam.py, target: Linux (GitHub Actions), Python 3.10+
# pip install curl_cffi aiofiles pystyle
import asyncio
import random
import json
import base64
from datetime import datetime
import os
import time
import sys

try:
    import aiofiles
    from curl_cffi.requests import AsyncSession
    from pystyle import Colorate, Colors
except ImportError:
    sys.exit(1)

SECRET_KEY = "k3y_b4o_m4t_cu4_ban_2024"

def xor_decrypt(data: str, key: str) -> str:
    return "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data))

def read_encrypted_file(filepath):
    enc_path = filepath + ".enc"
    if not os.path.exists(enc_path):
        return []
    try:
        with open(enc_path, "r", encoding="utf-8") as f:
            b64_data = f.read().strip()
        raw_data = base64.b64decode(b64_data).decode("utf-8")
        decrypted = xor_decrypt(raw_data, SECRET_KEY)
        return decrypted.splitlines()
    except Exception:
        return []

def get_headers(token):
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    props_json = json.dumps({
        "os": "Windows",
        "browser": "Chrome",
        "browser_user_agent": ua,
        "browser_version": "126.0.0.0",
        "client_build_number": 316286,
        "client_event_source": None
    }, separators=(',', ':'))
    super_props = base64.b64encode(props_json.encode()).decode()
    return {
        "Authorization": token,
        "Content-Type": "application/json",
        "X-Super-Properties": super_props,
        "User-Agent": ua,
        "Origin": "https://discord.com",
        "Accept": "*/*"
    }

async def die_token(dead_token):
    try:
        async with aiofiles.open("die.txt", "a") as f:
            await f.write(dead_token + "\n")
    except:
        pass

class SharedBag:
    def __init__(self, contents):
        self.original_contents = contents
        self.bag = []
        self.lock = asyncio.Lock()

    async def get_random_line(self):
        async with self.lock:
            if not self.bag:
                self.bag = self.original_contents.copy()
                random.shuffle(self.bag)
            return self.bag.pop()

class TurboClient:
    def __init__(self, token, contents, mode_type, shared_bag, proxies, delay, tags_string, channels):
        self.token = token
        self.channels = channels
        self.mode_type = mode_type
        if self.mode_type == '1':
            self.treo_text = "\n".join(contents)
        self.shared_bag = shared_bag
        self.proxies = proxies
        self.headers = get_headers(token)
        self.delay = delay
        self.tags_string = tags_string
        self.is_alive = True
        self.direct_cooldown_until = 0.0
        self.proxy_cooldowns = {}
        self.msg_count = 0
        self.session = None

    def choose_route(self):
        now = time.time()
        if now < self.direct_cooldown_until:
            available_proxies = [p for p in self.proxies if self.proxy_cooldowns.get(p, 0) <= now]
            if not available_proxies:
                return None, None
            return random.choice(available_proxies), "proxy"
        if self.proxies:
            if random.random() < 0.8:
                available_proxies = [p for p in self.proxies if self.proxy_cooldowns.get(p, 0) <= now]
                if available_proxies:
                    return random.choice(available_proxies), "proxy"
        return None, "direct"

    async def send_one(self, channel_id):
        if not self.is_alive:
            return None

        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"

        if self.mode_type == '1':
            base_content = self.treo_text
        else:
            base_content = await self.shared_bag.get_random_line()

        if self.tags_string:
            if self.mode_type == '1':
                final_content = f"{base_content}\n\n{self.tags_string}"
            else:
                final_content = f"{base_content} {self.tags_string}"
        else:
            final_content = base_content

        payload = {"content": final_content, "tts": False}

        asyncio.create_task(self._typing(channel_id))

        for _ in range(3):
            proxy, route = self.choose_route()
            if route is None:
                await asyncio.sleep(0.5)
                continue
            try:
                resp = await self.session.post(url, headers=self.headers, json=payload, proxy=proxy, timeout=10)
                p_log = proxy.split('@')[-1] if proxy else "TRỰC TIẾP"
                ts = datetime.now().strftime('%H:%M:%S')

                if resp.status_code in (200, 201):
                    self.msg_count += 1
                    print(Colorate.Horizontal(
                        Colors.green_to_white,
                        f"[{ts}] ✔️ GỬI OK | {self.token[:12]}... | {p_log} | Cid: {str(channel_id)[-4:]}"
                    ))
                    return max(0.01, self.delay + random.uniform(-0.05, 0.05))

                if resp.status_code == 400:
                    return self.delay

                if resp.status_code == 401:
                    print(Colorate.Horizontal(Colors.red_to_white, f"[{ts}] 💀 DIE | {self.token[:12]}..."))
                    self.is_alive = False
                    await die_token(self.token)
                    return None

                if resp.status_code == 429:
                    try:
                        retry = float(resp.json().get('retry_after', 3.0))
                    except:
                        retry = 3.0
                    if proxy:
                        self.proxy_cooldowns[proxy] = time.time() + retry
                    else:
                        self.direct_cooldown_until = time.time() + retry
                    return retry

                if resp.status_code == 403:
                    print(f"[{ts}] 🔐 403 | {self.token[:12]}...")
                    return 30.0

                if resp.status_code == 404:
                    return 2.0

            except Exception:
                if proxy:
                    self.proxy_cooldowns[proxy] = time.time() + 5.0
                else:
                    self.direct_cooldown_until = time.time() + 5.0
                await asyncio.sleep(0.5)
        return 2.0

    async def _typing(self, channel_id):
        url = f"https://discord.com/api/v10/channels/{channel_id}/typing"
        proxy, _ = self.choose_route()
        try:
            await self.session.post(url, headers=self.headers, proxy=proxy, timeout=3)
        except:
            pass

    async def run_loop(self, loop_count):
        round_idx = 0
        while self.is_alive:
            if loop_count > 0 and round_idx >= loop_count:
                break
            cid = random.choice(self.channels)
            wait = await self.send_one(cid)
            if wait is None:
                break
            if wait > 0:
                await asyncio.sleep(wait)
            round_idx += 1


async def main():
    # 1. Đọc config từ file .enc
    config_lines = read_encrypted_file("config.json")
    if not config_lines:
        print("❌ Thiếu file config.json.enc")
        return
    try:
        config = json.loads("\n".join(config_lines))
    except Exception as e:
        print(f"❌ Lỗi parse JSON config: {e}")
        return

    choice = str(config.get("mode", "1"))
    if choice == '1':
        file_ngon = "ngon.txt"
    elif choice == '2':
        file_ngon = "ngonnhay.txt"
    elif choice == '3':
        file_ngon = "ngongo.txt"
    else:
        print("❌ Config mode không hợp lệ (1/2/3)")
        return

    channel_ids = config.get("channel_ids", [])
    if not channel_ids:
        print("❌ Config thiếu channel_ids")
        return

    delay_value = float(config.get("delay", 0.2))
    loop_count = int(config.get("loop_count", 0))
    tag_ids = config.get("tag_ids", [])
    
    tags_string = " ".join([f"<@{uid}>" for uid in tag_ids]) if tag_ids else ""

    print(Colorate.Horizontal(Colors.cyan_to_blue, f"🚀 HEADLESS | MODE: {choice} | LOOP: {'∞' if loop_count == 0 else loop_count}"))

    # 2. Đọc contents
    contents = read_encrypted_file(file_ngon)
    if not contents:
        print(f"❌ File {file_ngon}.enc đang trống!")
        return

    # 3. Đọc tokens
    tokens = read_encrypted_file("token.txt")
    if not tokens:
        print("❌ token.txt.enc trống!")
        return

    # 4. Đọc proxies
    proxies = []
    prx_lines = read_encrypted_file("prx.txt")
    for line in prx_lines:
        line = line.strip()
        if not line:
            continue
        p = line.split(':')
        if len(p) == 4:
            proxies.append(f"http://{p[2]}:{p[3]}@{p[0]}:{p[1]}")
        elif len(p) == 2:
            proxies.append(f"http://{p[0]}:{p[1]}")

    shared_bag = SharedBag(contents) if choice in ('2', '3') else None

    clients = []
    sessions = []
    for t in tokens:
        c = TurboClient(t, contents, choice, shared_bag, proxies, delay_value, tags_string, channel_ids)
        s = AsyncSession(impersonate="chrome120")
        c.session = s
        clients.append(c)
        sessions.append(s)

    try:
        tasks = [asyncio.create_task(c.run_loop(loop_count)) for c in clients]
        await asyncio.gather(*tasks)
    finally:
        for s in sessions:
            try:
                await s.close()
            except:
                pass


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
            break
        except Exception:
            time.sleep(5)
            continue
