// 仕様: docs/spec/subtitle-display.md#受入基準
// 動画の下の字幕表示。表示・非表示の切替は画面の見た目だけを変え、通信もログも行わない。
(function (global) {
  "use strict";

  var cues = Array.isArray(global.__LECTURE_SUBTITLES__)
    ? global.__LECTURE_SUBTITLES__
    : [];
  var visible = false; // 初期状態は非表示(AC2)。永続化しない(AC14)。
  var lastPosition = 0;
  var area = document.getElementById("subtitle-area");
  var button = document.getElementById("subtitle-toggle");

  // 仕様: docs/spec/subtitle-display.md#受入基準 AC10
  // 有効(start <= position < end)なキューのうち start が最大のものの文。なければ ""。
  function selectCue(list, position) {
    var best = null;
    for (var i = 0; i < list.length; i++) {
      var cue = list[i];
      if (cue.start <= position && position < cue.end) {
        if (best === null || cue.start >= best.start) {
          best = cue;
        }
      }
    }
    return best === null ? "" : String(best.text);
  }

  function render() {
    if (area) {
      area.textContent = visible ? selectCue(cues, lastPosition) : "";
    }
    if (button) {
      button.textContent = visible ? "字幕を非表示にする" : "字幕を表示する";
    }
  }

  function update(position) {
    var value = Number(position);
    if (!isFinite(value)) {
      return;
    }
    lastPosition = value;
    render();
  }

  function toggle() {
    visible = !visible;
    render();
  }

  function isVisible() {
    return visible;
  }

  if (button && typeof button.addEventListener === "function") {
    button.addEventListener("click", toggle);
  }
  render();

  global.LectureSubtitles = {
    selectCue: selectCue,
    update: update,
    toggle: toggle,
    isVisible: isVisible,
  };
})(window);
