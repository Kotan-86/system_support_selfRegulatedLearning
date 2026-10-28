// 仕様: docs/spec/humanities-lectures.md#受入基準 (PBI #33。自動テスト対象: AC17, AC18, AC19(b)(c), AC20, AC21(a) の JS の論理)
// 実物の api_client.js / player.js / quiz.js / chat_panel.js / dialog_log.js / leave_guard.js / reflect_app.js を
// node:vm で読み込み、DOM・YouTube API・fetch だけを代役にして、サーバーに送られる本文と URL を観察する。
//
// test-writer が定めた公開IF(tests.md 参照。型は変えず、末尾に任意の講義ID引数を足す):
//   ApiClient.buildViewingLogPayload(pid, currentTime, action, duration, lectureId?)
//   ApiClient.postViewingLog(pid, currentTime, action, duration, lectureId?)
//   ApiClient.buildQuizAttemptPayload(pid, answers, num, den, lectureId?)
//   ApiClient.getLad(pid, lectureId?)            -> /api/participants/<pid>/lad?lecture_id=<講義ID>
//   ApiClient.postDialogLog(pid, endMethod, lectureId?) / ApiClient.postDialogLogOnLeave(pid, lectureId?)
//   ChatPanel.init(pid, lectureId?) / DialogLog.init(pid, lectureId?) / LeaveGuard.init(pid, lectureId?)
//   講義ページ: window.__LECTURE_ID__(player.js / quiz.js が読む)
//   振り返りページ: window.__REFLECT_LECTURE_ID__(reflect_app.js が読む。null / 未定義 = 講義IDなし)
//   講義IDがないとき、本文・URL に lecture_id を含めない(従来どおり)。
// 出力の各行の先頭のラベルに AC 番号を入れる。pytest 側がこの接頭辞で振り分ける。
// 使い方: node humanities_lecture_id.mjs (すべて成功で終了コード 0、失敗で 1)
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const jsRoot = path.resolve(here, "../../../framework_drivers/platform/static/js");
const read = (p) => fs.readFileSync(path.join(jsRoot, p), "utf8");
const src = {
  participant: read("common/participant_context.js"),
  api: read("common/api_client.js"),
  player: read("lecture/player.js"),
  quiz: read("lecture/quiz.js"),
  chat: read("reflect/chat_panel.js"),
  dialog: read("reflect/dialog_log.js"),
  leave: read("reflect/leave_guard.js"),
  reflectApp: read("reflect/reflect_app.js"),
};

const flush = () => new Promise((r) => setImmediate(r));
const failures = [];
function check(label, cond, detail) {
  if (cond) console.log(`ok   ${label}`);
  else { console.log(`FAIL ${label}: ${detail}`); failures.push(label); }
}
async function scenario(label, fn) {
  try { await fn(); }
  catch (e) { console.log(`FAIL ${label} [シナリオが例外で中断]: ${e && e.message}`); failures.push(`${label} [例外]`); }
}
const j = (v) => JSON.stringify(v);
const keysOf = (o) => Object.keys(o).sort().join(",");

// ---------- 共通の代役 ----------
function makeTarget(extra) {
  const listeners = {};
  return Object.assign({
    listeners,
    addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
    fire(type, ev) { for (const fn of (listeners[type] || []).slice()) fn(ev); },
  }, extra);
}

// fetch の代役。呼び出しを記録し、URL に応じた最小の応答を返す。
function makeFetch(calls) {
  return (url, init) => {
    calls.push({ url: String(url), init: init || {}, body: init && init.body ? JSON.parse(init.body) : undefined });
    const body = String(url).includes("/lad") ? { content_updated_at: null } : String(url) === "/chat" ? { response: "了解", session_id: "s1" } : {};
    return Promise.resolve({ ok: true, status: 200, json: async () => body, text: async () => "" });
  };
}
const callsTo = (calls, prefix) => calls.filter((c) => c.url.startsWith(prefix));

function newSandbox(extra) {
  const win = makeTarget();
  const sandbox = Object.assign(win, { console, URLSearchParams, location: { search: "" } }, extra);
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  return sandbox;
}
const run = (sandbox, code, name) => vm.runInContext(code, sandbox, { filename: name });

// ===================================================================
// Part A: ApiClient 単体(本文・URL の形)
// ===================================================================
function apiSandbox() {
  const calls = [];
  const sandbox = newSandbox({ fetch: makeFetch(calls) });
  run(sandbox, src.api, "api_client.js");
  return { sandbox, calls, api: sandbox.ApiClient };
}

await scenario("AC17 ApiClient 視聴ログ", async () => {
  const { api, calls } = apiSandbox();
  const p = api.buildViewingLogPayload("P01", 10, "play", 0, "lecture-4");
  check("AC17 buildViewingLogPayload: lecture_id が付き、従来の5項目も付く", p.lecture_id === "lecture-4" && keysOf(p) === "action,current_time,duration,lecture_id,participant_id,time_stamp", j(p));
  const q = api.buildViewingLogPayload("P01", 10, "play", 0);
  check("AC20 buildViewingLogPayload: 講義IDなしは従来の5項目だけ", keysOf(q) === "action,current_time,duration,participant_id,time_stamp", j(q));
  await api.postViewingLog("P01", 12, "pause", 0, "lecture-5");
  const c = callsTo(calls, "/api/viewing-log")[0];
  check("AC17 postViewingLog: POST /api/viewing-log の本文に lecture_id", c && c.init.method === "POST" && c.body.lecture_id === "lecture-5" && c.body.action === "pause" && c.body.participant_id === "P01", j(c));
  await api.postViewingLog("P01", 12, "pause", 0);
  const d = callsTo(calls, "/api/viewing-log")[1];
  check("AC20 postViewingLog: 講義IDなしは lecture_id を含まない", d && !("lecture_id" in d.body), j(d));
});

await scenario("AC18 ApiClient 小テスト", async () => {
  const { api } = apiSandbox();
  const answers = [{ question_index: 1, selected_answer: "x", is_correct: 0 }];
  const p = api.buildQuizAttemptPayload("P01", answers, 0, 1, "lecture-6");
  check("AC18 buildQuizAttemptPayload: lecture_id が付き、従来の5項目も付く", p.lecture_id === "lecture-6" && keysOf(p) === "answers,lecture_id,participant_id,score_denominator,score_numerator,timestamp", j(p));
  const q = api.buildQuizAttemptPayload("P01", answers, 0, 1);
  check("AC20 buildQuizAttemptPayload: 講義IDなしは従来の5項目だけ", keysOf(q) === "answers,participant_id,score_denominator,score_numerator,timestamp", j(q));
});

await scenario("AC19 ApiClient LAD の取得", async () => {
  const { api, calls } = apiSandbox();
  await api.getLad("P01", "lecture-4");
  await api.getLad("P01");
  const lads = callsTo(calls, "/api/participants/");
  check("AC19(b) getLad: 講義ID付きは ?lecture_id=lecture-4", lads[0] && lads[0].url === "/api/participants/P01/lad?lecture_id=lecture-4", j(lads[0]));
  check("AC19(c)/AC20 getLad: 講義IDなしは従来の URL(クエリなし)", lads[1] && lads[1].url === "/api/participants/P01/lad", j(lads[1]));
});

await scenario("AC21 ApiClient 対話ログ", async () => {
  const { api, calls } = apiSandbox();
  await api.postDialogLog("P01", "end_button", "lecture-4");
  await api.postDialogLog("P01", "end_button");
  api.postDialogLogOnLeave("P01", "lecture-4");
  api.postDialogLogOnLeave("P01");
  await flush();
  const logs = callsTo(calls, "/api/dialog-log");
  check("AC21(a) postDialogLog: lecture_id が付き、participant_id と end_method も付く", logs[0] && keysOf(logs[0].body) === "end_method,lecture_id,participant_id" && logs[0].body.lecture_id === "lecture-4" && logs[0].body.end_method === "end_button", j(logs[0]));
  check("AC13(d) postDialogLog: 講義IDなしは participant_id と end_method の2つだけ", logs[1] && keysOf(logs[1].body) === "end_method,participant_id", j(logs[1]));
  check("AC21(a) postDialogLogOnLeave: page_leave に lecture_id が付き、keepalive", logs[2] && logs[2].init.keepalive === true && keysOf(logs[2].body) === "end_method,lecture_id,participant_id" && logs[2].body.end_method === "page_leave" && logs[2].body.lecture_id === "lecture-4", j(logs[2]));
  check("AC13(d) postDialogLogOnLeave: 講義IDなしは2つだけ", logs[3] && keysOf(logs[3].body) === "end_method,participant_id", j(logs[3]));
});

// ===================================================================
// Part B: 講義ページ(player.js / quiz.js)が送る講義ID
// ===================================================================
function lecturePageSandbox(lectureId) {
  const calls = [];
  const timers = new Map();
  let timerSeq = 0;
  const storage = new Map();
  const seekbar = makeTarget({ value: 0, max: 0, style: {} });
  const time = { innerHTML: "" };
  const playerEl = { offsetWidth: 600 };
  let yt = null;
  const extra = {
    fetch: makeFetch(calls),
    YT: {
      PlayerState: { PLAYING: 1, PAUSED: 2 },
      Player: function (id, opts) {
        yt = this;
        this.events = opts.events; this.pos = 0;
        this.getCurrentTime = () => this.pos;
        this.getDuration = () => 100;
        this.setSize = () => {};
        this.seekTo = (t) => { this.pos = t; };
        this.playVideo = () => this.events.onStateChange({ data: 1 });
        this.pauseVideo = () => this.events.onStateChange({ data: 2 });
      },
    },
    innerWidth: 1000, innerHeight: 800,
    document: {
      readyState: "complete",
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
    __PARTICIPANT_ID__: "P01",
    __LECTURE_VIDEO_ID__: "vid",
  };
  if (lectureId !== undefined) extra.__LECTURE_ID__ = lectureId;
  const sandbox = newSandbox(extra);
  run(sandbox, src.participant, "participant_context.js");
  run(sandbox, src.api, "api_client.js");
  run(sandbox, src.player, "player.js");
  sandbox.onYouTubeIframeAPIReady();
  yt.events.onReady({ target: yt });
  calls.length = 0;
  return { sandbox, calls, seekbar, get yt() { return yt; } };
}

const VIEWING_KEYS_WITH_LECTURE = "action,current_time,duration,lecture_id,participant_id,time_stamp";
const VIEWING_KEYS_LEGACY = "action,current_time,duration,participant_id,time_stamp";

for (const lectureId of ["lecture-4", "lecture-5", "lecture-6", "lecture-1"]) {
  await scenario(`AC17 [${lectureId}] 視聴操作`, async () => {
    const e = lecturePageSandbox(lectureId);
    e.sandbox.play();
    e.sandbox.pause();
    e.sandbox.forwardSkip();
    e.sandbox.backwardSkip();
    e.yt.pos = 10;
    e.seekbar.value = 40; e.seekbar.fire("input"); e.seekbar.fire("change");   // 前方シーク
    e.yt.pos = 50;
    e.seekbar.value = 20; e.seekbar.fire("input"); e.seekbar.fire("change");   // 後方シーク
    const logs = callsTo(e.calls, "/api/viewing-log").map((c) => c.body);
    const actions = logs.map((b) => b.action).sort().join(",");
    check(`AC17 [${lectureId}] 6 種類の操作がそれぞれ送られる`, actions === "backward_seek,backward_skip,forward_seek,forward_skip,pause,play", actions);
    check(`AC17 [${lectureId}] すべての視聴ログの本文に lecture_id が付く`, logs.length >= 6 && logs.every((b) => b.lecture_id === lectureId), j(logs.map((b) => b.lecture_id)));
    check(`AC17 [${lectureId}] 従来の項目(participant_id, time_stamp, current_time, action, duration)も付く`, logs.every((b) => keysOf(b) === VIEWING_KEYS_WITH_LECTURE && b.participant_id === "P01"), j(logs.map(keysOf)));
  });
}

await scenario("AC20 講義ページに講義IDの埋め込みがない(従来のページ)", async () => {
  const e = lecturePageSandbox(undefined);
  e.sandbox.play();
  const logs = callsTo(e.calls, "/api/viewing-log").map((c) => c.body);
  check("AC20 __LECTURE_ID__ が無いとき、視聴ログに lecture_id を含めない", logs.length === 1 && keysOf(logs[0]) === VIEWING_KEYS_LEGACY, j(logs));
});

function quizSandbox(lectureId) {
  const calls = [];
  const ANSWERS = { 1: "a", 2: "b", 3: "c", 4: "d", 5: "e" };
  const els = {};
  const form = makeTarget({
    setAttribute() {},
    querySelector(sel) {
      const m = /name="q(\d+)"/.exec(sel);
      return m ? { value: ANSWERS[m[1]] } : null;
    },
  });
  els["quiz-form"] = form;
  els["quiz-error"] = { textContent: "", hidden: true };
  els["quiz-submit"] = { disabled: false };
  els["quiz-result"] = { hidden: true };
  const extra = {
    fetch: makeFetch(calls),
    document: { readyState: "complete", getElementById: (id) => els[id] || null, addEventListener() {} },
    __PARTICIPANT_ID__: "P01",
    __QUIZ_ANSWER_KEY__: ANSWERS,
  };
  if (lectureId !== undefined) extra.__LECTURE_ID__ = lectureId;
  const sandbox = newSandbox(extra);
  run(sandbox, src.participant, "participant_context.js");
  run(sandbox, src.api, "api_client.js");
  run(sandbox, src.quiz, "quiz.js");
  return { calls, form };
}

for (const lectureId of ["lecture-4", "lecture-5", "lecture-6", "lecture-1"]) {
  await scenario(`AC18 [${lectureId}] 小テスト送信`, async () => {
    const e = quizSandbox(lectureId);
    e.form.fire("submit", { preventDefault() {} });
    await flush(); await flush();
    const posts = callsTo(e.calls, "/api/quiz-attempts");
    check(`AC18 [${lectureId}] POST /api/quiz-attempts が1回`, posts.length === 1, `n=${posts.length}`);
    const b = (posts[0] || {}).body || {};
    check(`AC18 [${lectureId}] 本文に lecture_id が付く`, b.lecture_id === lectureId, j(b));
    check(`AC18 [${lectureId}] 従来の項目(participant_id, timestamp, score_numerator, score_denominator, answers)も付く`, keysOf(b) === "answers,lecture_id,participant_id,score_denominator,score_numerator,timestamp" && b.participant_id === "P01" && b.score_denominator === 5 && Array.isArray(b.answers) && b.answers.length === 5, j(b));
  });
}

await scenario("AC20 小テスト: 講義IDの埋め込みがない(従来のページ)", async () => {
  const e = quizSandbox(undefined);
  e.form.fire("submit", { preventDefault() {} });
  await flush(); await flush();
  const b = ((callsTo(e.calls, "/api/quiz-attempts")[0]) || {}).body || {};
  check("AC20 __LECTURE_ID__ が無いとき、小テストの本文に lecture_id を含めない", keysOf(b) === "answers,participant_id,score_denominator,score_numerator,timestamp", j(b));
});

// ===================================================================
// Part C: 振り返りページ(reflect_app.js + 各モジュール)が送る講義ID
// ===================================================================
function reflectSandbox(lectureId) {
  const calls = [];
  const children = [];
  const chatBox = { scrollTop: 0, scrollHeight: 0, appendChild(el) { children.push(el); } };
  const submitBtn = { disabled: false };
  const form = makeTarget({ querySelector: (sel) => (sel === 'button[type="submit"]' ? submitBtn : null) });
  const input = makeTarget({ value: "", style: {}, disabled: false });
  const hiddenEl = () => ({ hidden: true, setAttribute() { this.hidden = true; }, removeAttribute() { this.hidden = false; } });
  const endBtn = makeTarget({ disabled: false });
  const panel = { classList: { add() {} } };
  const table = {
    "message-form": form, "message-input": input, "chat-box": chatBox, "chat-panel": panel,
    "end-dialog-button": endBtn, "dialog-end-error": hiddenEl(), "dialog-end-complete": hiddenEl(),
  };
  const timers = [];
  const extra = {
    fetch: makeFetch(calls),
    document: {
      readyState: "complete",
      getElementById: (id) => table[id] || null,
      querySelector: () => null,
      createElement: () => ({ className: "", textContent: "", innerHTML: "", remove() {} }),
      addEventListener() {},
    },
    LadPanel: { render() {}, resizeCharts() {} },
    setInterval: (fn) => { timers.push(fn); return timers.length; },
    clearInterval() {},
    __PARTICIPANT_ID__: "P01",
    __REFLECT_PARTICIPANT_ID__: "P01",
    __REFLECT_POLL_INTERVAL_MS__: 5000,
  };
  if (lectureId !== undefined) extra.__REFLECT_LECTURE_ID__ = lectureId;
  const sandbox = newSandbox(extra);
  for (const [name, code] of [["participant_context.js", src.participant], ["api_client.js", src.api], ["chat_panel.js", src.chat], ["dialog_log.js", src.dialog], ["leave_guard.js", src.leave], ["reflect_app.js", src.reflectApp]]) {
    run(sandbox, code, name);   // 最後の reflect_app.js が、読み込み時に init を実行する
  }
  return {
    sandbox, calls,
    send(text) {
      input.value = text;
      input.fire("keydown", { key: "Enter", keyCode: 13, shiftKey: false, ctrlKey: false, metaKey: false, altKey: false, isComposing: false, preventDefault() {} });
    },
    clickEnd() { endBtn.fire("click", { type: "click", preventDefault() {} }); },
    pagehide() { sandbox.fire("pagehide", { persisted: false }); },
  };
}

for (const lectureId of ["lecture-4", "lecture-5", "lecture-6"]) {
  await scenario(`AC19/AC21 [${lectureId}] 振り返りページ`, async () => {
    const e = reflectSandbox(lectureId);
    await flush();
    const lads = callsTo(e.calls, "/api/participants/");
    check(`AC19(b) [${lectureId}] LAD の取得に lecture_id=${lectureId} が付く`, lads.length >= 1 && lads.every((c) => c.url === `/api/participants/P01/lad?lecture_id=${lectureId}`), j(lads.map((c) => c.url)));

    e.send("質問です");
    await flush(); await flush();
    const chats = callsTo(e.calls, "/chat");
    check(`AC19(b) [${lectureId}] /chat の本文に lecture_id が付き、従来の項目も付く`, chats.length === 1 && chats[0].body.lecture_id === lectureId && chats[0].body.message === "質問です" && chats[0].body.participant_id === "P01", j(chats));

    e.clickEnd();
    await flush(); await flush();
    const ends = callsTo(e.calls, "/api/dialog-log");
    check(`AC21(a) [${lectureId}] 終了ボタン: 本文に lecture_id が付き、participant_id と end_method=end_button も付く`, ends.length === 1 && keysOf(ends[0].body) === "end_method,lecture_id,participant_id" && ends[0].body.lecture_id === lectureId && ends[0].body.end_method === "end_button" && ends[0].body.participant_id === "P01", j(ends));
  });

  await scenario(`AC21 [${lectureId}] ページ離脱`, async () => {
    const e = reflectSandbox(lectureId);
    await flush();
    e.send("質問です");
    await flush(); await flush();
    e.pagehide();
    await flush();
    const leaves = callsTo(e.calls, "/api/dialog-log");
    check(`AC21(a) [${lectureId}] 発言済みの pagehide: 本文に lecture_id が付き、end_method=page_leave、participant_id も付く`, leaves.length === 1 && keysOf(leaves[0].body) === "end_method,lecture_id,participant_id" && leaves[0].body.lecture_id === lectureId && leaves[0].body.end_method === "page_leave" && leaves[0].init.keepalive === true, j(leaves));
  });
}

await scenario("AC19(c)/AC21(c) [講義IDなし] 振り返りページ", async () => {
  for (const missing of [undefined, null]) {
    const tag = missing === null ? "null" : "未定義";
    const e = reflectSandbox(missing);
    await flush();
    const lads = callsTo(e.calls, "/api/participants/");
    check(`AC19(c) [${tag}] LAD の取得に講義IDは付かない`, lads.length >= 1 && lads.every((c) => c.url === "/api/participants/P01/lad"), j(lads.map((c) => c.url)));
    e.send("質問です");
    await flush(); await flush();
    const chats = callsTo(e.calls, "/chat");
    check(`AC19(c) [${tag}] /chat の本文に講義IDは付かない(従来の項目だけ)`, chats.length === 1 && !("lecture_id" in chats[0].body) && keysOf(chats[0].body) === "message,participant_id", j(chats));
    e.clickEnd();
    await flush(); await flush();
    e.pagehide();
    await flush();
    const logs = callsTo(e.calls, "/api/dialog-log");
    check(`AC13(d) [${tag}] 終了ボタンの本文は participant_id と end_method の2つだけ`, logs.length >= 1 && keysOf(logs[0].body) === "end_method,participant_id" && logs[0].body.end_method === "end_button", j(logs[0]));
  }
  const e2 = reflectSandbox(undefined);
  await flush();
  e2.send("質問です");
  await flush(); await flush();
  e2.pagehide();
  await flush();
  const leave = callsTo(e2.calls, "/api/dialog-log");
  check("AC13(d) ページ離脱の本文は participant_id と end_method の2つだけ", leave.length === 1 && keysOf(leave[0].body) === "end_method,participant_id" && leave[0].body.end_method === "page_leave", j(leave));
});

if (failures.length) {
  console.log(`\n${failures.length} 件失敗`);
  process.exit(1);
}
console.log("\nすべて成功");
