// 仕様: docs/spec/framework-drivers-layer.md#参加者導線
// 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-6-LAD-AI-統合フロント
(function (global) {
  "use strict";

  var sessionId = null;
  var participantId = null;
  var sending = false;
  var sendStateListeners = [];

  // 仕様: docs/spec/dialog-log-save.md#受入基準 (A19)
  function notifySendState(value) {
    sendStateListeners.slice().forEach(function (listener) {
      try {
        listener(value);
      } catch (e) {
        // listener の失敗でチャットの送信を妨げない
      }
    });
  }

  function onSendStateChange(listener) {
    if (typeof listener === "function") {
      sendStateListeners.push(listener);
    }
  }

  function isSending() {
    return sending;
  }

  function getChatBox() {
    return document.getElementById("chat-box");
  }

  function appendMessage(text, className) {
    var chatBox = getChatBox();
    if (!chatBox) {
      return;
    }
    var div = document.createElement("div");
    div.className = className;
    div.textContent = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  function showLoading() {
    var chatBox = getChatBox();
    if (!chatBox) {
      return;
    }
    var wrap = document.createElement("div");
    wrap.id = "loading-indicator";
    wrap.className = "loading-indicator";
    wrap.innerHTML = '<div class="spinner"></div>';
    chatBox.appendChild(wrap);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  function hideLoading() {
    var el = document.getElementById("loading-indicator");
    if (el) {
      el.remove();
    }
  }

  // 仕様: docs/spec/reflect-chat-multiline-input.md#受入基準 (AC3, AC4, AC10)
  // 入力欄の高さを内容に合わせる。上限は CSS の max-height から読む。
  function adjustHeight(messageInput) {
    try {
      if (
        !messageInput ||
        !messageInput.style ||
        typeof global.getComputedStyle !== "function"
      ) {
        return;
      }
      messageInput.style.height = "auto";
      var scrollHeight = messageInput.scrollHeight;
      var maxHeight = parseFloat(global.getComputedStyle(messageInput).maxHeight);
      if (typeof scrollHeight !== "number" || !isFinite(scrollHeight)) {
        return;
      }
      var limit = isFinite(maxHeight) ? maxHeight : Infinity;
      messageInput.style.height = Math.min(scrollHeight, limit) + "px";
      messageInput.style.overflowY = scrollHeight > limit ? "auto" : "hidden";
    } catch (e) {
      // 高さの調整に失敗しても入力・送信は妨げない
    }
  }

  // 仕様: docs/spec/reflect-chat-multiline-input.md#受入基準 (AC5〜AC14, AC17)
  function bindForm() {
    var messageForm = document.getElementById("message-form");
    var messageInput = document.getElementById("message-input");
    if (!messageForm || !messageInput) {
      return;
    }

    function sendMessage() {
      if (sending) {
        return;
      }
      var userMessage = messageInput.value.trim();
      if (!userMessage || !participantId) {
        return;
      }
      sending = true;

      appendMessage(userMessage, "user-message");
      messageInput.value = "";
      adjustHeight(messageInput);
      var submitBtn = messageForm.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      showLoading();
      notifySendState(true);

      var body = { message: userMessage, participant_id: participantId };
      if (sessionId) {
        body.session_id = sessionId;
      }

      global.ApiClient.postChat(body)
        .then(function (response) {
          hideLoading();
          if (!response.ok) {
            return response
              .json()
              .catch(function () {
                return {};
              })
              .then(function (errData) {
                appendMessage(
                  "エラー: " + (errData.error || response.status),
                  "tutor-message",
                );
              });
          }
          return response.json().then(function (data) {
            if (data.session_id) {
              sessionId = data.session_id;
            }
            if (data.response) {
              appendMessage(data.response, "tutor-message");
            } else if (data.error) {
              appendMessage("エラー: " + data.error, "tutor-message");
            }
          });
        })
        .catch(function (err) {
          hideLoading();
          appendMessage("エラー: " + err.message, "tutor-message");
        })
        .finally(function () {
          sending = false;
          submitBtn.disabled = false;
          notifySendState(false);
        });
    }

    messageForm.addEventListener("submit", function (event) {
      event.preventDefault();
      sendMessage();
    });

    messageInput.addEventListener("keydown", function (event) {
      if (event.key !== "Enter") {
        return;
      }
      // IME 変換中(Safari は keyCode 229)は確定に任せる
      if (event.isComposing || event.keyCode === 229) {
        return;
      }
      if (event.ctrlKey || event.metaKey || event.altKey) {
        event.preventDefault();
        return;
      }
      if (event.shiftKey) {
        return; // 既定の改行
      }
      event.preventDefault();
      sendMessage();
    });

    messageInput.addEventListener("input", function () {
      adjustHeight(messageInput);
    });
  }

  function init(pid) {
    participantId = pid;
    bindForm();
    appendMessage(
      "学習記録をもとに振り返りを始めましょう。メッセージを入力してください。",
      "tutor-message",
    );
  }

  global.ChatPanel = {
    init: init,
    appendMessage: appendMessage,
    onSendStateChange: onSendStateChange,
    isSending: isSending,
  };
})(window);
