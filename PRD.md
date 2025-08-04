# 🧱 技術架構（純 Python 版本）

### 🖥 桌面應用（GUI + 截圖 + OCR + 文件生成）

| 元件             | 建議技術                                  | 說明                                           |
| -------------- | ------------------------------------- | -------------------------------------------- |
| GUI 前端         | `PyQt5` / `Tkinter` / `DearPyGui`     | 架設桌面界面與快捷鍵支援，例如按下快捷鍵自動截圖並儲存                  |
| 截圖功能           | `mss` / `Pillow` / `pyautogui`        | 可選區截圖、目前視窗、整個螢幕等，跨平台（支援 macOS/Windows/Linux） |
| OCR 辨識         | `pytesseract` / `EasyOCR`             | 圖片轉文字，可插入 Markdown 中                         |
| Markdown 編輯與輸出 | `Python-Markdown` / 手動產生 `.md`        | 將截圖內容 + OCR 結果產生 Markdown 檔案                 |
| 摘要與 GPT 串接     | `OpenAI API` + `schedule` 或 `FastAPI` | 呼叫 GPT 產生摘要、每日自動整理筆記                         |

---

### 📂 檔案管理結構

* 每次截圖會：

  * 儲存成圖片檔（JPG/PNG）
  * 自動建立一個 Markdown 檔（附上 OCR 結果、圖片路徑、時間戳、可選標籤）

  ```
  /SnapMarkData/
      2025/
          08/
              04/
                  screen_14-25-12.png  
                  screen_14-25-12.md
  ```

---

# 🔁 系統整合方式（純 Python）

| 模式                | 技術堆疊                      | 優點                | 缺點                 |
| ----------------- | ------------------------- | ----------------- | ------------------ |
| All-in-one 應用程式   | `PyQt5` / `Tkinter` + CLI | 單一應用即可截圖/OCR/產生筆記 | UI 較傳統，不如 Web 現代感強 |
| CLI 工具 + Tray App | `pystray` + `schedule`    | 背景執行、低干擾          | 較難做即時互動            |

---

# 🧰 第三方工具建議（Python 生態系）

| 功能          | 工具建議                                                          |
| ----------- | ------------------------------------------------------------- |
| OCR         | `pytesseract`, `EasyOCR`, `PaddleOCR`                         |
| 截圖          | `mss`, `pyautogui`, `Pillow`                                  |
| GUI         | `Tkinter`, `PyQt5`, `DearPyGui`（現代 GUI）                       |
| Markdown 處理 | `markdown`, `mistune`, 或直接寫 `.md` 文件                          |
| PDF 輸出      | `markdown2`, `pdfkit`, `reportlab`                            |
| 時間排程任務      | `schedule`, `APScheduler`, `cron`（Linux/mac）                  |
| GPT 摘要      | `openai`, `langchain`, `llama-index`（如需 embedding / indexing） |

---

# 🧭 功能地圖（Feature Map）

```
SnapMark（Python 版）
├── 1. 螢幕截圖 Screenshot
│   ├── 1.1 快捷鍵觸發截圖（使用熱鍵庫）
│   ├── 1.2 選區截圖 / 全螢幕
│   └── 1.3 圖片壓縮與命名（timestamp）
├── 2. Markdown 筆記管理
│   ├── 2.1 OCR 結果自動插入 Markdown
│   ├── 2.2 插圖 + metadata
│   └── 2.3 按日期與任務分類儲存
├── 3. AI 摘要與日誌
│   ├── 3.1 自動搜尋過去 N 天筆記
│   ├── 3.2 呼叫 GPT 產生總結
│   └── 3.3 排程每日執行
├── 4. 搜尋與查找
│   ├── 4.1 CLI/GUI 關鍵字查找
│   └── 4.2 預覽 Markdown + 圖
└── 5. 系統設定
    ├── 5.1 儲存路徑與偏好設定
    └── 5.2 跨平台支援（Windows/macOS/Linux）
```

---

# 🛠️ 工作拆解（Task Breakdown）

## ✅ 截圖模組

| 任務         | 工具                     | 備註                             |
| ---------- | ---------------------- | ------------------------------ |
| 快捷鍵截圖觸發    | `keyboard`, `pyhk`     | 熱鍵綁定，觸發 `mss` 或 `pyautogui` 截圖 |
| 選區 / 全螢幕截圖 | `mss`, `PIL.ImageGrab` | 提供 CLI 參數或簡單 GUI 讓使用者選擇        |
| 命名與儲存路徑    | `datetime`, `os.path`  | 用 timestamp 自動命名               |

## ✅ Markdown + OCR

| 任務              | 工具                        | 備註                   |
| --------------- | ------------------------- | -------------------- |
| 建立 Markdown 檔案  | `os`, `open()`            | 可定義模板：標題、圖片、OCR 結果   |
| OCR 辨識文字插入筆記    | `pytesseract`, `EasyOCR`  | 輸出加入 Markdown 文件     |
| 自動標籤與 meta info | `datetime`, `config.json` | 可加入位置、任務標籤等 metadata |

## ✅ AI 摘要模組

| 任務                   | 工具                        | 備註                 |
| -------------------- | ------------------------- | ------------------ |
| 撈取過去幾天的筆記            | `os`, `glob`, `datetime`  | 按日期搜尋 `.md` 檔      |
| 呼叫 GPT / Claude 產生摘要 | `openai`, `httpx`         | 組 prompt + 回傳筆記摘要  |
| 排程每日自動執行             | `schedule`, `apscheduler` | 每天某時間呼叫函式          |
| 輸出為 Markdown / PDF   | `markdown`, `pdfkit`      | optional，可存 PDF 報告 |

## ✅ 搜尋與查找（可 CLI 或 GUI）

| 任務            | 工具                         | 備註                                |
| ------------- | -------------------------- | --------------------------------- |
| CLI 搜尋筆記      | `argparse`, `re`, `os`     | 可支援 `--tag=xxx --date=2025-08-04` |
| GUI 預覽截圖 + 筆記 | `PyQt`, `Tkinter` GUI View | 可預覽圖片與 Markdown（轉 HTML 顯示）        |

---

# 🚀 發佈策略（純 Python）

| 平台      | 發佈方式                    | 備註                              |
| ------- | ----------------------- | ------------------------------- |
| macOS   | `py2app`, `pyinstaller` | 打包成 .app                        |
| Windows | `pyinstaller` + .exe    | 直接打包成獨立執行檔                      |
| Linux   | `.AppImage`, `.deb`     | 用 `fpm` 或 `appimage-builder` 打包 |
| 跨平台共用安裝 | `pip install snapmark`  | 若以 CLI 工具釋出，也可上傳 PyPI           |

---