// 仕様: docs/spec/framework-drivers-layer.md#参加者導線
// 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-6-LAD-AI-統合フロント
(function (global) {
  "use strict";

  var sessionId = null;
  var participantId = null;

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

  function bindForm() {
    var messageForm = document.getElementById("message-form");
    var messageInput = document.getElementById("message-input");
    if (!messageForm || !messageInput) {
      return;
    }

    messageForm.addEventListener("submit", function (event) {
      event.preventDefault();
      var userMessage = messageInput.value.trim();
      if (!userMessage || !participantId) {
        return;
      }

      appendMessage(userMessage, "user-message");
      messageInput.value = "";
      var submitBtn = messageForm.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      showLoading();

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
          submitBtn.disabled = false;
        });
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
  };
})(window);
