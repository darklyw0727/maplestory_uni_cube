"""
所有座標皆以「參考解析度」(ref_width x ref_height，對應 plan.md 附圖 step1~step7.1
的視窗 client area 尺寸) 為基準，記錄在 config.json 的 "regions" 區塊(單位是該
參考解析度下的像素，不是比例)。執行時依實際擷取到的視窗 client area 尺寸等比例
換算，藉此對視窗大小的些微差異有一定容錯度。

預設值是用附圖中的紅框(標示需要操作/讀取的區域)以程式偵測紅色像素邊界取得，
非人工肉眼估計。若遊戲改版、UI位置跑掉，或想在不同解析度下重新校正，
可直接修改 config.json 的 regions 區塊，不需要改程式碼。

對應遊戲畫面(見 plan.md)：
- step1~step3 是「潛在能力」大面板：確認目前選擇的貨幣(currency_label_box)、
  按下大面板的「重新設定」(reset_button)開始使用結合方塊、彈出的確認彈窗
  「確認」按鈕(reset_confirm_button)。這一步整個流程只需要做一次，用來叫出
  下面 step4~step7.1 的小視窗。
- step4~step7.1 是使用後跳出的「結合方塊」小視窗：固定顯示3個潛能
  (potential_list_box / potential_row_y_bounds / potential_text_x_offset)，
  其中一個底色會不同代表被選取；「重新選擇」(reselect_button)換選取哪一格
  (不改內容)、「重新設定」(reset_selected_button)重骰被選取那格的內容，兩者
  按下後都會彈出確認彈窗(reselect_confirm_button / reset_selected_confirm_button)，
  且都會消耗1個結合方塊。最後用「離開」(leave_button)結束。
"""

DEFAULT_REGIONS = {
    "ref_width": 1376,
    "ref_height": 759,
    # step1: 潛在能力大面板「方塊」分頁，「使用貨幣」欄位中間的貨幣名稱文字區域
    "currency_label_box": [764, 481, 832, 507],
    "currency_expected_text": "結合方塊",
    # step2: 大面板的「重新設定」按鈕(整個流程只會點這一次，用來叫出小視窗)
    "reset_button": [797, 704],
    # step3: 按下後彈出確認彈窗的「確認」按鈕
    "reset_confirm_button": [645, 453],
    # step4/step5: 小視窗固定顯示的3個潛能，整塊清單區域，含每一列的上下邊界
    # (共4條分隔線: 3列的上緣+最後一列下緣)
    "potential_list_box": [583, 319, 802, 400],
    "potential_row_y_bounds": [319, 346, 373, 400],
    # 潛能文字起始位置，相對於整列左緣的 x 偏移 (跳過等級圖示)
    "potential_text_x_offset": 29,
    # step6: 「重新選擇」按鈕(換選取哪一格，不改內容)
    "reselect_button": [589, 622],
    # step6_1: 按下後彈出確認彈窗的「確認」按鈕
    "reselect_confirm_button": [647, 428],
    # step7: 「重新設定」按鈕(重骰被選取那格的內容)
    "reset_selected_button": [786, 624],
    # step7_1: 按下後彈出確認彈窗的「確認」按鈕
    "reset_selected_confirm_button": [642, 413],
    # 「離開」按鈕
    "leave_button": [774, 660],
}


class Regions:
    """把 config.json 的 regions 區塊(參考解析度像素)轉成執行時要用的比例(0~1)。"""

    def __init__(self, data: dict):
        merged = {**DEFAULT_REGIONS, **data}
        ref_w = merged["ref_width"]
        ref_h = merged["ref_height"]

        def box(key):
            x0, y0, x1, y1 = merged[key]
            if x1 <= x0 or y1 <= y0:
                raise ValueError(
                    f"regions.{key} 的座標無效: {merged[key]}。"
                    f"必須是 [x0, y0, x1, y1] 且 x1>x0、y1>y0(框需要有實際寬高)，"
                    f"請用 tools/locate.py 重新分別記錄左上角與右下角兩個不同的點。"
                )
            return (x0 / ref_w, y0 / ref_h, x1 / ref_w, y1 / ref_h)

        def point(key):
            x, y = merged[key]
            return (x / ref_w, y / ref_h)

        def y_bounds(key):
            values = merged[key]
            if any(b <= a for a, b in zip(values, values[1:])):
                raise ValueError(
                    f"regions.{key} 的分隔線座標無效: {values}。"
                    f"必須由小到大嚴格遞增(每一列都要有實際高度)，請用 tools/locate.py 重新校正。"
                )
            return [y / ref_h for y in values]

        self.currency_label_box = box("currency_label_box")
        self.currency_expected_text = merged["currency_expected_text"]
        self.reset_button = point("reset_button")
        self.reset_confirm_button = point("reset_confirm_button")
        self.potential_list_box = box("potential_list_box")
        self.potential_row_y_bounds = y_bounds("potential_row_y_bounds")
        self.potential_text_x_offset = merged["potential_text_x_offset"] / ref_w
        self.reselect_button = point("reselect_button")
        self.reselect_confirm_button = point("reselect_confirm_button")
        self.reset_selected_button = point("reset_selected_button")
        self.reset_selected_confirm_button = point("reset_selected_confirm_button")
        self.leave_button = point("leave_button")


def scale_point(point_frac, client_w, client_h):
    fx, fy = point_frac
    return int(round(fx * client_w)), int(round(fy * client_h))


def scale_box(box_frac, client_w, client_h):
    x0, y0, x1, y1 = box_frac
    return (
        int(round(x0 * client_w)),
        int(round(y0 * client_h)),
        int(round(x1 * client_w)),
        int(round(y1 * client_h)),
    )


def scale_x(x_frac, client_w):
    return int(round(x_frac * client_w))


def scale_y(y_frac, client_h):
    return int(round(y_frac * client_h))
