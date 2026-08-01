"""
座標校正共用邏輯 —— CLI (tools/locate.py) 與 PyQt GUI 共用同一份步驟定義與底層
座標讀取工具，避免兩邊各自維護一份步驟順序而日後又對不上。

STEPS 是校正的完整步驟清單，每一項為 (regions欄位key, 種類, 說明文字, 種類專屬參數)：
- "point"：單一點，直接記錄目前滑鼠位置。
- "box"：矩形框，需連續記錄左上角、右下角兩個點。
- "lines"：N條分隔線的 y 座標，需依序記錄 N 個點(嚴格由上到下遞增)，種類專屬
  參數是 N。
- "text_offset"：特殊欄位，記錄的點會換算成與 potential_list_box 左緣的x偏移量。
"""
import win32gui
import pyautogui

from .regions import DEFAULT_REGIONS

STEPS = [
    ("currency_label_box", "box",
     "step1: 潛在能力大面板「方塊」分頁，『使用貨幣』文字欄位(顯示結合方塊那格)", None),
    ("reset_button", "point", "step2: 同一畫面，大面板的『重新設定』按鈕(整個流程只會點這一次)", None),
    ("reset_confirm_button", "point", "step3: 按下後彈出的確認彈窗，『確認』按鈕(按下後會叫出小視窗)", None),
    ("potential_list_box", "box", "step4: 小視窗固定顯示的3個潛能，整塊清單區域", None),
    ("potential_row_y_bounds", "lines",
     "step4: 3個潛能清單，逐條分隔線(由上到下，共4條: 3列的上緣+最後一列下緣)", 4),
    ("potential_text_x_offset", "text_offset",
     "step4: 任一列『文字』開頭處(跳過左邊等級圖示，移到潛能名稱第一個字的左緣)", None),
    ("reselect_button", "point", "step6: 小視窗的『重新選擇』按鈕(換選取哪一格，不改內容)，請定位按鈕的「右邊1/2處」", None),
    ("reselect_confirm_button", "point", "step6_1: 按下後彈出的確認彈窗，『確認』按鈕", None),
    ("reset_selected_button", "point", "step7: 小視窗的『重新設定』按鈕(重骰被選取那格的內容)請定位按鈕的「左邊1/2處」", None),
    ("reset_selected_confirm_button", "point", "step7_1: 按下後彈出的確認彈窗，『確認』按鈕", None),
    ("leave_button", "point", "小視窗的『離開』按鈕，請定位按鈕的「左邊1/2處」", None),
]

STEP_BY_KEY = {key: (key, kind, label, param) for key, kind, label, param in STEPS}


def find_window(title):
    return win32gui.FindWindow(None, title) or None


def client_rect_on_screen(hwnd):
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    left, top = win32gui.ClientToScreen(hwnd, (left, top))
    right, bottom = win32gui.ClientToScreen(hwnd, (right, bottom))
    return left, top, right, bottom


def current_ref_point(hwnd, ref_w, ref_h):
    """回傳目前滑鼠在「參考解析度」下的座標 (rx, ry)；滑鼠不在視窗範圍內時回傳 None。"""
    sx, sy = pyautogui.position()
    left, top, right, bottom = client_rect_on_screen(hwnd)
    cw, ch = right - left, bottom - top
    cx, cy = sx - left, sy - top
    if cw <= 0 or ch <= 0 or not (0 <= cx <= cw and 0 <= cy <= ch):
        return None
    return round(cx / cw * ref_w), round(cy / ch * ref_h)


def merge_regions(config_data: dict) -> dict:
    """取得 config_data["regions"]，缺項用 DEFAULT_REGIONS 補齊，並寫回 config_data。"""
    config_data.setdefault("regions", {})
    merged = {**DEFAULT_REGIONS, **config_data["regions"]}
    config_data["regions"] = merged
    return merged


class WizardState:
    """驅動一次校正流程(可以是全部步驟，或篩選後只有其中一步)，不綁定任何UI框架。

    使用方式：
        state = WizardState(hwnd, ref_w, ref_h, regions, steps)
        while not state.finished:
            顯示 state.prompt()
            顯示 state.current_position() (即時更新用)
            使用者觸發「記錄」時 -> ok, err = state.capture()
            使用者觸發「跳過」時 -> state.skip()
    """

    def __init__(self, hwnd, ref_w, ref_h, regions: dict, steps=None):
        self.hwnd = hwnd
        self.ref_w = ref_w
        self.ref_h = ref_h
        self.regions = regions
        self.steps = list(steps) if steps is not None else list(STEPS)
        self.step_idx = 0
        self.sub_idx = 0
        self._box_tl = None
        self._lines = []

    @property
    def finished(self) -> bool:
        return self.step_idx >= len(self.steps)

    @property
    def current_step(self):
        return self.steps[self.step_idx]

    def prompt(self) -> str:
        key, kind, label, param = self.current_step
        if kind == "box":
            return label + ("（請移到左上角）" if self.sub_idx == 0 else "（請移到右下角）")
        if kind == "lines":
            return label + f"（第 {self.sub_idx + 1}/{param} 條分隔線）"
        return label

    def current_position(self):
        return current_ref_point(self.hwnd, self.ref_w, self.ref_h)

    def capture(self):
        """在目前滑鼠位置記錄一個點。回傳 (this_step_done: bool, error: str|None)。"""
        key, kind, label, param = self.current_step
        pt = self.current_position()
        if pt is None:
            return False, "滑鼠不在遊戲視窗範圍內，請確認遊戲視窗位置後再試一次"

        if kind == "point":
            self.regions[key] = list(pt)
            self._advance_step()
            return True, None

        if kind == "text_offset":
            box = self.regions.get("potential_list_box")
            self.regions[key] = pt[0] - box[0]
            self._advance_step()
            return True, None

        if kind == "box":
            if self.sub_idx == 0:
                self._box_tl = pt
                self.sub_idx = 1
                return False, None
            if not (pt[0] > self._box_tl[0] and pt[1] > self._box_tl[1]):
                return False, "右下角的x、y都必須比左上角大(框需要有實際寬高)，請重新移到右下角"
            self.regions[key] = [self._box_tl[0], self._box_tl[1], pt[0], pt[1]]
            self._advance_step()
            return True, None

        if kind == "lines":
            if self._lines and pt[1] <= self._lines[-1]:
                return False, "這個位置沒有比上一條分隔線更低，請由上往下依序移動"
            self._lines.append(pt[1])
            self.sub_idx += 1
            if self.sub_idx >= param:
                self.regions[key] = list(self._lines)
                self._advance_step()
                return True, None
            return False, None

        raise ValueError(f"未知的校正種類: {kind}")

    def skip(self):
        """跳過目前這一整項(保留 regions 原本的值)，進入下一項。"""
        self._advance_step()

    def _advance_step(self):
        self.step_idx += 1
        self.sub_idx = 0
        self._box_tl = None
        self._lines = []
