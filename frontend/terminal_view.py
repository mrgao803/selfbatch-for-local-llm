#!/usr/bin/env python
"""在 SSH 终端里直接看实时状态——不依赖端口转发，登录就能用。

  python frontend/terminal_view.py                    # 看实时
  python frontend/terminal_view.py --once             # 只渲染一帧
  python frontend/terminal_view.py --state-file results/live_demo/state.json
  python frontend/terminal_view.py --think            # 显示思考内容
"""
import argparse
import json
import shutil
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESET, DIM, BOLD, INV = "\033[0m", "\033[2m", "\033[1m", "\033[7m"
CLR = "\033[2J\033[H"
COLS = ["\033[32m", "\033[36m", "\033[33m", "\033[35m", "\033[34m", "\033[31m"]


def dwidth(s: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def trunc(s: str, w: int) -> str:
    s = s.replace("\n", " ")
    out, acc = "", 0
    for c in s:
        d = 2 if unicodedata.east_asian_width(c) in "WF" else 1
        if acc + d > w:
            return out + "…"
        out, acc = out + c, acc + d
    return out


def wrap_lines(text: str, w: int, max_lines: int) -> list[str]:
    lines, cur, acc = [], "", 0
    for ch in text.replace("\r", ""):
        if ch == "\n":
            lines.append(cur)
            cur, acc = "", 0
            continue
        d = 2 if unicodedata.east_asian_width(ch) in "WF" else 1
        if acc + d > w:
            lines.append(cur)
            cur, acc = "", 0
        cur, acc = cur + ch, acc + d
    if cur:
        lines.append(cur)
    return lines[-max_lines:]


def render(state: dict, think: bool, w: int, h: int) -> str:
    if not state or state.get("empty"):
        return CLR + f"{DIM}等待运行器启动…（{time.strftime('%H:%M:%S')}）{RESET}\n"
    segs = state.get("segments", [])
    head = (f"{BOLD}{state.get('task_id','?')}{RESET} · 类别{state.get('cls','?')} · "
            f"N={state.get('n','?')} · seed={state.get('seed','?')} · "
            f"{state.get('condition','?')}"
            + (f" · {state.get('variant')}" if state.get("variant") else "")
            + (f" · 第{state.get('round')}轮" if state.get("round") else "")
            + f"  {INV} {state.get('phase','')} {RESET}")
    done = sum(1 for s in segs if s.get("state") == "done")
    out = [CLR, head, f"{DIM}{'─' * w}  同时写入 {len(segs) - done}/{len(segs)}{RESET}"]

    n = max(1, len(segs))
    ncol = 1 if n == 1 else (2 if n <= 4 else (3 if n <= 9 else 4))
    nrow = (n + ncol - 1) // ncol
    cellw = (w - (ncol - 1)) // ncol
    headroom = 3
    cellh = max(4, (h - headroom) // nrow - 1)

    for r in range(nrow):
        row_cells = segs[r * ncol:(r + 1) * ncol]
        if not row_cells:
            break
        titles, bodies = [], []
        for s in row_cells:
            col = COLS[(s["i"] - 1) % len(COLS)]
            mark = "✎" if s.get("state") == "writing" else "✓"
            titles.append(f"{col}{mark} 段{s['i']} {trunc(s.get('title',''), cellw - 12)}"
                          f" {DIM}{s.get('tokens',0)}t{RESET}")
            txt = s.get("text", "")
            if think and s.get("reasoning"):
                txt = f"{DIM}[思考] {s['reasoning']}{RESET}\n" + txt
            bodies.append(wrap_lines(txt, cellw - 1, cellh))
        out.append(" ".join(t.ljust(cellw + len(t) - dwidth(t)) for t in titles))
        for li in range(cellh):
            row = []
            for b in bodies:
                line = b[li] if li < len(b) else ""
                row.append(line + " " * max(0, cellw - dwidth(line)))
            out.append(" ".join(row))
        out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-file", default=str(ROOT / "results/live/state.json"))
    ap.add_argument("--interval", type=float, default=0.3)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--think", action="store_true", help="显示思考内容")
    args = ap.parse_args()
    path = Path(args.state_file)
    try:
        while True:
            w, h = shutil.get_terminal_size((100, 40))
            try:
                state = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                state = {}
            sys.stdout.write(render(state, args.think, w, h))
            sys.stdout.flush()
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        sys.stdout.write(RESET + "\n")


if __name__ == "__main__":
    main()
