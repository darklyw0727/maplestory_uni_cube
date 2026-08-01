"""
用 plan.md 附帶的 step*.png 參考截圖，驗證OCR辨識+選取/比對邏輯的正確性。
不需要開啟遊戲即可執行: python -m pytest tests/ -v

step*.png 是完整桌面截圖(不是乾淨的視窗client area截圖)，所以測試時會先裁切到
遊戲視窗的 client area(對應 DEFAULT_REGIONS 的 ref_width/ref_height)，模擬
GameWindow.screenshot() 實際回傳的畫面。
"""
from pathlib import Path

import pytest
from PIL import Image

from src import ocr
from src.config import Config
from src.controller import Controller, _combo_target
from src.regions import DEFAULT_REGIONS, Regions

ROOT = Path(__file__).resolve().parent.parent

try:
    ocr.configure("chinese_cht")
except Exception as e:  # pragma: no cover - 環境沒裝好時直接略過整份測試
    pytest.skip(f"PaddleOCR 初始化失敗，略過OCR相關測試: {e}", allow_module_level=True)

REGIONS = Regions({})  # 全部使用預設校正值

# step*.png 裡遊戲視窗 client area 相對於整張截圖左上角的位置，範圍剛好等於
# DEFAULT_REGIONS 的 ref_width x ref_height。
CLIENT_BOX_IN_SCREENSHOT = (44, 81, 44 + DEFAULT_REGIONS["ref_width"], 81 + DEFAULT_REGIONS["ref_height"])


def _make_controller(target_potentials):
    """target_potentials: 多組允許組合的list，每組3個字串(恰好1個非空)，例如
    [["無視怪物防禦率", "", ""]]；為了方便測試呼叫，傳入單一組合(flat list)時
    會自動包成只有一組的巢狀list。"""
    if target_potentials and isinstance(target_potentials[0], str):
        target_potentials = [target_potentials]
    cfg = Config(
        target_potentials=target_potentials,
        log_lv="info",
        max_cubes=0,
        window_title="x",
        ocr_lang="chinese_cht",
        ocr_match_threshold=0.55,
        click_delay_sec=0,
        post_action_wait_sec=0,
        dry_run=True,
        stop_hotkey="f8",
        regions=REGIONS,
    )
    ctrl = Controller.__new__(Controller)
    ctrl.cfg = cfg
    return ctrl


def _screenshot(img_path):
    return Image.open(ROOT / "plan" / img_path).crop(CLIENT_BOX_IN_SCREENSHOT)


@pytest.fixture(scope="module")
def step4_state():
    """step4.png: 3個潛能，「無視怪物防禦率 +30%」(第1格)底色為橘色、目前被選取。"""
    ctrl = _make_controller(["不影響讀取用的佔位字串", "", ""])

    class FakeWindow:
        def screenshot(self_inner):
            return _screenshot("step4.png")

    ctrl.win = FakeWindow()
    return ctrl.read_potentials()


def test_reads_three_potentials(step4_state):
    rows, _ = step4_state
    expected = [("無視怪物防禦率", 30), ("魔法攻擊力", 13), ("魔法攻擊力", 13)]
    assert len(rows) == 3
    for row, (name, value) in zip(rows, expected):
        score = ocr.match_score(row.name, name)
        assert score >= 0.55, f"row{row.index} name={row.name!r} expected~={name!r} score={score:.2f}"
        assert row.value == value, f"row{row.index} value={row.value!r} expected={value}"


def test_detects_highlighted_row(step4_state):
    _, highlighted = step4_state
    assert highlighted == 0  # 「無視怪物防禦率」那格底色是橘色，與其他2格明顯不同


def test_combo_target_extracts_position_and_text():
    assert _combo_target(["無視怪物防禦率", "", ""]) == (0, "無視怪物防禦率")
    assert _combo_target(["", "魔法攻擊力 +13%", ""]) == (1, "魔法攻擊力 +13%")
    assert _combo_target(["", "", "物理攻擊力"]) == (2, "物理攻擊力")


def test_is_goal_met_name_only_at_correct_position(step4_state):
    rows, _ = step4_state
    ctrl = _make_controller(["無視怪物防禦率", "", ""])  # 目標位置=第1格，剛好對上
    assert ctrl.is_goal_met(rows) is True


def test_is_goal_met_requires_exact_value_when_specified(step4_state):
    rows, _ = step4_state
    ctrl_ok = _make_controller(["無視怪物防禦率 +30%", "", ""])
    assert ctrl_ok.is_goal_met(rows) is True

    ctrl_fail = _make_controller(["無視怪物防禦率 +40%", "", ""])
    assert ctrl_fail.is_goal_met(rows) is False


def test_is_goal_met_requires_correct_position(step4_state):
    rows, _ = step4_state
    # 「無視怪物防禦率 +30%」實際在第1格，但目標寫在第2格，位置對不上不算達成。
    ctrl = _make_controller(["", "無視怪物防禦率 +30%", ""])
    assert ctrl.is_goal_met(rows) is False


def test_is_goal_met_if_any_combo_matches(step4_state):
    rows, _ = step4_state
    ctrl = _make_controller([
        ["物理攻擊力", "", ""],           # 這組對不上(位置1不是物理攻擊力)
        ["無視怪物防禦率 +30%", "", ""],  # 這組對得上
    ])
    assert ctrl.is_goal_met(rows) is True


def test_is_goal_met_when_no_combo_matches(step4_state):
    rows, _ = step4_state
    ctrl = _make_controller([
        ["物理攻擊力", "", ""],
        ["", "STR", ""],
    ])
    assert ctrl.is_goal_met(rows) is False


def test_find_matching_combo_by_position(step4_state):
    _, highlighted = step4_state  # 0
    ctrl = _make_controller([
        ["", "", "STR"],   # 目標位置2，跟目前被選取的位置0對不上
        ["DEX", "", ""],   # 目標位置0，跟目前被選取的位置0吻合
    ])
    combo, target = ctrl._find_matching_combo(highlighted)
    assert target == "DEX"


def test_find_matching_combo_priority_order(step4_state):
    _, highlighted = step4_state  # 0
    ctrl = _make_controller([
        ["A", "", ""],  # 優先權較高，目標位置也是0
        ["B", "", ""],  # 優先權較低，目標位置也是0
    ])
    combo, target = ctrl._find_matching_combo(highlighted)
    assert target == "A"


def test_find_matching_combo_none_when_position_not_targeted(step4_state):
    _, highlighted = step4_state  # 0
    ctrl = _make_controller([
        ["", "STR", ""],
        ["", "", "DEX"],
    ])
    combo, target = ctrl._find_matching_combo(highlighted)
    assert combo is None and target is None


def test_config_rejects_combo_without_exactly_one_target():
    with pytest.raises(ValueError):
        _make_controller(["STR", "INT", "DEX"])  # 3個非空
    with pytest.raises(ValueError):
        _make_controller(["", "", ""])  # 0個非空
