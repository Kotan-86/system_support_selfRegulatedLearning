// 仕様: docs/spec/framework-drivers-layer.md#LAD-フロント契約
// 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-6-LAD-AI-統合フロント
(function (global) {
  "use strict";

  var lastContentUpdatedAt = null;
  var pollTimerId = null;

  function getPollIntervalMs() {
    var configured = global.__REFLECT_POLL_INTERVAL_MS__;
    if (typeof configured === "number" && configured > 0) {
      return configured;
    }
    return 5000;
  }

  function fetchLad(participantId) {
    return global.ApiClient.getLad(participantId).then(function (response) {
      if (!response.ok) {
        console.error("LAD API エラー:", response.status);
        return null;
      }
      return response.json();
    });
  }

  function applyLadViewModel(viewModel, forceRender) {
    if (!viewModel) {
      return;
    }
    var updatedAt = viewModel.content_updated_at || null;
    if (forceRender || updatedAt !== lastContentUpdatedAt) {
      lastContentUpdatedAt = updatedAt;
      global.LadPanel.render(viewModel);
    }
  }

  function startPolling(participantId) {
    if (pollTimerId !== null) {
      clearInterval(pollTimerId);
    }
    pollTimerId = setInterval(function () {
      fetchLad(participantId).then(function (viewModel) {
        applyLadViewModel(viewModel, false);
      });
    }, getPollIntervalMs());
  }

  function init() {
    var participantId =
      global.__REFLECT_PARTICIPANT_ID__ ||
      (global.ParticipantContext &&
        global.ParticipantContext.getParticipantIdFromUrl());

    if (!participantId) {
      return;
    }

    global.ChatPanel.init(participantId);

    fetchLad(participantId).then(function (viewModel) {
      applyLadViewModel(viewModel, true);
      startPolling(participantId);
    });

    global.addEventListener("resize", function () {
      if (global.LadPanel && global.LadPanel.resizeCharts) {
        global.LadPanel.resizeCharts();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
