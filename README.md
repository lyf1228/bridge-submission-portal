# 🍁 中橋季刊 · 線上投稿與後台審稿系統 (Bridge Magazine Portal)

> 秋日紅楓（Autumn Red Maple）× 日式復古時計（和風時計）主題的 Streamlit 應用。
> 整合「前台讀者投稿表單」與「後台編輯審稿管理總覽」。
> 投稿的內文與照片可自動存進 **你的 Google Drive 資料夾**；另可選擇彙整到 Google Sheets、
> 或 email 通知編輯部。

---

## ✨ 功能總覽

### 模組一：前台投稿表單（訪客免登入）
- **投稿期別**：西元年份（預設 2026）＋ 刊物季別（春／夏／秋／冬季號）。
- **投稿者資料**：姓名、聯絡 Email（含格式驗證）。
- **稿件資訊**：文章標題、建議刊登單元類別
  （焦點快訊／橋海漫遊／橋藝教室／橋訊公告／讀者心得）。
- **牌局圖卡製作指引**：醒目提示卡片 ＋ 一鍵開啟
  [牌局與叫牌排版工作台](https://bridge-diagram-generator.streamlit.app/)。
- **內文雙軌輸入**：線上直接貼純文字，或上傳 `DOCX` / `PDF`
  （`python-docx` / `pypdf` 自動解析純文字，回填編輯框供微調）。
- **多張照片上傳**：每張即時縮圖預覽 ＋ 專屬圖說欄位。
- **儲存去向**（依 `.streamlit/secrets.toml` 設定，可同時開啟多個）：
  1. **本機**：一律在 `submissions/<年份>_<季>/<timestamp>_<投稿者>/` 留一份。
  2. **Google Drive**（`[drive]`）：在你指定的資料夾下，為每篇投稿開一個子資料夾，
     放入 `文章內文.txt`、`metadata.json`、所有原始照片與原始文檔。
  3. **Google Sheets**（`[google]`）：投稿文字彙整成一列，方便一覽（含該篇 Drive 連結）。
  4. **Email**（`[email]`）：把全文與原始附件寄給編輯部（可多位收件人）。
- 送出後顯示和風楓葉風格的感謝回條，並標示實際完成的儲存管道。

### 模組二：後台審稿管理（管理員驗證）
- 側邊欄「🔐 編輯後台登入」：帳號密碼**只從 `secrets.toml` 的 `[app]` 讀取**
  （原始碼不含預設密碼；未設定時後台無法登入），登入狀態存於 `st.session_state`。
- 資料來源自動判斷：**已設定 Google Sheets → 讀 Sheets**；否則讀本機 `submissions/`。
- 依「年份」與「季別」篩選稿件。
- 投稿清單表格 ＋ 文章詳情卡片：**放大字級**呈現完整內文、照片圖說、
  「開啟這篇投稿的 Google Drive 資料夾」連結、下載原始文檔／整包 ZIP。

### 字級
全站基礎字級 17px，文章內文／圖說約 20px（≥ 14pt），方便長時間審稿閱讀。

---

## 🗂️ 專案檔案結構

```
bridge-submission-portal/
├── app.py                       # 主程式（表單 + 後台 + 檔案解析 + 楓葉時計 CSS/SVG）
├── gdrive.py                    # Google Drive 儲存（透過 Apps Script Web App）
├── storage.py                   # Google Sheets 彙整總表
├── mailer.py                    # Gmail SMTP 投稿通知信
├── apps_script.gs               # 要貼到 script.google.com 的 Drive 收檔程式
├── requirements.txt
├── .gitignore                   # 排除 submissions/、.streamlit/secrets.toml
├── .streamlit/
│   └── secrets.toml.example     # 設定範本（複製成 secrets.toml 使用）
├── README.md
└── submissions/                 # 執行後自動產生（不進版控）
```

---

## 🚀 本機啟動

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

瀏覽器開啟 `http://localhost:8501`。未做任何設定時，投稿只存本機 `submissions/`，
後台也讀本機資料，足以完整試用。

---

## 📁 設定一：投稿檔案存進你的 Google Drive 資料夾（重點）

個人 Gmail 的「服務帳戶」沒有雲端硬碟容量，無法直接寫入你的 Drive。
解法：在**你自己的 Google 帳號**下部署一支小小的 Apps Script，以你的身分把檔案存進資料夾
（用你的 15GB、檔案也歸你所有）。做一次，約 6 分鐘。

1. 開 <https://script.google.com/> → **新增專案**。
2. 把本專案的 [`apps_script.gs`](apps_script.gs) 內容整段貼進 `Code.gs`（覆蓋原本內容）。
3. 修改最上面兩行：
   - `ROOT_FOLDER_ID`：你的目標資料夾 ID —— 資料夾網址
     `https://drive.google.com/drive/folders/`**`這一段`** 。
     （目前已預填 `1EoO3z1L0lz6MgryLPeJby_GRPHMHvO-R`）
   - `TOKEN`：自訂一組只有你知道的字串（英數即可）。
4. 右上 **部署 → 新增部署作業 → 類型：網頁應用程式**
   - 執行身分：**我**
   - 誰可以存取：**任何人**
   - 按「部署」，第一次會要求授權 → 允許（會出現「Google 未驗證這個應用程式」，
     點「進階 → 前往...（不安全）」，因為這支是你自己寫的）。
5. 複製「網頁應用程式」網址（`.../exec` 結尾）。
6. 在 `secrets.toml` 填：
   ```toml
   [drive]
   webapp_url = "剛剛複製的 .../exec 網址"
   token = "和 apps_script.gs 裡 TOKEN 一字不差的字串"
   ```

> 之後若修改 `apps_script.gs`，要「部署 → 管理部署作業 → 編輯(鉛筆) → 版本『新版本』→ 部署」
> 才會生效（網址不變）。

---

## 📊 設定二：Google Sheets 彙整總表（選用，方便一覽）

1. <https://console.cloud.google.com/> → 新增專案 → 「☰ → API 和服務 → 程式庫」
   啟用 **Google Sheets API**。
2. 「憑證 → + 建立憑證 → 服務帳戶」，名稱 `portal-bot`，完成。
3. 點進服務帳戶 → 「金鑰 KEYS → 新增金鑰 → JSON」，下載金鑰檔。
4. 開 <https://sheets.new> 命名「中橋季刊投稿」→ 右上「共用」→ 貼服務帳戶信箱
   （`portal-bot@....iam.gserviceaccount.com`）→ 權限「編輯者」。
5. `secrets.toml` 填 `[google] sheet_url` 與 `[gcp_service_account]`（JSON 逐欄貼上，
   `private_key` 的 `\n` 保留）。

---

## 📧 設定三：投稿通知信（選用）

1. 寄件信箱（例 `lyf1228@gmail.com`）先開**兩步驟驗證**，再到
   <https://myaccount.google.com/apppasswords> 產生「應用程式密碼」（16 碼）。
2. `secrets.toml` 填：
   ```toml
   [email]
   sender = "lyf1228@gmail.com"
   app_password = "16 碼"
   recipients = ["lyf1228@gmail.com", "shon.yang@gmail.com"]
   ```

---

## ☁️ 部署到 Streamlit Community Cloud

1. 專案已在 GitHub：`https://github.com/lyf1228/bridge-submission-portal`。
2. <https://share.streamlit.io> → 用 GitHub 帳號登入 → **New app**
   → Repository `lyf1228/bridge-submission-portal`、Branch `main`、Main file `app.py`。
3. **Advanced settings → Secrets**：把整份 `secrets.toml` 內容貼進去。
4. **Deploy**，取得公開網址後貼給投稿者。

> ⚠️ Streamlit Cloud 本機檔案系統是**暫存**的，重啟後 `submissions/` 會清空。
> 因此雲端部署務必至少完成「設定一（Google Drive）」，投稿檔案才會安全落在你的雲端硬碟。

---

## 🔐 安全提醒
- `submissions/`（讀者個資、原始稿件）與 `secrets.toml`（金鑰、密碼、Web App 網址）
  都已在 `.gitignore` 排除。
- 上線請把 `admin_password` 改成強密碼。
- Apps Script 的 `TOKEN` 就是防止別人亂丟檔案的關卡，別外流；要換就改 `.gs` 再重新部署。
- 服務帳戶金鑰或應用程式密碼若外洩，到 Google 對應頁面刪除即可，不影響個人帳號。
