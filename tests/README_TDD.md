# TDD: Red の確認

実装前に、テストが **Red（失敗）** になることを確認する。

## 実行方法（uv を使用）

プロジェクトルートで:

```bash
uv run pytest tests/ -v --tb=short
```

または:

```bash
uv run python run_tests.py
```

## 現状で期待される結果（Red）

- **Step 1**: `db/schema.sql` が存在しない → `test_schema_file_exists` が FAIL
- **Step 2**: `db/data/` が存在しない、`.gitignore` に db の記述がない → Step 2 のテストが FAIL
- **Step 3**: `db.init_db` が未実装 → `ImportError` でスキップ
- **Step 4**: `db.repository` が未実装 → スキップ
- **Step 5**: 同上 → スキップ

失敗するテストが複数あり、スキップが複数出れば「Red の確認」完了。  
以降、Step 1 から順に実装して Green にしていく。

---

## テストのフォルダ構成

- **tests/test_db/** … DB 構築（スキーマ・初期化・repository）のテスト（test_step1_schema 〜 test_step5_integration）
- **tests/test_app/** … 本開発用アプリ（/chat と履歴）のテスト（test_step1_skeleton 〜 test_step5_integration）
- **tests/conftest.py** … 共通フィクスチャ（両方で利用）

実行例:
- 全テスト: `uv run pytest tests/ -v --tb=short`
- DB のみ: `uv run pytest tests/test_db/ -v --tb=short`
- アプリのみ: `uv run pytest tests/test_app/ -v --tb=short`

## アプリ（/chat と履歴）の TDD

DB 構築完了後、本開発用アプリの TDD 用に **tests/test_app/** に次のテストを用意している。

| ファイル | 検証内容 |
|----------|----------|
| test_step1_skeleton.py | app.main に Flask の app がある。GET / が 200。POST /chat に message で JSON が返る。 |
| test_step2_session_id.py | session_id なしで POST → レスポンスに session_id。同じ session_id を送るとそのセッションが使われる。 |
| test_step3_history_in_prompt.py | 同一 session で 2 回 /chat したとき、2 回目のプロンプトに 1 回目のやり取りが含まれる（LLM は app.main._call_llm をモック）。 |
| test_step4_messages_persisted.py | POST /chat のあと、get_history に user と assistant の 2 件が保存されている。 |
| test_step5_integration.py | 同一 session で 2 回 /chat し、2 回目のプロンプトに 1 回目が含まれることと、履歴が 4 件になること。 |

実装時は **Step 1 → 2 → 3 → 4 → 5** の順で Green にしていく。Step 3 以降は LLM 呼び出しを `_call_llm(prompt)` にまとめておくと `patch("app.main._call_llm")` でモックしやすい。
