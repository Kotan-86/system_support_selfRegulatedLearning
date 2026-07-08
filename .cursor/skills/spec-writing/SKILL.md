---
name: spec-writing
description: Writes and updates product specifications with Why/What, issue numbers, and testable acceptance criteria—without implementation. Use when the user asks to write or update specs, says 仕様のみ, attaches @spec-writing, or works on docs/spec/.
---

# 仕様を書く・更新する

仕様: docs/tools/prompts.md（小規模チーム向け）

## 記述ルール

- Why（なぜ）と What（何を）を必ず書く
- issue 番号を必ず書く
- 受入基準は測定可能・テスト可能な形で書く
- 変更理由を記録する
- How（実装詳細）は書かない
- 曖昧な表現（「適切に」「必要に応じて」）を避ける
- 見出しは明確で具体的にする
- 仕様を書く・更新するのみで、実装はしない

## 新規作成時

1. issue 番号 → 目的（Why）→ 実現内容（What）→ 受入基準 → 制約・関連機能の順に確認する
2. 不明点は推測せずユーザーに質問する
3. GitHub Flavored Markdown で出力する

## 出力先

- 機能単位: `docs/spec/[機能名].md`
- 小規模・横断的な内容: `README.md`

## 更新時

1. 既存仕様を読み、変更対象の見出しを特定する
2. **変更理由（Why）** を追記または更新する（issue 番号を含める）
3. What・受入基準を変更内容に合わせて更新する
4. 関連仕様へのリンクが有効か確認する

## 作業手順

```
Task Progress:
- [ ] 関連 issue 番号を確認
- [ ] 既存仕様・関連仕様を読む
- [ ] 不明点をユーザーに質問（推測しない）
- [ ] Why / What / 受入基準 / 制約を起草
- [ ] GFM で出力先に書く（またはユーザーに提示）
- [ ] 実装・テスト・lint は行わない
```

## 仕様テンプレート

新規作成時は次の骨格を使う:

```markdown
# [機能名]

Issue: #NNN

## 変更理由（Why）

- [なぜこの仕様が必要か。issue と対応づける]

## 実現内容（What）

- [何を実現するか。ユーザー／システムの振る舞い]

## 受入基準

- [ ] [測定可能・テスト可能な条件 1]
- [ ] [測定可能・テスト可能な条件 2]

## 制約

- [技術的・業務的な制約。How は書かない]

## 関連仕様

- [既存仕様への相対リンク]
```

## 禁止事項

- コードの生成・修正
- テストの追加・実行
- lint の実行
- How（クラス名・API パス・アルゴリズム等の実装詳細）の記述
- 秘密情報（`.env` 実値、credentials 等）の記載

## 参考

- 既存仕様の文体: [docs/spec/application-usecase.md](../../docs/spec/application-usecase.md)
- プロジェクト SDD 原則: ユーザールール「仕様駆動開発」
