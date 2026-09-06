# -*- coding: utf-8 -*-
"""
Google Sheets 儲存後端
---------------------
- 未在 st.secrets 設定服務帳戶時：`is_enabled()` 回傳 False，呼叫端自動退回本機
  `submissions/` 資料夾。
- 已設定時：每筆投稿 append 一列到指定的 Google Sheet（人類可讀）。

照片本身不進試算表（見 mailer.py，改用 email 寄送原檔）；試算表只記圖說與檔名。

需要的 st.secrets 結構見 `.streamlit/secrets.toml.example`。
"""

from __future__ import annotations

import streamlit as st

# Google Sheet 的欄位標題（第一列）
SHEET_HEADERS = [
    "投稿時間",
    "年份",
    "季別",
    "投稿人",
    "Email",
    "文章標題",
    "建議分類",
    "內文輸入方式",
    "文章內文",
    "照片數",
    "照片圖說",
    "原始文檔",
    "Drive資料夾",
    "本機資料夾",
]

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


# --------------------------------------------------------------------------- #
# 內部：憑證與工作表
# --------------------------------------------------------------------------- #
def _has_secrets() -> bool:
    try:
        return "gcp_service_account" in st.secrets and "google" in st.secrets
    except Exception:  # noqa: BLE001 - st.secrets 不存在時會丟例外
        return False


@st.cache_resource(show_spinner=False)
def _gspread_client():
    from google.oauth2.service_account import Credentials
    import gspread

    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def _worksheet():
    """開啟目標工作表，必要時補上標題列。"""
    gc = _gspread_client()
    conf = st.secrets["google"]
    if conf.get("sheet_url"):
        spreadsheet = gc.open_by_url(conf["sheet_url"])
    elif conf.get("sheet_id"):
        spreadsheet = gc.open_by_key(conf["sheet_id"])
    else:
        raise RuntimeError("secrets[google] 需要 sheet_url 或 sheet_id")

    worksheet = spreadsheet.sheet1
    if not worksheet.row_values(1):
        worksheet.append_row(SHEET_HEADERS, value_input_option="USER_ENTERED")
    return worksheet


# --------------------------------------------------------------------------- #
# 對外 API
# --------------------------------------------------------------------------- #
def refresh() -> None:
    """清掉連線快取，讓下一次讀取重新連 Google。"""
    for fn in (_gspread_client, _worksheet):
        try:
            fn.clear()
        except Exception:  # noqa: BLE001
            pass


def is_enabled() -> bool:
    if not _has_secrets():
        return False
    try:
        _gspread_client()
        return True
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Google 憑證載入失敗，暫時改用本機儲存：{exc}")
        return False


def status_text() -> str:
    if not _has_secrets():
        return "未設定（資料存於本機 submissions/ 資料夾）"
    try:
        ws = _worksheet()
        return f"已連線 · 工作表「{ws.spreadsheet.title}」"
    except Exception as exc:  # noqa: BLE001
        return f"設定有誤：{exc}"


def _photos_cell(photos: list[dict]) -> str:
    lines: list[str] = []
    for idx, p in enumerate(photos, start=1):
        caption = (p.get("caption") or "(未填圖說)").replace("\n", " ")
        fname = p.get("filename", "")
        lines.append(f"{idx}. {caption}　[{fname}]" if fname else f"{idx}. {caption}")
    return "\n".join(lines)


def append_submission(meta: dict) -> bool:
    """把一筆投稿 append 到 Google Sheet。成功回傳 True。"""
    try:
        worksheet = _worksheet()
        worksheet.append_row(
            [
                meta.get("submitted_at", ""),
                meta.get("year", ""),
                meta.get("season", ""),
                meta.get("submitter_name", ""),
                meta.get("email", ""),
                meta.get("title", ""),
                meta.get("category", ""),
                meta.get("content_mode", ""),
                meta.get("content", ""),
                meta.get("photo_count", 0),
                _photos_cell(meta.get("photos", [])),
                meta.get("original_document", ""),
                meta.get("drive_folder_url", ""),
                meta.get("folder", ""),
            ],
            value_input_option="USER_ENTERED",
        )
        return True
    except Exception as exc:  # noqa: BLE001
        st.warning(f"寫入 Google Sheets 失敗（本機仍有完整備份）：{exc}")
        return False


def _parse_photos_cell(text: str) -> list[dict]:
    photos: list[dict] = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line[:1].isdigit() and ". " in line:
            line = line.split(". ", 1)[1]
        fname = ""
        if line.endswith("]") and "[" in line:
            line, fname = line[: line.rfind("[")], line[line.rfind("[") + 1 : -1]
        photos.append({"caption": line.strip("　 "), "filename": fname.strip()})
    return photos


def read_submissions() -> list[dict]:
    """從 Google Sheet 讀回所有投稿，格式與本機 metadata 對齊。"""
    try:
        worksheet = _worksheet()
        try:
            rows = worksheet.get_all_records(expected_headers=SHEET_HEADERS)
        except Exception:  # noqa: BLE001 - 舊表頭欄位不同時，改用寬鬆讀法
            rows = worksheet.get_all_records()
    except Exception as exc:  # noqa: BLE001
        st.error(f"讀取 Google Sheets 失敗：{exc}")
        return []

    result: list[dict] = []
    for r in rows:
        if not any(str(v).strip() for v in r.values()):
            continue
        result.append(
            {
                "submitted_at": str(r.get("投稿時間", "")),
                "year": r.get("年份", ""),
                "season": str(r.get("季別", "")),
                "submitter_name": str(r.get("投稿人", "")),
                "email": str(r.get("Email", "")),
                "title": str(r.get("文章標題", "")),
                "category": str(r.get("建議分類", "")),
                "content_mode": str(r.get("內文輸入方式", "")),
                "content": str(r.get("文章內文", "")),
                "photo_count": r.get("照片數", 0),
                "photos": _parse_photos_cell(r.get("照片圖說", "")),
                "original_document": str(r.get("原始文檔", "")),
                "drive_folder_url": str(r.get("Drive資料夾", "")),
                "folder": str(r.get("本機資料夾", "")),
                "_source": "sheet",
            }
        )
    result.sort(key=lambda m: m.get("submitted_at", ""), reverse=True)
    return result
