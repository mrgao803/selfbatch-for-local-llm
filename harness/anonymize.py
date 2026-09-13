"""匿名化：把三条件输出组成 pair 文件，顺序随机，映射写入不提交的 mapping.json。

03 §5【硬性】：提交给裁判的文件里不得出现任何能识别条件的字样。
"""
import json
import random
from pathlib import Path

from .config import RESULTS_DIR

RAW = RESULTS_DIR / "raw"
PAIRS = RESULTS_DIR / "pairs"
MAPPING = RESULTS_DIR / "mapping.json"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8").strip()


def compose_segments(task, task_id: str, rtype: str, variant: str | None, round_):
    """把 N 段拼成一份文档，格式与融合提示词里模型看到的一致。

    运行器落盘路径是 raw/{task}/{rtype}/{round}/{seg}.txt，其中 rtype 已含变体
    （如 A2-V1），所以这里不再另加变体目录。
    """
    if variant is not None:
        assert rtype.endswith(variant), f"rtype={rtype} 与 variant={variant} 不一致"
    parts = []
    for i in range(1, task.n + 1):
        body = _read(RAW / task_id / rtype / str(round_) / f"{i}.txt")
        parts.append(f"【部分{i}：{task.titles[i - 1]}】\n{body}")
    return "\n\n".join(parts)


def a0_text(task_id: str) -> str:
    return _read(RAW / task_id / "A0" / "0" / "1.txt")


def build_pair_file(task, material: str, doc_a: str, doc_b: str, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# 原始材料\n\n" + material + "\n\n---\n\n# 版本一\n\n" + doc_a +
        "\n\n---\n\n# 版本二\n\n" + doc_b + "\n", encoding="utf-8")


def build_pairs(tasks: list, seeds: list[int], variants: list[str], final_round: int,
                compare=("A0", "A2"), rng_seed: int = 20260912) -> dict:
    """默认比较 A0 与 A2 各变体的最后一轮；每个 (题, seed, 变体) 出一对。"""
    rng = random.Random(rng_seed)
    mapping = {}
    idx = 0
    for task in tasks:
        for seed in seeds:
            for v in variants:
                if compare == ("A0", "A2"):
                    doc_a = a0_text(task.task_id)
                    doc_b = compose_segments(task, task.task_id, f"A2-{v}", v, final_round)
                    label_a, label_b = "A0", f"A2-{v}-r{final_round}"
                elif compare == ("A0", "A1"):
                    doc_a = a0_text(task.task_id)
                    doc_b = compose_segments(task, task.task_id, "A1", None, 0)
                    label_a, label_b = "A0", "A1"
                else:
                    raise ValueError(f"未支持的比较 {compare}")
                idx += 1
                name = f"pair-{task.task_id}-{idx:03d}.md"
                if rng.random() < 0.5:
                    v1, v2 = doc_a, doc_b
                    map_v1, map_v2 = label_a, label_b
                else:
                    v1, v2 = doc_b, doc_a
                    map_v1, map_v2 = label_b, label_a
                build_pair_file(task, task.material, v1, v2, PAIRS / name)
                mapping[name] = {"task_id": task.task_id, "seed": seed,
                                 "版本一": map_v1, "版本二": map_v2}
    MAPPING.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    return mapping
