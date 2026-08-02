"""
百合会论坛图片下载器
用法:
  下载图片:  python yamibo_downloader.py <帖子URL> [保存目录]
  清除Cookie: python yamibo_downloader.py reset

首次运行会提示粘贴 Cookie，之后自动记住。

Cookie 获取方法 (只需一次):
  1. 浏览器打开百合会并登录
  2. 按 F12 → 网络(Network) 标签
  3. 刷新页面，点击列表中任意一个请求
  4. 找到请求头(Request Headers) 里的 Cookie 行
  5. 复制 Cookie 后面的整行值，粘贴到脚本即可
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin

try:
    import requests
except ImportError:
    print("需要 requests: pip install requests")
    sys.exit(1)

MAX_RETRIES = 3
RETRY_DELAY = 5

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".yamibo")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SITE = "https://bbs.yamibo.com/"


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(cfg: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get_session() -> requests.Session:
    cfg = load_config()
    cookie = cfg.get("cookie", "")

    if not cookie:
        print("首次使用，请粘贴 Cookie。\n")
        print("获取方法:")
        print("  浏览器打开百合会 → F12 → 网络 → 刷新 → 点任意请求")
        print("  → 请求头里找到 Cookie 行 → 复制后面的值\n")
        cookie = input("请粘贴 Cookie: ").strip()
        if not cookie:
            print("Cookie 不能为空"); sys.exit(1)
        cfg["cookie"] = cookie
        save_config(cfg)
        print("已保存!\n")

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": SITE,
        "Cookie": cookie,
    })
    return s


class _Parser(HTMLParser):
    """只解析帖子正文区域 (.t_f) 内的图片，忽略头像、表情等"""

    def __init__(self):
        super().__init__()
        self.images: list[str] = []
        self.title = ""
        self.pg_links: list[str] = []
        self._in_title = False
        self._in_post = False
        self._post_depth = 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "title":
            self._in_title = True

        # 检测进入/离开帖子正文区域
        cls = d.get("class", "")
        if tag == "div" and "t_f" in cls:
            self._in_post = True
            self._post_depth = 1
        elif self._in_post and tag == "div":
            self._post_depth += 1

        # 只收集帖子正文内的图片
        if self._in_post and tag == "img":
            src = d.get("file") or d.get("zoomfile") or d.get("src", "")
            if src and "none.gif" not in src and "static/image" not in src:
                self.images.append(src)

        if tag == "a":
            href = d.get("href", "")
            if href and "page" in href and "javascript" not in href:
                full = href if href.startswith("http") else urljoin(SITE, href)
                if full not in self.pg_links:
                    self.pg_links.append(full)

    def handle_data(self, data):
        if self._in_title:
            self.title += data

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if self._in_post and tag == "div":
            self._post_depth -= 1
            if self._post_depth <= 0:
                self._in_post = False


def _get(session: requests.Session, url: str, timeout: int = 30) -> requests.Response:
    """带重试的 GET 请求"""
    for attempt in range(MAX_RETRIES):
        try:
            r = session.get(url, timeout=timeout)
            r.raise_for_status()
            return r
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  超时，{RETRY_DELAY}秒后重试 ({attempt+1}/{MAX_RETRIES})...")
                time.sleep(RETRY_DELAY)
            else:
                raise


def fetch_images(session: requests.Session, url: str) -> tuple[str, list[str]]:
    r = _get(session, url)
    r.encoding = "utf-8"

    p = _Parser()
    p.feed(r.text)
    images = list(p.images)
    visited = {url}

    for pg in p.pg_links:
        if pg in visited:
            continue
        visited.add(pg)
        print("  读取分页...")
        try:
            r2 = _get(session, pg)
            r2.encoding = "utf-8"
            p2 = _Parser()
            p2.feed(r2.text)
            images.extend(p2.images)
        except Exception as e:
            print(f"  分页失败: {e}")

    return p.title.strip(), images


def download(url: str, save_dir: str):
    session = get_session()
    log_lines: list[str] = []

    def log(msg: str):
        print(msg)
        log_lines.append(msg)

    log(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"链接: {url}")

    log("正在获取帖子...")
    try:
        title, images = fetch_images(session, url)
    except Exception as e:
        log(f"获取失败: {e}")
        sys.exit(1)

    if "提示信息" in title or not images:
        log(f"页面: {title}")
        log("未找到图片。Cookie 可能过期，执行以下命令清除后重新粘贴:")
        log(f"  python {os.path.basename(__file__)} reset")
        sys.exit(1)

    # 清理标题作为文件夹名
    folder_name = re.sub(r'[\\/:*?"<>|]', '_', title.split(" - ")[0].strip())
    folder_path = os.path.join(save_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    total = len(images)
    log(f"标题: {title}")
    log(f"共 {total} 张 → {folder_path}")
    log("-" * 50)

    ok = 0
    skipped = 0
    failed: list[int] = []
    failed_reasons: dict[int, str] = {}
    for i, img in enumerate(images):
        full_url = img if img.startswith("http") else urljoin(SITE, img)
        fname = f"{i+1:03d}.jpg"
        fpath = os.path.join(folder_path, fname)

        if os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
            log(f"[{i+1:03d}/{total}] {fname} 已存在，跳过")
            ok += 1
            skipped += 1
            continue

        try:
            r = _get(session, full_url)
            if len(r.content) > 1000:
                with open(fpath, "wb") as f:
                    f.write(r.content)
                size_kb = len(r.content) / 1024
                log(f"[{i+1:03d}/{total}] {fname} ({size_kb:.1f} KB)")
                ok += 1
            else:
                reason = "文件太小"
                log(f"[{i+1:03d}/{total}] {fname} 跳过 ({reason})")
                failed.append(i + 1)
                failed_reasons[i + 1] = reason
        except Exception as e:
            reason = str(e)
            log(f"[{i+1:03d}/{total}] {fname} 失败: {reason}")
            failed.append(i + 1)
            failed_reasons[i + 1] = reason

        time.sleep(0.3)

    downloaded = ok - skipped
    log("-" * 50)
    log(f"完成! 成功 {ok}/{total} 张 (新下载 {downloaded}, 已存在 {skipped})")
    if failed:
        nums = ", ".join(str(n) for n in failed)
        log(f"失败 {len(failed)} 张: {nums}")
        log("重新运行同一命令即可重试（已下载的会跳过）")
    log(f"保存位置: {folder_path}")

    # 写入日志文件
    log_path = os.path.join(folder_path, "download_log.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")
    print(f"日志已保存: {log_path}")


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(0)

    if sys.argv[1] == "reset":
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
            print("已清除 Cookie")
        else:
            print("没有已保存的 Cookie")
        sys.exit(0)

    url = sys.argv[1]
    save_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.expanduser("~"), "Downloads")
    download(url, save_dir)


if __name__ == "__main__":
    main()
