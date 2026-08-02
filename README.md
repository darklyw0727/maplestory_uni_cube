# 自動洗閃炫方塊

依 [plan.md](plan/plan.md) 實作，讀取遊戲畫面(視窗標題預設「貓貓TMS」)並自動操作滑鼠，
重複使用結合方塊直到潛在能力符合設定的目標，或用完設定的方塊上限為止。

## 快速開始

1. **建立 Python 環境**(詳見下方「安裝」)：
   ```
   py -3.13 -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```
2. **設定 `config.json`**：至少確認 `window_title`(遊戲視窗標題)跟 `target_potentials`
   (目標潛能)符合你的需求，詳見下方「設定 (config.json)」。
3. **啟動程式**：第一次使用、或遊戲視窗大小/位置變動、或改版後，**先**執行座標校正
   工具，再執行主程式：
   ```
   .venv\Scripts\python tools/locate.py   # 先校正所有按鈕/讀取區域的座標
   .venv\Scripts\python run.py            # 校正完成後才執行自動化主程式
   ```
   座標校正只要遊戲視窗沒有變動，做過一次之後之後每次都可以直接跳過、只執行
   `run.py`。詳見下方「座標校正 (regions)」與「執行」。

   也可以改用整合了以上功能的圖形介面，見下方「圖形介面 (GUI)」。

## 圖形介面 (GUI)

除了 CLI(`tools/locate.py` + `run.py`)之外，也提供一個 PyQt6 圖形介面，把目標潛能
設定、座標校正、執行整合在同一個視窗：

```
.venv\Scripts\python gui.py
```

- **目標潛能組設定區**：視覺化編輯 `target_potentials`——每組3個輸入框，可以「+ 新增
  目標組合」新增一組、用每組右邊的 ↑/↓ 調整優先權順序(由上到下優先權由高到低)、
  「刪除」移除整組；「儲存目標潛能設定」會把目前畫面上的內容寫回 `config.json`。
- **開始/停止按鈕**：「開始」會先自動儲存目前的目標潛能設定，跳出確認提示後才開始
  自動化，執行中的 log 會即時顯示在下方文字區；「停止」會在目前這一輪跑完後收尾
  (自動點擊「離開」)，不是立即中斷。這兩個動作**全程**都可以用全域熱鍵觸發，不用
  點擊視窗——`start_hotkey`(預設 `ctrl+f1`)、`stop_hotkey`(預設 `ctrl+f2`)，
  遊戲畫面保持在前景也能按。
- **座標校正**：
  - 「全部校正」：依序引導校正全部欄位，跟 `tools/locate.py` 是同一套邏輯、同一份
    步驟清單，行為完全一致。
  - 「單一按鈕校正」：從下拉選單挑選某一個欄位，只重新校正那一項，不用整套重跑。
  校正時會有一個小視窗即時顯示滑鼠所在的參考解析度座標。**記錄／跳過／結束建議用
  熱鍵觸發**——`calibrate_confirm_hotkey`(預設 `ctrl+f3`)、`calibrate_skip_hotkey`
  (預設 `ctrl+f4`)、`calibrate_finish_hotkey`(預設 `ctrl+f5`)。這三個動作也有
  對應按鈕，但**點按鈕會讓滑鼠先移過去**，記錄到的會是按鈕座標而不是遊戲畫面上
  的定點，所以校正時請用熱鍵、不要點按鈕。

首次開啟視窗會先在背景初始化 PaddleOCR 引擎(需要一點時間，尤其是第一次要下載模型)，
初始化完成前「開始」與「座標校正」按鈕會維持停用狀態。

## 安裝

滑鼠控制用 [pyautogui](https://pyautogui.readthedocs.io/)，畫面文字辨識用
[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)。PaddleOCR 底層的
`paddlepaddle` 目前還沒有 Python 3.14 的預編譯版本，**必須用 Python 3.13 (或更早)**：

```
py -3.13 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

第一次執行時 PaddleOCR 會自動下載偵測/辨識模型(存到 `~/.paddlex/official_models/`)，
需要網路連線，之後就會用本機快取，不用再下載。

## 打包成 exe

用 [PyInstaller](https://pyinstaller.org/) 把 GUI(`gui.py`)打包成不需要安裝 Python
就能執行的程式：

```
.venv\Scripts\pip install pyinstaller
.venv\Scripts\pyinstaller AutoUniCube.spec
```

打包結果在 `dist/AutoUniCube/`，裡面的 `AutoUniCube.exe` 加上整個 `_internal/`
資料夾都要一起帶走(不能只複製 exe 單獨那個檔案)，`config.json` 要放在跟 exe 同一層
目錄。整包大約 700MB+(主要是 `paddlepaddle` 本身很大)，第一次啟動若本機還沒有
PaddleOCR 模型快取(`~/.paddlex/official_models/`)一樣需要網路下載。

`AutoUniCube.spec` 已經包含打包 `paddleocr`/`paddlex`/`paddle`/`keyboard` 這幾個
套件需要的 `--collect-all` 設定，改完程式碼後重新打包只要重跑上面那行指令即可，
不需要重新產生 `.spec`。

**已知問題**：打包後第一次執行若跳出「PaddleOCR 初始化失敗：A dependency error
occurred during pipeline creation」，是因為 `paddlex` 會用 `importlib.metadata`
讀取自己跟一串依賴套件(`imagesize`/`opencv-contrib-python`/`pyclipper`/
`pypdfium2`/`python-bidi`/`shapely`)的 dist-info 來判斷 OCR 功能是否可用，但
PyInstaller 預設不會打包這些 metadata，導致誤判成依賴缺失。`.spec` 裡已經用
`copy_metadata()` 補上這幾個套件的 metadata 解決這個問題；如果升級
`paddlepaddle`/`paddleocr`/`paddlex` 版本後又跳出同樣錯誤，多半是新版本用到了
別的 extra 套件組合，可以參考 `.spec` 裡的註解，用同樣方式把新缺的套件名稱
加進 `copy_metadata` 清單。

若防毒軟體對這個 exe 跳出誤判警告，這是 PyInstaller 打包的未簽章大型執行檔常見的
現象(尤其是包含大量原生 DLL 的 ML 相關套件)，可以自行評估是否加入例外。

CLI(`run.py`/`tools/locate.py`)目前沒有另外打包，仍需要用 Python 執行；如果需要
CLI 版本的 exe，可以比照 `.spec` 的做法各自打包一份。

## 設定 (config.json)

```json
{
  "target_potentials": [
    ["魔法攻擊力", "", ""],
    ["", "魔法攻擊力", ""],
    ["", "", "魔法攻擊力"]
  ],
  "log_lv": "info",
  "max_cubes": 0,
  "window_title": "貓貓TMS",
  "ocr_lang": "chinese_cht",
  "ocr_match_threshold": 0.55,
  "click_delay_sec": 0.35,
  "post_action_wait_sec": 0.6,
  "dry_run": false,
  "start_hotkey": "ctrl+f1",
  "stop_hotkey": "ctrl+f2",
  "calibrate_confirm_hotkey": "ctrl+f3",
  "calibrate_skip_hotkey": "ctrl+f4",
  "calibrate_finish_hotkey": "ctrl+f5",
  "regions": { "...": "所有按鈕/讀取區域座標，見下方「座標校正」" }
}
```

- `target_potentials`：**多組允許的目標組合**組成的list，每組固定3個字串槽位、
  依序對應遊戲畫面上固定的上/中/下位置，**每組必須恰好填其中1格，其餘2格留空**
  (因為遊戲畫面每一輪只會有1格被選取、程式也只能針對被選取的那一格重骰，無法同時
  鎖定2個以上位置)，**list中排越前面的組合優先權越高**。畫面上最終3個潛能只要
  **在對應位置**滿足**其中任一組合**就算達成目標、可以收手離開；重骰過程中每一輪
  會先讀取目前是哪一個位置被選取，依優先權由高到低尋找第一個「目標位置＝目前被
  選取位置」的組合：若有找到就點「重新設定」重骰該格，直到該格變成目標潛能；若
  沒有任何組合的目標位置等於目前被選取位置，就點「重新選擇」換一格(不會改變3個
  潛能的內容)。上面範例代表「魔法攻擊力」不管出現在哪個位置都算達成目標——
  對同一個潛能想要「不限位置」時，需要像範例一樣把它分別填在3組、3個不同位置。
  - 每個字串可只寫名稱，例如 `"魔法攻擊力"`：只比對名稱，不限數值。
  - 也可以連數值一起寫，例如 `"魔法攻擊力 +12%"`：數值必須完全相同才算符合，用來
    區分同名但不同數值的重複選項(例如"無視怪物防禦率"同時出現 +30% 和 +40% 兩種)。
- `log_lv`：`"debug"` 會印出每次點擊的詳細座標，其餘(含預設)只印重點流程訊息。
- `max_cubes`：最多使用幾個方塊，`0` 代表不限制。
- `dry_run`：`true` 時只讀取畫面、印出判斷結果，不會真的點擊滑鼠(用來乾跑測試座標/OCR)。
- `start_hotkey` / `stop_hotkey`：全域開始/停止熱鍵(語法例如 `"f8"`、`"ctrl+alt+q"`)，
  不管遊戲視窗有沒有 focus 都能觸發；`start_hotkey` 只在 GUI 有作用(等同點擊
  「開始」)，CLI 沒有「啟動中」以外的待機狀態，不需要開始熱鍵。停止會在目前這一輪
  跑完後收尾(自動點擊「離開」)、不是立即中斷。設成空字串 `""` 則不註冊該熱鍵，
  停止仍可改用滑鼠移到螢幕角落、Ctrl+C(CLI)或視窗裡的按鈕(GUI)。
- `calibrate_confirm_hotkey` / `calibrate_skip_hotkey` / `calibrate_finish_hotkey`：
  只有 GUI 的座標校正對話框會用到，分別對應「記錄」「跳過本項」「結束」。校正時
  滑鼠要停在遊戲畫面上的定點，**務必用這三個熱鍵觸發，不要點對話框裡的按鈕**——
  點按鈕會讓滑鼠先移到按鈕上，記錄到的會是按鈕座標而不是遊戲畫面上的定點。

## 座標校正 (regions)

所有滑鼠點擊/畫面讀取用的座標都放在 `config.json` 的 `regions` 區塊，不用改程式碼。
座標是以 `ref_width` x `ref_height`(預設 1376x759，對應 plan.md 附圖的視窗 client
area 大小)這個「參考解析度」下的像素記錄，執行時會依實際視窗大小等比例換算，因此
視窗大小只要沒差異太大都還算容錯。各欄位意義：

| 欄位 | 說明 |
| --- | --- |
| `currency_label_box` | [x0,y0,x1,y1]，潛在能力大面板「使用貨幣」欄位文字的區域 |
| `reset_button` / `reset_confirm_button` | 大面板的「重新設定」按鈕與其確認彈窗的「確認」按鈕(整個流程只會點這一次，用來叫出下面的小視窗) |
| `potential_list_box` / `potential_row_y_bounds` | 小視窗固定顯示的3個潛能清單方框，與其中4條分隔線(切出3列) |
| `potential_text_x_offset` | 每列文字起始位置，相對於整列左緣的x偏移(用來跳過等級圖示) |
| `reselect_button` / `reselect_confirm_button` | 小視窗的「重新選擇」按鈕(換選取哪一格，不改內容)與其確認彈窗的「確認」按鈕 |
| `reset_selected_button` / `reset_selected_confirm_button` | 小視窗的「重新設定」按鈕(重骰被選取那格的內容)與其確認彈窗的「確認」按鈕 |
| `leave_button` | 小視窗的「離開」按鈕 |

`reselect_button`/`reset_selected_button` 兩個按鈕按下後都會彈出確認彈窗，且都會
消耗1個結合方塊(即使沒有真的改變到想要的潛能)。

若遊戲改版、UI位置跟預設值對不上、或想確認目前設定是否準確，可執行座標校正工具：

```
.venv\Scripts\python tools/locate.py
```

程式會依 `currency_label_box` → ... → `leave_button` 的順序，逐項提示你
「遊戲畫面該停在哪一步、滑鼠要移到哪裡」；移到定點後直接按 Enter 就會記錄並
立刻寫回 `config.json`，自動進入下一項，不用自己輸入名稱。也支援輸入 `s` 跳過
該項(保留原值)、`q` 結束校正(已記錄的項目不會遺失)。

## 執行

0. 若還沒校正過座標(第一次使用、或遊戲視窗變動過)，先執行上一節的
   `tools/locate.py` 完成校正。
1. 先手動在遊戲中開啟潛在能力面板、切到「方塊」分頁並選擇「結合方塊」(對應 plan.md 步驟1)。
2. 執行：

```
.venv\Scripts\python run.py
```

3. 依提示輸入 `y` 開始，程式會倒數3秒後開始自動操作。
4. **緊急停止**：執行期間把滑鼠移到螢幕**任一角落**即會觸發 pyautogui 的 fail-safe
   中止(`pyautogui.FAILSAFE`)；也可以直接 Ctrl+C；或按下 `stop_hotkey` 設定的
   全域熱鍵(預設 `ctrl+f2`)，**不用切換視窗**、遊戲畫面保持在前景也能觸發，會在
   目前這一輪跑完後收尾。
5. 點擊完不會把滑鼠移回原位，游標會停在最後一次點擊的位置。

執行紀錄會寫在 `logs/run_*.log`。

## 測試（不需要開遊戲）

`tests/test_reference_screenshots.py` 用 plan.md 附的 `step*.png` 參考截圖驗證
OCR 辨識、選取邏輯、目標比對邏輯是否正確：

```
.venv\Scripts\python -m pytest tests/ -v
```

## 已知限制

- 所有座標是用參考截圖(約 1376x759 client area 大小)校準、以比例換算，若遊戲視窗
  大小差異太大可能會點不準，建議維持接近該大小的視窗，或用 `tools/locate.py`
  重新校正。
- PaddleOCR 對繁體字偶爾會辨識成筆劃相近的簡體/日文變體字(例如「擊」讀成「撃」、
  「視」讀成「视」)，但比對邏輯本來就用模糊比對容忍1~2個字差異，不影響判斷。
- 判斷「哪一格潛能目前被選取」是用該格底色的飽和度(選取時底色為紫/橘/綠等鮮豔色，
  未選取則接近面板底色)，若飽和度差異不明顯只會印警告、仍會挑飽和度最高的一格，
  不影響流程；若判斷持續錯誤，可能是 `potential_list_box`/`potential_row_y_bounds`
  需要重新校正。
- `gui.py` 圖形介面目前只在無畫面(offscreen)環境驗證過視窗能正常建立與基本互動
  (新增/刪除/排序目標潛能組、存檔)，**尚未在真實視窗環境實際點過「開始」跑完整流程**，
  建議第一次使用先搭配 `dry_run: true` 觀察 log。
