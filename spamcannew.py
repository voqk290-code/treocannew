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
    print("Vui lòng cài đặt thư viện bằng lệnh: pip install curl_cffi aiofiles pystyle")
    sys.exit(1)

RAINBOW_7 = [196, 208, 226, 46, 51, 21, 129]
RESET = "\033[0m"


def init_files():
    files = ['ngon.txt', 'ngonnhay.txt', 'ngongo.txt', 'token.txt', 'prx.txt']
    for file in files:
        if not os.path.exists(file):
            with open(file, 'w', encoding='utf-8'):
                pass


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
    init_files()

    # 1. Đọc config
    if not os.path.exists("config.json"):
        print("❌ Thiếu file config.json")
        return
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

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

    print(Colorate.Horizontal(Colors.cyan_to_blue, f"🚀 HEADLESS MODE | CHỨC NĂNG: {choice} | LOOP: {'∞' if loop_count == 0 else loop_count}"))

    # 2. Đọc contents
    with open(file_ngon, "r", encoding="utf-8") as f:
        contents = [line.strip() for line in f if line.strip()]

    if not contents:
        print(f"❌ File {file_ngon} đang trống!")
        return

    # 3. Đọc tokens
    with open("token.txt", "r") as f:
        tokens = [l.strip() for l in f if l.strip()]

    if not tokens:
        print("❌ token.txt trống!")
        return

    # 4. Đọc proxies
    proxies = []
    if os.path.exists("prx.txt"):
        with open("prx.txt", "r") as f:
            for line in f:
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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nĐã dừng Tool thủ công!")
