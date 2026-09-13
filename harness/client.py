"""vLLM OpenAI 兼容客户端：流式拿到 prefill / decode 分界。

- endpoint = "completions" -> POST /v1/completions（D13 裁定，直送提示词文本）
- endpoint = "chat"        -> POST /v1/chat/completions（不带 system 消息）
流式字段兼容两种：completions 用 choices[].text；chat 用 choices[].delta.content / .reasoning。

只有「请求报错」才重跑，并在记录里标 retry=true（03 §1.4）。
"""
import hashlib
import json
import re
import time
import urllib.error
import urllib.request

from .config import ServeConfig


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]


def split_thinking(text: str) -> tuple[str, str]:
    """把正文里的思考剥出来。返回 (正文, 思考)。

    走原生 /v1/completions 时，模型的思考以字面 <think>…</think> 混在正文里。
    若只有 <think> 而没有 </think>，说明被 max_tokens 截断在思考中间——此时正文为空。
    """
    m = re.search(r"<think>([\s\S]*?)</think>", text)
    if m:
        return text.replace(m.group(0), "", 1).strip(), m.group(1).strip()
    m = re.search(r"<think>([\s\S]*)$", text)
    if m:
        return "", m.group(1).strip()
    return text, ""


class Client:
    def __init__(self, cfg: ServeConfig):
        self.cfg = cfg

    def _payload(self, prompt: str, max_tokens: int, seed: int) -> dict:
        p = {"model": self.cfg.model, "max_tokens": max_tokens, "stream": True,
             "temperature": self.cfg.temperature, "top_p": self.cfg.top_p, "seed": seed}
        if self.cfg.endpoint == "completions":
            p["prompt"] = prompt
        elif self.cfg.endpoint == "chat":
            p["messages"] = [{"role": "user", "content": prompt}]
            if self.cfg.enable_thinking is not None:
                p["chat_template_kwargs"] = {"enable_thinking": self.cfg.enable_thinking}
        else:
            raise ValueError(f"未知 endpoint {self.cfg.endpoint}")
        return p

    def _path(self) -> str:
        return "/v1/completions" if self.cfg.endpoint == "completions" else "/v1/chat/completions"

    def complete(self, prompt: str, max_tokens: int, seed: int, on_delta=None) -> dict:
        """返回 text/reasoning/时间/用量。on_delta(piece, kind) 用于前端实时展示。"""
        cfg = self.cfg
        last_err = None
        for attempt in range(1, cfg.max_retries + 1):
            try:
                return self._once(prompt, max_tokens, seed, on_delta)
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                last_err = e
                time.sleep(2 * attempt)
        raise RuntimeError(f"请求连续失败 {cfg.max_retries} 次: {last_err!r}")

    def _once(self, prompt, max_tokens, seed, on_delta):
        cfg = self.cfg
        data = json.dumps(self._payload(prompt, max_tokens, seed)).encode("utf-8")
        req = urllib.request.Request(cfg.base_url + self._path(), data=data,
                                     headers={"Content-Type": "application/json"})
        t0 = time.perf_counter()
        ttft = None
        n = 0
        text, reasoning, finish = [], [], None
        with urllib.request.urlopen(req, timeout=cfg.timeout) as resp:
            for raw in resp:
                s = raw.decode("utf-8", "ignore").strip()
                if not s.startswith("data:"):
                    continue
                body = s[5:].strip()
                if body == "[DONE]":
                    break
                ch = json.loads(body)["choices"][0]
                d = ch.get("delta") or {}
                piece = ch.get("text") or d.get("content") or ""
                think = d.get("reasoning") or ""
                if piece or think:
                    if ttft is None:
                        ttft = time.perf_counter()
                    n += 1
                    if piece:
                        text.append(piece)
                        if on_delta:
                            on_delta(piece, "content")
                    if think:
                        reasoning.append(think)
                        if on_delta:
                            on_delta(think, "reasoning")
                if ch.get("finish_reason"):
                    finish = ch["finish_reason"]
        t1 = time.perf_counter()
        if ttft is None:
            raise ConnectionError("流结束但没有收到任何 token")
        return {"text": "".join(text), "reasoning": "".join(reasoning),
                "prefill_ms": (ttft - t0) * 1000, "decode_ms": (t1 - ttft) * 1000,
                "output_tokens": n, "finish_reason": finish,
                "wall_clock_ms": (t1 - t0) * 1000, "retry": False}


class MockClient:
    """不调模型：按提示词造一段假输出，用于跑通管线与演示前端。"""

    def __init__(self, cfg=None):
        self.cfg = cfg

    def complete(self, prompt, max_tokens, seed, on_delta=None):
        body = ("【模拟输出】本段用于验证管线与前端展示，不参与任何实验数据。"
                "工程记录显示各项读数平稳，巡检按班次归档，单位与精度在表头统一注明。")
        text = (body * 3)[: max(60, min(max_tokens, 220))]
        if on_delta:
            for k in range(0, len(text), 6):
                time.sleep(0.002)
                on_delta(text[k:k + 6], "content")
        return {"text": text, "reasoning": "", "prefill_ms": 120.0, "decode_ms": 400.0,
                "output_tokens": len(text) // 2, "finish_reason": "stop",
                "wall_clock_ms": 520.0, "retry": False}
