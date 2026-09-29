// 仕様: docs/spec/bugs/seek-duplicate-count.md#受入基準 (AC10 の (a)〜(d))
// player.js を node:vm でそのまま読み込み、DOM / YouTube API / ApiClient の最小の代役で検証する。
// 使い方: node lecture_player_seek_count.mjs (すべて成功で終了コード 0、失敗で 1)
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const jsRoot = path.resolve(here, "../../../framework_drivers/platform/static/js");
const playerSrc = fs.readFileSync(path.join(jsRoot, "lecture/player.js"), "utf8");
const participantSrc = fs.readFileSync(path.join(jsRoot, "common/participant_context.js"), "utf8");

function makeTarget() {
  const listeners = {};
  return {
    listeners,
    addEventListener(type, fn) {
      (listeners[type] = listeners[type] || []).push(fn);
    },
    dispatch(type) {
      for (const fn of (listeners[type] || []).slice()) fn({ type });
    },
    count(type) {
      return (listeners[type] || []).length;
    },
  };
}

// 1 シナリオ分の環境を作り、準備完了までを済ませる。
function setup() {
  const logs = [];
  const timers = new Map(); // 代役のタイマー(実タイマーを使わないので Node が残らない)
  let timerSeq = 0;
  const storage = new Map();

  const seekbar = Object.assign(makeTarget(), { value: 0, max: 0, style: {} });
  const time = { innerHTML: "" };
  const playerEl = { offsetWidth: 600 };
  const win = makeTarget();
  let ytPlayer = null;

  const YT = {
    PlayerState: { PLAYING: 1, PAUSED: 2 },
    Player: function (id, opts) {
      const self = this;
      ytPlayer = self;
      self.events = opts.events;
      self.pos = 0;
      self.getCurrentTime = () => self.pos;
      self.getDuration = () => 100;
      self.setSize = () => {};
      self.seekTo = (t) => { self.pos = t; };
      self.playVideo = () => self.events.onStateChange({ data: 1 });
      self.pauseVideo = () => self.events.onStateChange({ data: 2 });
    },
  };

  const sandbox = Object.assign(win, {
    YT,
    location: { search: "?participant_id=p1" },
    URLSearchParams,
    innerWidth: 1000,
    innerHeight: 800,
    document: {
      documentElement: { clientWidth: 1000, clientHeight: 800 },
      body: { clientWidth: 1000, clientHeight: 800 },
      getElementById: (id) => ({ seekbar, time, player: playerEl })[id] || null,
    },
    sessionStorage: {
      getItem: (k) => (storage.has(k) ? storage.get(k) : null),
      setItem: (k, v) => storage.set(k, String(v)),
      removeItem: (k) => storage.delete(k),
    },
    setInterval: (fn) => { timers.set(++timerSeq, fn); return timerSeq; },
    clearInterval: (id) => { timers.delete(id); },
    __LECTURE_VIDEO_ID__: "vid",
  });
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(participantSrc, sandbox, { filename: "participant_context.js" });
  sandbox.ApiClient = {
    postViewingLog(participantId, currentTime, action, duration) {
      logs.push({ participantId, current_time: currentTime, action, duration });
    },
  };
  vm.runInContext(playerSrc, sandbox, { filename: "player.js" });

  sandbox.onYouTubeIframeAPIReady();
  ytPlayer.events.onReady({ target: ytPlayer });
  logs.length = 0; // 準備完了直後の play/pause を捨てる

  return {
    logs,
    seekbar,
    win,
    sandbox,
    get player() { return ytPlayer; },
    resize(n) { for (let i = 0; i < n; i++) win.dispatch("resize"); },
    seeks() { return logs.filter((l) => l.action === "forward_seek" || l.action === "backward_seek"); },
  };
}

const failures = [];
function check(label, cond, detail) {
  if (cond) {
    console.log(`ok   ${label}`);
  } else {
    console.log(`FAIL ${label}: ${detail}`);
    failures.push(label);
  }
}
const fmt = (arr) => JSON.stringify(arr.map((l) => [l.action, l.current_time, l.duration]));

for (const N of [0, 1, 3]) {
  {
    // (a) 入力3回 + 確定1回 → 前方シークがちょうど1件(位置=到達位置、移動量=到達位置-開始位置)
    const e = setup();
    e.resize(N);
    e.player.pos = 10;
    for (const v of [15, 25, 40]) { e.seekbar.value = v; e.seekbar.dispatch("input"); }
    e.seekbar.dispatch("change");
    const s = e.seeks();
    check(`AC10(a) N=${N}: forward_seek が1件`, s.length === 1, `件数=${s.length} ${fmt(s)}`);
    check(
      `AC10(a) N=${N}: 内容(種類=forward_seek, 位置=40, 移動量=30)`,
      s.length >= 1 && s.every((l) => l.action === "forward_seek" && l.current_time === 40 && l.duration === 30),
      fmt(s)
    );
  }
  {
    // (b) 入力のみ → 0件
    const e = setup();
    e.resize(N);
    e.player.pos = 10;
    for (const v of [15, 25, 40]) { e.seekbar.value = v; e.seekbar.dispatch("input"); }
    const s = e.seeks();
    check(`AC10(b) N=${N}: 入力のみで seek は0件`, s.length === 0, `件数=${s.length} ${fmt(s)}`);
  }
  {
    // (c) 位置を1段進めて確定を3回 → forward_seek がちょうど3件
    const e = setup();
    e.resize(N);
    for (const v of [11, 12, 13]) { e.seekbar.value = v; e.seekbar.dispatch("change"); }
    const s = e.seeks();
    check(
      `AC10(c) N=${N}: 確定3回で forward_seek が3件`,
      s.length === 3 && s.every((l) => l.action === "forward_seek"),
      `件数=${s.length} ${fmt(s)}`
    );
  }
  {
    // (d) リサイズ N 回 → 再生 → 一時停止 → 5秒進む → 5秒戻る、各1件
    const e = setup();
    e.resize(N);
    e.sandbox.play();
    e.sandbox.pause();
    e.sandbox.forwardSkip();
    e.sandbox.backwardSkip();
    const counts = {};
    for (const l of e.logs) counts[l.action] = (counts[l.action] || 0) + 1;
    const ok =
      ["play", "pause", "forward_skip", "backward_skip"].every((a) => counts[a] === 1) &&
      e.logs.length === 4;
    check(`AC10(d) N=${N}: play/pause/forward_skip/backward_skip が各1件`, ok, `件数=${JSON.stringify(counts)}`);
  }
}

console.log(failures.length === 0 ? "ALL PASSED" : `FAILED: ${failures.length} 件`);
// 代役のタイマーのみだが、念のため明示的に終了する。
process.exit(failures.length === 0 ? 0 : 1);
