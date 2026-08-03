# 自動洗閃炫方塊

依 [plan.md](plan/plan.md) 實作，讀取遊戲畫面(視窗標題預設「貓貓TMS」)並自動操作滑鼠，
重複使用結合方塊直到潛在能力符合設定的目標，或用完設定的方塊上限為止。

提供兩種使用方式：**圖形介面(GUI)** 或 **程式碼(CLI)**，擇一即可，功能完全對等。
不熟悉命令列的話建議用 GUI。

## 安裝

滑鼠控制用 [pyautogui](https://pyautogui.readthedocs.io/)，畫面文字辨識用
[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)。PaddleOCR 底層的
`paddlepaddle` 目前還沒有 Python 3.14 的預編譯版本，**必須用 Python 3.13 (或更早)**：

```
py -3.13 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

第一次執行時 PaddleOCR 會自動下載偵測/辨識模型(存到 `~/.paddlex/official_models/`)，
需要網路連線，之後就會用本機快取，不用再下載。(如果是用打包好的 exe，模型檔已經
內建，不受此限制，見下方「打包成 exe」。)

安裝完成後，繼續看下方「使用教學」開始設定並執行。

## 使用教學

### 方式一：圖形介面 (GUI)

```
.venv\Scripts\python gui.py
```

#### 1. 等待初始化完成

視窗開啟後會先在背景初始化 PaddleOCR 引擎(第一次執行需要下載模型，需要一點時間)。
**初始化完成前，「開始」跟「座標校正」的按鈕都會維持反灰、不能按**，狀態列會顯示
「正在初始化 OCR 引擎，請稍候…」；等狀態列變成「就緒」，按鈕才會恢復可以點擊。
如果初始化失敗，會跳出錯誤訊息視窗說明原因。

#### 2. 設定遊戲解析度

視窗上方「遊戲解析度設定」區塊：對應 `config.json` 的 `regions.ref_width` /
`ref_height`，所有按鈕座標都是以這個解析度為基準記錄的。

- 「偵測目前遊戲視窗大小」：自動抓取目前遊戲視窗的實際大小，填入寬度/高度欄位
  (不會馬上存檔，填入後可以自己再檢查一次)。
- 「儲存解析度設定」：把目前欄位裡的數值寫回 `config.json`。

**第一次使用、或遊戲視窗大小變動過，建議先點「偵測目前遊戲視窗大小」再「儲存
解析度設定」，存檔後接著做下一步的「全部校正」**——只改解析度不重新校正，既有
的按鈕座標會套用新的縮放比例，但不會自動變準確；唯一準確的方式還是解析度存好後
重新走一次「全部校正」。

#### 3. 校正座標(第一次使用、或遊戲視窗變動過，必須先做這一步)

視窗下方「座標校正」區塊：

- **「全部校正」**：依序引導校正全部欄位(共11項)，跟 CLI 的 `tools/locate.py`
  是同一套邏輯、行為完全一致。
- **「單一按鈕校正」**：從下拉選單挑選某一個欄位，只重新校正那一項，不用整套重跑。

點下去後會開一個小視窗，即時顯示滑鼠所在的參考解析度座標，操作方式：

1. 依畫面提示，先手動把遊戲切到對應的畫面/步驟。
2. 把滑鼠移到遊戲畫面上要記錄的定點。
3. 觸發「記錄」——**強烈建議用熱鍵 `ctrl+f3` 觸發，不要用滑鼠點對話框裡的按鈕**。
   點按鈕會讓滑鼠先移到按鈕上，記錄到的會是按鈕座標，不是遊戲畫面上的定點，
   整組校正就會是錯的。
4. 想跳過這一項(保留原本的值)按 `ctrl+f4`；全部做完或想中途結束按 `ctrl+f5`。

校正結果會即時寫回 `config.json`，不用手動存檔。

#### 4. 設定目標潛能組

視窗上方「目標潛能組設定」區塊：每一組是3個輸入框，依序對應遊戲畫面上固定的
上/中/下位置，**每組必須恰好填其中1格、其餘2格留空**(遊戲畫面每一輪只會有1格被
選取，程式只能針對被選取的那一格重骰，無法同時鎖定2個以上位置)。可以：

- 「+ 新增目標組合」：新增一組。
- 每組右邊的 `↑`/`↓`：調整優先權順序，**由上到下優先權由高到低**。
- 「刪除」：移除整組。
- 「儲存目標潛能設定」：把目前畫面上的內容寫回 `config.json`(會先檢查每組是否
  恰好填1格，沒通過會跳出錯誤提示、不會存檔)。

詳細比對規則(數值要不要完全相符、多組之間怎麼決定優先權)見下方「Config 設定教學」
的 `target_potentials` 說明。

#### 5. 開始執行

1. 先手動在遊戲中開啟潛在能力面板、切到「方塊」分頁並選擇「結合方塊」。
2. 點「開始」——會先自動儲存目前的目標潛能設定，跳出確認提示後才真正開始自動化。
3. 執行中的 log 會即時顯示在視窗下方文字區。

#### 6. 停止

- 點視窗裡的「停止」按鈕。
- 或按熱鍵 `ctrl+f2`(`stop_hotkey`)——不用切換視窗，遊戲畫面保持在前景也能按。
- 或把滑鼠移到螢幕**任一角落**，觸發 pyautogui 的 fail-safe 中止。

「停止」不是立即中斷，會等**目前這一輪跑完**才收尾(自動點擊「離開」)。「開始」
也有對應熱鍵 `ctrl+f1`(`start_hotkey`)，等同點擊「開始」按鈕。

以上5個熱鍵(`start_hotkey`/`stop_hotkey`/`calibrate_confirm_hotkey`/
`calibrate_skip_hotkey`/`calibrate_finish_hotkey`)都可以在 `config.json` 改成別的
按鍵組合。

### 方式二：程式碼 (CLI)

#### 1. 校正座標(第一次使用、或遊戲視窗變動過，必須先做這一步)

```
.venv\Scripts\python tools/locate.py
```

程式會依 `currency_label_box` → ... → `leave_button` 的順序，逐項提示你
「遊戲畫面該停在哪一步、滑鼠要移到哪裡」；移到定點後直接按 Enter 就會記錄並
立刻寫回 `config.json`，自動進入下一項，不用自己輸入名稱。也支援輸入 `s` 跳過
該項(保留原值)、`q` 結束校正(已記錄的項目不會遺失)。

#### 2. 設定 `config.json`

至少確認 `window_title`(遊戲視窗標題)跟 `target_potentials`(目標潛能)符合你的
需求，詳見下方「Config 設定教學」。

#### 3. 執行

1. 先手動在遊戲中開啟潛在能力面板、切到「方塊」分頁並選擇「結合方塊」。
2. 執行：
   ```
   .venv\Scripts\python run.py
   ```
3. 依提示輸入 `y` 開始，程式會倒數3秒後開始自動操作。

#### 4. 停止

- 把滑鼠移到螢幕**任一角落**，觸發 pyautogui 的 fail-safe 中止。
- 直接按 Ctrl+C。
- 按熱鍵 `ctrl+f2`(`stop_hotkey`)——不用切換視窗，會在目前這一輪跑完後收尾。
  (CLI 沒有「待機中」狀態可以用熱鍵啟動，所以 `start_hotkey` 只有 GUI 有作用。)

執行紀錄會寫在 `logs/run_*.log`。點擊完不會把滑鼠移回原位，游標會停在最後一次
點擊的位置。

## Config 設定教學

所有設定都在專案根目錄的 `config.json`，用文字編輯器打開即可修改，不用重開程式、
存檔後下次執行就會套用(GUI 的目標潛能組設定與座標校正另外有介面可以直接改，
改完會自動存檔)。

### 完整範例

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
  "regions": { "...": "所有按鈕/讀取區域座標，見下方「regions：座標設定」" }
}
```

### 目標潛能設定

- `target_potentials`：**多組允許的目標組合**組成的list，每組固定3個字串槽位、
  依序對應遊戲畫面上固定的上/中/下位置，**每組必須恰好填其中1格，其餘2格留空**
  (因為遊戲畫面每一輪只會有1格被選取、程式也只能針對被選取的那一格重骰，無法同時
  鎖定2個以上位置)，**list中排越前面的組合優先權越高**。畫面上最終3個潛能只要
  **在對應位置**滿足**其中任一組合**就算達成目標、可以收手離開；重骰過程中每一輪
  會先讀取目前是哪一個位置被選取，依優先權由高到低尋找第一個「目標位置＝目前被
  選取位置」的組合：若有找到就點「重新設定」重骰該格，直到該格變成目標潛能；若
  沒有任何組合的目標位置等於目前被選取位置，就點「重新選擇」換一格(不會改變3個
  潛能的內容)。上面範例代表「魔法攻擊力」不管出現在哪個位置都算達成目標——對同一個
  潛能想要「不限位置」時，需要像範例一樣把它分別填在3組、3個不同位置。
  - 每個字串可只寫名稱，例如 `"魔法攻擊力"`：只比對名稱，不限數值。
  - 也可以連數值一起寫，例如 `"魔法攻擊力 +12%"`：數值必須完全相同才算符合，用來
    區分同名但不同數值的重複選項(例如"無視怪物防禦率"同時出現 +30% 和 +40% 兩種)。
  - GUI 使用者可直接用「目標潛能組設定」區塊編輯，不用手動改 JSON。

### 熱鍵設定

- `start_hotkey` / `stop_hotkey`：全域開始/停止熱鍵(語法例如 `"f8"`、`"ctrl+alt+q"`)，
  不管遊戲視窗有沒有 focus 都能觸發；`start_hotkey` 只在 GUI 有作用(等同點擊
  「開始」)，CLI 沒有「啟動中」以外的待機狀態，不需要開始熱鍵。停止會在目前這一輪
  跑完後收尾(自動點擊「離開」)、不是立即中斷。設成空字串 `""` 則不註冊該熱鍵，
  停止仍可改用滑鼠移到螢幕角落、Ctrl+C(CLI)或視窗裡的按鈕(GUI)。
- `calibrate_confirm_hotkey` / `calibrate_skip_hotkey` / `calibrate_finish_hotkey`：
  只有 GUI 的座標校正對話框會用到，分別對應「記錄」「跳過本項」「結束」。校正時
  滑鼠要停在遊戲畫面上的定點，**務必用這三個熱鍵觸發，不要點對話框裡的按鈕**——
  點按鈕會讓滑鼠先移到按鈕上，記錄到的會是按鈕座標而不是遊戲畫面上的定點。

### 其他基本設定

- `window_title`：遊戲視窗標題，預設 `"貓貓TMS"`，需要跟實際視窗標題完全一致
  才找得到視窗。
- `ocr_lang`：PaddleOCR 的語言模型，預設 `"chinese_cht"`(繁體中文)。
- `ocr_match_threshold`：潛能文字模糊比對的相似度門檻(0~1)，預設 `0.55`，數值
  越高比對越嚴格，OCR 稍有誤差就可能判定不符合。一般不需要調整。
- `max_cubes`：最多使用幾個方塊，`0` 代表不限制。「重新選擇」跟「重新設定」
  每點一次都算用掉1個方塊(即使沒有真的改變到想要的潛能)，都會計入這個上限。
- `click_delay_sec` / `post_action_wait_sec`：每次點擊之間、以及每個動作(如按下
  重新選擇/重新設定)之後的等待秒數，數值太小可能因為遊戲畫面還沒反應過來、
  截圖讀到舊畫面而誤判，一般不需要調整。
- `dry_run`：`true` 時只讀取畫面、印出判斷結果，不會真的點擊滑鼠(用來乾跑測試
  座標/OCR 設定是否正確，建議調整完設定後先開著這個測一輪再正式執行)。
- `log_lv`：`"debug"` 會印出每次點擊的詳細座標，其餘(含預設 `"info"`)只印重點
  流程訊息。

### regions：座標設定

所有滑鼠點擊/畫面讀取用的座標都放在 `regions` 區塊，**不用改程式碼**，用座標校正
工具(GUI 的「座標校正」或 CLI 的 `tools/locate.py`，見上方「使用教學」)就能重新
產生，一般不需要手動編輯這個區塊。

座標是以 `ref_width` x `ref_height`(預設 1376x759，對應 plan.md 附圖的視窗 client
area 大小)這個「參考解析度」下的像素記錄，執行時會依實際視窗大小等比例換算，因此
視窗大小只要沒差異太大都還算容錯；但若遊戲視窗大小差異太大，仍建議重新校正一次，
會更準確。GUI 使用者可以直接用「遊戲解析度設定」區塊的「偵測目前遊戲視窗大小」
按鈕填入這兩個值，不用手動量測。

各欄位意義：

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

什麼時候需要重新校正：第一次使用、遊戲改版導致 UI 位置跑掉、換了不同大小/位置的
遊戲視窗，或懷疑目前設定不準確時。

---

## 打包成 exe

用 [PyInstaller](https://pyinstaller.org/) 把 GUI(`gui.py`)打包成不需要安裝 Python
就能執行的程式：

```
.venv\Scripts\pip install pyinstaller
.venv\Scripts\pyinstaller AutoUniCube.spec
```

打包結果在 `dist/AutoUniCube/`，裡面的 `AutoUniCube.exe` 加上整個 `_internal/`
資料夾都要一起帶走(不能只複製 exe 單獨那個檔案)，`config.json` 要放在跟 exe 同一層
目錄。整包大約 850MB+(主要是 `paddlepaddle` 本身很大，OCR 模型檔約再多133MB)。
打包好的 exe 使用方式跟上方「使用教學 → 方式一：圖形介面 (GUI)」完全一樣，且目前
`.spec` 設定 `console=True`，執行時會額外開一個終端機視窗顯示 log/例外訊息，方便
排查問題(不想看到這個視窗的話，可以把 `.spec` 裡 `EXE(...)` 的 `console=True`
改成 `False` 再重新打包)。

`AutoUniCube.spec` 已經包含打包 `paddleocr`/`paddlex`/`paddle`/`keyboard` 這幾個
套件需要的 `--collect-all` 設定，改完程式碼後重新打包只要重跑上面那行指令即可，
不需要重新產生 `.spec`。

**OCR 模型檔已直接打包進 exe，執行時不需要網路**：`.spec` 會把 `paddlex_models/`
資料夾(PaddleOCR 官方模型檔)一起收進 `_internal/`，`gui.py` 在打包後的 frozen
模式下會把 `PADDLE_PDX_CACHE_HOME` 指到這裡，完全不會嘗試連線下載。這個資料夾
預設不在版控裡(`.gitignore` 已排除，因為133MB對版控來說太大)，第一次要打包前
需要自己準備：

1. 用 `python gui.py`(一般開發環境、非打包模式)正常執行一次，讓程式走完整個
   OCR 初始化流程。PaddleOCR 偵測到本機沒有對應語言的模型，會自動連線官方模型
   來源(HuggingFace/AIStudio/ModelScope/BOS 其中之一)下載，存到
   `~/.paddlex/official_models/`(Windows 上是
   `C:\Users\<你的帳號>\.paddlex\official_models\`)。這一步需要網路連線。
2. 把下載好的模型資料夾複製到專案裡，讓 `.spec` 打包時抓得到：
   ```
   mkdir paddlex_models\official_models
   xcopy /E /I "%USERPROFILE%\.paddlex\official_models\PP-OCRv6_medium_det" paddlex_models\official_models\PP-OCRv6_medium_det
   xcopy /E /I "%USERPROFILE%\.paddlex\official_models\PP-OCRv6_medium_rec" paddlex_models\official_models\PP-OCRv6_medium_rec
   ```
   (實際的模型資料夾名稱依 `config.json` 的 `ocr_lang` 而定；`chinese_cht` 對應的
   就是上面這兩個。換了 `ocr_lang` 導致用到別的模型時，同樣先跑一次
   `python gui.py` 讓它下載好，再照上面方式複製過來、重新打包一次。)

之後只要 `paddlex_models/` 資料夾內容沒變，重新打包(`pyinstaller
AutoUniCube.spec`)就會沿用同一份模型檔，不需要每次都重新下載複製。這也是解決
「在完全沒有網路、或連不到 huggingface/modelscope/aistudio/bos 任何一個模型來源
的乾淨電腦上，執行 exe 會卡在『初始化 OCR』甚至直接卡死」這個問題的方法——只要
模型檔跟著打包進去，就完全不會嘗試連線。

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

## 測試（不需要開遊戲）

`tests/test_reference_screenshots.py` 用 plan.md 附的 `step*.png` 參考截圖驗證
OCR 辨識、選取邏輯、目標比對邏輯是否正確：

```
.venv\Scripts\python -m pytest tests/ -v
```

## 已知限制

- 所有座標是用參考截圖(約 1376x759 client area 大小)校準、以比例換算，若遊戲視窗
  大小差異太大可能會點不準，建議維持接近該大小的視窗，或重新校正。
- PaddleOCR 對繁體字偶爾會辨識成筆劃相近的簡體/日文變體字(例如「擊」讀成「撃」、
  「視」讀成「视」)，但比對邏輯本來就用模糊比對容忍1~2個字差異，不影響判斷。
- 判斷「哪一格潛能目前被選取」是用該格底色的飽和度(選取時底色為紫/橘/綠等鮮豔色，
  未選取則接近面板底色)，若飽和度差異不明顯只會印警告、仍會挑飽和度最高的一格，
  不影響流程；若判斷持續錯誤，可能是 `potential_list_box`/`potential_row_y_bounds`
  需要重新校正。
- `gui.py` 圖形介面目前只在無畫面(offscreen)環境驗證過視窗能正常建立與基本互動
  (新增/刪除/排序目標潛能組、存檔)，**尚未在真實視窗環境實際點過「開始」跑完整流程**，
  建議第一次使用先搭配 `dry_run: true` 觀察 log。
