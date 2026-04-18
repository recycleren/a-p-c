import sys
sys.path.insert(0, '.')

from curl_cffi.requests import Session

# 测试当前代理
proxy_url = "http://127.0.0.1:7890"

session = Session(
    proxies={"http": proxy_url, "https": proxy_url},
    impersonate="chrome",
    verify=False,
)

# 1. Cloudflare trace - 看IP和位置
print("=== 1. Cloudflare Trace ===")
try:
    resp = session.get("https://1.1.1.1/cdn-cgi/trace", timeout=10)
    print(resp.text[:300])
except Exception as e:
    print(f"失败: {e}")

# 2. IP信息查询
print("\n=== 2. IP 信息 (ip-api.com) ===")
try:
    resp = session.get("http://ip-api.com/json/?fields=status,country,countryCode,region,city,isp,org,as,query,proxy,hosting,mobile", timeout=10)
    print(resp.text)
except Exception as e:
    print(f"失败: {e}")

# 3. 另一个IP信息源
print("\n=== 3. IP 信息 (ipinfo.io) ===")
try:
    resp = session.get("https://ipinfo.io/json", timeout=10)
    print(resp.text)
except Exception as e:
    print(f"失败: {e}")

# 4. 检查是否被列入黑名单
print("\n=== 4. AbuseIPDB 检查 ===")
try:
    # 先获取IP
    resp = session.get("https://api.ipify.org?format=json", timeout=10)
    ip = resp.json()['ip']
    print(f"当前IP: {ip}")
except Exception as e:
    print(f"失败: {e}")
