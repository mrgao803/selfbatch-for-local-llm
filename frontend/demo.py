#!/usr/bin/env python
"""不碰 GPU 的演示脚本：一边跑一边更新 state.json，让人立刻看到前端效果。

  python frontend/demo.py
  python frontend/demo.py --interval 0.01 --pause 0.2
  python frontend/demo.py --out results/live_demo/state.json

流程（N=4 的假任务）：
  1) A1：4 段并行生成——4 段交错逐字增长，真的同时在写
  2) A2-V1 第 1 轮汇总融合——4 段同时重写，内容有可见修订
  3) A2-V1 第 2 轮汇总融合——再次同时重写，进一步收敛

纯 CPU、纯标准库，不加载模型、不联网。state 文件用「临时文件 + 原子替换」写入，
保证前端永远读不到半截 JSON。
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TASK_ID = "DEMO-01"
SEED = 101

SECTIONS = [
    {
        "i": 1,
        "title": "产品定位与目标用户",
        "v0": "檐语 T2 是摆在玄关与客厅之间的桌面语音终端，面向两代人同住、常有访客来往的家"
              "庭。它要解决的核心问题是：家里同时有老人、孩子和访客时，助手该听谁的、该记住"
              "什么。产品主打家务提醒、访客留言与家电口令三类日常功能。",
        "rev1": "檐语 T2 是摆在玄关与客厅之间的桌面语音终端，面向两代人同住、常有访客来往的家"
                "庭。设备要回答的核心问题是：家中同时有老人、孩子与访客时，助手应听从谁、又该"
                "记住什么。产品围绕家务提醒、访客留言与家电口令三类日常场景展开。",
        "rev2": "檐语 T2 是置于玄关与客厅之间的桌面语音终端，面向两代人同住、常有访客来往的家"
                "庭。它要回答的核心问题是：家中同时存在老人、孩子与访客时，助手听从谁、记住"
                "什么。功能上聚焦家务提醒、访客留言与家电口令三类日常场景。",
        "reason": {
            "a1": "本节只依据材料「一、产品定位」独立撰写，不引用其他部分，段内自足。",
            "r1": "已看到硬件段与音频段正文；发现「目标用户」与硬件描述的称呼不一致，统一为"
                  "「两代人同住的家庭」，并把功能范围对齐其他段的措辞。",
            "r2": "上轮已基本一致；本轮只做措辞收敛，压缩重复表述，保留三类功能不变。",
        },
    },
    {
        "i": 2,
        "title": "硬件规格",
        "v0": "主控为八核异构处理器（4 大核 + 4 小核），主频 2.0GHz，NPU 算力 3.5 TOPS。整机"
              "配备 6GB LPDDR5 内存与 64GB eMMC 存储。拾音由四麦克风线性阵列加 1 个顶部全向"
              "麦克风组成，共 5 路，最远拾音距离 4 米。发声单元为 1.75 英寸全频单元 × 2，额定"
              "总功率 16W。",
        "rev1": "主控采用八核异构处理器，含 4 个大核与 4 个小核，主频 2.0GHz，NPU 算力 3.5 "
                "TOPS。内存 6GB LPDDR5，存储 64GB eMMC。拾音为四麦克风线性阵列加顶部全向麦"
                "克风各 1，共 5 路，最远 4 米。发声为 1.75 英寸全频单元 × 2，额定总功率 16W。",
        "rev2": "主控为八核异构处理器（4 大核 + 4 小核），主频 2.0GHz，NPU 3.5 TOPS。整机配 "
                "6GB LPDDR5 内存与 64GB eMMC 存储。拾音共 5 路：四麦克风线性阵列加 1 个顶部全"
                "向麦克风，最远 4 米。发声为 1.75 英寸全频单元 × 2，额定总功率 16W。",
        "reason": {
            "a1": "参数全部逐字取自材料「二、硬件规格」，只排列已知数值，不做换算。",
            "r1": "音频段引用了「五路麦克风」，与本节拾音描述需保持同一口径；统一写成 5 路。",
            "r2": "与隐私段的硬件描述对齐，去掉重复的量词，参数数值一个不改。",
        },
    },
    {
        "i": 3,
        "title": "音频处理的四级链路",
        "v0": "音频链路在本地 DSP 上完成四级处理：先做回声消除，扣除设备自身扬声器的输出；再"
              "做波束成形，依据五路麦克风的相位差锁定声源方向；随后做噪声抑制，稳态噪声压制 "
              "18dB、突发噪声压制 10dB；最后做自动增益，把远近声源拉进同一响度区间。四级串联"
              "总延迟不超过 35ms。",
        "rev1": "音频链路全部在本地 DSP 上完成，共四级：第一步回声消除，扣除扬声器输出；第二步"
                "波束成形，用五路麦克风相位差锁定声源；第三步噪声抑制，稳态压制 18dB、突发压制 "
                "10dB；第四步自动增益，统一远近声源响度。总延迟不超过 35ms。",
        "rev2": "本地 DSP 上的音频链路分为四级：回声消除扣除自身扬声器输出；波束成形依据五路麦"
                "克风相位差定位声源；噪声抑制对稳态噪声压制 18dB、对突发噪声压制 10dB；自动增"
                "益拉平远近声源响度。四级串联总延迟不超过 35ms。",
        "reason": {
            "a1": "严格按材料「三、音频处理」的四步顺序写，步骤名与数值照抄。",
            "r1": "硬件段也提到 5 路麦克风，本节沿用同一说法；四步的表述改为统一步骤句式。",
            "r2": "检查四步顺序与延迟数值与其余段一致，仅精简连接词。",
        },
    },
    {
        "i": 4,
        "title": "唤醒与识别",
        "v0": "唤醒词为四个字的固定短语，用户可在应用内录制替换。误唤醒指标为：连续播放 24 小"
              "时电视伴音，触发次数不超过 2 次。唤醒响应由本地模型完成，平均 150ms。语音识别"
              "对中文普通话准确率 96.5%（安静环境），支持 12 种方言。设备可登记 6 位家庭成员"
              "的声纹，登记后按声源区分说话人。",
        "rev1": "设备唤醒词是四字固定短语，可在应用内自行录制替换。误唤醒方面，连续播放 24 小时"
                "电视伴音，触发不超过 2 次。唤醒模型运行在本地，平均响应 150ms。语音识别在安静"
                "环境下中文普通话准确率 96.5%，支持 12 种方言；可登记 6 位家庭成员声纹并按声源"
                "区分说话人。",
        "rev2": "唤醒词为四字固定短语，支持在应用内录制替换。连续播放 24 小时电视伴音时，误唤醒"
                "不超过 2 次。本地唤醒模型平均响应 150ms。中文普通话识别准确率 96.5%（安静环"
                "境），支持 12 种方言；可登记 6 位家庭成员声纹，按声源区分说话人。",
        "reason": {
            "a1": "依据材料「四、唤醒与识别」逐条写，四条指标分别成句。",
            "r1": "与音频段同为「本地处理」，统一「本地」的表述；识别指标数值保持不变。",
            "r2": "与定位段呼应「家庭成员」用词，句序微调，指标不动。",
        },
    },
]


def atomic_write(path: Path, state: dict) -> None:
    """临时文件 + os.replace，保证读者看到的永远是完整 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".state-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def emit(state: dict, path: Path) -> None:
    state["updated_at"] = round(time.time(), 3)
    atomic_write(path, state)


def make_state(condition: str, round_: int, phase: str, variant, reason_key: str) -> dict:
    segments = [
        {
            "i": sec["i"],
            "title": sec["title"],
            "text": "",
            "reasoning": sec["reason"][reason_key],
            "tokens": 0,
            "state": "writing",
        }
        for sec in SECTIONS
    ]
    return {
        "task_id": TASK_ID,
        "cls": "A",
        "n": len(SECTIONS),
        "chain": None,
        "seed": SEED,
        "condition": condition,
        "variant": variant,
        "round": round_,
        "phase": phase,
        "segments": segments,
        "updated_at": round(time.time(), 3),
    }


def grow(state: dict, texts: dict, path: Path, interval: float,
         tag: str, log_every: int = 8) -> list:
    """让 N 段交错逐字增长：每一 tick 每个未完成的段都前进一点，看起来就是同时写。"""
    segs = state["segments"]
    pos = {s["i"]: 0 for s in segs}
    rate = {s["i"]: 3 + (s["i"] * 2) % 3 for s in segs}   # 每 tick 前进 3~5 字，各段不同
    ticks = 0
    samples = []
    while True:
        active = False
        for seg in segs:
            i = seg["i"]
            full = texts[i]
            if pos[i] < len(full):
                pos[i] = min(len(full), pos[i] + rate[i])
                seg["text"] = full[: pos[i]]
                seg["tokens"] = len(seg["text"])
                seg["state"] = "writing" if pos[i] < len(full) else "done"
                active = True
        emit(state, path)
        ticks += 1
        if ticks % log_every == 0 or not active:
            snapshot = [s["tokens"] for s in segs]
            samples.append(snapshot)
            print("  [%s] tick %3d  tokens=%s  states=%s"
                  % (tag, ticks, snapshot, [s["state"] for s in segs]), flush=True)
        if not active:
            break
        time.sleep(interval)
    return samples


def main():
    ap = argparse.ArgumentParser(description="多段并行生成 · 无 GPU 演示（写 state.json）")
    ap.add_argument("--out", default="results/live_demo/state.json")
    ap.add_argument("--interval", type=float, default=0.05, help="每 tick 间隔秒数（逐字增长步长）")
    ap.add_argument("--pause", type=float, default=1.0, help="阶段之间的停顿秒数")
    ap.add_argument("--log-every", type=int, default=8, help="每多少 tick 打印一次 tokens 采样")
    args = ap.parse_args()

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out

    print("[demo] 输出：%s" % out, flush=True)
    print("[demo] N=%d   interval=%.3fs   pause=%.2fs" % (len(SECTIONS), args.interval, args.pause),
          flush=True)

    print("\n=== 阶段 1 / A1：N 段并行生成（4 段交错逐字增长）===", flush=True)
    state = make_state("A1", 0, "N 段并行生成", None, "a1")
    grow(state, {s["i"]: s["v0"] for s in SECTIONS}, out, args.interval, "A1", args.log_every)
    print("[demo] A1 全部完成，4 段同时写入结束。", flush=True)
    time.sleep(args.pause)

    for r in (1, 2):
        print("\n=== 阶段 %d / A2-V1：第 %d 轮汇总融合（4 段同时重写）===" % (r + 1, r), flush=True)
        state = make_state("A2-V1", r, "第 %d 轮汇总融合" % r, "V1", "r1" if r == 1 else "r2")
        texts = {s["i"]: (s["rev1"] if r == 1 else s["rev2"]) for s in SECTIONS}
        grow(state, texts, out, args.interval, "A2-R%d" % r, args.log_every)
        print("[demo] 第 %d 轮融合完成。" % r, flush=True)
        if r == 1:
            time.sleep(args.pause)

    print("\n[demo] 全部完成。state 文件：%s" % out, flush=True)
    print("[demo] 用 server.py 可视化：  python frontend/server.py "
          "--state-file %s" % args.out, flush=True)


if __name__ == "__main__":
    main()
