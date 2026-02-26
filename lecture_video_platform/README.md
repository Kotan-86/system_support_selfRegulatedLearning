# gas/ — 講義動画プラットフォーム（GAS 用）

- **コピペ用**: 直下の `lectureVideoPlatform.gs` と `lectureVideoPlatform.html` を GAS エディタに貼る。
- **payload テスト**: `payload/` に視聴ログの JSON 組み立てロジックと Jest テスト（`gas/lectureVideoPlatform.gs` の `buildViewingLogPayload` と同一仕様）。

## コピペ手順

1. **GAS プロジェクトを開く**（新規または既存の Web アプリ用プロジェクト）。

2. **スクリプトプロパティを設定**
   - 編集 → プロジェクトのプロパティ → スクリプト プロパティ
   - `API_BASE_URL` を追加し、値に自 app のルート URL を指定（例: `https://your-app.example.com`）。末尾のスラッシュは付けない。

3. **.gs の内容をコピペ**
   - `lectureVideoPlatform.gs` の内容を、GAS の「コード.gs」または新規 .gs ファイルに貼り付ける。

4. **.html を追加**
   - GAS で「ファイル」→「新規」→「HTML ファイル」を選び、名前を **lectureVideoPlatform** にする（拡張子は GAS が付ける）。
   - `lectureVideoPlatform.html` の内容をそのファイルに貼り付ける。

5. **デプロイ**
   - デプロイ →  New deployment → 種類「ウェブアプリ」でデプロイし、URL にアクセスして動作確認。

## 注意

- `createTemplateFromFile('lectureVideoPlatform')` の引数と、追加した HTML ファイル名（拡張子なし）は一致させる。
- `participant_id` は現在 HTML 内で `1` 固定。本番では URL パラメータや入力欄で渡す運用を推奨。

## payload テスト（gas/payload/）

`lectureVideoPlatform.gs` の payload 組み立てと同一仕様を Jest で検証する。

```bash
cd gas/payload && npm install && npm test
```

API 契約は pytest: `uv run pytest tests/test_api/test_viewing_log_gas_contract.py -v`
