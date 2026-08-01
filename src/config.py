import json
from dataclasses import dataclass, field
from pathlib import Path

from .regions import Regions


@dataclass
class Config:
    target_potentials: list
    log_lv: str
    max_cubes: int
    window_title: str
    ocr_lang: str
    ocr_match_threshold: float
    click_delay_sec: float
    post_action_wait_sec: float
    dry_run: bool
    stop_hotkey: str
    regions: Regions

    def __post_init__(self):
        # target_potentials 是多組「允許的目標組合」，每組固定3個槽位，依序對應畫面上
        # 固定的上/中/下位置。每組必須恰好1個非空字串(2個空字串)：非空字串代表「想讓
        # 這個位置變成這個潛能」，因為畫面每一輪只會有1格被選取、只能針對那1格重骰。
        # 只要最終3個潛能在該位置符合其中任一組合，就算達成目標。
        if not self.target_potentials:
            raise ValueError("target_potentials 至少需要一組")
        for combo in self.target_potentials:
            if len(combo) > 3:
                raise ValueError(f"target_potentials 每組最多只能設定3個字串，收到: {combo}")
            while len(combo) < 3:
                combo.append("")
            non_empty = [s for s in combo if s]
            if len(non_empty) != 1:
                raise ValueError(
                    f"target_potentials 每組必須恰好有1個非空字串(2個空字串)，收到: {combo}。"
                    f"每組代表「畫面上固定的某個位置」想要的潛能，因為每一輪只能針對被選取的"
                    f"那1格重骰，無法同時鎖定2個以上的位置。"
                )


def load_config(path: str = "config.json") -> Config:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data.pop("// 使用說明", None)
    return Config(
        target_potentials=[list(combo) for combo in data["target_potentials"]],
        log_lv=str(data["log_lv"]),
        max_cubes=int(data.get("max_cubes", 0)),
        window_title=data.get("window_title", "貓貓TMS"),
        ocr_lang=data.get("ocr_lang", "chinese_cht"),
        ocr_match_threshold=float(data.get("ocr_match_threshold", 0.55)),
        click_delay_sec=float(data.get("click_delay_sec", 0.35)),
        post_action_wait_sec=float(data.get("post_action_wait_sec", 0.6)),
        dry_run=bool(data.get("dry_run", False)),
        stop_hotkey=data.get("stop_hotkey", "ctrl+f2"),
        regions=Regions(data.get("regions", {})),
    )
