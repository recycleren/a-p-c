"""
OpenAI 注册专用工具函数
从 any-auto-register-main 移植的关键功能
"""
import random
import hashlib
import base64
import re
import uuid
import secrets
from typing import Optional


def generate_device_id():
    """生成设备唯一标识（oai-did），UUID v4 格式"""
    return str(uuid.uuid4())

# Chrome 版本列表 (用于随机化指纹)
CHROME_VERSIONS = [
    ("120", "120.0.6099.130"),
    ("121", "121.0.6167.85"),
    ("122", "122.0.6261.57"),
    ("123", "123.0.6412.52"),
    ("124", "124.0.6366.118"),
    ("125", "125.0.6425.112"),
    ("126", "126.0.6458.77"),
    ("127", "127.0.6533.88"),
    ("128", "128.0.6472.112"),
    ("129", "129.0.6465.86"),
    ("130", "130.0.6510.111"),
    ("131", "131.0.6778.109"),
    ("132", "132.0.6834.76"),
    ("133", "133.0.6887.105"),
    ("134", "134.0.6998.90"),
    ("135", "135.0.7015.84"),
    ("136", "136.0.7103.64"),
    ("137", "137.0.7155.54"),
    ("138", "138.0.7200.134"),
    ("139", "139.0.7271.109"),
    ("140", "140.0.7418.149"),
    ("141", "141.0.7454.0"),
    ("142", "142.0.7465.91"),
    ("143", "143.0.7470.120"),
    ("144", "144.0.7476.85"),
    ("145", "145.0.7485.0"),
    ("146", "146.0.7680.178"),
]


def _random_chrome_version():
    """随机选择一个 Chrome 版本组合 (major, full)"""
    major, full = random.choice(CHROME_VERSIONS)
    sec_ch_ua = f'"Chromium";v="{major}", "Google Chrome";v="{major}", "Not.A/Brand";v="99"'
    ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{full} Safari/537.36"
    return ua, major, full, sec_ch_ua


def extract_chrome_full_version(user_agent: str) -> Optional[str]:
    """从 User-Agent 字符串中提取 Chrome 完整版本号"""
    match = re.search(r"Chrome/(\d+\.\d+\.\d+\.\d+)", user_agent)
    return match.group(1) if match else None


def build_sec_ch_ua_full_version_list(sec_ch_ua: Optional[str], chrome_full: Optional[str]) -> Optional[str]:
    """构建 sec-ch-ua-full-version-list 头"""
    if not sec_ch_ua or not chrome_full:
        return None
    
    brands = []
    for match in re.finditer(r'"([^"]+)";v="([^"]+)"', sec_ch_ua):
        brand, version = match.groups()
        if brand == "Chromium":
            version = chrome_full
        brands.append(f'"{brand}";v="{version}"')
    
    return ", ".join(brands) if brands else None


def infer_sec_fetch_site(url: str, referer: Optional[str] = None, navigation: bool = False) -> str:
    """推断 sec-fetch-site 头的值"""
    if navigation:
        return "none"
    
    if not referer:
        return "none"
    
    try:
        from urllib.parse import urlparse
        url_domain = urlparse(url).netloc
        ref_domain = urlparse(referer).netloc
        if url_domain == ref_domain:
            return "same-origin" if url_domain.endswith("openai.com") else "same-site"
        return "cross-site"
    except:
        return "none"


def build_browser_headers(
    url: str,
    user_agent: str,
    sec_ch_ua: Optional[str] = None,
    chrome_full_version: Optional[str] = None,
    accept: Optional[str] = None,
    accept_language: str = "en-US,en;q=0.9",
    referer: Optional[str] = None,
    origin: Optional[str] = None,
    content_type: Optional[str] = None,
    navigation: bool = False,
    fetch_mode: Optional[str] = None,
    fetch_dest: Optional[str] = None,
    fetch_site: Optional[str] = None,
    headed: bool = False,
    extra_headers: Optional[dict] = None,
) -> dict:
    """构造更接近真实 Chrome 有头浏览器的请求头"""
    chrome_full = chrome_full_version or extract_chrome_full_version(user_agent)
    full_version_list = build_sec_ch_ua_full_version_list(sec_ch_ua, chrome_full)

    headers = {
        "User-Agent": user_agent,
        "Accept-Language": accept_language,
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua-arch": '"x86"',
        "sec-ch-ua-bitness": '"64"',
    }

    if accept:
        headers["Accept"] = accept
    if referer:
        headers["Referer"] = referer
    if origin:
        headers["Origin"] = origin
    if content_type:
        headers["Content-Type"] = content_type
    if sec_ch_ua:
        headers["sec-ch-ua"] = sec_ch_ua
    if chrome_full:
        headers["sec-ch-ua-full-version"] = f'"{chrome_full}"'
        headers["sec-ch-ua-platform-version"] = '"15.0.0"'
    if full_version_list:
        headers["sec-ch-ua-full-version-list"] = full_version_list

    if navigation:
        headers["Sec-Fetch-Dest"] = "document"
        headers["Sec-Fetch-Mode"] = "navigate"
        headers["Sec-Fetch-User"] = "?1"
        headers["Upgrade-Insecure-Requests"] = "1"
        headers["Cache-Control"] = "max-age=0"
    else:
        headers["Sec-Fetch-Dest"] = fetch_dest or "empty"
        headers["Sec-Fetch-Mode"] = fetch_mode or "cors"

    headers["Sec-Fetch-Site"] = fetch_site or infer_sec_fetch_site(url, referer, navigation)

    if headed:
        headers.setdefault("Priority", "u=0, i" if navigation else "u=1, i")
        headers.setdefault("DNT", "1")
        headers.setdefault("Sec-GPC", "1")

    if extra_headers:
        for key, value in extra_headers.items():
            if value is not None:
                headers[key] = value

    return headers


def generate_datadog_trace() -> dict:
    """生成 Datadog APM 追踪头"""
    trace_id = str(random.getrandbits(64))
    parent_id = str(random.getrandbits(64))
    trace_hex = format(int(trace_id), "016x")
    parent_hex = format(int(parent_id), "016x")
    return {
        "traceparent": f"00-0000000000000000{trace_hex}-{parent_hex}-01",
        "tracestate": "dd=s:1;o:rum",
        "x-datadog-origin": "rum",
        "x-datadog-parent-id": parent_id,
        "x-datadog-sampling-priority": "1",
        "x-datadog-trace-id": trace_id,
    }


def generate_pkce():
    """生成 PKCE code_verifier 和 code_challenge"""
    code_verifier = (
        base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode("ascii")
    )
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


# 需要 secrets 模块
import secrets
