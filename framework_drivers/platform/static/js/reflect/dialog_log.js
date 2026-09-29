// 仕様: docs/spec/dialog-log-save.md#受入基準 (PBI-A-2: A9, A10, A18, A19)
// 公開IF: window.DialogLog = { init(participantId), isEnded() }
(function (global) {
  "use strict";

  var participantId = null;
  var ended = false;
  var saving = false;
  var waitingReply = false;

  function byId(id) {
    return document.getElementById(id);
  }

  function setHidden(el, hidden) {
    if (!el) {
      return;
    }
    el.hidden = hidden;
    if (hidden) {
      if (el.setAttribute) el.setAttribute("hidden", "");
    } else if (el.removeAttribute) {
      el.removeAttribute("hidden");
    }
  }

  function submitButton() {
    var form = byId("message-form");
    return form && form.querySelector
      ? form.querySelector('button[type="submit"]')
      : null;
  }

  // 保存中は入力・送信も止める(保存後の発言が保存から漏れないように)。失敗で戻す。
  function setChatDisabled(disabled) {
    var input = byId("message-input");
    var submit = submitButton();
    if (input) input.disabled = disabled;
    if (submit) submit.disabled = disabled;
  }

  function refreshEndButton() {
    var btn = byId("end-dialog-button");
    if (btn) {
      btn.disabled = ended || saving || waitingReply;
    }
  }

  function showComplete() {
    ended = true;
    setHidden(byId("dialog-end-error"), true);
    setHidden(byId("dialog-end-complete"), false);
    var panel = byId("chat-panel");
    if (panel && panel.classList) {
      panel.classList.add("dialog-ended");
    }
    setChatDisabled(true);
    refreshEndButton();
  }

  function showFailure() {
    setHidden(byId("dialog-end-error"), false);
    setChatDisabled(false);
    refreshEndButton();
  }

  function onEndClick() {
    if (ended || saving || waitingReply) {
      return;
    }
    saving = true;
    setHidden(byId("dialog-end-error"), true);
    setChatDisabled(true);
    refreshEndButton();

    var request;
    try {
      request = global.ApiClient.postDialogLog(participantId, "end_button");
    } catch (e) {
      request = Promise.reject(e);
    }
    request
      .then(function (response) {
        saving = false;
        if (response && response.ok) {
          showComplete();
        } else {
          showFailure();
        }
      })
      .catch(function () {
        saving = false;
        showFailure();
      });
  }

  function init(pid) {
    participantId = pid;
    var btn = byId("end-dialog-button");
    if (btn && btn.addEventListener) {
      btn.addEventListener("click", onEndClick);
    }
    if (global.ChatPanel && global.ChatPanel.onSendStateChange) {
      global.ChatPanel.onSendStateChange(function (sending) {
        waitingReply = !!sending;
        refreshEndButton();
      });
    }
  }

  function isEnded() {
    return ended;
  }

  global.DialogLog = { init: init, isEnded: isEnded };
})(window);
