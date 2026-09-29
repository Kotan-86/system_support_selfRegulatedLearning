// 仕様: docs/spec/reflect-chat-multiline-input.md#受入基準 (自動テスト対象: AC5〜AC14, AC17)
// chat_panel.js を node:vm でそのまま読み込み、DOM / ApiClient の最小の代役で検証する。
// 観察するもの: postChat の呼び出し回数と引数(=POST /chat の件数と内容)、keydown の preventDefault の有無
// (=Enter による改行が入るか)、入力欄の値、ユーザーメッセージ要素の textContent / innerHTML の扱い。
// 高さ・見た目は代役では観察できないので検証しない(PO確認)。
// 使い方: node reflect_chat_panel_input.mjs (すべて成功で終了コード 0、失敗で 1)
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const jsRoot = path.resolve(here, "../../../framework_drivers/platform/static/js");
const chatSrc = fs.readFileSync(path.join(jsRoot, "reflect/chat_panel.js"), "utf8");

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

// postMode: "manual" = 呼び出しごとに保留(resolve/reject を手動で)、"ok" = 即成功
function setup() {
  const posts = [];
  const pending = [];
  const createdDivs = []; // document.createElement で作られた要素
  const createdTags = [];
  const children = [];

  const chatBox = {
    scrollTop: 0,
    scrollHeight: 0,
    appendChild(el) { children.push(el); },
  };
  const submitBtn = { disabled: false };
  const form = makeTarget({ querySelector: (sel) => (sel === 'button[type="submit"]' ? submitBtn : null) });
  const input = makeTarget({ value: "", style: {} });

  const doc = {
    getElementById: (id) => ({
      "message-form": form,
      "message-input": input,
      "chat-box": chatBox,
    })[id] || null,
    createElement(tag) {
      createdTags.push(tag);
      const el = {
        tagName: tag,
        className: "",
        innerHTMLAssigned: false,
        _text: "",
        _inner: "",
        get textContent() { return this._text; },
        set textContent(v) { this._text = String(v); },
        get innerHTML() { return this._inner; },
        set innerHTML(v) { this.innerHTMLAssigned = true; this._inner = String(v); },
        remove() { const i = children.indexOf(el); if (i >= 0) children.splice(i, 1); },
      };
      createdDivs.push(el);
      return el;
    },
  };

  const sandbox = { document: doc, console };
  sandbox.window = sandbox;
  sandbox.ApiClient = {
    postChat(body) {
      posts.push(body);
      return new Promise((resolve, reject) => pending.push({ resolve, reject }));
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(chatSrc, sandbox, { filename: "chat_panel.js" });
  sandbox.ChatPanel.init(1);

  const okResponse = { ok: true, status: 200, json: async () => ({ response: "了解", session_id: "s1" }) };
  const ngResponse = { ok: false, status: 500, json: async () => ({ error: "boom" }) };

  function keydown(opts) {
    const ev = Object.assign(
      { key: "Enter", keyCode: 13, shiftKey: false, ctrlKey: false, metaKey: false, altKey: false, isComposing: false },
      opts,
    );
    ev.defaultPrevented = false;
    ev.preventDefault = () => { ev.defaultPrevented = true; };
    input.fire("keydown", ev);
    return ev;
  }
  function submit() {
    const ev = { type: "submit", defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } };
    form.fire("submit", ev);
    return ev;
  }
  return {
    posts, pending, input, submitBtn, sandbox, createdTags,
    keydown, submit,
    userMessages: () => children.filter((c) => c.className === "user-message"),
    userDivsCreated: () => createdDivs.filter((c) => c.className === "user-message"),
    async respond(i, kind) {
      const p = pending[i];
      if (kind === "ok") p.resolve(okResponse);
      else if (kind === "ng") p.resolve(ngResponse);
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

// AC5: Enter(修飾キーなし・非変換中)で1件送信、Enter の改行は入力にも送信内容にも加わらない
{
  const e = setup();
  e.input.value = "こんにちは";
  const ev = e.keydown({});
  await flush();
  check("AC5 Enter で postChat が1件", e.posts.length === 1, `posts=${e.posts.length}`);
  check("AC5 Enter は preventDefault(改行が入らない)", ev.defaultPrevented === true, "preventDefault されていない");
  check("AC5 送信内容に改行が加わらない", e.posts.length === 1 && e.posts[0].message === "こんにちは", j(e.posts[0]));
  check("AC5 送信後に入力欄が空", e.input.value === "", j(e.input.value));
  check("AC5 ユーザーメッセージが1件表示される", e.userMessages().length === 1, `n=${e.userMessages().length}`);
}

// AC6: Shift+Enter は送信しない・改行を妨げない
{
  const e = setup();
  e.input.value = "こんにちは";
  const ev = e.keydown({ shiftKey: true });
  await flush();
  check("AC6 Shift+Enter で postChat が0件", e.posts.length === 0, `posts=${e.posts.length}`);
  check("AC6 Shift+Enter は preventDefault されない(既定の改行が入る)", ev.defaultPrevented === false, "preventDefault された");
  check("AC6 入力欄の値は変わらない", e.input.value === "こんにちは", j(e.input.value));
  check("AC6 ユーザーメッセージが追加されない", e.userMessages().length === 0, `n=${e.userMessages().length}`);
}

// AC7: IME 変換中の Enter は送信せず、値は不変。確定後の Enter で送信
for (const [label, opts] of [
  ["isComposing=true", { isComposing: true, keyCode: 13 }],
  ["isComposing=false, keyCode=229 (Safari)", { isComposing: false, keyCode: 229 }],
  ["isComposing=true, keyCode=229", { isComposing: true, keyCode: 229 }],
]) {
  const e = setup();
  e.input.value = "今日";
  const ev = e.keydown(opts);
  await flush();
  check(`AC7 [${label}] postChat が0件`, e.posts.length === 0, `posts=${e.posts.length}`);
  check(`AC7 [${label}] 入力欄に「今日」が残る`, e.input.value === "今日", j(e.input.value));
  check(`AC7 [${label}] preventDefault しない(IME の確定に任せる)`, ev.defaultPrevented === false, "preventDefault された");
  e.keydown({ keyCode: 13, isComposing: false });
  await flush();
  check(`AC7 [${label}] 確定後の Enter で1件送信`, e.posts.length === 1 && e.posts[0].message === "今日", j(e.posts));
}

// AC8: 空・空白だけは送信しない。Enter は preventDefault(改行なし)、値は不変
for (const v of ["", "   ", "\n\n\n", " \t\n "]) {
  {
    const e = setup();
    e.input.value = v;
    const ev = e.keydown({});
    await flush();
    check(`AC8 Enter ${j(v)}: postChat が0件`, e.posts.length === 0, `posts=${e.posts.length}`);
    check(`AC8 Enter ${j(v)}: ユーザーメッセージ追加なし`, e.userMessages().length === 0, `n=${e.userMessages().length}`);
    check(`AC8 Enter ${j(v)}: preventDefault 済み(改行が入らない)`, ev.defaultPrevented === true, "preventDefault されていない");
    check(`AC8 Enter ${j(v)}: 入力欄の値は不変`, e.input.value === v, j(e.input.value));
  }
  {
    const e = setup();
    e.input.value = v;
    e.submit();
    await flush();
    check(`AC8 送信ボタン ${j(v)}: postChat が0件`, e.posts.length === 0, `posts=${e.posts.length}`);
    check(`AC8 送信ボタン ${j(v)}: ユーザーメッセージ追加なし`, e.userMessages().length === 0, `n=${e.userMessages().length}`);
    check(`AC8 送信ボタン ${j(v)}: 入力欄の値は不変`, e.input.value === v, j(e.input.value));
  }
}

// AC9 / AC14: 送信内容の整形。Enter でも送信ボタン(submit)でも同じ
{
  const raw = "  1行目\n\n\n2行目\n  ";
  const want = "1行目\n\n\n2行目";
  for (const via of ["Enter", "submit"]) {
    const e = setup();
    e.input.value = raw;
    if (via === "Enter") e.keydown({}); else e.submit();
    await flush();
    check(`AC9/AC14 ${via}: 送信内容が整形される`, e.posts.length === 1 && e.posts[0].message === want, j(e.posts));
    check(`AC9/AC14 ${via}: participant_id が付く`, e.posts.length === 1 && String(e.posts[0].participant_id) === "1", j(e.posts));
    check(`AC10/AC14 ${via}: 送信後に入力欄が空`, e.input.value === "", j(e.input.value));
    check(`AC12/AC14 ${via}: 表示が整形後の内容`, e.userMessages().length === 1 && e.userMessages()[0].textContent === want, j(e.userMessages().map((m) => m.textContent)));
  }
}

// AC10: 5行分の入力を送信すると入力欄は空
{
  const e = setup();
  e.input.value = "a\nb\nc\nd\ne";
  e.keydown({});
  await flush();
  check("AC10 5行の送信後に入力欄が空", e.posts.length === 1 && e.input.value === "", `posts=${e.posts.length} value=${j(e.input.value)}`);
}

// AC11: 送信中の二重送信防止。成功・!ok・例外のいずれの応答後も次を送れる
for (const kind of ["ok", "ng", "reject"]) {
  const e = setup();
  e.input.value = "first";
  e.keydown({});
  await flush();
  check(`AC11 [${kind}] 最初の1件が送信される`, e.posts.length === 1, `posts=${e.posts.length}`);

  e.input.value = "second\nline";
  const ev = e.keydown({});
  await flush();
  check(`AC11 [${kind}] 応答待ちの Enter で送信されない`, e.posts.length === 1, `posts=${e.posts.length}`);
  check(`AC11 [${kind}] 応答待ちの Enter は preventDefault 済み(改行が入らない)`, ev.defaultPrevented === true, "preventDefault されていない");
  check(`AC11 [${kind}] 応答待ちの Enter で書いた入力が残る`, e.input.value === "second\nline", j(e.input.value));
  e.submit();
  await flush();
  check(`AC11 [${kind}] 応答待ちの送信ボタン(submit)でも送信されない`, e.posts.length === 1, `posts=${e.posts.length}`);
  check(`AC11 [${kind}] 応答待ちの送信ボタンでも入力が残る`, e.input.value === "second\nline", j(e.input.value));

  await e.respond(0, kind);
  check(`AC11 [${kind}] 応答後に送信ボタンが押せる状態に戻る`, e.submitBtn.disabled === false, `disabled=${e.submitBtn.disabled}`);
  e.keydown({});
  await flush();
  check(`AC11 [${kind}] 応答後の Enter で次が送信される`, e.posts.length === 2 && e.posts[1].message === "second\nline", j(e.posts));
}

// AC12: 表示で改行を保つ(表示要素の文字列)
{
  const e = setup();
  const msg = "1行目\n2行目\n\n4行目";
  e.input.value = msg;
  e.keydown({});
  await flush();
  const m = e.userMessages();
  check("AC12 ユーザーメッセージの textContent が改行を保つ", m.length === 1 && m[0].textContent === msg, j(m.map((x) => x.textContent)));
  check("AC12 4行(3行目は空行)", m.length === 1 && m[0].textContent.split("\n").length === 4 && m[0].textContent.split("\n")[2] === "", j(m.map((x) => x.textContent)));
}

// AC13: HTML として解釈しない
for (const [via, msg] of [
  ["Enter", "<b>太字</b>"],
  ["Enter", "<img src=x onerror=alert(1)>"],
  ["Enter", "<b>\nx"],
  ["submit", "<img src=x onerror=alert(1)>"],
  ["submit", "<b>\nx"],
]) {
  const e = setup();
  e.input.value = msg;
  if (via === "Enter") e.keydown({}); else e.submit();
  await flush();
  const m = e.userMessages();
  check(`AC13 ${via} ${j(msg)}: 文字どおり textContent に入る`, m.length === 1 && m[0].textContent === msg, j(m.map((x) => x.textContent)));
  check(`AC13 ${via} ${j(msg)}: innerHTML を使わない`, e.userDivsCreated().length === 1 && e.userDivsCreated().every((d) => d.innerHTMLAssigned === false), "innerHTML に代入された");
  check(`AC13 ${via} ${j(msg)}: b / img 要素が作られない`, !e.createdTags.some((t) => /^(b|img)$/i.test(t)), j(e.createdTags));
}

// AC17: 修飾キー付き Enter では何も起きない(Shift 同時を含む)
for (const mod of ["ctrlKey", "metaKey", "altKey"]) {
  for (const shift of [false, true]) {
    const label = `${mod}${shift ? "+shiftKey" : ""}`;
    const e = setup();
    e.input.value = "こんにちは";
    const ev = e.keydown({ [mod]: true, shiftKey: shift });
    await flush();
    check(`AC17 ${label}: postChat が0件`, e.posts.length === 0, `posts=${e.posts.length}`);
    check(`AC17 ${label}: preventDefault 済み(改行が加わらない)`, ev.defaultPrevented === true, "preventDefault されていない");
    check(`AC17 ${label}: 入力欄は「こんにちは」のまま`, e.input.value === "こんにちは", j(e.input.value));
    check(`AC17 ${label}: ユーザーメッセージ追加なし`, e.userMessages().length === 0, `n=${e.userMessages().length}`);
  }
}

// 補足(AC5 の裏): Enter 以外のキーは送信しない
{
  const e = setup();
  e.input.value = "abc";
  const ev = e.keydown({ key: "a", keyCode: 65 });
  await flush();
  check("AC5(裏) Enter 以外のキーは送信せず preventDefault もしない", e.posts.length === 0 && ev.defaultPrevented === false, `posts=${e.posts.length}`);
}

if (failures.length) {
  console.log(`\n${failures.length} 件失敗`);
  process.exit(1);
}
console.log("\nすべて成功");
