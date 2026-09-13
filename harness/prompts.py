"""提示词拼装 —— 逐字取自 handoff/04-prompt-spec.md §四，一个字符都不改。

替换位只有 {{材料全文}} {{N}} {{大纲全文}} {{i}} {{标题i}} {{全部段落全文}}，
以及三个变体的规则行。
"""
from .taskloader import Task

# ---- R-OUT：生成大纲（04 §四） ----
R_OUT = """以下是原始材料：

{material}

请为一份 {n} 个部分的文档列出大纲。每个部分一行，格式为「部分N：标题」。
只输出大纲，不要输出其他内容。"""

# ---- R-A0：基线，一次写完 ----
R_A0 = """以下是原始材料：

{material}

请基于以上材料，写一份完整的文档，共 {n} 个部分：
{outline}

要求：直接输出文档正文，不要输出其他内容。"""

# ---- R-A1：分段生成第 i 段 ----
# 【硬性】本提示词里不得出现任何其他部分的正文。只有材料 + 大纲（标题级）。
R_A1 = """以下是原始材料：

{material}

这是文档的大纲：
{outline}

请只写其中的【部分{i}】，标题为「{title}」。
直接输出该部分正文，不要重复标题，不要写其他部分。"""

# ---- R-A2：融合修订（三个变体只差规则那一行） ----
R_A2 = """以下是一份文档的全部 {n} 个部分：

{all_parts}

请修订【部分{i}】，使其与其他部分在术语、事实、数字、时间线上保持一致。

规则：{rule}
只输出修订后的【部分{i}】正文，不要输出其他内容。"""

RULES = {
    "V1": "只做必要的修改。不需要改的地方保持原样。",
    "V2": "检查是否存在不一致之处，并修正它们。",
    "V3": "仔细审查该部分与其余所有部分的衔接，全面改进一致性。",
}


def all_parts(titles: list[str], bodies: list[str]) -> str:
    """{{全部段落全文}} 的精确格式：段号升序、段间空一行、全角冒号、`部分`后无空格。"""
    if len(titles) != len(bodies):
        raise ValueError("标题数与正文数不一致")
    blocks = [f"【部分{i}：{t}】\n{b}" for i, (t, b) in enumerate(zip(titles, bodies), 1)]
    return "\n\n".join(blocks)


def r_out(task: Task) -> str:
    return R_OUT.format(material=task.material, n=task.n)


def r_a0(task: Task, outline: str) -> str:
    return R_A0.format(material=task.material, n=task.n, outline=outline)


def r_a1(task: Task, outline: str, i: int) -> str:
    return R_A1.format(material=task.material, outline=outline,
                       i=i, title=task.titles[i - 1])


def r_a2(task: Task, variant: str, titles: list[str], bodies: list[str], i: int) -> str:
    if variant not in RULES:
        raise ValueError(f"未知变体 {variant}")
    return R_A2.format(n=task.n, all_parts=all_parts(titles, bodies),
                       i=i, rule=RULES[variant])
