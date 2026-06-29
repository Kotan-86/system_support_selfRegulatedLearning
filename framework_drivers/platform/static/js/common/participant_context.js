// 仕様: docs/spec/framework-drivers-layer.md#参加者導線
// 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-5-講義動画フロント
(function (global) {
  "use strict";

  /**
   * URL クエリから participant_id を取得する。
   * @returns {string|null} 空白のみの場合は null
   */
  function getParticipantIdFromUrl() {
    var params = new URLSearchParams(global.location.search);
    var id = params.get("participant_id");
    if (id === null || String(id).trim() === "") {
      return null;
    }
    return String(id).trim();
  }

  global.ParticipantContext = {
    getParticipantIdFromUrl: getParticipantIdFromUrl,
  };
})(window);
