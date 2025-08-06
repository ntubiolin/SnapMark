### 🎯 目標（Goal）

作為一位開發者／研究者／創作者，我希望能用快捷鍵快速截圖，並與 AI 互動分析、生成筆記／報告，以便加速我在技術研究、debug、會議記錄等工作流程。

---

### 📌 使用情境（Scenario）

1. **使用者按下自定義快捷鍵**，系統觸發截圖功能。
2. 截圖完成後，**畫面右側會跳出一個前端視窗**，顯示剛才的截圖，並附有：

   * ✅ **複製按鈕**：複製圖片到剪貼簿。
   * 🔴 **紅框工具**：讓使用者手動標記截圖區域。
3. 左側是一個**對話區塊**，使用者可以輸入指令與 AI 對話：

   * 🧠 支援自然語言輸入
   * 🔧 可以調用本地 MCP tool 處理特定任務
   * 💬 所有對話會保留在左側以供回顧
4. 右下角提供選項欄位：

   * 🤖 **模型選擇**（例如 GPT-4、GPT-3.5、本地模型等）
   * 🗂️ **Markdown 輸出路徑設定**
   * 🖼️ **截圖儲存路徑設定**
5. **Summary 區塊**：

   * 📄 有一個 `Summary` 按鈕與 prompt 輸入框
   * 當使用者輸入 prompt 並按下按鈕，系統會遍歷指定資料夾下的所有 markdown 檔與截圖，並根據使用者提示生成**整合報告**
   * 輸出格式支援 Markdown 或 PDF

---

### 💻 技術需求（Technical Considerations）

* **熱鍵系統**需支援跨平台（macOS、Windows、Linux）差異：

  * macOS：需處理 Accessibility 權限與特殊快捷鍵
  * Windows：可能使用 `pywin32` 或 `keyboard` 庫
* **前端界面**可考慮使用：

  * `PyQt` / `Tkinter` / `Tauri + Python` / `Electron + Python backend`
* **截圖功能**使用 Python 內建或第三方工具：

  * `pyautogui`, `Pillow`, `mss`
* **紅框註記**：類似圖片編輯的小工具，可簡易標記（可用 `cv2` 或 `PIL` 畫圖）
* **AI 對話功能**可透過：

  * Azure OpenAI / OpenAI API / 本地 LLM 模型（Mistral、LLaMA、GPT4All）
* **資料結構設計**：

  * 每次截圖 + 對話 = 一個會話 Session 資料夾，裡面包含 markdown + png + JSON log

---

### ✅ Acceptance Criteria（驗收標準）

| 編號  | 驗收標準描述                                              |
| --- | --------------------------------------------------- |
| AC1 | 使用者可透過快捷鍵進行截圖                                       |
| AC2 | 截圖後自動跳出包含該圖像的互動視窗                                   |
| AC3 | 左側可與 AI 進行自然語言互動，右側可複製圖片或紅框標記                       |
| AC4 | 支援多作業系統的快捷鍵處理方式                                     |
| AC5 | 可自訂模型與輸出路徑                                          |
| AC6 | Summary 功能可整合目錄下的所有 markdown + image，根據 prompt 輸出報告 |
