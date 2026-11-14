// 仕様: docs/spec/multi-video-learning.md#受入基準 (AC16。What 9節、Q15)
// player.js を node:vm でそのまま読み込み、DOM / YouTube API / ApiClient の最小の代役で検証する。
// 代役の YouTube API は、状態の変化を即時に(playVideo / pauseVideo の呼び出しの中で)通知する
// (bugs/seek-duplicate-count.md の AC10 と同じ方式。lecture_player_seek_count.mjs の setup に合わせた)。
// 既存のテストと違い、準備完了の直後の記録を捨てずに数える。
// 使い方: node lecture_player_ready_no_log.mjs (すべて成功で終了コード 0、失敗で 1)
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
    addEventListener(type, fn) {
      (listeners[type] = listeners[type] || []).push(fn);
    },
    dispatch(type) {
      for (const fn of (listeners[type] || []).slice()) fn({ type });
    },
  };
}

// 1 シナリオ分の環境を作り、YouTube API の準備完了(onReady)まで進める。記録は捨てない。
function setupUntilReady() {
  const logs = [];
  const timers = new Map();
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
  // ここで記録を捨てない(AC16「記録を捨てずに数える」)

  return { logs, sandbox, win, get player() { return ytPlayer; } };
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

{
  // 準備完了まで: 視聴ログは0件
  const e = setupUntilReady();
  check("AC16 準備完了まで進めただけでは視聴ログが0件", e.logs.length === 0, `件数=${e.logs.length} ${fmt(e.logs)}`);

  // 続けて利用者の再生の操作: play が1件
  e.player.pos = 7;
  e.sandbox.play();
  const afterPlay = e.logs.slice();
  check(
    "AC16 利用者の再生の操作で play が1件(他の記録なし)",
    afterPlay.length === 1 && afterPlay[0].action === "play",
    `件数=${afterPlay.length} ${fmt(afterPlay)}`
  );

  // 続けて利用者の一時停止の操作: pause が1件
  e.player.pos = 9;
  e.sandbox.pause();
  const afterPause = e.logs.slice(afterPlay.length);
  check(
    "AC16 利用者の一時停止の操作で pause が1件(他の記録なし)",
    afterPause.length === 1 && afterPause[0].action === "pause",
    `件数=${afterPause.length} ${fmt(afterPause)}`
  );
  check(
    "AC16 合計は play・pause の2件(準備完了の分を含まない)",
    e.logs.length === 2 && fmt(e.logs) === JSON.stringify([["play", 7, 0], ["pause", 9, 0]]),
    fmt(e.logs)
  );
}

console.log(failures.length === 0 ? "ALL PASSED" : `FAILED: ${failures.length} 件`);
process.exit(failures.length === 0 ? 0 : 1);
