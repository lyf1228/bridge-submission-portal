/**
 * 中橋季刊投稿系統 — Google Drive 收檔 Web App
 * ===========================================================================
 * 作用：接收投稿系統送來的檔案，用「你的身分」存進你指定的 Drive 資料夾。
 *
 * 一次性設定步驟：
 *   1. 到 https://script.google.com/ → 新增專案
 *   2. 把本檔全部內容貼進 Code.gs（覆蓋原本的 myFunction）
 *   3. 修改下面兩個常數：
 *        ROOT_FOLDER_ID —— 你的目標資料夾 ID（資料夾網址 /folders/ 後面那串）
 *        TOKEN          —— 自訂一組通關密語（英數即可），等一下要填進 secrets.toml
 *   4. 右上「部署 → 新增部署作業 → 類型選『網頁應用程式』」
 *        - 執行身分：我（你的帳號）
 *        - 誰可以存取：任何人
 *      按「部署」，第一次會要求授權 → 允許
 *   5. 複製「網頁應用程式」網址（.../exec 結尾），填進 secrets.toml 的 [drive] webapp_url
 *
 *   之後若修改程式，要「部署 → 管理部署作業 → 編輯(鉛筆) → 版本選『新版本』→ 部署」
 *   才會生效（網址不變）。
 * ===========================================================================
 */

// ↓↓↓ 貼進 script.google.com 後，把 TOKEN 換成 secrets.toml [drive] token 裡那一串 ↓↓↓
const ROOT_FOLDER_ID = '1EoO3z1L0lz6MgryLPeJby_GRPHMHvO-R';   // 你的 Drive 目標資料夾
const TOKEN = 'PUT_THE_SAME_TOKEN_AS_secrets_toml';           // 兩邊必須一字不差
// ↑↑↑ ↑↑↑


function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    if (body.token !== TOKEN) {
      return _json({ ok: false, error: 'unauthorized' });
    }

    const root = DriveApp.getFolderById(ROOT_FOLDER_ID);
    let target = root;
    if (body.folder) {
      const name = String(body.folder).replace(/[\\/:*?"<>|]/g, '_');
      const it = root.getFoldersByName(name);
      target = it.hasNext() ? it.next() : root.createFolder(name);
    }

    const f = body.file;
    const blob = Utilities.newBlob(
      Utilities.base64Decode(f.dataB64),
      f.mimeType || 'application/octet-stream',
      f.name
    );
    const created = target.createFile(blob);

    return _json({
      ok: true,
      folderUrl: target.getUrl(),
      file: { name: f.name, url: created.getUrl(), id: created.getId() }
    });
  } catch (err) {
    return _json({ ok: false, error: String(err) });
  }
}

function doGet() {
  return _json({ ok: true, service: 'bridge-magazine drive intake' });
}

function _json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
