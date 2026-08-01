import logging
import time
from dataclasses import dataclass

from . import ocr, regions
from .config import Config
from .window import GameWindow

log = logging.getLogger("auto_shine_cube")

# 判斷「哪一格潛能目前被選取」時，被選取那格的底色飽和度必須比另外兩格明顯更高，
# 差距至少要超過這個門檻才視為判斷可信；差距太小只印警告，仍以飽和度最高的那格
# 為準(不中止流程，交由使用者從log自行確認畫面狀態是否正確)。
HIGHLIGHT_SATURATION_MARGIN = 0.15


@dataclass
class PotentialRow:
    index: int  # 0=上, 1=中, 2=下(畫面上固定的位置，不會因重骰而改變順序)
    name: str  # 潛能名稱，例如「魔法攻擊力」
    value: object  # 百分比數值(int)，讀不到時為 None

    @property
    def display(self) -> str:
        return f"{self.name} +{self.value}%" if self.value is not None else self.name


class AbortError(RuntimeError):
    pass


def _combo_target(combo):
    """回傳 combo(固定3槽位，恰好1個非空字串)的 (目標位置index, 目標潛能文字)。"""
    for idx, text in enumerate(combo):
        if text:
            return idx, text
    return None, None  # 理論上不會發生，Config 已驗證每組必有1個非空字串


def _saturation(rgb) -> float:
    r, g, b = (c / 255.0 for c in rgb[:3])
    mx, mn = max(r, g, b), min(r, g, b)
    return 0.0 if mx == 0 else (mx - mn) / mx


class Controller:
    def __init__(self, config: Config, window: GameWindow, stop_event=None):
        self.cfg = config
        self.win = window
        self.used_cubes = 0
        self.stop_event = stop_event  # threading.Event，供GUI等外部要求提早停止(可為None)

    # ---------- 基礎工具 ----------

    def _wait(self, sec=None):
        time.sleep(sec if sec is not None else self.cfg.click_delay_sec)

    def _click(self, point_frac):
        w, h = self.win.client_size()
        x, y = regions.scale_point(point_frac, w, h)
        log.debug("click at client(%d, %d)", x, y)
        if not self.cfg.dry_run:
            self.win.click(x, y)
        self._wait()

    # ---------- 畫面讀取 ----------

    def _read_currency_label(self) -> str:
        img = self.win.screenshot()
        w, h = img.size
        box = regions.scale_box(self.cfg.regions.currency_label_box, w, h)
        raw = ocr.read_row_text(img.crop(box))
        return ocr.extract_name(raw)

    def read_potentials(self):
        """讀取目前顯示的3個潛能，並判斷哪一格目前被選取(底色飽和度最高的那格)。

        回傳 (rows: list[PotentialRow] 長度固定3, highlighted_index: int 0~2)。
        """
        img = self.win.screenshot()
        w, h = img.size
        x0, y0, x1, y1 = regions.scale_box(self.cfg.regions.potential_list_box, w, h)
        text_x0 = x0 + regions.scale_x(self.cfg.regions.potential_text_x_offset, w)
        y_bounds = [regions.scale_y(y, h) for y in self.cfg.regions.potential_row_y_bounds]

        rows = []
        saturations = []
        for i in range(3):
            ry0, ry1 = y_bounds[i], y_bounds[i + 1]
            text_row = img.crop((text_x0, ry0, x1, ry1))
            name, value = ocr.split_name_value(ocr.read_row_text(text_row))
            rows.append(PotentialRow(index=i, name=name, value=value))

            sample_x = x0 + int(round((x1 - x0) * 0.92))
            sample_y = (ry0 + ry1) // 2
            saturations.append(_saturation(img.getpixel((sample_x, sample_y))))

        highlighted = max(range(3), key=lambda i: saturations[i])
        others = sorted(s for i, s in enumerate(saturations) if i != highlighted)
        if saturations[highlighted] - others[-1] < HIGHLIGHT_SATURATION_MARGIN:
            log.warning(
                "無法明確判斷目前被選取的潛能格(3格底色飽和度=%s)，暫定為第%d格，"
                "若實際判斷錯誤請確認 potential_list_box/potential_row_y_bounds 座標是否需要用"
                "tools/locate.py 重新校正",
                [round(s, 2) for s in saturations], highlighted + 1,
            )
        return rows, highlighted

    # ---------- 流程各步驟 ----------

    def verify_currency_selected(self):
        # 完全辨識不到文字(代表面板可能根本沒開/擷取錯位置)才視為致命錯誤，
        # 辨識到但相似度偏低則只警告、不中止流程，留給使用者自行判斷。
        label = self._read_currency_label()
        expected = self.cfg.regions.currency_expected_text
        score = ocr.match_score(label, expected)
        if score < 0.15:
            raise AbortError(
                f"讀不到使用貨幣欄位內容(讀到「{label}」)，請確認已開啟潛在能力面板的方塊分頁。"
            )
        if score < 0.4:
            log.warning(
                "使用貨幣欄位讀到「%s」，與「%s」相似度僅%.2f，"
                "若目前面板選的不是結合方塊請自行中止程式(Ctrl+C)",
                label, expected, score,
            )
        else:
            log.info("已確認目前使用貨幣為結合方塊 (相似度%.2f)", score)

    def click_initial_reset(self):
        log.debug("點擊大面板「重新設定」(開始使用結合方塊，這個步驟整個流程只做一次)")
        self._click(self.cfg.regions.reset_button)
        self._wait(self.cfg.post_action_wait_sec)
        log.debug("點擊確認彈窗「確認」")
        self._click(self.cfg.regions.reset_confirm_button)
        self._wait(self.cfg.post_action_wait_sec)
        self.used_cubes += 1

    def _find_matching_combo(self, highlighted_index: int):
        """依優先權由高到低，找出「目標位置＝目前被選取位置」的第一個組合。

        回傳 (combo, target_text)；找不到時回傳 (None, None)。"""
        for combo in self.cfg.target_potentials:
            idx, target = _combo_target(combo)
            if idx == highlighted_index:
                return combo, target
        return None, None

    def is_goal_met(self, rows) -> bool:
        """rows(固定3格，依畫面上的位置)只要滿足 target_potentials 任一組合就算達成：
        該組合唯一的目標位置上，畫面實際潛能需與目標潛能文字相符(位置必須對應)。"""
        threshold = self.cfg.ocr_match_threshold
        for combo in self.cfg.target_potentials:
            idx, target = _combo_target(combo)
            row = rows[idx]
            if ocr.potential_matches(row.name, row.value, target, threshold):
                return True
        return False

    def click_reselect(self):
        log.debug("點擊「重新選擇」")
        self._click(self.cfg.regions.reselect_button)
        self._wait(self.cfg.post_action_wait_sec)
        log.debug("點擊確認彈窗「確認」")
        self._click(self.cfg.regions.reselect_confirm_button)
        self._wait(self.cfg.post_action_wait_sec)
        self.used_cubes += 1

    def click_reset_selected(self):
        log.debug("點擊「重新設定」(重骰被選取的潛能)")
        self._click(self.cfg.regions.reset_selected_button)
        self._wait(self.cfg.post_action_wait_sec)
        log.debug("點擊確認彈窗「確認」")
        self._click(self.cfg.regions.reset_selected_confirm_button)
        self._wait(self.cfg.post_action_wait_sec)
        self.used_cubes += 1

    def click_leave(self):
        log.debug("點擊「離開」")
        self._click(self.cfg.regions.leave_button)

    # ---------- 主流程 ----------

    def run(self):
        self.win.find()
        self.win.ensure_foreground()

        self.verify_currency_selected()
        self.click_initial_reset()

        while True:
            if self.stop_event is not None and self.stop_event.is_set():
                log.info("收到停止要求，點擊離開結束")
                self.click_leave()
                return "stopped"

            rows, highlighted = self.read_potentials()
            log.info(
                "目前3個潛能(第%d格被選取): %s",
                highlighted + 1, [r.display for r in rows],
            )

            if self.is_goal_met(rows):
                log.info("已達成目標潛能，點擊離開結束")
                self.click_leave()
                return "success"

            if self.cfg.max_cubes and self.used_cubes >= self.cfg.max_cubes:
                log.info("已達方塊使用上限(%d)，點擊離開結束", self.cfg.max_cubes)
                self.click_leave()
                return "limit_reached"

            combo, target = self._find_matching_combo(highlighted)
            if combo is not None:
                log.info("第%d格是目標槽位(%s)，點擊「重新設定」重骰", highlighted + 1, target)
                self.click_reset_selected()
            else:
                log.info("第%d格不是任何目標槽位，點擊「重新選擇」換一格", highlighted + 1)
                self.click_reselect()

            log.info("已使用方塊，累計使用 %d 個", self.used_cubes)
