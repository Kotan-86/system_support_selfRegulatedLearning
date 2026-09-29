// 仕様: docs/spec/dialog-log-save.md#PBI-B
// 公開IF: window.LeaveGuard = { init(participantId), shouldConfirm() }
(function (global) {
  "use strict";

  // 発言済み: この画面の中だけ。永続化しない（N4）。
  var hasSpoken = false;

  function isEnded() {
    return !!(
      global.DialogLog &&
      typeof global.DialogLog.isEnded === "function" &&
      global.DialogLog.isEnded()
    );
  }

  // 発言済み かつ 未終了
  function shouldConfirm() {
    return hasSpoken && !isEnded();
  }

  function init(participantId) {
    if (global.ChatPanel && typeof global.ChatPanel.onSendStateChange === "function") {
      global.ChatPanel.onSendStateChange(function (sending) {
        if (sending === true) {
          hasSpoken = true;
        }
      });
    }
    if (typeof global.addEventListener !== "function") {
      return;
    }
    // B1・B3: 確認のみ要求する。保存要求は送らない。
    global.addEventListener("beforeunload", function (event) {
      if (!shouldConfirm()) {
        return;
      }
      event.preventDefault();
      event.returnValue = "";
    });
    // B4: 離脱の確定で page_leave を保存（確認の有無によらない）。
    global.addEventListener("pagehide", function () {
      if (
        shouldConfirm() &&
        global.ApiClient &&
        typeof global.ApiClient.postDialogLogOnLeave === "function"
      ) {
        global.ApiClient.postDialogLogOnLeave(participantId);
      }
    });
  }

  global.LeaveGuard = { init: init, shouldConfirm: shouldConfirm };
})(window);
