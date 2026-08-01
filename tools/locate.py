"""
互動式座標校正工具：依序引導你在遊戲畫面上對應位置移動滑鼠、按 Enter 記錄，
不需要自己輸入名稱，每記錄一項就立刻寫回 config.json 的 regions 區塊。

用法:
    python tools/locate.py [--config config.json]

操作方式:
    程式會照 currency_label_box -> ... -> leave_button 的順序，
    逐項提示你「遊戲畫面該停在哪一步」、「滑鼠要移到哪裡」。
    - 移到定點後直接按 Enter：記錄並寫入 config.json，自動進入下一項。
    - 輸入 s 再 Enter：跳過這一項，保留 config.json 原本的值。
    - 輸入 q 再 Enter：結束校正(已記錄的項目不會遺失)。
"""
import argparse
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import calibration
from src.window import ensure_dpi_aware

ensure_dpi_aware()


class Quit(Exception):
    pass


def live_loop(hwnd, ref_w, ref_h, stop_event, pause_event):
    while not stop_event.is_set():
        if not pause_event.is_set():
            pt = calibration.current_ref_point(hwnd, ref_w, ref_h)
            text = f"參考解析度座標=({pt[0]:4d},{pt[1]:4d})" if pt else "(滑鼠不在遊戲視窗範圍內)"
            print("\r" + text + " " * 10, end="", flush=True)
        time.sleep(0.05)


def save(config_path, data):
    config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="互動式座標校正工具")
    parser.add_argument("--config", default="config.json", help="設定檔路徑")
    args = parser.parse_args()
    config_path = Path(args.config)

    if not config_path.exists():
        print(f"找不到設定檔 {config_path}，請先確認 config.json 存在。")
        return
    data = json.loads(config_path.read_text(encoding="utf-8"))
    regions = calibration.merge_regions(data)
    window_title = data.get("window_title", "貓貓TMS")
    ref_w, ref_h = regions["ref_width"], regions["ref_height"]

    hwnd = calibration.find_window(window_title)
    if not hwnd:
        print(f"找不到遊戲視窗「{window_title}」，請開啟遊戲後重新執行。")
        return

    left, top, right, bottom = calibration.client_rect_on_screen(hwnd)
    actual_w, actual_h = right - left, bottom - top
    print(f"已找到遊戲視窗「{window_title}」")
    print(f"視窗目前實際 client area 大小: {actual_w} x {actual_h}")
    if (actual_w, actual_h) != (ref_w, ref_h):
        print(
            f"目前 ref_width/ref_height 是 {ref_w}x{ref_h}，與實際視窗大小不同，"
            f"建議先手動把 config.json 的 ref_width 改成 {actual_w}、ref_height 改成 {actual_h}，"
            f"存檔後重新執行本工具，這樣記錄的座標會跟畫面像素 1:1 對應。"
        )
        try:
            input("仍要用目前的 ref_width/ref_height 繼續嗎？按 Enter 繼續，或 Ctrl+C 取消: ")
        except (EOFError, KeyboardInterrupt):
            print("\n已取消")
            return

    print(__doc__)

    stop_event = threading.Event()
    pause_event = threading.Event()
    t = threading.Thread(target=live_loop, args=(hwnd, ref_w, ref_h, stop_event, pause_event), daemon=True)
    t.start()

    state = calibration.WizardState(hwnd, ref_w, ref_h, regions, calibration.STEPS)

    try:
        while not state.finished:
            key = state.current_step[0]
            pause_event.set()
            print()
            print(f"【{state.prompt()}】")
            try:
                cmd = input("  移到定點後按 Enter 記錄 (s=跳過本項 / q=結束校正): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                pause_event.clear()
                raise Quit()
            pause_event.clear()

            if cmd == "q":
                raise Quit()
            if cmd == "s":
                state.skip()
                print(f"  (保留 {key} 原值: {regions[key]})")
                continue

            ok, err = state.capture()
            if err:
                print(f"  -> {err}")
                continue
            if ok:
                save(config_path, data)
                print(f"  已寫入 config.json -> {key} = {regions[key]}")

        print("\n全部項目校正完畢！")
    except Quit:
        print("\n已手動結束校正，目前為止記錄的項目已經寫入 config.json。")
    finally:
        stop_event.set()
        t.join(timeout=0.5)

    print("=" * 70)
    print(f"結果已即時寫入 {config_path}，可以直接執行程式或用 dry_run 測試。")
    print("=" * 70)


if __name__ == "__main__":
    main()
