# -*- coding: utf-8 -*-
"""
中橋季刊線上投稿與後台審稿系統 (Bridge Magazine Portal)
------------------------------------------------------
秋日紅楓風格

功能：
  模組一：前台讀者投稿表單（免登入）
  模組二：後台編輯審稿管理區（帳密驗證）

Designed & Developed by LuLu
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image

import gdrive
import mailer
import storage

# --------------------------------------------------------------------------- #
# 常數設定
# --------------------------------------------------------------------------- #
APP_TITLE = "中橋季刊 · 線上投稿與審稿系統"
SUBMISSIONS_DIR = Path(__file__).parent / "submissions"


def _secret(section: str, key: str, default: str) -> str:
    """讀 st.secrets[section][key]，未設定時回傳 default。"""
    try:
        return str(st.secrets[section][key])
    except Exception:  # noqa: BLE001
        return default


# 管理員帳密：優先讀 secrets[app]，未設定時用預設值
# 管理員帳密只從 st.secrets[app] 讀取（原始碼不放預設密碼）。
# 本機用 .streamlit/secrets.toml，雲端用 Streamlit Cloud 的 Secrets。
ADMIN_USERNAME = _secret("app", "admin_username", "admin")
ADMIN_PASSWORD = _secret("app", "admin_password", "")

DIAGRAM_TOOL_URL = "https://bridge-diagram-generator.streamlit.app/"

SEASONS = ["春季號", "夏季號", "秋季號", "冬季號"]
SEASON_KEY = {"春季號": "春", "夏季號": "夏", "秋季號": "秋", "冬季號": "冬"}

CATEGORIES = [
    "焦點快訊（重大賽事戰報、大賽報導）",
    "橋海漫遊（人物專訪、歷史回顧、交流故事、文藝隨筆）",
    "橋藝教室（牌理教學、Bridge Master 解析、叫牌制度研討）",
    "橋訊公告（協會會務、賽程資訊、榜單公文）",
    "讀者心得（參賽感想、社團交流感言）",
]

IMAGE_EXTS = {".png", ".jpg", ".jpeg"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --------------------------------------------------------------------------- #
# 頁面設定與主題樣式（秋日紅楓風格）
# --------------------------------------------------------------------------- #
st.set_page_config(page_title=APP_TITLE, page_icon="🍁", layout="centered")

CUSTOM_CSS = """
<style>
:root {
    --maple-red-1: #BA181B;
    --maple-red-2: #9E2A2B;
    --amber-gold: #D4A373;
    --parchment:  #FAF8F5;
    --walnut:     #2B231F;
}

/* 全域底色與文字 */
.stApp {
    background-color: var(--parchment);
    color: var(--walnut);
}
.stApp, .stApp p, .stApp label, .stApp span, .stApp div {
    font-family: "Noto Serif TC", "Songti TC", "Yu Mincho", "Georgia", serif;
}
h1, h2, h3, h4 {
    color: var(--maple-red-2) !important;
    letter-spacing: 0.04em;
}

/* ---- 放大字級，方便閱讀（內文 ≥ 14pt） ---- */
html, body, .stApp { font-size: 17px; }
.stApp p, .stApp li, .stApp label,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
    font-size: 1.06rem !important;      /* ≈ 18px */
    line-height: 1.9;
}
.stApp h3 { font-size: 1.5rem !important; }
.stApp h4 { font-size: 1.22rem !important; }
/* 表單輸入文字 */
.stTextInput input, .stNumberInput input,
.stSelectbox div[data-baseweb="select"] div,
.stRadio label p, [data-testid="stWidgetLabel"] p {
    font-size: 1.05rem !important;
}
/* 文章內文／圖說等閱讀區塊 ≈ 15pt */
.stTextArea textarea {
    font-size: 1.18rem !important;      /* ≈ 20px */
    line-height: 1.95;
}
.mp-article {
    font-size: 1.2rem;
    line-height: 2.05;
    white-space: pre-wrap;
    color: var(--walnut);
}
.mp-caption { font-size: 1.08rem; color: #5f4b3f; }
[data-testid="stDataFrame"] { font-size: 1.02rem; }
.stButton > button, .stDownloadButton > button,
.stFormSubmitButton > button, .stLinkButton > a {
    font-size: 1.06rem !important;
}

/* 頂部橫幅：簡潔米白，只有標題旁一朵楓葉 */
.mp-header {
    margin: -1rem -1rem 1.6rem -1rem;
    padding: 2rem 1.4rem 1.5rem 1.4rem;
    background: linear-gradient(135deg, #fdfbf8 0%, #f6efe6 100%);
    border-bottom: 2px solid var(--amber-gold);
}
.mp-header h1 {
    margin: 0;
    font-size: 1.9rem;
    color: var(--maple-red-1) !important;
}
.mp-header .mp-sub {
    margin-top: 0.35rem;
    font-size: 0.95rem;
    color: #6f5b4e;
    letter-spacing: 0.14em;
}
.mp-leaf-strip {
    margin-top: 1rem;
    height: 3px;
    background: repeating-linear-gradient(
        90deg,
        var(--maple-red-1) 0 22px,
        var(--amber-gold) 22px 30px,
        transparent 30px 52px
    );
    border-radius: 2px;
}

/* 卡片：圓角細邊框 + 微光陰影 */
.mp-card {
    background: #ffffff;
    border: 1px solid rgba(212,163,115,0.55);
    border-radius: 16px;
    padding: 1.25rem 1.4rem;
    margin: 0.9rem 0 1.2rem 0;
    box-shadow: 0 6px 22px rgba(158,42,43,0.08), 0 1px 0 rgba(255,255,255,0.7) inset;
}
.mp-info {
    background: linear-gradient(135deg, #fff7ee 0%, #fdeede 100%);
    border: 1px solid var(--amber-gold);
    border-left: 5px solid var(--maple-red-1);
    border-radius: 12px;
    padding: 1rem 1.15rem;
    margin: 0.8rem 0 1.1rem 0;
    font-size: 0.94rem;
    line-height: 1.7;
}
.mp-receipt {
    background: linear-gradient(135deg, #fff8f0 0%, #f7e9d9 100%);
    border: 1.5px dashed var(--maple-red-2);
    border-radius: 16px;
    padding: 1.4rem 1.5rem;
    margin: 1rem 0;
    text-align: center;
}
.mp-receipt h3 { color: var(--maple-red-1) !important; margin-top: 0; }

/* 楓金漸層按鈕 */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
    background: linear-gradient(135deg, var(--maple-red-1) 0%, var(--amber-gold) 130%);
    color: #fff;
    border: none;
    border-radius: 10px;
    padding: 0.5rem 1.2rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    transition: transform 0.12s ease, box-shadow 0.12s ease;
    box-shadow: 0 4px 14px rgba(186,24,27,0.25);
}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 7px 20px rgba(186,24,27,0.35);
    color: #fff;
}
.stLinkButton > a {
    background: linear-gradient(135deg, #7a3b12 0%, var(--amber-gold) 130%) !important;
    color: #fff !important;
    border-radius: 10px !important;
    border: none !important;
    letter-spacing: 0.05em;
}

/* 有框容器 -> 卡片：圓角細邊框 + 微光陰影 */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff;
    border: 1px solid rgba(212,163,115,0.55) !important;
    border-radius: 16px !important;
    padding: 0.4rem 1.15rem 0.9rem 1.15rem;
    box-shadow: 0 6px 22px rgba(158,42,43,0.08), 0 1px 0 rgba(255,255,255,0.7) inset;
    margin-bottom: 0.4rem;
}

/* 檔案上傳區：拉寬按鈕、文字不擠、隱藏未載入的圖示 ligature */
[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"] {
    padding: 1rem 1.2rem;
    border-radius: 12px;
    align-items: center;
    gap: 1rem;
}
[data-testid="stFileUploader"] button,
[data-testid="stFileUploaderDropzone"] button {
    min-width: 150px;
    white-space: nowrap;
    padding: 0.5rem 1.4rem !important;
    font-size: 1rem !important;
    background: linear-gradient(135deg, var(--maple-red-1) 0%, var(--amber-gold) 130%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    letter-spacing: normal !important;
}
/* Google Material Symbols 沒載入時會顯示 "upload" 等文字，藏起來 */
[data-testid="stFileUploaderDropzone"] [data-testid="stFileUploaderDropzoneInstructions"] span:first-child {
    flex: 0 0 auto;
}
[data-testid="stFileUploader"] .material-symbols-rounded,
[data-testid="stFileUploader"] [class*="material-symbols"] {
    font-size: 0 !important;
}

/* 輸入元件外觀 */
.stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
    border-radius: 10px !important;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f7efe4 0%, #f2e5d3 100%);
    border-right: 2px solid var(--amber-gold);
}
hr { border-color: rgba(212,163,115,0.5); }
</style>
"""

# 頂部橫幅：只保留標題旁一朵楓葉，不再放時鐘與散落葉片
HEADER_HTML = f"""
{CUSTOM_CSS}
<div class="mp-header">
  <h1>🍁 中橋季刊 · 線上投稿與審稿系統</h1>
  <div class="mp-sub">B R I D G E &nbsp; M A G A Z I N E &nbsp; P O R T A L &nbsp;— &nbsp;光陰流轉 · 季刊編採</div>
  <div class="mp-leaf-strip"></div>
</div>
"""


# --------------------------------------------------------------------------- #
# 工具函式
# --------------------------------------------------------------------------- #
def _html_escape(text: str) -> str:
    """最小化 HTML 轉義，供內文安全嵌入自訂樣式區塊。"""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def drive_folder_name(name: str, title: str) -> str:
    """Google Drive 子資料夾名稱：投稿者姓名＿文章標題（去掉不合法字元）。"""
    raw = f"{name.strip()}＿{title.strip()}"
    raw = re.sub(r'[\\/:*?"<>|]', "", raw)      # Drive／作業系統禁用字元
    raw = re.sub(r"\s+", " ", raw).strip(" ＿_")
    return raw[:120] or "未命名投稿"


def slugify(text: str) -> str:
    """把姓名整理成安全的資料夾名稱片段。"""
    text = re.sub(r"\s+", "_", text.strip())
    text = re.sub(r"[^0-9A-Za-z一-鿿_\-]", "", text)
    return text or "anonymous"


def extract_text_from_docx(data: bytes) -> str:
    """使用 python-docx 提取 Word 內文純文字。"""
    import docx  # python-docx

    document = docx.Document(io.BytesIO(data))
    lines: list[str] = [p.text for p in document.paragraphs]
    # 併入表格文字
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                lines.append(" | ".join(cells))
    return "\n".join(lines).strip()


def extract_text_from_pdf(data: bytes) -> str:
    """使用 pypdf 解析 PDF 文字。"""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return "\n\n".join(pages).strip()


def parse_document(uploaded_file) -> str:
    """依副檔名選擇解析器，回傳純文字。"""
    name = (uploaded_file.name or "").lower()
    data = uploaded_file.getvalue()
    if name.endswith(".docx"):
        return extract_text_from_docx(data)
    if name.endswith(".pdf"):
        return extract_text_from_pdf(data)
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="replace").strip()
    raise ValueError("僅支援 .docx / .pdf / .txt 檔案")


def season_folder(year: int, season: str) -> str:
    return f"{year}_{SEASON_KEY.get(season, season)}"


def list_submissions() -> list[dict]:
    """掃描 submissions 目錄，回傳所有投稿 metadata（含資料夾路徑）。"""
    results: list[dict] = []
    if not SUBMISSIONS_DIR.exists():
        return results
    for meta_path in sorted(SUBMISSIONS_DIR.glob("*/*/metadata.json")):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        meta["_dir"] = str(meta_path.parent)
        results.append(meta)
    results.sort(key=lambda m: m.get("submitted_at", ""), reverse=True)
    return results


def build_zip(folder: Path) -> bytes:
    """把投稿資料夾打包成 zip（記憶體）。"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(folder))
    buffer.seek(0)
    return buffer.read()


# --------------------------------------------------------------------------- #
# 模組一：前台投稿表單
# --------------------------------------------------------------------------- #
def render_submission_form() -> None:
    st.subheader("📮 讀者投稿表單")
    st.caption("歡迎橋友賜稿！請填寫以下欄位，標示 * 為必填。")

    # --- 期別設定 ---
    with st.container(border=True):
        st.markdown("#### 一、投稿期別設定 *")
        col_y, col_s = st.columns([1, 1.4])
        with col_y:
            year = st.number_input("西元年份 *", min_value=2000, max_value=2100,
                                   value=2026, step=1)
        with col_s:
            season = st.radio("刊物季別 *", SEASONS, horizontal=True)

    # --- 投稿者資料 ---
    with st.container(border=True):
        st.markdown("#### 二、投稿者基本資料 *")
        name = st.text_input("投稿者姓名 *", placeholder="王小明")
        email = st.text_input("聯絡 Email *", placeholder="you@example.com")

    # --- 稿件資訊 ---
    with st.container(border=True):
        st.markdown("#### 三、稿件基本資訊 *")
        title = st.text_input("文章標題 *", placeholder="例：全國團體賽冠軍之路")
        category = st.selectbox("建議刊登單元類別 *", CATEGORIES)

    # --- 牌局圖卡製作指引 ---
    st.markdown(
        f"""
        <div class="mp-info">
        💡 <b>貼心提醒</b>：若您的稿件包含牌局覆盤或叫牌討論，建議先前往
        <b>【牌局與叫牌排版工作台】</b>製作高畫質牌圖照片檔，
        完成後再於下方「照片上傳區」上傳插圖！
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.link_button("🃏 前往牌局與叫牌排版工作台（另開新視窗）", DIAGRAM_TOOL_URL)

    # --- 內文輸入 ---
    with st.container(border=True):
        st.markdown("#### 四、文章內文 *")
        mode = st.radio(
            "內文輸入方式",
            ["線上直接貼純文字", "上傳文件檔（DOCX / PDF）"],
            horizontal=True,
        )

        doc_file = None
        if mode == "上傳文件檔（DOCX / PDF）":
            doc_file = st.file_uploader(
                "上傳文章檔（.docx / .pdf）",
                type=["docx", "pdf", "txt"],
                accept_multiple_files=False,
                key="doc_file",
            )
            if doc_file is not None:
                try:
                    parsed_text = parse_document(doc_file)
                    st.success(
                        f"已解析「{doc_file.name}」，共 {len(parsed_text)} 字，可於下方微調。"
                    )
                    if st.button("↩️ 以解析結果覆寫下方編輯框"):
                        st.session_state["content_body"] = parsed_text
                        st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"解析失敗：{exc}")

        content_body = st.text_area(
            "文章純文字內容（可預覽與微調）*",
            height=300,
            key="content_body",
        )

    # --- 照片與圖說 ---
    with st.container(border=True):
        st.markdown("#### 五、活動／牌局照片上傳與圖說")
        photos = st.file_uploader(
            "上傳照片（可多張，PNG / JPG / JPEG）",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="photos",
        )
        captions: list[str] = []
        if photos:
            for idx, photo in enumerate(photos):
                c1, c2 = st.columns([1, 2])
                with c1:
                    try:
                        st.image(photo, use_container_width=True)
                    except Exception:  # noqa: BLE001
                        st.write(photo.name)
                with c2:
                    cap = st.text_input(
                        f"照片 {idx + 1} 圖說（{photo.name}）",
                        key=f"caption_{idx}",
                        placeholder="請輸入這張照片的圖說…",
                    )
                    captions.append(cap)

    # --- 送出 ---
    submitted = st.button("🍁 送出投稿", use_container_width=True)
    if not submitted:
        return

    # 驗證
    errors: list[str] = []
    if not name.strip():
        errors.append("請填寫投稿者姓名。")
    if not email.strip() or not EMAIL_RE.match(email.strip()):
        errors.append("請填寫正確格式的聯絡 Email。")
    if not title.strip():
        errors.append("請填寫文章標題。")
    if not content_body.strip():
        errors.append("文章內文不可空白（請貼上文字或上傳檔案解析）。")
    if errors:
        for e in errors:
            st.error(e)
        return

    # 建立資料夾
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = SUBMISSIONS_DIR / season_folder(int(year), season) / f"{timestamp}_{slugify(name)}"
    folder.mkdir(parents=True, exist_ok=True)

    # 儲存原始文檔
    doc_saved = ""
    if doc_file is not None:
        doc_saved = doc_file.name
        (folder / doc_file.name).write_bytes(doc_file.getvalue())

    # 儲存內文
    (folder / "content.txt").write_text(content_body.strip(), encoding="utf-8")

    # 儲存照片（本機一律留一份），並蒐集雲端上傳 / email 附件
    google_on = storage.is_enabled()
    mail_on = mailer.is_enabled()
    drive_on = gdrive.is_enabled()
    photo_records: list[dict] = []
    files_payload: list[dict] = []
    with st.spinner("正在儲存投稿…"):
        for idx, photo in enumerate(photos or []):
            ext = Path(photo.name).suffix.lower()
            if ext not in IMAGE_EXTS:
                ext = ".png"
            fname = f"photo_{idx + 1:02d}{ext}"
            data = photo.getvalue()
            (folder / fname).write_bytes(data)
            photo_records.append({
                "filename": fname,
                "original_name": photo.name,
                "caption": (captions[idx] if idx < len(captions) else "").strip(),
            })
            files_payload.append({
                "filename": fname,
                "data": data,
                "mime": photo.type or "image/jpeg",
            })

        if doc_file is not None:
            files_payload.append({
                "filename": doc_file.name,
                "data": doc_file.getvalue(),
                "mime": doc_file.type or "application/octet-stream",
            })

        # 內文純文字也一起帶上雲端
        content_bytes = content_body.strip().encode("utf-8")
        files_payload.append({
            "filename": "文章內文.txt",
            "data": content_bytes,
            "mime": "text/plain",
        })

        # metadata.json
        submitted_at = datetime.now().isoformat(timespec="seconds")
        subfolder_name = drive_folder_name(name, title)
        metadata = {
            "year": int(year),
            "season": season,
            "season_key": SEASON_KEY.get(season, season),
            "submitter_name": name.strip(),
            "email": email.strip(),
            "title": title.strip(),
            "category": category,
            "content_mode": mode,
            "content": content_body.strip(),
            "original_document": doc_saved,
            "photos": photo_records,
            "photo_count": len(photo_records),
            "submitted_at": submitted_at,
            "folder": str(folder.relative_to(SUBMISSIONS_DIR.parent)),
            "drive_folder_url": "",
        }

        # 上傳 Google Drive（透過 Apps Script）
        drive_ok = False
        if drive_on:
            up = gdrive.upload_files(
                subfolder_name,
                files_payload
                + [{
                    "filename": "metadata.json",
                    "data": json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"),
                    "mime": "application/json",
                }],
            )
            if up and up.get("folder_url"):
                metadata["drive_folder_url"] = up["folder_url"]
                drive_ok = True

        (folder / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        sheet_ok = storage.append_submission(metadata) if google_on else False
        mail_ok = (
            mailer.send_submission(metadata, files_payload) if mail_on else False
        )

    # 成功回條
    routes: list[str] = []
    if drive_on:
        routes.append("原稿與照片已存入編輯部 Google Drive 📁" if drive_ok else "Drive 上傳未完成")
    if google_on:
        routes.append("已寫入編輯部 Google Sheets ☁️" if sheet_ok else "Google Sheets 同步未完成")
    if mail_on:
        routes.append("已 email 通知編輯部 📧" if mail_ok else "通知信寄送未完成")
    if not routes:
        routes.append("已存編輯部收稿系統")
    where = "　".join(routes)
    st.balloons()
    st.markdown(
        f"""
        <div class="mp-receipt">
          <h3>🍁 投稿成功 · 感謝賜稿 🍁</h3>
          <p>
            <b>{metadata['year']} {metadata['season']}</b><br/>
            投稿人：{metadata['submitter_name']}　|　標題：《{metadata['title']}》<br/>
            建議單元：{metadata['category'].split('（')[0]}　|　照片 {metadata['photo_count']} 張<br/>
            收稿時間：{metadata['submitted_at']}<br/>
            {where}
          </p>
          <p style="font-size:0.95rem;color:#7a6353;">
            編輯部將於審稿後與您聯繫。願橋藝與文字，皆如秋楓般溫潤動人。
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # 清掉草稿
    for k in list(st.session_state.keys()):
        if k.startswith("caption_") or k == "content_body":
            del st.session_state[k]


# --------------------------------------------------------------------------- #
# 模組二：後台審稿管理
# --------------------------------------------------------------------------- #
def render_admin_login() -> None:
    st.sidebar.markdown("### 🔐 編輯後台")
    if st.session_state.get("is_admin"):
        st.sidebar.success(f"已登入：{ADMIN_USERNAME}")
        st.sidebar.caption(f"Google Drive：{gdrive.status_text()}")
        st.sidebar.caption(f"Google Sheets：{storage.status_text()}")
        st.sidebar.caption(f"投稿通知信：{mailer.status_text()}")
        if st.sidebar.button("登出"):
            st.session_state["is_admin"] = False
            st.rerun()
        return

    st.sidebar.caption("編輯者請於此登入以檢視所有投稿內容。")
    if not st.session_state.get("show_login"):
        if st.sidebar.button("🔐 編輯後台登入", use_container_width=True):
            st.session_state["show_login"] = True
            st.rerun()
        return

    with st.sidebar.form("admin_login"):
        u = st.text_input("帳號")
        p = st.text_input("密碼", type="password")
        c1, c2 = st.columns(2)
        ok = c1.form_submit_button("登入", use_container_width=True)
        cancel = c2.form_submit_button("取消", use_container_width=True)
    if cancel:
        st.session_state["show_login"] = False
        st.rerun()
    if ok:
        if not ADMIN_PASSWORD:
            st.sidebar.error("後台尚未設定密碼（請在 secrets 的 [app] 填 admin_password）")
        elif u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            st.session_state["is_admin"] = True
            st.session_state["show_login"] = False
            st.rerun()
        else:
            st.sidebar.error("帳號或密碼錯誤")


def render_admin_panel() -> None:
    st.subheader("🗂️ 後台審稿管理總覽")

    google_on = storage.is_enabled()
    if google_on:
        subs = storage.read_submissions()
        local = list_submissions()
        seen = {(s.get("submitted_at"), s.get("title")) for s in subs}
        extra = [s for s in local if (s.get("submitted_at"), s.get("title")) not in seen]
        subs = subs + extra
        src = "Google Sheets" + ("（＋本機未同步稿件）" if extra else "")
    else:
        subs = list_submissions()
        src = "本機 submissions/ 資料夾"
    st.caption(f"資料來源：{src}")

    if google_on and st.button("🔄 重新連線 / 重新整理"):
        storage.refresh()
        st.rerun()

    if not subs:
        st.info("目前尚無任何投稿。")
        return

    years = sorted({str(s.get("year")) for s in subs if s.get("year") not in (None, "")}, reverse=True)
    col1, col2 = st.columns(2)
    with col1:
        year_filter = st.selectbox("依年份篩選", ["全部"] + years)
    with col2:
        season_filter = st.selectbox("依季別篩選", ["全部"] + SEASONS)

    filtered = subs
    if year_filter != "全部":
        filtered = [s for s in filtered if str(s.get("year")) == year_filter]
    if season_filter != "全部":
        filtered = [s for s in filtered if s.get("season") == season_filter]

    st.caption(f"符合條件的投稿：{len(filtered)} 筆")

    # 清單表格
    st.dataframe(
        [
            {
                "投稿時間": s.get("submitted_at", ""),
                "期別": f"{s.get('year')} {s.get('season')}",
                "投稿人": s.get("submitter_name", ""),
                "Email": s.get("email", ""),
                "文章標題": s.get("title", ""),
                "建議分類": s.get("category", "").split("（")[0],
                "照片數": s.get("photo_count", 0),
            }
            for s in filtered
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # 詳情卡片（同時支援 Google Sheets 與本機兩種來源）
    for i, s in enumerate(filtered):
        uid = s.get("_dir") or f"sheet_{i}_{s.get('submitted_at','')}"
        local_dir = Path(s["_dir"]) if s.get("_dir") else None
        header = (
            f"《{s.get('title') or '(無標題)'}》— {s.get('submitter_name','')}"
            f"　[{s.get('year')} {s.get('season')}]"
        )
        with st.expander(header):
            st.markdown(
                f"**投稿人**：{s.get('submitter_name','')}　|　"
                f"**Email**：{s.get('email','')}　|　"
                f"**收稿**：{s.get('submitted_at','')}"
            )
            st.markdown(f"**建議單元**：{s.get('category','')}")
            if s.get("content_mode"):
                st.markdown(f"**內文輸入方式**：{s.get('content_mode','')}")
            if s.get("drive_folder_url"):
                st.markdown(f"📁 **[開啟這篇投稿的 Google Drive 資料夾]({s['drive_folder_url']})**")

            st.markdown("##### 📄 文章內文")
            body = (s.get("content") or "").strip()
            st.markdown(
                f'<div class="mp-card"><div class="mp-article">{_html_escape(body)}</div></div>',
                unsafe_allow_html=True,
            )
            with st.expander("✏️ 以純文字檢視／複製"):
                st.text_area(
                    "內文純文字", value=body, height=280,
                    key=f"view_{uid}", label_visibility="collapsed",
                )

            photos = s.get("photos", [])
            if photos:
                st.markdown("##### 🖼️ 照片與圖說")
                if not local_dir:
                    st.caption("印刷級原照請見寄至編輯部信箱的投稿通知信附件。")
                for j, p in enumerate(photos):
                    cc1, cc2 = st.columns([1, 2])
                    with cc1:
                        if local_dir and p.get("filename"):
                            img_path = local_dir / p["filename"]
                            if img_path.exists():
                                try:
                                    st.image(str(img_path), use_container_width=True)
                                except Exception:  # noqa: BLE001 - 檔案毀損不應中斷整頁
                                    st.caption(f"（無法預覽 {p['filename']}）")
                            else:
                                st.caption(f"（{p['filename']}）")
                    with cc2:
                        st.markdown(
                            f'<div class="mp-caption"><b>圖 {j + 1} 圖說</b>：'
                            f'{_html_escape(p.get("caption") or "（未填）")}'
                            + (f'　<code>{_html_escape(p["filename"])}</code>' if p.get("filename") else "")
                            + "</div>",
                            unsafe_allow_html=True,
                        )

            # 原始文檔 / ZIP 下載（僅本機來源有實體檔）
            if local_dir:
                if s.get("original_document"):
                    doc_path = local_dir / s["original_document"]
                    if doc_path.exists():
                        st.download_button(
                            f"⬇️ 下載原始文檔（{s['original_document']}）",
                            data=doc_path.read_bytes(),
                            file_name=s["original_document"],
                            key=f"doc_{uid}",
                        )
                st.download_button(
                    "📦 下載本投稿完整打包（ZIP）",
                    data=build_zip(local_dir),
                    file_name=f"{local_dir.name}.zip",
                    mime="application/zip",
                    key=f"zip_{uid}",
                )
            elif s.get("original_document"):
                st.caption(f"原始文檔：{s['original_document']}（存於投稿者本機提交紀錄）")


# --------------------------------------------------------------------------- #
# 主程式
# --------------------------------------------------------------------------- #
def main() -> None:
    st.markdown(HEADER_HTML, unsafe_allow_html=True)
    st.session_state.setdefault("is_admin", False)

    render_admin_login()

    if st.session_state.get("is_admin"):
        render_admin_panel()
    else:
        render_submission_form()

    st.markdown(
        '<hr/><div style="text-align:center;color:#9a8574;font-size:0.82rem;">'
        "中橋季刊編輯部 · Bridge Magazine Portal &nbsp;—&nbsp; Designed &amp; Developed by LuLu"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
