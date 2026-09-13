"""运行配置。默认值一律取自 handoff/ 冻结文档，不在此处发挥。"""
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
# 真实结果的落盘根；mock/试跑可用 EXPERIMENT_RESULTS_DIR 整体隔离
RESULTS_DIR = Path(os.environ.get("EXPERIMENT_RESULTS_DIR", str(ROOT / "results")))

# 04-prompt-spec.md §一 全局参数
TEMPERATURE = 0.7
TOP_P = 0.9
SEEDS_DEFAULT = [101, 202, 303]


@dataclass
class ServeConfig:
    base_url: str = "http://127.0.0.1:8003"
    model: str = "qwen38-27b"
    # D13：操作员裁定走原生 completions。
    endpoint: str = "completions"          # "completions" | "chat"
    # D12：操作员裁定保持模型默认（不关思考）。completions 下该参数无效。
    enable_thinking: bool | None = None
    temperature: float = TEMPERATURE
    top_p: float = TOP_P
    timeout: int = 1800
    max_retries: int = 3


@dataclass
class RunConfig:
    seeds: list[int] = field(default_factory=lambda: list(SEEDS_DEFAULT))
    variants: list[str] = field(default_factory=lambda: ["V1", "V2", "V3"])
    rounds: int = 8                        # 03 §4.5【硬性】跑满 8 轮
    tasks: list[str] | None = None         # None = 全部
    # 04 §六：试点用题内固定大纲；正式题按 04 应由 R-OUT 生成。
    # 本任务集大纲在出题时已给定（02 §3.4），故默认用题内大纲（记录为 D16）。
    outline_source: str = "task_file"      # "task_file" | "model"
    emit_live: bool = True
    mock: bool = False                     # True = 不调模型，用假数据跑通管线
