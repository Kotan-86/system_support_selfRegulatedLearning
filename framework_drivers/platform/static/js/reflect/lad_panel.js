// 仕様: docs/spec/framework-drivers-layer.md#LAD-フロント契約
// 仕様: docs/spec/interfaces-layer.md#LAD-表示要件と-ViewModel-契約
(function (global) {
  "use strict";

  var ACTION_LABELS = {
    play: "再生",
    pause: "一時停止",
    forward_skip: "先送りスキップ",
    backward_skip: "巻き戻しスキップ",
    forward_seek: "前方シーク",
    backward_seek: "後方シーク",
  };

  var ACTION_ORDER = [
    "play",
    "pause",
    "forward_skip",
    "backward_skip",
    "forward_seek",
    "backward_seek",
  ];

  var FIXED_BUCKET_COUNT = 5;
  var SEGMENT_WIDTH_SEC = 120;

  var pieChart = null;
  var barChart = null;

  function labelForAction(action) {
    return ACTION_LABELS[action] || action;
  }

  function formatSegmentLabel(segmentStartSec) {
    var end = segmentStartSec + SEGMENT_WIDTH_SEC;
    return segmentStartSec + "–" + end + " 秒";
  }

  /**
   * video_segments を 5 固定バケットに整形する。
   */
  function normalizeSegments(videoSegments) {
    var byStart = {};
    (videoSegments || []).forEach(function (segment) {
      byStart[segment.segment_start_sec] = segment.action_counts || {};
    });

    var buckets = [];
    for (var i = 0; i < FIXED_BUCKET_COUNT; i += 1) {
      var start = i * SEGMENT_WIDTH_SEC;
      buckets.push({
        segment_start_sec: start,
        action_counts: byStart[start] || {},
      });
    }
    return buckets;
  }

  function renderActionCountsPie(actionCounts) {
    var el = document.getElementById("action-counts-chart");
    if (!el || typeof echarts === "undefined") {
      return;
    }
    if (!pieChart) {
      pieChart = echarts.init(el);
    }

    var data = ACTION_ORDER.map(function (action) {
      return {
        name: labelForAction(action),
        value: (actionCounts && actionCounts[action]) || 0,
      };
    }).filter(function (item) {
      return item.value > 0;
    });

    if (data.length === 0) {
      data = [{ name: "データなし", value: 1 }];
    }

    pieChart.setOption({
      tooltip: { trigger: "item" },
      legend: { bottom: 0 },
      series: [
        {
          type: "pie",
          radius: "60%",
          data: data,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: "rgba(0, 0, 0, 0.2)",
            },
          },
        },
      ],
    });
  }

  function renderVideoSegmentsBar(videoSegments) {
    var el = document.getElementById("video-segments-chart");
    if (!el || typeof echarts === "undefined") {
      return;
    }
    if (!barChart) {
      barChart = echarts.init(el);
    }

    var buckets = normalizeSegments(videoSegments);
    var categories = buckets.map(function (bucket) {
      return formatSegmentLabel(bucket.segment_start_sec);
    });

    var series = ACTION_ORDER.map(function (action) {
      return {
        name: labelForAction(action),
        type: "bar",
        stack: "actions",
        emphasis: { focus: "series" },
        data: buckets.map(function (bucket) {
          return (bucket.action_counts && bucket.action_counts[action]) || 0;
        }),
      };
    });

    barChart.setOption({
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      legend: { bottom: 0 },
      grid: { left: "3%", right: "4%", bottom: "18%", containLabel: true },
      xAxis: { type: "category", data: categories },
      yAxis: { type: "value", minInterval: 1 },
      series: series,
    });
  }

  function renderQuizTable(quizResults, score) {
    var scoreEl = document.getElementById("quiz-score");
    var tbody = document.getElementById("quiz-results-body");
    if (!scoreEl || !tbody) {
      return;
    }

    if (score === null || score === undefined) {
      scoreEl.textContent = "得点: 未受験";
    } else {
      scoreEl.textContent = "得点: " + score;
    }

    tbody.innerHTML = "";
    var rows = quizResults || [];
    if (rows.length === 0) {
      var emptyRow = document.createElement("tr");
      var emptyCell = document.createElement("td");
      emptyCell.colSpan = 3;
      emptyCell.textContent = "小テスト結果はまだありません";
      emptyRow.appendChild(emptyCell);
      tbody.appendChild(emptyRow);
      return;
    }

    rows.forEach(function (row) {
      var tr = document.createElement("tr");
      var qCell = document.createElement("td");
      qCell.textContent = row.question_text || ("Q" + (row.question_index + 1));
      var choiceCell = document.createElement("td");
      choiceCell.textContent = row.selected_choice || "";
      var correctCell = document.createElement("td");
      correctCell.textContent = row.is_correct ? "正解" : "不正解";
      tr.appendChild(qCell);
      tr.appendChild(choiceCell);
      tr.appendChild(correctCell);
      tbody.appendChild(tr);
    });
  }

  function renderLearnerProfile(profile) {
    var container = document.getElementById("learner-profile");
    if (!container) {
      return;
    }
    container.innerHTML = "";

    if (!profile) {
      container.textContent = "プロファイルデータはまだありません";
      return;
    }

    if (profile.type_name) {
      var typeEl = document.createElement("div");
      typeEl.className = "profile-type";
      typeEl.textContent = "学習者タイプ: " + profile.type_name;
      container.appendChild(typeEl);
    }

    var behaviors = profile.learning_behaviors || [];
    if (behaviors.length > 0) {
      var ul = document.createElement("ul");
      ul.className = "profile-behaviors";
      behaviors.forEach(function (item) {
        var li = document.createElement("li");
        li.textContent = item.label + ": " + item.value;
        ul.appendChild(li);
      });
      container.appendChild(ul);
    }

    var staticWrap = document.createElement("div");
    staticWrap.className = "profile-static";
    [
      { label: "特徴", value: profile.characteristics },
      { label: "動機づけ", value: profile.motivation },
      { label: "成績傾向", value: profile.performance },
    ].forEach(function (entry) {
      if (entry.value) {
        var p = document.createElement("p");
        p.textContent = entry.label + ": " + entry.value;
        staticWrap.appendChild(p);
      }
    });
    if (staticWrap.childNodes.length > 0) {
      container.appendChild(staticWrap);
    }
  }

  function render(viewModel) {
    var data = viewModel || {};
    renderActionCountsPie(data.action_counts || {});
    renderVideoSegmentsBar(data.video_segments || []);
    renderQuizTable(data.quiz_results || [], data.score);
    renderLearnerProfile(data.learner_profile || null);
  }

  function resizeCharts() {
    if (pieChart) {
      pieChart.resize();
    }
    if (barChart) {
      barChart.resize();
    }
  }

  global.LadPanel = {
    render: render,
    resizeCharts: resizeCharts,
    labelForAction: labelForAction,
    normalizeSegments: normalizeSegments,
  };
})(window);
