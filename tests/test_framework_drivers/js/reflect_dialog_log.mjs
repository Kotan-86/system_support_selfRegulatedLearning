// 仕様: docs/spec/dialog-log-save.md#受入基準 (PBI-A-2。自動テスト対象: A9・A10・A19 の「画面の JS の論理」)
// chat_panel.js(実物)と dialog_log.js(実物)を node:vm で読み込み、DOM と ApiClient の最小の代役で検証する。
// 観察するもの: postDialogLog の呼び出し回数と引数、要素の disabled / hidden / class、DialogLog.isEnded()、
//   ChatPanel.onSendStateChange の listener の呼ばれ方。
// 見た目・位置・実ブラウザの操作は代役では観察できないので検証しない(PO確認)。
// 出力の各行の先頭のラベルに AC 番号(A9 / A10 / A19)か「IF」(T5 の公開IF)を入れる。pytest 側がこの接頭辞で振り分ける。
// 使い方: node reflect_dialog_log.mjs (すべて成功で終了コード 0、失敗で 1)
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const jsRoot = path.resolve(here, "../../../framework_drivers/platform/static/js");
const chatSrc = fs.readFileSync(path.join(jsRoot, "reflect/chat_panel.js"), "utf8");
const dialogSrc = fs.readFileSync(path.join(jsRoot, "reflect/dialog_log.js"), "utf8");

const PID = "1";
const flush = () => new Promise((r) => setImmediate(r));

function makeTarget(extra) {
  const listeners = {};
  return Object.assign(
    {
      listeners,
      addEventListener(type, fn) {
        (listeners[type] = listeners[type] || []).push(fn);
      },
      fire(type, ev) {
        for (const fn of (listeners[type] || []).slice()) fn(ev);
      },
    },
    extra,
  );
}

// hidden / disabled / class の3通りの操作方法(プロパティ、属性、classList)を代役で受ける
function makeEl(id, init) {
  const el = makeTarget({
    id,
    disabled: false,
    hidden: false,
    className: "",
    style: {},
    textContent: "",
    setAttribute(n, v) {
      if (n === "hidden") el.hidden = true;
      else if (n === "disabled") el.disabled = true;
      else if (n === "class") el.className = String(v);
    },
    removeAttribute(n) {
      if (n === "hidden") el.hidden = false;
      else if (n === "disabled") el.disabled = false;
    },
    classList: {
      add(...cs) { for (const c of cs) if (!el.classList.contains(c)) el.className = (el.className + " " + c).trim(); },
      remove(...cs) { el.className = el.className.split(/\s+/).filter((x) => x && !cs.includes(x)).join(" "); },
      contains(c) { return el.className.split(/\s+/).includes(c); },
      toggle(c, force) {
        const on = force === undefined ? !el.classList.contains(c) : !!force;
        if (on) el.classList.add(c); else el.classList.remove(c);
        return on;
      },
    },
  });
  return Object.assign(el, init);
}
const visible = (el) => el.hidden === false && el.style.display !== "none";
const concealed = (el) => el.hidden === true || el.style.display === "none";
const hasClass = (el, c) => el.className.split(/\s+/).includes(c);

// opts.dialog=false: DialogLog を init しない(ChatPanel 単体の検証用)
// opts.missing: getElementById が null を返す id の配列("*" ですべて)
function setup(opts = {}) {
  const chatPosts = [];
  const chatPending = [];
  const dialogPosts = [];
  const dialogPending = [];
  const children = [];
  const events = []; // 呼び出し順の記録

  const chatBox = { scrollTop: 0, scrollHeight: 0, appendChild(el) { children.push(el); } };
  const submitBtn = { disabled: false };
  const form = makeTarget({
    querySelector: (sel) => (sel === 'button[type="submit"]' ? submitBtn : null),
  });
  const input = makeTarget({ value: "", style: {}, disabled: false });
  const endBtn = makeEl("end-dialog-button");
  const errorEl = makeEl("dialog-end-error", { hidden: true });
  const completeEl = makeEl("dialog-end-complete", { hidden: true });
  const panel = makeEl("chat-panel");

  const missing = opts.missing || [];
  const table = {
    "message-form": form,
    "message-input": input,
    "chat-box": chatBox,
    "chat-panel": panel,
    "end-dialog-button": endBtn,
    "dialog-end-error": errorEl,
    "dialog-end-complete": completeEl,
  };
  const doc = {
    getElementById: (id) => (missing.includes("*") || missing.includes(id) ? null : table[id] || null),
    querySelector: (sel) => {
      if (missing.includes("*")) return null;
      if (/button\[type="submit"\]/.test(sel)) return submitBtn;
      const m = /^#([\w-]+)$/.exec(sel);
      return m ? doc.getElementById(m[1]) : null;
    },
    createElement(tag) {
      const el = {
        tagName: tag,
        className: "",
        _text: "",
        get textContent() { return this._text; },
        set textContent(v) { this._text = String(v); },
        innerHTML: "",
        remove() { const i = children.indexOf(el); if (i >= 0) children.splice(i, 1); },
      };
      return el;
    },
  };

  const sandbox = { document: doc, console };
  sandbox.window = sandbox;
  sandbox.ApiClient = {
    postChat(body) {
      events.push("postChat");
      chatPosts.push(body);
      return new Promise((resolve, reject) => chatPending.push({ resolve, reject }));
    },
    postDialogLog(participantId, endMethod) {
      events.push("postDialogLog");
      dialogPosts.push({ participantId, endMethod });
      return new Promise((resolve, reject) => dialogPending.push({ resolve, reject }));
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(chatSrc, sandbox, { filename: "chat_panel.js" });
  vm.runInContext(dialogSrc, sandbox, { filename: "dialog_log.js" });
  sandbox.ChatPanel.init(PID);
  if (opts.dialog !== false) sandbox.DialogLog.init(PID);

  const okRes = { ok: true, status: 200, json: async () => ({ response: "了解", session_id: "s1" }) };
  const ngRes = { ok: false, status: 500, json: async () => ({ error: "boom" }) };
  const saveOk = { ok: true, status: 200, json: async () => ({}) };
  const saveNg = { ok: false, status: 500, json: async () => ({}), text: async () => "" };

  function keydown(o) {
    const ev = Object.assign(
      { key: "Enter", keyCode: 13, shiftKey: false, ctrlKey: false, metaKey: false, altKey: false, isComposing: false },
      o,
    );
    ev.preventDefault = () => {};
    input.fire("keydown", ev);
  }
  return {
    sandbox, chatPosts, dialogPosts, events, children, input, submitBtn, endBtn, errorEl, completeEl, panel,
    send(text, o) { input.value = text; keydown(o || {}); },
    clickEnd() { endBtn.fire("click", { type: "click", preventDefault() {} }); },
    async respondChat(i, kind) {
      const p = chatPending[i];
      if (kind === "ok") p.resolve(okRes);
      else if (kind === "ng") p.resolve(ngRes);
      else p.reject(new Error("network"));
      await flush();
    },
    async respondSave(i, kind) {
      const p = dialogPending[i];
      if (kind === "ok") p.resolve(saveOk);
      else if (kind === "ng") p.resolve(saveNg);
      else p.reject(new Error("network"));
      await flush();
    },
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
const j = (v) => JSON.stringify(v);

// シナリオ内の例外(スタブの not implemented、未実装の関数を呼んだ TypeError を含む)を、そのシナリオの失敗として記録する
async function scenario(label, fn) {
  try {
    await fn();
  } catch (e) {
    console.log(`FAIL ${label} [シナリオが例外で中断]: ${e && e.message}`);
    failures.push(`${label} [例外]`);
  }
}

// ---------- A9: 押すと保存要求を1回送り、成功で完了画面に切り替わる ----------
for (const rounds of [0, 2]) {
  await scenario(`A9 [発言${rounds}往復]`, async () => {
    const e = setup();
    for (let i = 0; i < rounds; i++) {
      e.send(`発言${i}`);
      await flush();
      await e.respondChat(i, "ok");
    }
    const tag = `A9 [${rounds}往復の後]`;
    check(`${tag} 押す前は完了表示が隠れている`, concealed(e.completeEl), "表示されている");
    check(`${tag} 押す前は isEnded() が false`, e.sandbox.DialogLog.isEnded() === false, "true");

    e.clickEnd();
    await flush();
    check(`${tag} 押すと postDialogLog が(pid, "end_button")で1回`, e.dialogPosts.length === 1 && String(e.dialogPosts[0].participantId) === PID && e.dialogPosts[0].endMethod === "end_button", j(e.dialogPosts));
    check(`${tag} 保存中はボタンが無効`, e.endBtn.disabled === true, `disabled=${e.endBtn.disabled}`);
    e.clickEnd();
    await flush();
    check(`${tag} 保存中の再押下で2回目が送られない`, e.dialogPosts.length === 1, `n=${e.dialogPosts.length}`);
    check(`${tag} 応答前は完了にならない`, concealed(e.completeEl) && e.sandbox.DialogLog.isEnded() === false, "完了になった");

    await e.respondSave(0, "ok");
    check(`${tag} 成功で isEnded() が true`, e.sandbox.DialogLog.isEnded() === true, "false");
    check(`${tag} 完了表示(#dialog-end-complete)が表示される`, visible(e.completeEl), `hidden=${e.completeEl.hidden}`);
    check(`${tag} #chat-panel に dialog-ended が付く`, hasClass(e.panel, "dialog-ended"), j(e.panel.className));
    check(`${tag} メッセージ入力欄が無効`, e.input.disabled === true, `disabled=${e.input.disabled}`);
    check(`${tag} 送信ボタンが無効`, e.submitBtn.disabled === true, `disabled=${e.submitBtn.disabled}`);
    check(`${tag} 終了ボタンが無効`, e.endBtn.disabled === true, `disabled=${e.endBtn.disabled}`);
    check(`${tag} 失敗表示は隠れている`, concealed(e.errorEl), "表示されている");

    e.clickEnd();
    await flush();
    check(`${tag} 完了後の押下で保存要求が増えない`, e.dialogPosts.length === 1, `n=${e.dialogPosts.length}`);
  });
}

// ---------- A10: 失敗(!ok / 例外)で失敗表示、完了にならず、再押下で再送、成功で完了 ----------
for (const kind of ["ng", "reject"]) {
  await scenario(`A10 [${kind}]`, async () => {
    const e = setup();
    const tag = `A10 [${kind === "ng" ? "!ok の応答" : "通信の例外"}]`;
    check(`${tag} 押す前は失敗表示が隠れている`, concealed(e.errorEl), "表示されている");
    e.clickEnd();
    await flush();
    await e.respondSave(0, kind);
    check(`${tag} 失敗表示(#dialog-end-error)が表示される`, visible(e.errorEl), `hidden=${e.errorEl.hidden}`);
    check(`${tag} 完了にならない(isEnded() が false)`, e.sandbox.DialogLog.isEnded() === false, "true");
    check(`${tag} 完了表示は隠れたまま`, concealed(e.completeEl), "表示されている");
    check(`${tag} #chat-panel に dialog-ended が付かない`, !hasClass(e.panel, "dialog-ended"), j(e.panel.className));
    check(`${tag} 終了ボタンが再び押せる`, e.endBtn.disabled === false, `disabled=${e.endBtn.disabled}`);
    check(`${tag} 入力欄・送信ボタンは無効にならない`, e.input.disabled === false && e.submitBtn.disabled === false, `input=${e.input.disabled} submit=${e.submitBtn.disabled}`);

    e.clickEnd();
    await flush();
    check(`${tag} 再押下で2回目の保存要求が(pid, "end_button")で送られる`, e.dialogPosts.length === 2 && e.dialogPosts[1].endMethod === "end_button" && String(e.dialogPosts[1].participantId) === PID, j(e.dialogPosts));
    check(`${tag} 再押下の間は失敗表示が隠れる`, concealed(e.errorEl), "表示されたまま");

    await e.respondSave(1, "ok");
    check(`${tag} 再試行が成功すると完了になる`, e.sandbox.DialogLog.isEnded() === true && visible(e.completeEl) && hasClass(e.panel, "dialog-ended"), `ended=${e.sandbox.DialogLog.isEnded()} hidden=${e.completeEl.hidden}`);
    check(`${tag} 完了後は失敗表示が隠れ、入力・送信・終了ボタンが無効`, concealed(e.errorEl) && e.input.disabled === true && e.submitBtn.disabled === true && e.endBtn.disabled === true, `err.hidden=${e.errorEl.hidden}`);
  });
}

await scenario("A10 [失敗の連続]", async () => {
  const e = setup();
  e.clickEnd(); await flush(); await e.respondSave(0, "ng");
  e.clickEnd(); await flush(); await e.respondSave(1, "reject");
  check("A10 [失敗の連続] 2回失敗しても失敗表示が出て、まだ押せる", visible(e.errorEl) && e.endBtn.disabled === false && e.sandbox.DialogLog.isEnded() === false, `hidden=${e.errorEl.hidden} disabled=${e.endBtn.disabled}`);
  e.clickEnd(); await flush();
  check("A10 [失敗の連続] 3回目の押下も送られる", e.dialogPosts.length === 3, `n=${e.dialogPosts.length}`);
});

// ---------- A19: 応答待ちの間は終了ボタンを押せない ----------
for (const kind of ["ok", "ng", "reject"]) {
  await scenario(`A19 [${kind}]`, async () => {
    const e = setup();
    const tag = `A19 [応答=${kind}]`;
    check(`${tag} 送信前は終了ボタンが押せる`, e.endBtn.disabled === false, `disabled=${e.endBtn.disabled}`);

    e.send("こんにちは");
    await flush();
    check(`${tag} 送信が始まった`, e.chatPosts.length === 1, `n=${e.chatPosts.length}`);
    check(`${tag} 応答待ちの間は終了ボタンが無効`, e.endBtn.disabled === true, `disabled=${e.endBtn.disabled}`);
    e.clickEnd();
    await flush();
    check(`${tag} 応答待ちの押下で保存要求が送られない`, e.dialogPosts.length === 0, `n=${e.dialogPosts.length}`);

    await e.respondChat(0, kind);
    check(`${tag} 応答(またはエラー)の表示後は終了ボタンが押せる`, e.endBtn.disabled === false, `disabled=${e.endBtn.disabled}`);
    e.clickEnd();
    await flush();
    check(`${tag} 応答後の押下で保存要求が1回送られる`, e.dialogPosts.length === 1 && e.dialogPosts[0].endMethod === "end_button", j(e.dialogPosts));
  });
}

await scenario("A19 [送信されない操作]", async () => {
  // 送信が始まらない操作(空、修飾キー付き Enter など)では終了ボタンを無効にしない
  const e = setup();
  e.send("   ");
  e.send("あ", { ctrlKey: true });
  e.send("あ", { isComposing: true });
  await flush();
  check("A19 [送信されない操作] 空・修飾キー・IME では postChat が0件で、終了ボタンは押せる", e.chatPosts.length === 0 && e.endBtn.disabled === false, `posts=${e.chatPosts.length} disabled=${e.endBtn.disabled}`);
});

// ---------- IF: 11-T5 の公開IF(ChatPanel.onSendStateChange / isSending / 要素が無いとき) ----------
await scenario("IF [onSendStateChange の順序]", async () => {
  for (const kind of ["ok", "ng", "reject"]) {
    const e = setup({ dialog: false });
    const seen = [];
    e.sandbox.ChatPanel.onSendStateChange((s) => {
      e.events.push(`state:${s}`);
      const last = e.children[e.children.length - 1];
      seen.push({ s, lastClass: last && last.className, lastText: last && last.textContent });
    });
    check(`IF [${kind}] 送信前は isSending() が false`, e.sandbox.ChatPanel.isSending() === false, "true");
    e.send("こんにちは");
    await flush();
    check(`IF [${kind}] 送信で listener(true) が postChat の直前に1回`, j(e.events) === j(["state:true", "postChat"]), j(e.events));
    check(`IF [${kind}] 応答待ちの間は isSending() が true`, e.sandbox.ChatPanel.isSending() === true, "false");
    await e.respondChat(0, kind);
    check(`IF [${kind}] 応答後に listener(false) が1回`, seen.length === 2 && seen[1].s === false, j(seen));
    check(`IF [${kind}] listener(false) は応答(エラー)の表示後に呼ばれる`, seen.length === 2 && seen[1].lastClass === "tutor-message" && seen[1].lastText !== "", j(seen[1]));
    check(`IF [${kind}] 応答後は isSending() が false`, e.sandbox.ChatPanel.isSending() === false, "true");
  }
});

await scenario("IF [送信されない操作では listener を呼ばない]", async () => {
  const e = setup({ dialog: false });
  const calls = [];
  e.sandbox.ChatPanel.onSendStateChange((s) => calls.push(s));
  e.send("");
  e.send("  \n ");
  e.send("あ", { isComposing: true });
  e.send("あ", { keyCode: 229 });
  e.send("あ", { ctrlKey: true });
  e.send("あ", { metaKey: true });
  e.send("あ", { altKey: true });
  e.send("あ", { shiftKey: true });
  await flush();
  check("IF 送信されない操作で listener は0回", calls.length === 0 && e.chatPosts.length === 0, `calls=${j(calls)} posts=${e.chatPosts.length}`);

  e.send("first");
  await flush();
  e.send("second"); // 応答待ちの間の操作
  await flush();
  check("IF 応答待ちの間の操作で listener が増えない(true が1回だけ)", j(calls) === j([true]) && e.chatPosts.length === 1, `calls=${j(calls)}`);
});

await scenario("IF [複数の listener]", async () => {
  const e = setup({ dialog: false });
  const a = [];
  const b = [];
  e.sandbox.ChatPanel.onSendStateChange((s) => a.push(s));
  e.sandbox.ChatPanel.onSendStateChange((s) => b.push(s));
  e.send("hi");
  await flush();
  await e.respondChat(0, "ok");
  check("IF 登録済みの listener がすべて呼ばれる", j(a) === j([true, false]) && j(b) === j([true, false]), `a=${j(a)} b=${j(b)}`);
});

await scenario("IF [要素が見つからないとき]", async () => {
  for (const missing of [["*"], ["end-dialog-button"], ["dialog-end-error", "dialog-end-complete", "chat-panel"]]) {
    let threw = null;
    let e = null;
    try {
      e = setup({ missing });
    } catch (err) {
      threw = err;
    }
    // スタブの not implemented もここで検出される(setup の中の DialogLog.init の例外)
    check(`IF [欠落 ${j(missing)}] init が例外を出さない`, threw === null, threw && threw.message);
    if (e) {
      let t2 = null;
      try { e.clickEnd(); e.sandbox.DialogLog.isEnded(); } catch (err) { t2 = err; }
      check(`IF [欠落 ${j(missing)}] 押下・isEnded() が例外を出さない`, t2 === null, t2 && t2.message);
    }
  }
});

if (failures.length) {
  console.log(`\n${failures.length} 件失敗`);
  process.exit(1);
}
console.log("\nすべて成功");
