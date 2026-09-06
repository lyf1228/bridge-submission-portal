# -*- coding: utf-8 -*-
"""
Google Drive 儲存後端（透過 Google Apps Script Web App 代理）
----------------------------------------------------------
個人 Gmail 的「服務帳戶」沒有 Drive 儲存容量，無法直接寫入你的雲端硬碟。
解法：在你自己的 Google 帳號下部署一支小小的 Apps Script（見 apps_script.gs），
以「你的身分」執行，把檔案寫進你指定的資料夾（用你自己的 15GB 容量、檔案也歸你所有）。

本模組把每筆投稿的內文、metadata、照片、原始文檔 POST 給那支 Web App。

未在 st.secrets 設定 [drive] 時，`is_enabled()` 回傳 False，呼叫端自動略過。

secrets 範例：
    [drive]
    webapp_url = "https://script.google.com/macros/s/AKfyc.../exec"
    token = "自訂的一組通關密語，要和 Apps Script 裡的 TOKEN 一致"
"""

from __future__ import annotations

import base64

import requests
import streamlit as st

_TIMEOUT = 180


def _conf() -> dict | None:
    try:
        if "drive" not in st.secrets:
            return None
        c = dict(st.secrets["drive"])
    except Exception:  # noqa: BLE001
        return None
    url = str(c.get("webapp_url", "")).strip()
    if not url or not c.get("token") or url.upper().startswith("PASTE_"):
        return None
    c["webapp_url"] = url
    return c


def is_enabled() -> bool:
    return _conf() is not None


def status_text() -> str:
    return "已設定（Apps Script Web App）" if _conf() else "未設定"


def _post(payload: dict) -> dict:
    c = _conf()
    resp = requests.post(c["webapp_url"], json=payload, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def upload_files(subfolder: str, files: list[dict]) -> dict | None:
    """
    把多個檔案上傳到 Drive 目標資料夾下的子資料夾 `subfolder`。
    files: [{"filename": str, "data": bytes, "mime": str}, ...]
    回傳 {"folder_url": str, "files": [{"name","url","id"}...]}；整體失敗回傳 None。
    """
    c = _conf()
    if not c:
        return None

    out: dict = {"folder_url": None, "files": []}
    try:
        for f in files:
            payload = {
                "token": c["token"],
                "folder": subfolder,
                "file": {
                    "name": f["filename"],
                    "mimeType": f.get("mime") or "application/octet-stream",
                    "dataB64": base64.b64encode(f["data"]).decode("ascii"),
                },
            }
            resp = _post(payload)
            if not resp.get("ok"):
                st.warning(f"上傳 Drive 失敗（{f['filename']}）：{resp.get('error')}")
                continue
            out["folder_url"] = resp.get("folderUrl") or out["folder_url"]
            if resp.get("file"):
                out["files"].append(resp["file"])
        return out if out["files"] else None
    except Exception as exc:  # noqa: BLE001
        st.warning(f"上傳 Google Drive 失敗（本機仍有完整備份）：{exc}")
        return None
