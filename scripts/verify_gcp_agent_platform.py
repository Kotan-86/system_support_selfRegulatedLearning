# 仕様: docs/spec/framework-drivers-layer.md#Gemini-Enterprise-Agent-Platform-初期設定
"""
Gemini Enterprise Agent Platform（旧 Vertex AI）の API・課金・SA ロールを検証する。

実行例（.env.local を読み込んだうえで）:
  set -a && source .env.local && set +a
  uv run python scripts/verify_gcp_agent_platform.py

API を未有効なら有効化を試行する:
  uv run python scripts/verify_gcp_agent_platform.py --enable-api
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import google.auth
import google.auth.transport.requests

# Agent Platform（Generative AI on Vertex）の REST エンドポイント用 API
_AGENT_PLATFORM_API = "aiplatform.googleapis.com"
_SERVICE_USAGE_API = "serviceusage.googleapis.com"
_REQUIRED_SA_ROLES = (
    "roles/aiplatform.user",
    "roles/aiplatform.admin",
    "roles/owner",
    "roles/editor",
)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _authorized_session() -> tuple[google.auth.transport.requests.AuthorizedSession, str | None]:
    credentials, default_project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    session = google.auth.transport.requests.AuthorizedSession(credentials)
    return session, default_project


def _service_account_email(credentials: Any) -> str | None:
    email = getattr(credentials, "service_account_email", None)
    if email:
        return str(email)
    return None


def _get_json(session: google.auth.transport.requests.AuthorizedSession, url: str) -> dict[str, Any]:
    response = session.get(url, timeout=30)
    if response.status_code == 404:
        return {}
    if not response.ok:
        raise RuntimeError(f"GET {url} failed ({response.status_code}): {response.text[:500]}")
    return response.json()


def _post_json(
    session: google.auth.transport.requests.AuthorizedSession, url: str
) -> dict[str, Any]:
    response = session.post(url, json={}, timeout=120)
    if not response.ok:
        raise RuntimeError(f"POST {url} failed ({response.status_code}): {response.text[:500]}")
    return response.json()


def _resolve_project_id(default_project: str | None) -> str:
    project_id = os.environ.get("VERTEX_PROJECT_ID") or default_project
    if not project_id:
        raise RuntimeError(
            "VERTEX_PROJECT_ID が未設定です（.env.local または gcloud ADC を確認）"
        )
    return project_id


def _check_api_enabled(
    session: google.auth.transport.requests.AuthorizedSession, project_id: str
) -> str:
    url = (
        f"https://{_SERVICE_USAGE_API}/v1/projects/{project_id}"
        f"/services/{_AGENT_PLATFORM_API}"
    )
    try:
        body = _get_json(session, url)
    except RuntimeError as exc:
        if "403" in str(exc) and "serviceusage" in str(exc).lower():
            return "UNKNOWN (Service Usage API 未有効。コンソールまたは gcloud で有効化が必要)"
        raise
    state = body.get("state", "UNKNOWN")
    return str(state)


def _enable_api(
    session: google.auth.transport.requests.AuthorizedSession, project_id: str
) -> str:
    url = (
        f"https://{_SERVICE_USAGE_API}/v1/projects/{project_id}"
        f"/services/{_AGENT_PLATFORM_API}:enable"
    )
    operation = _post_json(session, url)
    op_name = operation.get("name", "(operation)")
    return f"ENABLE requested ({op_name})"


def _check_billing(
    session: google.auth.transport.requests.AuthorizedSession, project_id: str
) -> str:
    url = f"https://cloudbilling.googleapis.com/v1/projects/{project_id}/billingInfo"
    response = session.get(url, timeout=30)
    if response.status_code == 403:
        return "UNKNOWN (cloudbilling.projects.get 権限なし。課金はコンソールで確認)"
    if response.status_code == 404:
        return "NOT LINKED (課金アカウント未紐づけ)"
    if not response.ok:
        return f"UNKNOWN (HTTP {response.status_code})"
    body = response.json()
    if body.get("billingEnabled"):
        return "ENABLED"
    return "DISABLED"


def _check_sa_roles(
    session: google.auth.transport.requests.AuthorizedSession,
    project_id: str,
    sa_email: str | None,
) -> str:
    if not sa_email:
        return "UNKNOWN (サービスアカウントメールを取得できませんでした)"
    url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{project_id}:getIamPolicy"
    response = session.get(url, timeout=30)
    if response.status_code == 403:
        return (
            f"UNKNOWN (resourcemanager.projects.getIamPolicy 権限なし。"
            f"ロールはコンソール IAM で {sa_email} を確認)"
        )
    if response.status_code == 404:
        return (
            "UNKNOWN (Cloud Resource Manager API 未有効、または SA に IAM 参照権限なし。"
            "Generate content probe が OK なら roles/aiplatform.user は付与済み)"
        )
    if not response.ok:
        return f"UNKNOWN (HTTP {response.status_code})"
    policy = response.json()
    member = f"serviceAccount:{sa_email}"
    matched: list[str] = []
    for binding in policy.get("bindings", []):
        if member not in binding.get("members", []):
            continue
        role = binding.get("role", "")
        if role in _REQUIRED_SA_ROLES or role.startswith("roles/aiplatform."):
            matched.append(role)
    if matched:
        return "OK (" + ", ".join(sorted(set(matched))) + ")"
    return f"MISSING (roles/aiplatform.user 以上が {sa_email} に見つかりません)"


def _probe_generate_content(project_id: str, location: str, model_name: str) -> str:
    try:
        from google import genai
    except ImportError:
        return "SKIP (google-genai 未インストール)"

    client = genai.Client(vertexai=True, project=project_id, location=location)
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Reply with exactly: ok",
        )
        text = (response.text or "").strip()
        if text:
            return f"OK (model={model_name}, reply_len={len(text)})"
        return "FAILED (empty response)"
    except Exception as exc:
        return f"FAILED ({type(exc).__name__}: {exc})"


def _print_check(
    label: str,
    result: str,
    *,
    ok_values: tuple[str, ...] = ("OK", "ENABLED"),
    severity: str = "required",
) -> bool:
    """severity: required=全体成否に影響, advisory=参考情報のみ"""
    if any(result.startswith(v) for v in ok_values):
        status = "PASS"
    elif severity == "advisory" and result.startswith("UNKNOWN"):
        status = "INFO"
    else:
        status = "FAIL"
    print(f"[{status}] {label}: {result}")
    if status == "FAIL":
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify GCP Agent Platform setup")
    parser.add_argument(
        "--enable-api",
        action="store_true",
        help="aiplatform.googleapis.com が DISABLED のとき有効化を試行する",
    )
    args = parser.parse_args()

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and not Path(creds_path).is_absolute():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(_project_root() / creds_path)

    location = os.environ.get("VERTEX_LOCATION", "us-east4")
    model_name = os.environ.get("VERTEX_MODEL_NAME", "gemini-2.5-flash")

    session, default_project = _authorized_session()
    credentials = session.credentials
    sa_email = _service_account_email(credentials)

    try:
        project_id = _resolve_project_id(default_project)
    except RuntimeError as exc:
        print(f"[FAIL] project: {exc}", file=sys.stderr)
        return 1

    print(f"project_id={project_id}")
    print(f"location={location}")
    print(f"model={model_name}")
    if sa_email:
        print(f"service_account={sa_email}")
    if creds_path:
        print(f"credentials_path={os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")

    passed = True
    advisory_ok = True

    api_state = _check_api_enabled(session, project_id)
    if api_state == "ENABLED":
        advisory_ok &= _print_check("Agent Platform API", api_state, ok_values=("ENABLED",), severity="advisory")
    elif api_state.startswith("DISABLED") or api_state == "SERVICE_DISABLED":
        if args.enable_api:
            try:
                enable_result = _enable_api(session, project_id)
                advisory_ok &= _print_check("Agent Platform API", enable_result, ok_values=("ENABLE",), severity="advisory")
                api_state = _check_api_enabled(session, project_id)
                advisory_ok &= _print_check(
                    "Agent Platform API (after enable)", api_state, ok_values=("ENABLED",), severity="advisory"
                )
            except RuntimeError as exc:
                advisory_ok &= _print_check("Agent Platform API enable", str(exc), ok_values=(), severity="advisory")
        else:
            advisory_ok &= _print_check(
                "Agent Platform API",
                f"{api_state} (--enable-api で有効化を試行可能)",
                ok_values=("ENABLED",),
                severity="advisory",
            )
    else:
        advisory_ok &= _print_check(
            "Agent Platform API", api_state, ok_values=("ENABLED", "UNKNOWN"), severity="advisory"
        )

    advisory_ok &= _print_check(
        "Billing", _check_billing(session, project_id), ok_values=("ENABLED",), severity="advisory"
    )
    advisory_ok &= _print_check(
        "Service account IAM",
        _check_sa_roles(session, project_id, sa_email),
        ok_values=("OK",),
        severity="advisory",
    )

    probe = _probe_generate_content(project_id, location, model_name)
    passed &= _print_check("Generate content probe", probe, ok_values=("OK",), severity="required")

    if passed:
        if advisory_ok:
            print("\nAll checks passed.")
        else:
            print(
                "\nFunctional check passed (Generate content probe OK). "
                "Advisory checks could not be verified with this SA; see spec for console confirmation."
            )
        return 0
    print("\nSome checks failed. See docs/spec/framework-drivers-layer.md#Gemini-Enterprise-Agent-Platform-初期設定", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
