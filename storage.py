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

import json

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
    "AI校對狀態",
    "AI校正後內文",
    "AI修訂對照表",
    "AI校正資料夾",
    "已通知投稿者",
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
    existing = worksheet.row_values(1)
    if not existing:
        worksheet.append_row(SHEET_HEADERS, value_input_option="USER_ENTERED")
    elif existing != SHEET_HEADERS and existing == SHEET_HEADERS[: len(existing)]:
        # 舊表（例如上線初期版本）缺少後來新增的欄位（如 AI 校對相關）—— 直接補在後面，
        # 不動既有欄位與資料，向下相容舊列（缺的欄位讀取時自動視為空字串）。
        missing = SHEET_HEADERS[len(existing) :]
        start_col = len(existing) + 1
        worksheet.update(
            range_name=f"{_col_a1(start_col)}1:{_col_a1(start_col + len(missing) - 1)}1",
            values=[missing],
        )
    return worksheet


def _col_a1(col: int) -> str:
    """1-based 欄位編號轉 A1 表示法的欄位字母（1→A, 27→AA）。"""
    letters = ""
    while col > 0:
        col, rem = divmod(col - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


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
                meta.get("ai_status", ""),
                meta.get("ai_corrected_content", ""),
                json.dumps(meta.get("ai_revisions", []), ensure_ascii=False),
                meta.get("ai_folder_url", ""),
                meta.get("notified", ""),
            ],
            value_input_option="USER_ENTERED",
        )
        return True
    except Exception as exc:  # noqa: BLE001
        st.warning(f"寫入 Google Sheets 失敗（本機仍有完整備份）：{exc}")
        return False


def update_row(submitted_at: str, submitter_name: str, title: str, fields: dict) -> bool:
    """
    找到符合（投稿時間, 投稿人, 標題）的那一列，更新 `fields`（欄位名稱 -> 新值）。
    用於：編輯者在「AI 校對與審稿」確認送出後，回寫最終定稿與通知狀態。
    """
    try:
        worksheet = _worksheet()
        values = worksheet.get_all_values()
        if not values:
            return False
        header = values[0]
        idx = {name: i for i, name in enumerate(header)}
        needed = {"投稿時間", "投稿人", "文章標題"}
        if not needed.issubset(idx):
            return False
        target_row = None
        for r, row in enumerate(values[1:], start=2):
            if (
                row[idx["投稿時間"]] == submitted_at
                and row[idx["投稿人"]] == submitter_name
                and row[idx["文章標題"]] == title
            ):
                target_row = r
                break
        if target_row is None:
            return False
        for col_name, value in fields.items():
            if col_name not in idx:
                continue
            worksheet.update_cell(target_row, idx[col_name] + 1, value)
        return True
    except Exception as exc:  # noqa: BLE001
        st.warning(f"更新 Google Sheets 失敗：{exc}")
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


def _parse_revisions_cell(text: str) -> list[dict]:
    try:
        data = json.loads(text) if text else []
        return data if isinstance(data, list) else []
    except Exception:  # noqa: BLE001
        return []


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
                "ai_status": str(r.get("AI校對狀態", "")),
                "ai_corrected_content": str(r.get("AI校正後內文", "")),
                "ai_revisions": _parse_revisions_cell(r.get("AI修訂對照表", "")),
                "ai_folder_url": str(r.get("AI校正資料夾", "")),
                "notified": str(r.get("已通知投稿者", "")),
                "_source": "sheet",
            }
        )
    result.sort(key=lambda m: m.get("submitted_at", ""), reverse=True)
    return result
