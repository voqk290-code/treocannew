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
    from pystyle import Colorate, Colors, Center, System
except ImportError:
    print("Vui lòng cài đặt thư viện bằng lệnh: pip install curl_cffi aiofiles pystyle")
    exit()

MAX_CONCURRENT_REQUESTS = 10
RAINBOW_7 = [196, 208, 226, 46, 51, 21, 129]
RESET = "\033[0m"

SKIP_WORDS = ("next", "skip", "boqua")


def clear_screen():
    System.Clear()


def _rgb_ansi(idx):
    return f"\033[38;5;{idx}m"


def rainbow_line(text, offset):
    out = []
    for i, ch in enumerate(text):
        color = RAINBOW_7[(i + offset) % len(RAINBOW_7)]
        out.append(f"{_rgb_ansi(color)}{ch}")
    out.append(RESET)
    return "".join(out)


def display_info_banner():
    banner = r"""
 ██╗  ██╗██╗    ██╗███╗   ██╗ ██████╗
 ██║ ██╔╝██║    ██║████╗  ██║██╔════╝
 █████╔╝ ██║ █╗ ██║██╔██╗ ██║██║  ███╗
 ██╔═██╗ ██║███╗██║██║╚██╗██║██║   ██║
 ██║  ██╗╚███╔███╔╝██║ ╚████║╚██████╔╝
 ╚═╝  ╚═╝ ╚══╝╚══╝ ╚═╝  ╚═══╝ ╚═════╝
    """
    box_content = """
    TOOL SPAM DISCORD - BẢN TỐI ƯU HÓA PRO
    [+] Coder: KWNG
    [+] Chức năng: Treo Trụ, Nhây, Gõ
    """

    title_lines = banner.strip("\n").split("\n")
    box_lines = box_content.strip("\n").split("\n")

    print()
    for line in title_lines:
        print(rainbow_line(line.center(60), 0))
    print()
    for line in box_lines:
        print(rainbow_line(line.center(60), 0))
    print()


def is_skip(text):
    return text.strip().lower() in SKIP_WORDS


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


def apply_format(content, fmt, tags_string):
    outside_tags = ""
    if not fmt or fmt == '1':
        body = content
    elif fmt == '2':
        body = f"# {content}"
    elif fmt == '3':
        body = f"```{content}```"
        outside_tags = tags_string
        tags_string = ""
    elif fmt == '4':
        body = f"# ```{content}```"
        outside_tags = tags_string
        tags_string = ""
    elif fmt == '5':
        body = f"# > {content}"
    else:
        body = content

    if outside_tags:
        return f"{outside_tags}\n{body}"
    if tags_string:
        return f"{body} {tags_string}"
    return body


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


class TokenSlot:
    def __init__(self, token, channels, contents, mode_type, shared_bag, proxies, delay, tags_string, fmt, gif_link):
        self.token = token
        self.channels = channels
        self.mode_type = mode_type
        self.fmt = fmt
        self.gif_link = gif_link

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

    def choose_route(self):
        now = time.time()
        available_direct = now >= self.direct_cooldown_until
        available_proxies = [p for p in self.proxies if self.proxy_cooldowns.get(p, 0) <= now]
        if not available_direct and not available_proxies:
            return None, None
        if available_direct and available_proxies:
            if random.random() < 0.8:
                return random.choice(available_proxies), "proxy"
            return None, "direct"
        if available_proxies:
            return random.choice(available_proxies), "proxy"
        return None, "direct"

    async def fire_typing(self, session, channel_id):
        url = f"https://discord.com/api/v10/channels/{channel_id}/typing"
        proxy, _ = self.choose_route()
        try:
            await session.post(url, headers=self.headers, proxy=proxy, timeout=3)
        except:
            pass

    def build_content(self):
        if self.mode_type == '1':
            base_content = self.treo_text
            if self.tags_string:
                final_content = f"{base_content}\n\n{self.tags_string}"
            else:
                final_content = base_content
            if self.gif_link:
                final_content = f"{self.gif_link}\n{final_content}"
            return final_content
        return None

    async def fast_post(self, session, channel_id):
        if not self.is_alive:
            return None

        asyncio.create_task(self.fire_typing(session, channel_id))
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"

        if self.mode_type == '1':
            final_content = self.build_content()
        else:
            base_content = await self.shared_bag.get_random_line()
            final_content = apply_format(base_content, self.fmt, self.tags_string)

        payload = {"content": final_content, "tts": False}

        proxy, route = self.choose_route()
        if route is None:
            return 0.2

        try:
            resp = await session.post(
                url,
                headers=self.headers,
                json=payload,
                proxy=proxy,
                timeout=10
            )
            p_log = proxy.split('@')[-1] if proxy else "TRỰC TIẾP"

            if resp.status_code in [200, 201]:
                msg = f"[{datetime.now().strftime('%H:%M:%S')}] ✔️ GỬI THÀNH CÔNG | Token: {self.token[:15]}... | Tuyến: {p_log}"
                print(Colorate.Horizontal(Colors.green_to_white, msg))
                return self.delay

            elif resp.status_code == 400:
                print(Colorate.Horizontal(Colors.red_to_white, f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ LỖI 400 | Trụ quá dài (vượt 2000 kí tự), hãy giảm bớt dòng!"))
                return self.delay

            elif resp.status_code == 401:
                print(Colorate.Horizontal(Colors.red_to_white, f"[{datetime.now().strftime('%H:%M:%S')}] 💀 DIE TOKEN | {self.token[:15]}..."))
                self.is_alive = False
                await die_token(self.token)
                return None

            elif resp.status_code == 429:
                try:
                    retry = float(resp.json().get('retry_after', 3.0))
                except:
                    retry = 3.0
                if proxy:
                    self.proxy_cooldowns[proxy] = time.time() + retry
                else:
                    self.direct_cooldown_until = time.time() + retry
                return self.delay

            elif resp.status_code == 403:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔐 BỊ CHẶN (403) | {self.token[:15]}... | {p_log}")
                return self.delay

            elif resp.status_code == 404:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧨 LỖI ID CHAT (404) KHÔNG TÌM THẤY KÊNH")
                return self.delay
        except Exception:
            if proxy:
                self.proxy_cooldowns[proxy] = time.time() + 2.0
            else:
                self.direct_cooldown_until = time.time() + 2.0
            return self.delay

        return self.delay


async def dispatch_loop(slots, channels, delay, semaphore):
    async with AsyncSession(impersonate="chrome120") as session:
        while True:
            alive = [s for s in slots if s.is_alive]
            if not alive:
                break
            slot = random.choice(alive)
            cid = random.choice(channels)
            async with semaphore:
                wait = await slot.fast_post(session, cid)
            if wait is None:
                continue
            await asyncio.sleep(max(0.01, wait))


def read_lines_from_file(path):
    if not path:
        return []
    if not os.path.exists(path):
        print(Colorate.Horizontal(Colors.red_to_white, f"❌ Không tìm thấy file: {path}"))
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def ask_path(prompt, default_name):
    print(Colorate.Horizontal(Colors.cyan_to_blue, f"(Để trống dùng mặc định: {default_name})"))
    print(Colorate.Horizontal(Colors.cyan_to_blue, "(Host không gửi được dòng trống — gõ 'next' để dùng mặc định)"))
    raw = input(Colorate.Horizontal(Colors.green_to_yellow, f"👉 {prompt}: ")).strip().strip('"').strip("'")
    if not raw or is_skip(raw):
        return default_name
    return raw


def input_tokens():
    print(Colorate.Horizontal(Colors.cyan_to_blue, "\n===== NGUỒN TOKEN ====="))
    print(Colorate.Horizontal(Colors.yellow_to_red, "1. Đọc từ file token"))
    print(Colorate.Horizontal(Colors.yellow_to_red, "2. Nhập thủ công (gõ 'done' để chốt)"))
    print(Colorate.Horizontal(Colors.yellow_to_red, "3. Cả hai (file + thủ công)\n"))

    while True:
        opt = input(Colorate.Horizontal(Colors.green_to_yellow, "👉 Chọn nguồn token (1/2/3): ")).strip()
        if opt in ('1', '2', '3'):
            break
        print("⚠️ Chọn 1, 2 hoặc 3.")

    file_tokens = []
    if opt in ('1', '3'):
        token_path = ask_path("Đường dẫn file token", "token.txt")
        file_tokens = read_lines_from_file(token_path)
        if file_tokens:
            print(Colorate.Horizontal(Colors.cyan_to_blue, f"➡️ Đọc {len(file_tokens)} token từ {token_path}."))

    manual_tokens = []
    if opt in ('2', '3'):
        print(Colorate.Horizontal(Colors.yellow_to_red, "Nhập token thủ công, mỗi dòng 1 token. Gõ 'done' để chốt."))
        while True:
            line = input(Colorate.Horizontal(Colors.green_to_yellow, f"Token #{len(manual_tokens)+1} (hoặc 'done'): ")).strip()
            if line.lower() == 'done':
                break
            if line:
                manual_tokens.append(line)

    if opt == '1':
        return file_tokens
    if opt == '2':
        return manual_tokens
    tokens = file_tokens + manual_tokens
    print(Colorate.Horizontal(Colors.cyan_to_blue, f"➡️ Tổng {len(tokens)} token (file: {len(file_tokens)}, tay: {len(manual_tokens)})."))
    return tokens


def input_treo_manual():
    print(Colorate.Horizontal(Colors.cyan_to_blue, "\n===== NHẬP NỘI DUNG TREO ====="))
    print(Colorate.Horizontal(Colors.yellow_to_red, "Nhập từng dòng nội dung. Gõ 'done' để chốt."))
    lines = []
    while True:
        line = input(Colorate.Horizontal(Colors.green_to_yellow, f"Dòng #{len(lines)+1} (hoặc 'done'): "))
        if line.strip().lower() == 'done':
            break
        if line.strip():
            lines.append(line.strip())
    return lines


def input_format_menu():
    menu = """
    ===== CHỌN FORMAT =====
    [ 1 ] Thường
    [ 2 ] Bự: # nội dung
    [ 3 ] Codeblock: ``` nội dung ```
    [ 4 ] Bự + CBL: # ``` nội dung ```
    [ 5 ] Ghi chú: # > nội dung
    """
    print(Colorate.Horizontal(Colors.cyan_to_blue, menu))
    while True:
        fmt = input(Colorate.Horizontal(Colors.yellow_to_red, "👉 Chọn format (1-5): ")).strip()
        if fmt in ('1', '2', '3', '4', '5'):
            return fmt
        print("⚠️ Chọn 1-5.")


def input_tag_scope():
    print(Colorate.Horizontal(Colors.cyan_to_blue, "\n===== TAG ====="))
    print(Colorate.Horizontal(Colors.yellow_to_red, "1. Không tag"))
    print(Colorate.Horizontal(Colors.yellow_to_red, "2. Tag user"))
    print(Colorate.Horizontal(Colors.yellow_to_red, "3. Tag @everyone"))
    while True:
        opt = input(Colorate.Horizontal(Colors.green_to_yellow, "👉 Chọn (1/2/3): ")).strip()
        if opt == '1':
            return ""
        if opt == '2':
            ids_raw = input(Colorate.Horizontal(Colors.yellow_to_red, "👉 Nhập ID user (cách nhau dấu phẩy, 'next' để bỏ qua): ")).strip()
            if is_skip(ids_raw) or not ids_raw:
                return ""
            tag_list = [f"<@{uid.strip()}>" for uid in ids_raw.split(",") if uid.strip()]
            if tag_list:
                print(Colorate.Horizontal(Colors.green_to_yellow, f"✔️ Đã nạp {len(tag_list)} ID tag."))
            return " ".join(tag_list)
        if opt == '3':
            return "@everyone"
        print("⚠️ Chọn 1, 2 hoặc 3.")


def load_proxies():
    print(Colorate.Horizontal(Colors.cyan_to_blue, "\n===== PROXY ====="))
    print(Colorate.Horizontal(Colors.cyan_to_blue, "(Gõ 'next' để bỏ qua, không dùng proxy)"))
    path = ask_path("Đường dẫn file proxy", "prx.txt")
    if not path or not os.path.exists(path):
        return []
    proxies = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            p = line.split(':')
            if len(p) == 4:
                proxies.append(f"http://{p[2]}:{p[3]}@{p[0]}:{p[1]}")
            elif len(p) == 2:
                proxies.append(f"http://{p[0]}:{p[1]}")
    if proxies:
        print(Colorate.Horizontal(Colors.cyan_to_blue, f"➡️ Đã nạp {len(proxies)} proxy."))
    return proxies


async def main():
    clear_screen()
    display_info_banner()

    try:
        menu = """
    [ 1 ] TREO TRỤ THÁNG NĂM
    [ 2 ] NHÂY TREO THÁNG NĂM
    [ 3 ] TREO GÕ NĂM THÁNG
        """
        print(Colorate.Horizontal(Colors.cyan_to_blue, menu))

        choice = input(Colorate.Horizontal(Colors.yellow_to_red, "👉 Nhập lựa chọn của bạn (1/2/3): ")).strip()

        contents = []
        gif_link = ""

        if choice == '1':
            print(Colorate.Horizontal(Colors.green_to_yellow, "\n=> Đã chọn TREO (Gộp nội dung thành Trụ dài)"))
            print(Colorate.Horizontal(Colors.cyan_to_blue, "Nguồn nội dung:"))
            print(Colorate.Horizontal(Colors.yellow_to_red, "1. Đọc từ file"))
            print(Colorate.Horizontal(Colors.yellow_to_red, "2. Nhập tay"))
            while True:
                src = input(Colorate.Horizontal(Colors.green_to_yellow, "👉 Chọn (1/2): ")).strip()
                if src in ('1', '2'):
                    break
            if src == '1':
                path = ask_path("Đường dẫn file nội dung treo", "ngon.txt")
                contents = read_lines_from_file(path)
            else:
                contents = input_treo_manual()

            print()
            print(Colorate.Horizontal(Colors.cyan_to_blue, "Có kèm link GIF không?"))
            print(Colorate.Horizontal(Colors.yellow_to_red, "1. Không"))
            print(Colorate.Horizontal(Colors.yellow_to_red, "2. Có (nhập link)"))
            while True:
                gif_opt = input(Colorate.Horizontal(Colors.green_to_yellow, "👉 Chọn (1/2): ")).strip()
                if gif_opt == '1':
                    gif_link = ""
                    break
                if gif_opt == '2':
                    gif_raw = input(Colorate.Horizontal(Colors.yellow_to_red, "👉 Nhập link GIF ('next' để bỏ qua): ")).strip()
                    gif_link = "" if is_skip(gif_raw) else gif_raw
                    break
        elif choice == '2':
            print(Colorate.Horizontal(Colors.green_to_yellow, "\n=> Đã chọn NHÂY (Random chống trùng)"))
            path = ask_path("Đường dẫn file nội dung nhây", "ngonnhay.txt")
            contents = read_lines_from_file(path)
        elif choice == '3':
            print(Colorate.Horizontal(Colors.green_to_yellow, "\n=> Đã chọn GÕ (Random chống trùng)"))
            path = ask_path("Đường dẫn file nội dung gõ", "ngongo.txt")
            contents = read_lines_from_file(path)
        else:
            print("❌ Lựa chọn không hợp lệ!")
            return

        if not contents:
            print("❌ Nội dung trống! Điền file hoặc nhập tay rồi mở lại tool.")
            return

        fmt = input_format_menu()
        tags_string = input_tag_scope()

        ids_raw = input(Colorate.Horizontal(Colors.yellow_to_red, "💬 ID KÊNH CHAT (Ngăn cách bằng dấu phẩy): ")).strip()
        channel_ids = [int(i.strip()) for i in ids_raw.split(",") if i.strip()]

        if not channel_ids:
            print("❌ Chưa nhập ID kênh chat!")
            return

        tokens = input_tokens()

        if not tokens:
            print("❌ Không có token nào!")
            return

        proxies = load_proxies()

        while True:
            try:
                delay_input = input(Colorate.Horizontal(Colors.yellow_to_red, "⏱️ Nhập Delay (giây, ví dụ 0.1): ")).strip()
                if is_skip(delay_input) or not delay_input:
                    delay_value = 0.1
                    print(Colorate.Horizontal(Colors.cyan_to_blue, "➡️ Delay mặc định 0.1s."))
                    break
                delay_value = float(delay_input)
                if delay_value <= 0:
                    print("⚠️ Delay phải là số dương!")
                    continue
                break
            except ValueError:
                print("⚠️ Vui lòng nhập một số hợp lệ!")

        print(Colorate.Horizontal(Colors.red_to_yellow, f"\n🚀 ĐANG KHỞI CHẠY {len(tokens)} TOKENS | CHỨC NĂNG: {choice} | FMT: {fmt} | TAG: {'CÓ' if tags_string else 'KHÔNG'} | GIF: {'CÓ' if gif_link else 'KHÔNG'}\n"))
        print("-" * 60)

        shared_bag = SharedBag(contents) if choice in ['2', '3'] else None

        slots = [TokenSlot(t, channel_ids, contents, choice, shared_bag, proxies, delay_value, tags_string, fmt, gif_link) for t in tokens]

        sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        await dispatch_loop(slots, channel_ids, delay_value, sem)

    except Exception as e:
        print(f"❌ Lỗi thực thi: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nĐã dừng Tool thủ công!")
