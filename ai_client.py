"""
软著工厂 - AI 客户端
调用 Nous Research API（OpenAI 兼容格式）
"""

import json
import os
import time
import urllib.request


def _load_api_key() -> str:
    """从 auth.json 读取 Nous API key"""
    auth_path = os.path.expanduser("~/.hermes/auth.json")
    with open(auth_path, "r") as f:
        auth = json.load(f)
    return auth["providers"]["nous"]["agent_key"]


def call_ai(prompt: str, system_prompt: str = "", model: str = "xiaomi/mimo-v2-pro") -> dict:
    """
    调用 AI 完成单次推理。
    返回: {"content": str, "tokens": int, "elapsed": float}
    """
    api_key = _load_api_key()
    url = "https://inference-api.nousresearch.com/v1/chat/completions"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": 8192,
        "temperature": 0.7,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    start = time.time()
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    elapsed = time.time() - start

    content = result["choices"][0]["message"]["content"]
    usage = result.get("usage", {})
    total_tokens = usage.get("total_tokens", 0)

    return {
        "content": content,
        "tokens": total_tokens,
        "elapsed": round(elapsed, 1),
    }


def call_ai_json(prompt: str, system_prompt: str = "", model: str = "xiaomi/mimo-v2-pro") -> dict:
    """调用 AI 并解析 JSON 输出"""
    full_system = (system_prompt + "\n\n" if system_prompt else "")
    full_system += "你必须只输出合法的 JSON，不要输出任何其他文字、解释或 markdown 代码块标记。"
    result = call_ai(prompt, full_system, model)

    # 尝试解析 JSON（处理 AI 可能包裹的 ```json ``` 标记）
    content = result["content"].strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI 输出不是合法 JSON: {e}\n原始输出:\n{content[:500]}")

    return {**result, "parsed": parsed}


if __name__ == "__main__":
    # 快速测试
    r = call_ai("用一句话介绍你自己", system_prompt="你是一个简短的助手")
    print(f"✅ API 连接正常: {r['content'][:100]}")
    print(f"   Token: {r['tokens']}, 耗时: {r['elapsed']}s")
