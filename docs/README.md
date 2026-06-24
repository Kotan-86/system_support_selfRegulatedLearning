# ドキュメント

自己調整学習支援システム（SSSRL）の仕様・実装計画。

## 背景

- 既存 ADR: [Arcitecture/ADR_SSSRL-backend_2026-02-23.md](../Arcitecture/ADR_SSSRL-backend_2026-02-23.md)
- 現行実装は Flask + SQLite（対話用 / 学習データ用の 2 DB）のモノリス
- リファクタ目的: LAD・AI チューター・将来の統合フロントが共有する**ドメインモデル**を確立し、AI による段階的実装を可能にする

## 仕様一覧

| ドキュメント | 内容 |
|-------------|------|
| [spec/domain-model.md](spec/domain-model.md) | エンティティ・値オブジェクト・不変条件・Read Model |
| [spec/domain-implementation-plan.md](spec/domain-implementation-plan.md) | ドメイン層の段階的実装計画（AI 実装用） |
| [spec/application-usecase.md](spec/application-usecase.md) | Use Case / Port / DTO・Interactor 規約 |
| [spec/application-error-handling.md](spec/application-error-handling.md) | `Result` / `AppError`・エラーステータス一覧 |
| [spec/interfaces-layer.md](spec/interfaces-layer.md) | Controller / Presenter / ViewModel・LAD 表示契約 |
| [spec/interfaces-implementation-plan.md](spec/interfaces-implementation-plan.md) | interfaces 層の段階的実装計画（AI 実装用） |

## 読み方

1. **domain-model.md** … 何を作るか（What）と受入条件の根拠
2. **domain-implementation-plan.md** … ドメイン層をどの順序で PR 分割するか
3. **application-usecase.md** … Use Case と Port の契約
4. **application-error-handling.md** … 失敗の型と HTTP 委譲の前提
5. **interfaces-layer.md** … 外部契約（ViewModel）と ingress / egress の責務分界
6. **interfaces-implementation-plan.md** … interfaces 層をどの順序で PR 分割するか。各フェーズ末尾の受入基準で完了判定

## 用語

| ドメイン | API / DB（既存） |
|----------|------------------|
| Learner | participant |
| LearnerId | participant_id |
| positionDelta | duration（視聴ログ） |
| videoPosition | current_time（視聴ログ） |
| occurredAt | time_stamp（視聴ログ） |
