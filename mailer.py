# -*- coding: utf-8 -*-
"""
投稿通知信 — 透過 Gmail SMTP 寄出
--------------------------------
每筆投稿寄一封信給編輯部（可多位收件人），內含全文與「印刷級原照」附件。

未在 st.secrets 設定 [email] 時，`is_enabled()` 回傳 False，呼叫端略過寄信。

secrets 範例：
    [email]
    sender = "lyf1228@gmail.com"
    app_password = "abcd efgh ijkl mnop"      # Gmail「應用程式密碼」，非登入密碼
    recipients = ["lyf1228@gmail.com", "shon.yang@gmail.com"]
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import formataddr

import streamlit as st

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 465


def _conf() -> dict | None:
    try:
        if "email" not in st.secrets:
            return None
        c = dict(st.secrets["email"])
    except Exception:  # noqa: BLE001
        return None
    pw = str(c.get("app_password", "")).strip()
    if not c.get("sender") or not pw or pw.upper().startswith("PASTE_"):
        return None
    recipients = c.get("recipients") or [c["sender"]]
    if isinstance(recipients, str):
        recipients = [r.strip() for r in recipients.replace(";", ",").split(",") if r.strip()]
    c["recipients"] = recipients
    return c


def is_enabled() -> bool:
    return _conf() is not None


def status_text() -> str:
    c = _conf()
    if not c:
        return "未設定"
    return f"寄至 {', '.join(c['recipients'])}"


def _body(meta: dict) -> str:
    photos = meta.get("photos", [])
    photo_lines = "\n".join(
        f"  {i}. {p.get('caption') or '(未填圖說)'}　[{p.get('filename', '')}]"
        for i, p in enumerate(photos, start=1)
    ) or "  （無）"
    ai_status = meta.get("ai_status") or "（未執行）"
    ai_line = f"AI 校對　：{ai_status}"
    if meta.get("ai_folder_url"):
        ai_line += f"（{meta['ai_folder_url']}）"
    return (
        f"中橋季刊收到一筆新投稿\n"
        f"{'=' * 40}\n"
        f"期別　　：{meta.get('year')} {meta.get('season')}\n"
        f"投稿人　：{meta.get('submitter_name')}\n"
        f"Email　 ：{meta.get('email')}\n"
        f"文章標題：{meta.get('title')}\n"
        f"建議單元：{meta.get('category')}\n"
        f"內文方式：{meta.get('content_mode')}\n"
        f"收稿時間：{meta.get('submitted_at')}\n"
        f"照片數　：{meta.get('photo_count')}\n"
        f"照片圖說：\n{photo_lines}\n"
        f"{ai_line}\n"
        f"{'=' * 40}\n\n"
        f"【文章內文】\n\n{meta.get('content', '')}\n"
    )


def send_submission(meta: dict, attachments: list[dict]) -> bool:
    """
    寄出投稿通知信。
    attachments: [{"filename": str, "data": bytes, "mime": "image/jpeg"}...]
    成功回傳 True。
    """
    c = _conf()
    if not c:
        return False

    msg = EmailMessage()
    msg["Subject"] = (
        f"[中橋季刊投稿] {meta.get('year')}{meta.get('season')}"
        f" · {meta.get('title')} · {meta.get('submitter_name')}"
    )
    msg["From"] = formataddr(("中橋季刊投稿系統", c["sender"]))
    msg["To"] = ", ".join(c["recipients"])
    if meta.get("email"):
        msg["Reply-To"] = meta["email"]
    msg.set_content(_body(meta))

    for att in attachments:
        maintype, _, subtype = (att.get("mime") or "application/octet-stream").partition("/")
        msg.add_attachment(
            att["data"],
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=att["filename"],
        )

    return _send(c, msg, on_error="投稿通知信寄送失敗（投稿本身已存檔）")


def _send(c: dict, msg: EmailMessage, on_error: str) -> bool:
    try:
        with smtplib.SMTP_SSL(_SMTP_HOST, _SMTP_PORT, timeout=30) as smtp:
            smtp.login(c["sender"], str(c["app_password"]).replace(" ", ""))
            smtp.send_message(msg)
        return True
    except Exception as exc:  # noqa: BLE001
        st.warning(f"{on_error}：{exc}")
        return False


def _revision_table_text(revisions: list[dict]) -> str:
    if not revisions:
        return "（本次校對未發現需要修訂之處）"
    lines = []
    for i, r in enumerate(revisions, start=1):
        lines.append(
            f"{i}. 原句：{r.get('original', '')}\n"
            f"   修訂：{r.get('revised', '')}\n"
            f"   理由：{r.get('reason', '')}"
        )
    return "\n\n".join(lines)


def send_to_submitter(
    submitter_email: str,
    submitter_name: str,
    title: str,
    final_text: str,
    revisions: list[dict],
    attachments: list[dict] | None = None,
) -> bool:
    """
    編輯在「AI 校對與審稿」確認定稿後，寄給投稿者：修訂後全文 ＋ 修訂對照表。
    這是編輯手動觸發的動作，失敗時用 st.warning 提示編輯（此函式只在後台呼叫）。
    """
    c = _conf()
    if not c or not submitter_email:
        return False

    msg = EmailMessage()
    msg["Subject"] = f"[中橋季刊] 您的投稿《{title}》編輯校對完成"
    msg["From"] = formataddr(("中橋季刊編輯部", c["sender"]))
    msg["To"] = submitter_email
    msg["Reply-To"] = c["sender"]

    body = (
        f"{submitter_name} 您好：\n\n"
        f"感謝您投稿《{title}》，編輯部已完成校對，修訂後全文與修訂對照表如下，"
        f"敬請確認內容無誤。如有疑問歡迎直接回覆本信。\n\n"
        f"{'=' * 40}\n"
        f"【修訂對照表】\n\n{_revision_table_text(revisions)}\n"
        f"{'=' * 40}\n\n"
        f"【修訂後全文】\n\n{final_text}\n\n"
        f"祝橋藝精進\n"
        f"中橋季刊編輯部"
    )
    msg.set_content(body)

    for att in attachments or []:
        maintype, _, subtype = (att.get("mime") or "application/octet-stream").partition("/")
        msg.add_attachment(
            att["data"],
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=att["filename"],
        )

    return _send(c, msg, on_error="寄送定稿信失敗")
