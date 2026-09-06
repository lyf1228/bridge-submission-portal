# 🍁 中橋季刊 · 線上投稿與後台審稿系統

**Bridge Magazine Portal** — 秋日紅楓 × 和風時計主題的 Streamlit 網站，
一套系統同時做兩件事：

| 對象 | 用途 |
|---|---|
| **投稿者**（橋友，免登入） | 填表單、貼／上傳文章、上傳多張照片＋圖說 |
| **編輯**（帳密登入） | 依年份季別檢視所有投稿全文、圖說、下載原檔 |

送出的每一筆投稿會**同時**存到 4 個地方（見下方〈資料流向〉），
編輯不必守著網站，投稿一進來就會收到 email。

---

## 目錄

1. [投稿者怎麼用](#投稿者怎麼用)
2. [編輯怎麼用](#編輯怎麼用)
3. [資料流向：投稿存到哪裡](#資料流向投稿存到哪裡)
4. [本系統目前的部署資訊](#本系統目前的部署資訊)
5. [本機開發啟動](#本機開發啟動)
6. [完整設定教學（重建時看這裡）](#完整設定教學重建時看這裡)
7. [維護與更新](#維護與更新)
8. [疑難排解](#疑難排解)
9. [檔案結構](#檔案結構)
10. [安全須知](#安全須知)

---

## 投稿者怎麼用

1. 打開編輯給的網址（`https://<名稱>.streamlit.app`）。
2. 依序填：
   - **投稿期別**：西元年份 ＋ 春／夏／秋／冬季號
   - **投稿者姓名、聯絡 Email**（會做 Email 格式檢查）
   - **文章標題**、**建議刊登單元**
     （焦點快訊／橋海漫遊／橋藝教室／橋訊公告／讀者心得）
   - **文章內文**：可「線上直接貼純文字」，或「上傳 DOCX / PDF」
     （系統會自動抽出純文字回填，可再修改）
   - **照片**：可一次多張（PNG／JPG／JPEG），**每張有獨立的圖說欄位**
3. 若稿件有牌局覆盤，表單上方有按鈕可先去
   [牌局與叫牌排版工作台](https://bridge-diagram-generator.streamlit.app/) 做高畫質牌圖，再回來上傳。
4. 按「🍁 送出投稿」→ 出現楓葉感謝回條即完成。

---

## 編輯怎麼用

1. 開同一個網址，左側欄點「🔐 編輯後台登入」。
2. 輸入帳號密碼（設定在 secrets 的 `[app]`，見〈部署資訊〉）。
3. 登入後：
   - 左側欄會顯示 Google Drive／Sheets／通知信三個管道的連線狀態
   - 主畫面「後台審稿管理總覽」：
     - 上方可依 **年份** 與 **季別** 篩選
     - 清單表格：投稿時間、投稿人、Email、標題、分類、照片數
     - 點任一筆展開：**放大字級**的完整內文、每張照片圖說、
       「開啟這篇投稿的 Google Drive 資料夾」連結、下載原始文檔／整包 ZIP
4. 想拿**印刷級照片原檔** → 點該篇的 Drive 資料夾連結，或去收件信箱找那封投稿通知信的附件。

---

## 資料流向：投稿存到哪裡

一筆投稿送出後，系統依 `secrets.toml` 有設定哪些區塊，把資料送到對應的地方
（可同時開啟多個；沒設定的就自動略過）：

| # | 目的地 | secrets 區塊 | 內容 |
|---|---|---|---|
| 1 | **本機資料夾** `submissions/<年>_<季>/<時間>_<投稿者>/` | 無（一定會做） | `content.txt`、原始照片、原始文檔、`metadata.json` |
| 2 | **Google Drive** 目標資料夾下的子資料夾 `投稿者姓名＿文章標題` | `[drive]` | `文章內文.txt`、原始照片、原始文檔、`metadata.json` |
| 3 | **Google Sheets** 總表新增一列 | `[google]` + `[gcp_service_account]` | 時間／期別／投稿人／Email／標題／分類／全文／照片數／圖說／**該篇 Drive 連結** |
| 4 | **Email** 給編輯部（可多位收件人） | `[email]` | 全文正文 ＋ 所有原始照片、文檔附件；回覆會回到投稿者 |

> ⚠️ **部署到 Streamlit Cloud 時，第 1 項（本機）會在容器重啟後消失。**
> 所以雲端版務必至少設定 `[drive]` 或 `[email]`，投稿檔案才會安全保存。

---

## 本系統目前的部署資訊

> 機密值（金鑰、密碼、Web App 網址）不寫在這裡也不進 Git，
> 集中在本機的 `我的設定值.local.md`（已被 `.gitignore` 排除）。

| 項目 | 值 |
|---|---|
| GitHub | <https://github.com/lyf1228/bridge-submission-portal>（公開，branch `main`） |
| 線上網址 | `https://<部署時取的名稱>.streamlit.app`（名稱不可含 `portal`） |
| 後台帳號 | 設定在 Streamlit Cloud 的 Secrets `[app]` |
| Google Drive 目標資料夾 | <https://drive.google.com/drive/folders/1EoO3z1L0lz6MgryLPeJby_GRPHMHvO-R> |
| Google Sheets 總表 | 「中橋季刊投稿」（服務帳戶 `portal-bot@…` 已共用為編輯者） |
| Apps Script 專案 | 「中橋季刊投稿－Drive 收檔」（script.google.com，執行身分＝擁有者） |
| 投稿通知信收件人 | `lyf1228@gmail.com`、`shon.yang@gmail.com` |

---

## 本機開發啟動

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

- 瀏覽器開 `http://localhost:8501`
- 本機設定放 `.streamlit/secrets.toml`（見下方教學；此檔不進 Git）
- 完全沒有 `secrets.toml` 也能跑：投稿只存本機 `submissions/`，後台讀本機資料

---

## 完整設定教學（重建時看這裡）

三個區塊都是**選填、可任意搭配**。把值填進 `.streamlit/secrets.toml`
（本機開發用）以及 Streamlit Cloud 的 **App → Settings → Secrets**（雲端用）。

### 設定一：Google Drive（存投稿檔案）

個人 Gmail 的服務帳戶沒有雲端硬碟容量，無法直接寫入 Drive。
做法：在自己的 Google 帳號下部署一支 Apps Script，以「你的身分」把檔案寫進資料夾。

1. <https://script.google.com/> → **新增專案**
2. 把 [`apps_script.gs`](apps_script.gs) 整段貼進 `Code.gs`（覆蓋原有內容）
3. 改最上面兩行：
   - `ROOT_FOLDER_ID`：目標資料夾 ID（資料夾網址 `/folders/` 後那串；已預填）
   - `TOKEN`：自訂一組通關字串（英數）
4. 右上 **部署 → 新增部署作業 → 網頁應用程式**
   - 執行身分：**我**
   - 誰可以存取：**任何人**
   - 部署 → 授權（出現「Google 未驗證」→ 進階 → 前往…（不安全）→ 允許）
5. 複製「網頁應用程式」網址（`…/exec` 結尾）
6. 填 secrets：
   ```toml
   [drive]
   token = "和 apps_script.gs 裡 TOKEN 一字不差"
   webapp_url = "剛剛複製的 …/exec 網址"
   ```

### 設定二：Google Sheets（彙整總表）

1. <https://console.cloud.google.com/> → 新增專案
2. 「☰ → API 和服務 → 程式庫」→ 啟用 **Google Sheets API**
3. 「憑證 → 建立憑證 → 服務帳戶」名稱 `portal-bot` → 建立
4. 點進該服務帳戶 → 分頁「**金鑰 / KEYS**」→ 新增金鑰 → JSON → 下載
5. <https://sheets.new> 建試算表「中橋季刊投稿」→ 右上「共用」→
   貼服務帳戶信箱（`portal-bot@專案.iam.gserviceaccount.com`）→ 權限「**編輯者**」
6. 填 secrets：
   ```toml
   [google]
   sheet_url = "你的試算表完整網址"

   [gcp_service_account]
   type = "service_account"
   project_id = "…"
   private_key_id = "…"
   # ↓ 用三引號多行，直接貼 PEM，不要用 \n（貼到 Streamlit 才不會壞）
   private_key = """
   -----BEGIN PRIVATE KEY-----
   MIIE…（很多行）…
   -----END PRIVATE KEY-----
   """
   client_email = "portal-bot@專案.iam.gserviceaccount.com"
   client_id = "…"
   token_uri = "https://oauth2.googleapis.com/token"
   ```

### 設定三：投稿通知信（Gmail SMTP）

1. 寄件信箱開啟**兩步驟驗證** → <https://myaccount.google.com/apppasswords> 產生「應用程式密碼」（16 碼）
2. 填 secrets：
   ```toml
   [email]
   sender = "lyf1228@gmail.com"
   app_password = "abcd efgh ijkl mnop"
   recipients = ["lyf1228@gmail.com", "shon.yang@gmail.com"]
   ```

### 部署到 Streamlit Community Cloud

1. <https://share.streamlit.io> → GitHub 帳號登入 → **New app** → **從現有 repo 部署**
2. Repository `lyf1228/bridge-submission-portal`、Branch **`main`**、Main file **`app.py`**
3. **App URL** 取一個名稱（**不能含 `portal`**，例：`bridge-magazine-submission`）
4. **Advanced settings → Secrets** → 貼上整份 secrets 內容 → 儲存
5. **Deploy**，2–5 分鐘後取得公開網址

---

## 維護與更新

- **改程式**：本機改好 → `git push` 到 `main` → Streamlit Cloud 會**自動重新部署**。
- **改設定（金鑰／密碼／收件人）**：App → **⋮ → Settings → Secrets** 改完 Save，
  約 1 分鐘生效。本機的 `.streamlit/secrets.toml` 記得同步改。
- **改 Apps Script**：改完 `Code.gs` → **部署 → 管理部署作業 → 編輯(鉛筆) →
  版本選「新版本」→ 部署**（網址不變）。只按儲存不重新部署不會生效。
- **Streamlit 自動加的 commit**：首次部署後 Streamlit 會 push 一個
  `Added Dev Container Folder`（`.devcontainer/`），下次本機 `git pull` 收下即可。

---

## 疑難排解

| 症狀 | 原因 / 解法 |
|---|---|
| 部署表單「This repository does not exist」 | repo 是私有的，Streamlit 看不到 → 改公開，或到 <https://github.com/settings/installations> 授權 Streamlit 存取該 repo |
| 部署表單「This branch does not exist」 | branch 欄填成 `master` → 改 **`main`** |
| App URL「can't include the term 'portal'」 | 換一個不含 `portal` 的名稱 |
| 後台「後台尚未設定密碼」 | Streamlit 的 Secrets 沒貼、或沒有 `[app]` 區塊 → 補上並 Save |
| 後台「Invalid private key」 | 貼進 Secrets 的 `private_key` 壞了 → 改用**三引號多行**格式重貼（見設定二） |
| 後台「Invalid format: please enter valid TOML」 | 貼到不完整或含說明文字（如「…中間很多行…」）→ 貼**完整**內容 |
| 打開 Google 試算表顯示「無法開啟這個檔案」 | 瀏覽器登入的 Google 帳號不是擁有者 → 切換到擁有者帳號 |
| 投稿回條只出現部分管道 | 該管道的 secrets 沒設定或設定錯 → 登入後台看左側欄狀態文字 |

---

## 檔案結構

```
bridge-submission-portal/
├── app.py                        # 主程式：表單 + 後台 + 檔案解析 + 楓葉時計 CSS/SVG
├── storage.py                    # Google Sheets 後端（gspread）
├── gdrive.py                     # Google Drive 後端（POST 給 Apps Script）
├── mailer.py                     # Gmail SMTP 投稿通知信
├── apps_script.gs                # 要貼到 script.google.com 的 Drive 收檔程式
├── requirements.txt
├── README.md
├── .gitignore
├── .devcontainer/                # Streamlit Cloud 自動產生
├── .streamlit/
│   ├── secrets.toml.example      # 設定範本
│   └── secrets.toml              # 你的實際設定（不進 Git）
├── 我的設定值.local.md            # 個人機密備份（不進 Git，*.local.* 規則）
└── submissions/                  # 執行後自動產生（不進 Git）
```

字級：全站 base 17px、文章內文／圖說約 20px（≥ 14pt），方便長時間審稿。

---

## 安全須知

- **不進 Git**：`submissions/`（讀者個資）、`.streamlit/secrets.toml`、任何 `*.local.*` 檔。
  推之前先 `git status` 確認這些沒被加進去。
- 後台密碼、服務帳戶金鑰、Gmail 應用程式密碼、Apps Script `TOKEN` —— 任何一個外洩：
  到對應的 Google 頁面撤銷／重建即可，不影響你的個人帳號主體。
- `TOKEN` 是 Apps Script 唯一的門禁（擋別人亂丟檔案到你 Drive），要換就 `.gs` 和 secrets 兩邊一起改並重新部署。
- 原始碼本身不含任何機密：帳密只從 `st.secrets` 讀，未設定時後台無法登入。
