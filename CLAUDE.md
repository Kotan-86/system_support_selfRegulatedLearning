## dev-team プロダクト設定

- 仕様の置き場: docs/spec/
- バグ仕様の置き場: docs/spec/bugs/
- 検査コマンド:
  - 静的解析: なし(未設定)
  - 型検査: なし(未設定)
  - ビルド: なし(`uv sync` で依存解決)
  - テスト: `uv run pytest tests/ -v`(実呼び出しは `-m real_llm`、認証が必要)
- UI確認の準備: `uv run flask --app framework_drivers.platform.main run`。Vertex認証は `.env.local`(README参照)
- UI以外の実動作の確認方法: `uv run pytest tests/ -v`
- Gitホストと提出手順: GitHub PR、ベースブランチ: develop
- PBIの大きさの基準: 実装コード(src)の変更が300行超で超過(仮。運用して見直す。テスト、仕様、記録は数えない)
- 最新であるべきドキュメントの一覧: 既定(変更の影響を受けるもの)
- DoDの追加項目: なし
- レビュー観点の追加: なし
- プロダクトゴール: docs/product-goal.md
- `.work/` の扱い: git管理しない(`.gitignore`)

## コンパクション時の指示

圧縮するときは、スプリントの状態(ゴール、PBIの状態、未解決の判断依頼、障害物)を優先して残す。
