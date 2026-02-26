// =============================================================================
// 講義動画プラットフォーム（視聴ログ → 自 app API）
// 使い方: このファイルの内容を Google Apps Script エディタにそのままコピペする。
// - スクリプトプロパティに API_BASE_URL を設定（例: https://your-app.example.com）
// - 同じ GAS プロジェクトに lectureVideoPlatform.html を追加し、上記の名前で保存する。
// =============================================================================

function doGet(e) {
  var template = HtmlService.createTemplateFromFile('lectureVideoPlatform');
  return template.evaluate()
    .setTitle('講義動画')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/**
 * POST /api/viewing-log に送る payload を組み立てる。
 * （lectureVideoPlatform/buildViewingLogPayload.js と同じ仕様・Node でテスト済み）
 */
function buildViewingLogPayload(participant_id, currentTime, action, duration) {
  var now = new Date();
  return {
    participant_id: String(participant_id),
    time_stamp: now.toISOString(),
    current_time: Number(currentTime),
    action: String(action),
    duration: Number(duration)
  };
}

/**
 * 視聴イベントを自 app の POST /api/viewing-log に送る。
 * Spreadsheet には書き込まない（ADR 準拠）。
 */
function recordLog(participant_id, currentTime, action, duration) {
  var baseUrl = PropertiesService.getScriptProperties().getProperty('API_BASE_URL');
  if (!baseUrl) {
    console.error('API_BASE_URL がスクリプトプロパティに設定されていません');
    return;
  }
  var payload = buildViewingLogPayload(participant_id, currentTime, action, duration);
  var options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };
  var response = UrlFetchApp.fetch(baseUrl + '/api/viewing-log', options);
  var code = response.getResponseCode();
  if (code < 200 || code >= 300) {
    console.error('viewing-log API エラー: ' + code + ' ' + response.getContentText());
  }
}
