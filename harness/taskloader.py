"""解析 tasks/{id}.md，只取出运行器需要的东西。

关键不变量（D10）：{{材料全文}} 只来自「## 原始材料」后的第一个围栏代码块，
逐字不变；「自检记录 / 分段方案 / 任务要求」等一律不进提示词。
"""
import re
from dataclasses import dataclass
from pathlib import Path

from .config import TASKS_DIR


@dataclass
class Task:
    task_id: str
    cls: str                # "A" | "B" | "C"
    n: int                  # 段数 N
    chain: int | None       # 链长（A 类为 None）
    max_tokens_a01: int
    max_tokens_a2: int
    material: str           # 逐字材料
    outline: str            # 大纲全文（题内固定）
    titles: list[str]       # 长度 == n
    path: Path


def _fence_after(text: str, header: str) -> str:
    m = re.search(re.escape(header) + r".*?```(.*?)```", text, re.S)
    if not m:
        raise ValueError(f"找不到小节 {header} 后的代码块")
    return m.group(1).strip("\n")


def load(task_id: str, tasks_dir: Path = TASKS_DIR) -> Task:
    path = tasks_dir / f"{task_id}.md"
    t = path.read_text(encoding="utf-8")

    cls = re.search(r"\*\*类别\*\*：\s*([ABC])", t).group(1)
    n = int(re.search(r"\*\*段数\*\*：\s*N\s*=\s*(\d+)", t).group(1))
    m_chain = re.search(r"\*\*链长\*\*：\s*(\d+|—)", t)
    chain = None if (not m_chain or m_chain.group(1) == "—") else int(m_chain.group(1))
    m_a = re.search(r"\*\*max_tokens（A0/A1）\*\*：\s*(\d+)", t)
    m_b = re.search(r"\*\*max_tokens（A2）\*\*：\s*(\d+)", t)
    if not m_a or not m_b:
        raise ValueError(f"{task_id}: 缺 max_tokens 声明")

    material = _fence_after(t, "## 原始材料")
    outline = _fence_after(t, "## 大纲标题列表").strip()
    titles = re.findall(r"部分(\d+)：\s*(.+)", outline)
    if len(titles) != n:
        raise ValueError(f"{task_id}: 大纲 {len(titles)} 条 != N={n}")
    ordered = [None] * n
    for idx, title in titles:
        ordered[int(idx) - 1] = title.strip()
    if any(x is None for x in ordered):
        raise ValueError(f"{task_id}: 大纲段号不连续")

    return Task(task_id=task_id, cls=cls, n=n, chain=chain,
                max_tokens_a01=int(m_a.group(1)), max_tokens_a2=int(m_b.group(1)),
                material=material, outline=outline, titles=ordered, path=path)


def all_ids(tasks_dir: Path = TASKS_DIR) -> list[str]:
    ids = []
    for c in "ABC":
        for i in range(1, 11):
            tid = f"{c}-{i:02d}"
            if (tasks_dir / f"{tid}.md").exists():
                ids.append(tid)
    return ids
