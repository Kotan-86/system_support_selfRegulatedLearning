// 仕様: docs/spec/dialog-log-save.md#受入基準 (PBI-B。自動テスト対象: B1, B2, B3, B4, B6 の JS の論理)
// leave_guard.js と api_client.js を node:vm で読み込み、ブラウザ環境を偽物で置き換えて検証する。
// 依存する A-2 の公開IF(ChatPanel.onSendStateChange, DialogLog.isEnded)は tasks.md の公開IFに沿った偽物。
//   - 「送信ボタン / Enter / 応答が失敗した送信」は、いずれも ChatPanel の契約上
//     onSendStateChange(true) → (応答後) onSendStateChange(false) として現れる。
//   - 「空・空白のみ / IME / 修飾キー付きEnter / 応答待ち中の操作」は listener が呼ばれない(=契約)。
// 観察するもの: beforeunload の preventDefault と returnValue、pagehide での postDialogLogOnLeave の呼び出し回数と引数、
// beforeunload が保存要求を送らないこと。ダイアログの表示や実際の通信は実ブラウザでのみ観察できる(PO確認)。
// 使い方: node reflect_leave_guard.mjs (すべて成功で終了コード 0、失敗で 1)
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const jsRoot = path.resolve(here, "../../../framework_drivers/platform/static/js");
const read = (p) => fs.readFileSync(path.join(jsRoot, p), "utf8");
const guardSrc = read("reflect/leave_guard.js");
const apiSrc = read("common/api_client.js");

const flush = () => new Promise((r) => setImmediate(r));

let unhandled = 0;
process.on("unhandledRejection", () => { unhandled += 1; });

const failures = [];
function check(label, cond, detail) {
  if (cond) console.log(`ok   ${label}`);
  else { console.log(`FAIL ${label}: ${detail}`); failures.push(label); }
}
async function scenario(label, fn) {
  try { await fn(); }
  catch (e) {
    console.log(`FAIL ${label}: 例外 ${e && e.message}`);
    failures.push(label);
  }
}
const j = (v) => JSON.stringify(v);

// opts: { window: false → addEventListener なし, chatPanel: false, dialogLog: false, apiClient: false }
function setup(opts = {}) {
  const listeners = {};
  const leavePosts = [];
  const chatListeners = [];
  const state = { ended: false };
  const sandbox = { console };
  sandbox.window = sandbox;
  if (opts.window !== false) {
    sandbox.addEventListener = (type, fn) => { (listeners[type] = listeners[type] || []).push(fn); };
  }
  if (opts.chatPanel !== false) {
    sandbox.ChatPanel = { onSendStateChange: (fn) => chatListeners.push(fn), isSending: () => false };
  }
  if (opts.dialogLog !== false) {
    sandbox.DialogLog = { init() {}, isEnded: () => state.ended };
  }
  if (opts.apiClient !== false) {
    sandbox.ApiClient = { postDialogLogOnLeave: (pid) => { leavePosts.push(pid); } };
  }
  vm.createContext(sandbox);
  vm.runInContext(guardSrc, sandbox, { filename: "leave_guard.js" });
  return {
    sandbox, listeners, leavePosts, state,
    init: (pid = "1") => sandbox.LeaveGuard.init(pid),
    // ChatPanel の契約: 送信が始まったとき true、応答・エラー表示後に false
    sendStart: () => chatListeners.forEach((fn) => fn(true)),
    sendEnd: () => chatListeners.forEach((fn) => fn(false)),
    chatListenerCount: () => chatListeners.length,
    beforeunload() {
      const ev = { defaultPrevented: false, returnValue: undefined, preventDefault() { this.defaultPrevented = true; } };
      (listeners.beforeunload || []).forEach((fn) => fn(ev));
      return ev;
    },
    pagehide() {
      const ev = { persisted: false };
      (listeners.pagehide || []).forEach((fn) => fn(ev));
      return ev;
    },
  };
}
const confirmed = (ev) => ev.defaultPrevented === true && ev.returnValue === "";

// ---------- B1: 発言済み・未終了で beforeunload が確認を求める ----------
for (const kind of ["送信ボタン", "Enter", "応答が失敗した送信"]) {
  await scenario(`B1 ${kind}`, async () => {
    const e = setup(); e.init();
    e.sendStart(); e.sendEnd(); // 応答の成否は問わない(成功・失敗とも start → end)
    const ev = e.beforeunload();
    check(`B1 ${kind}の後: beforeunload で preventDefault`, ev.defaultPrevented === true, "preventDefault されていない");
    check(`B1 ${kind}の後: returnValue が空文字(文言は指定しない)`, ev.returnValue === "", j(ev.returnValue));
    check(`B1 ${kind}の後: shouldConfirm() が true`, e.sandbox.LeaveGuard.shouldConfirm() === true, "false");
  });
}
await scenario("B1 応答待ち中", async () => {
  const e = setup(); e.init();
  e.sendStart(); // 応答待ちの間(まだ end していない)
  check("B1 応答待ち中(送信済み)でも beforeunload で確認を求める", confirmed(e.beforeunload()), "確認を求めていない");
});
await scenario("B1 複数回の送信・登録", async () => {
  const e = setup(); e.init();
  check("B1 init は ChatPanel.onSendStateChange を購読する", e.chatListenerCount() >= 1, `n=${e.chatListenerCount()}`);
  check("B1 window に beforeunload と pagehide を登録する", (e.listeners.beforeunload || []).length >= 1 && (e.listeners.pagehide || []).length >= 1, j(Object.keys(e.listeners)));
});

// ---------- B2: 発言していないときは確認も保存もしない ----------
await scenario("B2 送信前", async () => {
  const e = setup(); e.init();
  const ev = e.beforeunload();
  check("B2 送信前: beforeunload で preventDefault しない", ev.defaultPrevented === false, "preventDefault された");
  check("B2 送信前: returnValue を設定しない", ev.returnValue === undefined, j(ev.returnValue));
  check("B2 送信前: shouldConfirm() が false", e.sandbox.LeaveGuard.shouldConfirm() === false, "true");
  e.pagehide();
  check("B2 送信前: pagehide で保存要求を送らない", e.leavePosts.length === 0, j(e.leavePosts));
});
await scenario("B2 送信が行われない操作(listener が呼ばれない)", async () => {
  // 空・空白のみ、IME確定のEnter、修飾キー付きEnter、応答待ち中の操作は ChatPanel が listener を呼ばない(契約)。
  const e = setup(); e.init();
  e.sendEnd(); // false だけが来ても発言済みにならない
  check("B2 sending=false の通知だけでは発言済みにならない(beforeunload)", e.beforeunload().defaultPrevented === false, "preventDefault された");
  e.pagehide();
  check("B2 sending=false の通知だけでは pagehide で送らない", e.leavePosts.length === 0, j(e.leavePosts));
});
await scenario("B2 新しい画面は過去の訪問を引き継がない", async () => {
  const first = setup(); first.init(); first.sendStart(); first.sendEnd();
  const second = setup(); second.init(); // 再読み込み後の新しい画面(過去の発言は数えない)
  check("B2 再読み込み後、送信前は確認を求めない", second.beforeunload().defaultPrevented === false, "preventDefault された");
  second.pagehide();
  check("B2 再読み込み後、送信前は保存要求を送らない", second.leavePosts.length === 0, j(second.leavePosts));
  second.sendStart(); second.sendEnd();
  check("B2/N4 再読み込み後に改めて送信すると確認を求める", confirmed(second.beforeunload()), "確認を求めていない");
});

// ---------- B3: 確認の要求は保存要求を送らない(キャンセルでは送らない) ----------
await scenario("B3", async () => {
  const e = setup(); e.init();
  e.sendStart(); e.sendEnd();
  e.beforeunload();
  check("B3 beforeunload(確認の要求)は保存要求を送らない", e.leavePosts.length === 0, j(e.leavePosts));
  // キャンセル = pagehide が起きない。続けて送信でき、再度確認を求め、その間も送らない
  e.sendStart(); e.sendEnd();
  const ev2 = e.beforeunload();
  check("B3 キャンセル後に続けて発言しても、再度の beforeunload で確認を求める", confirmed(ev2), "確認を求めていない");
  check("B3 キャンセル後(pagehide なし)は保存要求が0件のまま", e.leavePosts.length === 0, j(e.leavePosts));
});

// ---------- B4: 離脱の確定(pagehide)で page_leave の保存を1回送る ----------
await scenario("B4 pagehide のみ(確認のダイアログなし・再読み込み相当)", async () => {
  const e = setup(); e.init("1");
  e.sendStart(); e.sendEnd();
  e.pagehide();
  check("B4 beforeunload なしでも pagehide で postDialogLogOnLeave が1回", e.leavePosts.length === 1, j(e.leavePosts));
  check("B4 participant_id を渡す", e.leavePosts[0] === "1", j(e.leavePosts));
});
await scenario("B4 beforeunload → pagehide(離れるを選んだ場合)", async () => {
  const e = setup(); e.init("2");
  e.sendStart(); e.sendEnd();
  e.beforeunload();
  e.pagehide();
  check("B4 beforeunload の後の pagehide で1回だけ送る", e.leavePosts.length === 1, j(e.leavePosts));
  check("B4 participant_id が init に渡した値", e.leavePosts[0] === "2", j(e.leavePosts));
});
await scenario("B4 応答待ち中の離脱", async () => {
  const e = setup(); e.init("3");
  e.sendStart();
  e.pagehide();
  check("B4 応答待ち中でも、発言済みなら pagehide で送る", e.leavePosts.length === 1, j(e.leavePosts));
});
await scenario("B4 postDialogLogOnLeave の内容", async () => {
  const calls = [];
  const sandbox = { console };
  sandbox.window = sandbox;
  sandbox.fetch = (url, init) => { calls.push({ url, init }); return Promise.resolve({ ok: true }); };
  vm.createContext(sandbox);
  vm.runInContext(apiSrc, sandbox, { filename: "api_client.js" });
  check("B4 ApiClient.postDialogLogOnLeave が関数", typeof sandbox.ApiClient.postDialogLogOnLeave === "function", typeof sandbox.ApiClient.postDialogLogOnLeave);
  sandbox.ApiClient.postDialogLogOnLeave(7);
  check("B4 fetch が1回呼ばれる", calls.length === 1, `n=${calls.length}`);
  const c = calls[0] || { init: {} };
  check("B4 POST /api/dialog-log", c.url === "/api/dialog-log" && c.init.method === "POST", j(c));
  check("B4 keepalive: true(離脱後も送れるようにする)", c.init.keepalive === true, j(c.init.keepalive));
  check("B4 Content-Type: application/json", c.init.headers && c.init.headers["Content-Type"] === "application/json", j(c.init.headers));
  let body = null;
  try { body = JSON.parse(c.init.body); } catch (_) { /* 下で失敗になる */ }
  check("B4 本文は participant_id(文字列)と end_method=page_leave の2つだけ", body !== null && Object.keys(body).sort().join() === "end_method,participant_id" && body.participant_id === "7" && body.end_method === "page_leave", j(c.init.body));
});
await scenario("B4 通信の失敗は握りつぶす", async () => {
  const sandbox = { console };
  sandbox.window = sandbox;
  sandbox.fetch = () => Promise.reject(new Error("network"));
  vm.createContext(sandbox);
  vm.runInContext(apiSrc, sandbox, { filename: "api_client.js" });
  const before = unhandled;
  let threw = false;
  try { sandbox.ApiClient.postDialogLogOnLeave("1"); } catch (_) { threw = true; }
  await flush(); await flush();
  check("B4 fetch が失敗しても例外を出さない", threw === false && typeof sandbox.ApiClient.postDialogLogOnLeave === "function", `threw=${threw}`);
  check("B4 fetch の失敗が未処理の rejection にならない", typeof sandbox.ApiClient.postDialogLogOnLeave === "function" && unhandled === before, `unhandled=${unhandled - before}`);
});

// ---------- B6: 終了済みの後は確認も保存もしない ----------
await scenario("B6 終了済み", async () => {
  const e = setup(); e.init();
  e.sendStart(); e.sendEnd();
  e.state.ended = true; // 終了ボタンの保存が成功した(DialogLog.isEnded() が true)
  const ev = e.beforeunload();
  check("B6 終了済み: beforeunload で preventDefault しない", ev.defaultPrevented === false, "preventDefault された");
  check("B6 終了済み: returnValue を設定しない", ev.returnValue === undefined, j(ev.returnValue));
  check("B6 終了済み: shouldConfirm() が false", e.sandbox.LeaveGuard.shouldConfirm() === false, "true");
  e.pagehide();
  check("B6 終了済み: pagehide で保存要求を送らない(end_button を上書きしない)", e.leavePosts.length === 0, j(e.leavePosts));
});
await scenario("B6 終了の判定は離脱時点の状態を見る", async () => {
  const e = setup(); e.init();
  e.sendStart(); e.sendEnd();
  check("B6 終了前は確認を求める", confirmed(e.beforeunload()), "確認を求めていない");
  e.state.ended = true;
  check("B6 終了後は確認を求めない(状態の変化に追随)", e.beforeunload().defaultPrevented === false, "preventDefault された");
  e.pagehide();
  check("B6 終了後の pagehide で送らない", e.leavePosts.length === 0, j(e.leavePosts));
});
await scenario("B6 終了後に未発言の再訪相当", async () => {
  const e = setup(); e.init();
  e.state.ended = true;
  e.sendStart(); e.sendEnd(); // 終了後に通知が来ても、終了済みなら確認・保存しない
  check("B6 終了済みなら、その後の通知があっても確認を求めない", e.beforeunload().defaultPrevented === false, "preventDefault された");
});

// ---------- 依存や window が無い環境(公開IFの防御) ----------
for (const [name, o] of [["window.addEventListener が無い", { window: false }], ["ChatPanel が無い", { chatPanel: false }], ["DialogLog が無い", { dialogLog: false }], ["ApiClient が無い", { apiClient: false }]]) {
  await scenario(`防御 ${name}`, async () => {
    const e = setup(o);
    let threw = null;
    try { e.init(); } catch (err) { threw = err; }
    check(`防御(B4/B6の前提) ${name}: init が例外を出さない`, threw === null, threw && threw.message);
  });
}

if (failures.length) {
  console.log(`\n${failures.length} 件失敗`);
  process.exit(1);
}
console.log("\nすべて成功");
