---
name: spec-implementation
description: Implements features from specifications in docs/spec/ or README.md, with tests and spec links in code. Use when the user asks to implement from spec, says 仕様から実装, attaches @spec-implementation, or implements acceptance criteria.
---

# 仕様から実装する

仕様: docs/tools/prompts.md#仕様からコードを生成するプロンプト

## 手順

1. 関連仕様（docs/spec/\*.md または README.md）を読む
2. 仕様が無い・曖昧なら実装前に質問する
3. 受入基準を満たす実装を行う
4. 必要ならテストを追加・更新する
5. コード変更に伴い仕様更新が必要なら同時に更新する
6. 関数・モジュール等に仕様リンクのコメントを付ける

## 部分修正

依頼範囲のみ仕様に合わせて修正する。仕様に無い振る舞いを追加する場合は、先に仕様更新を提案する。

## 複数ファイル更新

仕様・コード・テストの 3 者の整合性を保つ。

## 作業手順

```
Task Progress:
- [ ] 関連仕様・受入基準を読む
- [ ] 不明点をユーザーに質問（推測しない）
- [ ] 実装（依頼範囲のみ）
- [ ] テスト追加・更新
- [ ] 仕様リンクコメントを付与
- [ ] 仕様変更が必要なら更新（または @spec-writing を提案）
- [ ] 仕様・コード・テストの整合を確認
```

## 仕様リンクコメント

プロジェクト慣例に従う:

- Python: `# 仕様: docs/spec/[機能名].md#[見出し]`
- JavaScript/TypeScript: `// 仕様: docs/spec/[機能名].md#[見出し]`

## 仕様更新が必要な場合

- 仕様に無い振る舞いを追加する → **先に仕様更新を提案**（`@spec-writing`）
- 実装で仕様の What / 受入基準が変わる → コードと**同時に**仕様を更新
- 仕様のみの変更が必要で実装不要 → `@spec-writing` に委ねる

## 関連スキル

- 仕様の作成・更新のみ: [spec-writing](../spec-writing/SKILL.md)
