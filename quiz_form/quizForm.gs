// =============================================================================
// 小テスト（Google Form）→ 自 app POST /api/quiz-attempts
// 使い方: このファイルの内容を GAS エディタにコピペする。
// - フォーム送信時トリガーで onFormSubmit を指定する。
// - スクリプトプロパティに API_BASE_URL を設定する。
// - Form は「クイズ」にし、項目順は 1 番目「idを入力」、2〜6 番目が問 1〜5（4 択）。
// =============================================================================

/**
 * フォーム送信時に実行する。回答を自 app の POST /api/quiz-attempts に JSON で送る。
 * Spreadsheet には書き込まない（ADR 準拠）。
 */
function onFormSubmit(e) {
  var form = e.source;
  var response = e.response;
  var items = form.getItems();

  if (items.length < 6) {
    console.error('フォーム項目は 6 以上必要です（id + 問1〜5）');
    return;
  }

  var participantId = String(response.getResponseForItem(items[0]) || '');
  var timestamp = _formatTimestamp(response.getTimestamp());

  var answers = [];
  var scoreNumerator = 0;
  for (var i = 1; i <= 5; i++) {
    var item = items[i];
    var gradable = response.getGradableResponseForItem(item);
    var points = item.getPoints ? item.getPoints() : 1;
    var score = gradable ? gradable.getScore() : 0;
    var isCorrect = (score === points) ? 1 : 0;
    scoreNumerator += isCorrect;
    var selectedAnswer = response.getResponseForItem(item);
    answers.push({
      question_index: i,
      selected_answer: selectedAnswer != null ? String(selectedAnswer) : '',
      is_correct: isCorrect
    });
  }

  var payload = {
    participant_id: participantId,
    timestamp: timestamp,
    score_numerator: scoreNumerator,
    score_denominator: 5,
    answers: answers
  };

  var baseUrl = PropertiesService.getScriptProperties().getProperty('API_BASE_URL');
  if (!baseUrl) {
    console.error('API_BASE_URL がスクリプトプロパティに設定されていません');
    return;
  }

  var options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };
  var resp = UrlFetchApp.fetch(baseUrl + '/api/quiz-attempts', options);
  var code = resp.getResponseCode();
  if (code < 200 || code >= 300) {
    console.error('quiz-attempts API エラー: ' + code + ' ' + resp.getContentText());
  }
}

/**
 * Date を POST /api/quiz-attempts の timestamp 形式（yyyy-MM-dd'T'HH:mm:ss）に整形する。
 */
function _formatTimestamp(date) {
  if (!date) return '';
  var y = date.getFullYear();
  var m = ('0' + (date.getMonth() + 1)).slice(-2);
  var d = ('0' + date.getDate()).slice(-2);
  var h = ('0' + date.getHours()).slice(-2);
  var min = ('0' + date.getMinutes()).slice(-2);
  var s = ('0' + date.getSeconds()).slice(-2);
  return y + '-' + m + '-' + d + 'T' + h + ':' + min + ':' + s;
}
