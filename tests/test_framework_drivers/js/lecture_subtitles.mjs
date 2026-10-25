// 仕様: docs/spec/subtitle-display.md#受入基準 (AC2〜AC8, AC10, AC12, AC14, 制約: HTML非解釈)
// subtitles.js と player.js を node:vm でそのまま読み込み、DOM / YouTube API / ApiClient の最小の代役で検証する。
// 使い方: node lecture_subtitles.mjs [lectures ディレクトリ]  (すべて成功で終了コード 0、失敗で 1)
//
// テストが前提にする公開IF(tests.md に記録):
//   - subtitles.js は window.LectureSubtitles を公開する(selectCue / update / toggle / isVisible)。
//   - 読み込み時に window.__LECTURE_SUBTITLES__ ([{start,end,text}] 秒) と、
//     DOM の #subtitle-area / #subtitle-toggle を自分で結びつける(切替は click イベント)。
//   - 表示は #subtitle-area の textContent に設定する。非表示のとき textContent は空文字。
//   - player.js は再生位置を更新するたびに LectureSubtitles.update(位置) を呼ぶ
//     (LectureSubtitles が無い環境でも壊れない)。
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const jsRoot = path.resolve(here, "../../../framework_drivers/platform/static/js");
const lecturesDir = process.argv[2] || path.resolve(here, "../../../lectures");
const playerSrc = fs.readFileSync(path.join(jsRoot, "lecture/player.js"), "utf8");
const participantSrc = fs.readFileSync(path.join(jsRoot, "common/participant_context.js"), "utf8");
const subtitlesSrc = fs.readFileSync(path.join(jsRoot, "lecture/subtitles.js"), "utf8");

function makeTarget() {
  const listeners = {};
  return {
    listeners,
    addEventListener(type, fn) {
      (listeners[type] = listeners[type] || []).push(fn);
    },
    dispatch(type) {
      for (const fn of (listeners[type] || []).slice()) fn({ type, preventDefault() {} });
    },
  };
}

// 合成キュー。重なり: A(0-5) B(3-8) C(6-10)。間隔: 10-12。包含: E(20-30) F(22-30)。
const CUES = [
  { start: 0, end: 5, text: "A" },
  { start: 3, end: 8, text: "B" },
  { start: 6, end: 10, text: "C" },
  { start: 12, end: 15, text: "D" },
  { start: 20, end: 30, text: "E" },
  { start: 22, end: 30, text: "F" },
];

function setup(opts = {}) {
  const cues = "cues" in opts ? opts.cues : CUES;
  const logs = [];
  const timers = new Map();
  let timerSeq = 0;
  const storage = opts.storage || new Map(); // 再読み込みを模すとき、呼び出し側が共有する
  const calls = { seekTo: 0, playVideo: 0, pauseVideo: 0, fetch: 0, xhr: 0, beacon: 0 };

  const seekbar = Object.assign(makeTarget(), { value: 0, max: 0, style: {} });
  const time = { innerHTML: "" };
  const playerEl = { offsetWidth: 600 };
  const innerHTMLSets = [];
  const areaState = { text: "" };
  const area = {
    get textContent() { return areaState.text; },
    set textContent(v) { areaState.text = String(v); },
    get innerText() { return areaState.text; },
    set innerText(v) { areaState.text = String(v); },
    set innerHTML(v) { innerHTMLSets.push(String(v)); },
    get innerHTML() { return ""; },
    style: {},
    hidden: false,
    setAttribute() {},
    removeAttribute() {},
  };
  const button = Object.assign(makeTarget(), { textContent: "", style: {}, setAttribute() {} });
  const win = makeTarget();
  let ytPlayer = null;

  const YT = {
    PlayerState: { PLAYING: 1, PAUSED: 2 },
    Player: function (id, o) {
      const self = this;
      ytPlayer = self;
      self.events = o.events;
      self.pos = 0;
      self.getCurrentTime = () => self.pos;
      self.getDuration = () => 100;
      self.setSize = () => {};
      self.seekTo = (t) => { calls.seekTo++; self.pos = t; };
      self.playVideo = () => { calls.playVideo++; self.events.onStateChange({ data: 1 }); };
      self.pauseVideo = () => { calls.pauseVideo++; self.events.onStateChange({ data: 2 }); };
    },
  };

  const elements = opts.noElements
    ? { seekbar, time, player: playerEl }
    : { seekbar, time, player: playerEl, "subtitle-area": area, "subtitle-toggle": button };

  const sandbox = Object.assign(win, {
    YT,
    location: { search: "?participant_id=p1" },
    URLSearchParams,
    innerWidth: 1000,
    innerHeight: 800,
    document: {
      documentElement: { clientWidth: 1000, clientHeight: 800 },
      body: { clientWidth: 1000, clientHeight: 800 },
      getElementById: (id) => elements[id] || null,
    },
    sessionStorage: {
      getItem: (k) => (storage.has(k) ? storage.get(k) : null),
      setItem: (k, v) => storage.set(k, String(v)),
      removeItem: (k) => storage.delete(k),
    },
    localStorage: {
      getItem: (k) => (storage.has("ls:" + k) ? storage.get("ls:" + k) : null),
      setItem: (k, v) => storage.set("ls:" + k, String(v)),
      removeItem: (k) => storage.delete("ls:" + k),
    },
    // 通信の代役(切替で1件も呼ばれないことを検証する)
    fetch: () => { calls.fetch++; return Promise.resolve({ ok: true, json: async () => ({}) }); },
    XMLHttpRequest: function () { calls.xhr++; this.open = () => {}; this.send = () => {}; this.setRequestHeader = () => {}; },
    navigator: { sendBeacon: () => { calls.beacon++; return true; } },
    setInterval: (fn) => { timers.set(++timerSeq, fn); return timerSeq; },
    clearInterval: (id) => { timers.delete(id); },
    __LECTURE_VIDEO_ID__: "vid",
  });
  if (cues !== undefined) sandbox.__LECTURE_SUBTITLES__ = cues;
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(participantSrc, sandbox, { filename: "participant_context.js" });
  sandbox.ApiClient = {
    postViewingLog(participantId, currentTime, action, duration) {
      logs.push({ participantId, current_time: currentTime, action, duration });
    },
  };
  if (!opts.noSubtitlesScript) {
    vm.runInContext(subtitlesSrc, sandbox, { filename: "subtitles.js" });
  }
  vm.runInContext(playerSrc, sandbox, { filename: "player.js" });

  sandbox.onYouTubeIframeAPIReady();
  ytPlayer.events.onReady({ target: ytPlayer });
  logs.length = 0;
  for (const k of Object.keys(calls)) calls[k] = 0;

  return {
    logs, calls, seekbar, sandbox, area, button, storage, innerHTMLSets,
    get player() { return ytPlayer; },
    get shown() { return areaState.text; },
    tick() { for (const fn of [...timers.values()]) fn(); },
    timerCount() { return timers.size; },
    click() { button.dispatch("click"); },
    // 再生中にして、位置 t で1回 tick する(500ms ごとの定期更新の1回分)
    playAt(t) { if (timers.size === 0) sandbox.play(); ytPlayer.pos = t; this_tick(); },
    at(t) { ytPlayer.pos = t; this_tick(); },
  };
  function this_tick() { for (const fn of [...timers.values()]) fn(); }
}

const failures = [];
function check(label, cond, detail) {
  if (cond) console.log(`ok   ${label}`);
  else { console.log(`FAIL ${label}: ${detail}`); failures.push(label); }
}
const q = (s) => JSON.stringify(s);

// ---- AC2: 初期状態は非表示 ----
{
  const e = setup();
  check("AC2: ページを開いた直後、表示領域は空", e.shown === "", q(e.shown));
  e.sandbox.play();
  e.player.pos = 6; e.tick();
  check("AC2: 有効なキューがある位置で再生しても、ボタンを押すまで文は出ない", e.shown === "", q(e.shown));
  e.click();
  check("AC2: ボタンを押すと表示される(前提確認、位置6.0 -> C)", e.shown === "C", q(e.shown));
}

// ---- AC3: 再生中の同期(1秒以内 = 500ms の更新1回で反映) ----
{
  const e = setup();
  e.click(); // 表示にする
  e.sandbox.play();
  for (const [t, want] of [[1, "A"], [3.0, "B"], [6.0, "C"], [8.5, "C"], [11, ""], [13, "D"], [16, ""]]) {
    e.player.pos = t; e.tick();
    check(`AC3: 再生中 位置${t} の表示=${q(want)}`, e.shown === want, q(e.shown));
  }
}

// ---- AC4: 一時停止中は変わらない ----
{
  const e = setup();
  e.click();
  e.sandbox.play();
  e.player.pos = 6; e.tick();
  e.sandbox.pause();
  check("AC4: 一時停止した位置(6.0)の文 C のまま", e.shown === "C", q(e.shown));
  e.tick(); e.tick();
  check("AC4: 一時停止中に更新が走っても変わらない", e.shown === "C", q(e.shown));
  check("AC4: 一時停止中は定期更新が残っていない", e.timerCount() === 0, `timers=${e.timerCount()}`);
}

// ---- AC5: スキップ・シーク追従(再生中/一時停止中) ----
{
  const e = setup();
  e.click();
  e.sandbox.play();
  e.player.pos = 10; e.seekbar.value = 10; e.tick();
  e.sandbox.pause();
  e.player.pos = 7; e.seekbar.value = 7; // 一時停止中の位置
  e.sandbox.forwardSkip(); // 12 -> D
  check("AC5: 一時停止中の先送りスキップ後(位置12)の文 D", e.shown === "D", q(e.shown));
  e.sandbox.backwardSkip(); // 7 -> C
  check("AC5: 一時停止中の巻き戻しスキップ後(位置7)の文 C", e.shown === "C", q(e.shown));
}
{
  const e = setup();
  e.click();
  e.sandbox.play();
  e.player.pos = 1; e.seekbar.value = 1; e.tick();
  e.sandbox.forwardSkip(); // 6 -> C
  check("AC5: 再生中の先送りスキップ後(位置6)の文 C", e.shown === "C", q(e.shown));
  e.sandbox.backwardSkip(); // 1 -> A
  check("AC5: 再生中の巻き戻しスキップ後(位置1)の文 A", e.shown === "A", q(e.shown));
}
{
  // シークバー: 一時停止中にドラッグ(input) -> 確定(change)
  const e = setup();
  e.click();
  e.sandbox.play();
  e.player.pos = 1; e.seekbar.value = 1; e.tick();
  e.sandbox.pause();
  e.seekbar.value = 13; e.seekbar.dispatch("input"); e.seekbar.dispatch("change");
  check("AC5: 一時停止中のシークバー(位置13)移動後の文 D", e.shown === "D", q(e.shown));
  e.seekbar.value = 4; e.seekbar.dispatch("input"); e.seekbar.dispatch("change");
  check("AC5: シークバーで戻した後(位置4)の文 B", e.shown === "B", q(e.shown));
  e.seekbar.value = 11; e.seekbar.dispatch("input"); e.seekbar.dispatch("change");
  check("AC5: 有効なキューがない位置(11)にシークすると空", e.shown === "", q(e.shown));
}

// ---- AC6: 表示と非表示の切替 ----
{
  const e = setup();
  e.sandbox.play();
  e.player.pos = 1; e.tick();      // 非表示のまま位置が進む
  e.player.pos = 13; e.tick();
  e.click();
  check("AC6: 非表示のとき押すと、その時点の位置(13)の文 D が出る", e.shown === "D", q(e.shown));
  e.click();
  check("AC6: 表示のとき押すと、文が出なくなる", e.shown === "", q(e.shown));
  e.player.pos = 6; e.tick();
  check("AC6: 非表示の間は更新されても出ない", e.shown === "", q(e.shown));
  e.click();
  check("AC6: 再度表示にすると位置6の文 C", e.shown === "C", q(e.shown));
}
{
  // 非表示のまま一時停止中にスキップし、その後で表示にする
  const e = setup();
  e.sandbox.play(); e.sandbox.pause();
  e.player.pos = 2; e.seekbar.value = 2;
  e.sandbox.forwardSkip(); // 7
  e.click();
  check("AC6: 非表示のまま一時停止中にスキップ(位置7)後、表示にすると C", e.shown === "C", q(e.shown));
}

// ---- AC7: 切替は HTTP 要求を1件も送らない ----
{
  const e = setup();
  e.sandbox.play(); e.player.pos = 6; e.tick();
  e.logs.length = 0;
  for (let i = 0; i < 4; i++) e.click(); // 再生中に4回
  e.sandbox.pause(); e.logs.length = 0;
  for (let i = 0; i < 3; i++) e.click(); // 一時停止中に3回
  check("AC7: 切替でログ(ApiClient.postViewingLog)が0件", e.logs.length === 0, q(e.logs));
  check("AC7: 切替で fetch/XHR/sendBeacon が0件", e.calls.fetch === 0 && e.calls.xhr === 0 && e.calls.beacon === 0, q(e.calls));
}

// ---- AC8: 切替は再生に影響しない ----
for (const playing of [true, false]) {
  const e = setup();
  e.sandbox.play();
  if (!playing) e.sandbox.pause();
  e.player.pos = 6; e.seekbar.value = 6;
  e.storage.set("currenttime", "77");
  for (const k of Object.keys(e.calls)) e.calls[k] = 0;
  e.logs.length = 0;
  const before = { pos: e.player.pos, bar: e.seekbar.value, ct: e.storage.get("currenttime") };
  e.click(); e.click(); e.click();
  const lab = playing ? "再生中" : "一時停止中";
  check(`AC8(${lab}): seekTo/playVideo/pauseVideo が呼ばれない`,
    e.calls.seekTo === 0 && e.calls.playVideo === 0 && e.calls.pauseVideo === 0, q(e.calls));
  check(`AC8(${lab}): 再生位置と currenttime が変わらない`,
    e.player.pos === before.pos && e.seekbar.value === before.bar && e.storage.get("currenttime") === before.ct,
    q({ pos: e.player.pos, ct: e.storage.get("currenttime") }));
  check(`AC8(${lab}): 切替でログが0件`, e.logs.length === 0, q(e.logs));
}
{
  // 切替の直後に操作したときのログが、切替なしの場合と同じ
  const run = (toggle) => {
    const e = setup();
    const t = () => { if (toggle) e.click(); };
    t(); e.sandbox.play();
    t(); e.player.pos = 5; e.seekbar.value = 5; e.tick();
    t(); e.sandbox.forwardSkip();
    t(); e.sandbox.backwardSkip();
    t(); e.sandbox.pause();
    t(); e.player.pos = 5; e.seekbar.value = 5; e.seekbar.dispatch("input"); e.seekbar.value = 20; e.seekbar.dispatch("change");
    t();
    return e.logs.map((l) => [l.action, l.current_time, l.duration]);
  };
  const base = run(false), withToggle = run(true);
  check("AC8: 切替ありの操作ログが、切替なしと件数・内容とも同じ(件数>0)",
    base.length > 0 && q(base) === q(withToggle), `${q(base)} vs ${q(withToggle)}`);
}

// ---- AC10: 重なりの整理(合成データ) ----
{
  const e = setup();
  e.click(); e.sandbox.play();
  const table = [[0.0, "A"], [2.999, "A"], [3.0, "B"], [4.9, "B"], [5.0, "B"], [6.0, "C"], [7.9, "C"],
    [8.0, "C"], [9.999, "C"], [10.0, ""], [11.9, ""], [12.0, "D"], [15.0, ""], [21, "E"], [22, "F"], [29.9, "F"], [30, ""]];
  for (const [t, want] of table) {
    e.player.pos = t; e.tick();
    check(`AC10(合成): 位置${t} の表示=${q(want)}(開始が最も遅い1件)`, e.shown === want, q(e.shown));
  }
}

// ---- AC10: 実データ ----
function parseTs(s) {
  const m = s.trim().match(/(\d+):(\d+):(\d+)[,.](\d+)/);
  return m ? +m[1] * 3600 + +m[2] * 60 + +m[3] + +m[4] / 1000 : 0;
}
function parseSrt(text) {
  const cues = [];
  for (const block of text.split(/\r?\n\s*\r?\n/)) {
    const lines = block.trim().split(/\r?\n/).map((l) => l.trim()).filter((l) => l);
    if (lines.length < 2) continue;
    const arrow = lines[1].indexOf("-->");
    if (arrow === -1) continue;
    cues.push({ start: parseTs(lines[1].slice(0, arrow)), end: parseTs(lines[1].slice(arrow + 3)), text: lines.slice(2).join(" ") });
  }
  return cues;
}
function oracle(cues, t) { // 仕様の定義: 有効=開始<=t<終了、表示すべき文=開始が最も遅いキュー
  let best = null;
  for (const c of cues) if (c.start <= t && t < c.end && (best === null || c.start >= best.start)) best = c;
  return best ? best.text : "";
}
for (const id of ["lecture-1", "lecture-2", "lecture-3"]) {
  const cues = parseSrt(fs.readFileSync(path.join(lecturesDir, id, "subtitles.srt"), "utf8"));
  const e = setup({ cues });
  e.click(); e.sandbox.play();
  const maxEnd = Math.max(...cues.map((c) => c.end));
  const positions = new Set();
  for (let t = 0; t <= maxEnd + 2; t += 0.25) positions.add(t);
  for (const c of cues) { positions.add(c.start); positions.add(c.end); positions.add((c.start + c.end) / 2); }
  let bad = null, n = 0;
  for (const t of [...positions].sort((a, b) => a - b)) {
    e.player.pos = t; e.tick(); n++;
    const want = oracle(cues, t);
    if (e.shown !== want) { bad = { t, got: e.shown, want }; break; }
  }
  check(`AC10(実データ ${id}): ${n} 地点で表示=有効なキューのうち開始が最も遅い1件`, bad === null, q(bad));
  if (id === "lecture-1") {
    check("AC10(前提 lecture-1): キュー2=2.9-8.149 / キュー3=5.779-9.05 の時刻構成",
      cues[1].start === 2.9 && cues[1].end === 8.149 && cues[2].start === 5.779 && cues[2].end === 9.05,
      q(cues.slice(0, 3)));
    e.player.pos = 6.0; e.tick();
    check("AC10(lecture-1): 6.0秒はキュー3の文だけ(キュー2の文は出ない)",
      e.shown === cues[2].text && e.shown !== cues[1].text && !e.shown.includes(cues[1].text), q(e.shown));
    e.player.pos = 3.0; e.tick();
    check("AC10(lecture-1): 3.0秒はキュー2の文だけ(キュー1の文は出ない)",
      e.shown === cues[1].text && !e.shown.includes(cues[0].text), q(e.shown));
  }
}

// ---- AC12: SRT がない / 字幕データが空・欠落・要素欠落でも画面が止まらない ----
for (const [label, o] of [["字幕データが空配列", { cues: [] }], ["字幕データが無い", { cues: undefined }], ["表示要素が無い", { noElements: true }]]) {
  let threw = null, e = null;
  try {
    e = setup(o);
    if (!o.noElements) e.click();
    e.sandbox.play(); e.player.pos = 6; e.tick();
    if (!o.noElements) e.click(); // 表示/非表示
    e.sandbox.pause();
    e.sandbox.forwardSkip();
    e.sandbox.backwardSkip();
  } catch (err) { threw = err; }
  check(`AC12(${label}): 例外なく動く`, threw === null, String(threw && threw.stack));
  if (e && threw === null) {
    const actions = e.logs.map((l) => l.action);
    check(`AC12(${label}): 視聴ログが従来どおり(play, pause, forward_skip, backward_skip)`,
      q(actions) === q(["play", "pause", "forward_skip", "backward_skip"]), q(actions));
    check(`AC12(${label}): 表示領域は空のまま`, e.shown === "", q(e.shown));
  }
}
{
  // subtitles.js 自体が読み込まれていない環境でも player.js が従来どおり動く(AC12/AC16 の防御)
  const e = setup({ noSubtitlesScript: true });
  e.sandbox.play(); e.player.pos = 6; e.tick(); e.sandbox.pause(); e.sandbox.forwardSkip();
  check("AC12: LectureSubtitles が無くても player.js のログが従来どおり",
    q(e.logs.map((l) => l.action)) === q(["play", "pause", "forward_skip"]), q(e.logs));
}

// ---- AC14: 再読み込みで初期状態(非表示)に戻る(sessionStorage / localStorage は共有) ----
{
  const shared = new Map();
  const a = setup({ storage: shared });
  a.click(); a.sandbox.play(); a.player.pos = 6; a.tick();
  check("AC14(前提): 表示にすると C が出る", a.shown === "C", q(a.shown));
  const b = setup({ storage: shared }); // 再読み込み(新しいページ、同じブラウザの記憶領域)
  check("AC14: 再読み込み直後は非表示", b.shown === "", q(b.shown));
  b.sandbox.play(); b.player.pos = 6; b.tick();
  check("AC14: 再読み込み後、ボタンを押すまで文は出ない", b.shown === "", q(b.shown));
}

// ---- 制約: 字幕の文を HTML として解釈させない ----
{
  const raw = "<b>x</b> & <img src=x onerror=alert(1)>";
  const e = setup({ cues: [{ start: 0, end: 5, text: raw }] });
  e.click(); e.sandbox.play(); e.player.pos = 1; e.tick();
  check("制約: 文は textContent にそのまま入る(HTML 非解釈)", e.shown === raw, q(e.shown));
  check("制約: innerHTML に文を入れない", e.innerHTMLSets.every((s) => !s.includes("<")), q(e.innerHTMLSets));
}

console.log(failures.length === 0 ? "ALL PASSED" : `FAILED: ${failures.length} 件`);
process.exit(failures.length === 0 ? 0 : 1);
