"""QuickJS 版 Sentinel SDK token 获取（用于 username_password_create / oauth_create_account flow）。"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Optional

logger = __import__("logging").getLogger(__name__)

SENTINEL_VERSION = "20260219f9f6"
SENTINEL_SDK_URL = f"https://sentinel.openai.com/sentinel/{SENTINEL_VERSION}/sdk.js"
SENTINEL_REQ_URL = "https://sentinel.openai.com/backend-api/sentinel/req"

# QuickJS wrapper script (Node.js 执行)
_QUICKJS_WRAPPER = r"""
const fs = require('fs');
const path = require('path');
const timeoutMs = Number(process.env.OPENAI_SENTINEL_VM_TIMEOUT_MS || '10000');
const sdkFile = process.env.OPENAI_SENTINEL_SDK_FILE;
const scriptFile = process.env.OPENAI_SENTINEL_QUICKJS_SCRIPT;
const payloadFile = process.env.OPENAI_SENTINEL_PAYLOAD_FILE || '';
const action = process.env.OPENAI_SENTINEL_ACTION || 'requirements';

let payloadStr = '{}';
if (payloadFile && fs.existsSync(payloadFile)) {
    try { payloadStr = fs.readFileSync(payloadFile, 'utf8').trim(); } catch(e) {}
}

const payload = JSON.parse(payloadStr || '{}');
payload.action = action;

globalThis.__payload_json = JSON.stringify(payload);
globalThis.__sdk_source = fs.readFileSync(sdkFile, 'utf8');
globalThis.__vm_done = false;
globalThis.__vm_output_json = '';
globalThis.__vm_error = '';

async function main() {
    try {
        const script = fs.readFileSync(scriptFile, 'utf8');
        await eval(script);
        const started = Date.now();
        while (!globalThis.__vm_done) {
            if ((Date.now() - started) > timeoutMs) {
                console.log(JSON.stringify({__timeout: true}));
                return;
            }
            await new Promise(r => setTimeout(r, 50));
        }
        console.log(globalThis.__vm_output_json);
    } catch(e) {
        console.log(JSON.stringify({__error: e.message || String(e)}));
    }
}

main();
"""


def _quickjs_script_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent.parent
        / "scripts"
        / "js"
        / "openai_sentinel_quickjs.js"
    )


def _resolve_node_binary() -> str:
    return os.getenv("OPENAI_SENTINEL_NODE_PATH", "").strip() or "node"


def _ensure_sdk_file(session: Any, timeout_ms: int) -> Path:
    cache_dir = Path(tempfile.gettempdir()) / "openai-sentinel-demo" / SENTINEL_VERSION
    cache_dir.mkdir(parents=True, exist_ok=True)
    sdk_file = cache_dir / "sdk.js"
    if sdk_file.exists() and sdk_file.stat().st_size > 0:
        return sdk_file
    resp = session.get(
        SENTINEL_SDK_URL,
        headers={
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9",
            "referer": "https://auth.openai.com/",
            "sec-fetch-dest": "script",
            "sec-fetch-mode": "no-cors",
            "sec-fetch-site": "same-site",
        },
        timeout=max(10, int(timeout_ms / 1000)),
    )
    resp.raise_for_status()
    content = getattr(resp, "content", b"")
    if not content:
        raise RuntimeError("Sentinel sdk.js 下载失败: 响应为空")
    sdk_file.write_bytes(content)
    return sdk_file


def _run_quickjs_action_with_node(
    *,
    action: str,
    sdk_file: Path,
    quickjs_script: Path,
    payload: dict,
    timeout_ms: int,
) -> dict:
    # Write payload to temp file (avoids stdin deadlock with Node's stdin.on('end'))
    import tempfile
    import uuid
    payload_file = Path(tempfile.gettempdir()) / f"qjs_payload_{uuid.uuid4().hex[:8]}.json"
    payload_file.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")

    wrapper_env = {
        **os.environ,
        "OPENAI_SENTINEL_VM_TIMEOUT_MS": str(timeout_ms),
        "OPENAI_SENTINEL_SDK_FILE": str(sdk_file),
        "OPENAI_SENTINEL_QUICKJS_SCRIPT": str(quickjs_script),
        "OPENAI_SENTINEL_PAYLOAD_FILE": str(payload_file),
        "OPENAI_SENTINEL_ACTION": action,
    }
    try:
        result = subprocess.run(
            [_resolve_node_binary(), "-e", _QUICKJS_WRAPPER],
            capture_output=True,
            text=True,
            env=wrapper_env,
            timeout=max(15, int(timeout_ms / 1000)),
        )
        raw = result.stdout.strip()
        if not raw:
            raise RuntimeError(f"QuickJS 无输出: stderr={result.stderr[:200]}")
        out = json.loads(raw)
        if out.get("__error"):
            raise RuntimeError(f"QuickJS 错误: {out['__error']}")
        if out.get("__timeout"):
            raise RuntimeError("QuickJS 执行超时")
        return out
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"QuickJS subprocess 超时 ({timeout_ms}ms)")
    finally:
        try:
            payload_file.unlink(missing_ok=True)
        except Exception:
            pass


def _fetch_sentinel_challenge(
    session: Any,
    *,
    device_id: str,
    flow: str,
    request_p: str,
    timeout_ms: int,
) -> dict:
    body = json.dumps({"p": request_p, "id": device_id, "flow": flow}, separators=(",", ":"))
    resp = session.post(
        SENTINEL_REQ_URL,
        data=body,
        headers={
            "origin": "https://sentinel.openai.com",
            "referer": f"https://sentinel.openai.com/backend-api/sentinel/frame.html?sv={SENTINEL_VERSION}",
            "content-type": "text/plain;charset=UTF-8",
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "zh-CN,zh;q=0.9",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        },
        timeout=max(10, int(timeout_ms / 1000)),
    )
    resp.raise_for_status()
    payload = resp.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Sentinel challenge 响应不是 JSON 对象")
    return payload


def is_authenticated_socks5_proxy(proxy: Any) -> bool:
    """检查代理是否为带认证的 SOCKS5 代理（QuickJS 无法处理，需要跳过）。"""
    if not proxy:
        return False
    if isinstance(proxy, dict):
        for val in proxy.values():
            if isinstance(val, str) and val.lower().startswith("socks5://"):
                return True
    elif isinstance(proxy, str) and proxy.lower().startswith("socks5://"):
        return True
    return False


def get_sentinel_token_via_quickjs(
    *,
    flow: str,
    proxy: Any = None,
    timeout_ms: int = 45000,
    device_id: Optional[str] = None,
    log_fn: Any = None,
) -> Optional[str]:
    """通过 curl_cffi + QuickJS Node.js 获取 Sentinel token（用于需要完整 PoW 解的 flow）。"""
    _log = log_fn or (lambda msg: logger.info(msg))

    try:
        from curl_cffi import requests as curl_requests
    except Exception as e:
        _log(f"Sentinel QuickJS 不可用: curl_cffi 导入失败: {e}")
        return None

    quickjs_script = _quickjs_script_path()
    if not quickjs_script.exists():
        _log(f"Sentinel QuickJS 脚本不存在: {quickjs_script}")
        return None

    did = str(device_id or uuid.uuid4())
    session = curl_requests.Session(impersonate="chrome136")
    if proxy:
        session.proxies = proxy if isinstance(proxy, dict) else {"http": proxy, "https": proxy}

    try:
        sdk_file = _ensure_sdk_file(session, timeout_ms)

        requirements = _run_quickjs_action_with_node(
            action="requirements",
            sdk_file=sdk_file,
            quickjs_script=quickjs_script,
            payload={"device_id": did},
            timeout_ms=timeout_ms,
        )
        request_p = str(requirements.get("request_p") or "").strip()
        if not request_p:
            _log("Sentinel QuickJS 失败: requirements 未返回 request_p")
            return None

        challenge = _fetch_sentinel_challenge(
            session,
            device_id=did,
            flow=flow,
            request_p=request_p,
            timeout_ms=timeout_ms,
        )
        c_value = str(challenge.get("token") or "").strip()
        if not c_value:
            _log("Sentinel QuickJS 失败: challenge token 为空")
            return None

        solved = _run_quickjs_action_with_node(
            action="solve",
            sdk_file=sdk_file,
            quickjs_script=quickjs_script,
            payload={
                "device_id": did,
                "request_p": request_p,
                "challenge": challenge,
            },
            timeout_ms=timeout_ms,
        )
        final_p = str(solved.get("final_p") or solved.get("p") or "").strip()
        if not final_p:
            _log("Sentinel QuickJS 失败: solve 未返回 final_p")
            return None

        t_raw = solved.get("t")
        t_value = "" if t_raw is None else str(t_raw).strip()
        if not t_value:
            _log("Sentinel QuickJS 失败: solve 未返回有效 t")
            return None

        token = json.dumps(
            {
                "p": final_p,
                "t": t_value,
                "c": c_value,
                "id": did,
                "flow": flow,
            },
            separators=(",", ":"),
            ensure_ascii=False,
        )
        _log(f"Sentinel QuickJS 成功: p=OK t=OK c=OK flow={flow}")
        return token
    except Exception as e:
        _log(f"Sentinel QuickJS 异常: {e}")
        return None
    finally:
        try:
            session.close()
        except Exception:
            pass
