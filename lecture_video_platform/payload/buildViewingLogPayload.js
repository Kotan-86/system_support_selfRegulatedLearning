/**
 * POST /api/viewing-log に送る payload を組み立てる純粋関数。
 * GAS の recordLog（lectureVideoPlatform.gs）から呼ぶ想定と同一仕様。
 * time_stamp は第5引数で渡すか省略時は現在時刻。Node でユニットテスト可能。
 *
 * @param {string|number} participant_id - 参加者 ID
 * @param {number} currentTime - 再生位置（秒）
 * @param {string} action - play | pause | forward_skip | backward_skip | forward_seek | backward_seek
 * @param {number} duration - 0 またはスキップ秒数など
 * @param {Date} [now] - テスト用。省略時は new Date()
 * @returns {{ participant_id: string, time_stamp: string, current_time: number, action: string, duration: number }}
 */
function buildViewingLogPayload(participant_id, currentTime, action, duration, now = new Date()) {
  return {
    participant_id: String(participant_id),
    time_stamp: now.toISOString(),
    current_time: Number(currentTime),
    action: String(action),
    duration: Number(duration),
  };
}

module.exports = { buildViewingLogPayload };
