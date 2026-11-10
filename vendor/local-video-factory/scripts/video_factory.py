#!/usr/bin/env python3
"""Resumable vertical-video factory for verified Vietnamese local-business briefs."""

from __future__ import annotations

import argparse
import base64
import copy
import datetime as dt
import hashlib
import html
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

try:
    import jsonschema
except ImportError:  # pragma: no cover - environment preflight handles this
    jsonschema = None


for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


SKILL_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_VERSION = "1"
PIPELINE_STEPS = (
    "preflight_and_normalize",
    "generate_candidates",
    "script_hard_gate",
    "editorial_judge_and_revision",
    "select_or_review",
    "create_experiment_variants",
    "create_variant_production_plans",
    "prepare_media_and_audio",
    "subtitles_and_render",
    "technical_qc",
    "post_package",
)
STATUSES = {"pending", "completed", "failed", "waiting_review", "needs_input"}
ANGLES = ("product-first", "story-first", "process-first", "offer-first")
FALLBACK_ANGLE = "local-life-first"
VIEW_METRICS = {
    "viewed_vs_swiped",
    "average_watch_seconds",
    "average_percentage_viewed",
    "completion_rate",
}
METRIC_COMPATIBILITY = {
    "reach": {"viewed_vs_swiped", "shares_per_view"},
    "retention": VIEW_METRICS,
    "engagement": {"shares_per_view", "saves_per_view", "comments"},
    "profile_visit": {"profile_visits"},
    "messages": {"messages"},
    "orders": {"orders"},
}
JUDGE_WEIGHTS = {
    "hook_first_frame": 20,
    "retention_pacing": 20,
    "proof_payoff": 15,
    "clarity": 10,
    "product_appeal": 10,
    "authenticity_grounding": 10,
    "visual_audio_feasibility": 10,
    "cta_platform_fit": 5,
}
ENV_EXAMPLE = """OPENAI_API_KEY=
OPENAI_TEXT_MODEL=
OPENAI_IMAGE_ENABLED=false
OPENAI_IMAGE_MODEL=
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
ELEVENLABS_MODEL=eleven_flash_v2_5
VIDEO_BGM_PATH=
SUBTITLE_FONT_PATH=
VIDEO_FPS=30
"""


class FactoryError(Exception):
    status = "failed"
    exit_code = 1

    def __init__(self, message: str, details: Iterable[str] | None = None):
        super().__init__(message)
        self.message = message
        self.details = list(details or [])


class NeedsInput(FactoryError):
    status = "needs_input"
    exit_code = 2


@dataclass
class RunContext:
    workspace: Path
    allow_paid: bool = False
    dry_run: bool = False
    job_dir: Path | None = None
    manifest: dict[str, Any] | None = None


BRIEF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "profile",
        "platform",
        "distribution_mode",
        "campaign_goal",
        "primary_metric",
        "variant_count",
        "duration_range_seconds",
        "topic",
    ],
    "properties": {
        "profile": {"enum": ["homemade", "milk-tea"]},
        "platform": {"enum": ["tiktok", "instagram-reels", "youtube-shorts"]},
        "distribution_mode": {"enum": ["organic", "paid", "boosted"]},
        "campaign_goal": {"enum": list(METRIC_COMPATIBILITY)},
        "primary_metric": {"type": "string", "minLength": 1},
        "variant_count": {"enum": [1, 3]},
        "duration_range_seconds": {
            "type": "object",
            "required": ["min", "max"],
            "properties": {
                "min": {"type": "number", "minimum": 10, "maximum": 60},
                "max": {"type": "number", "minimum": 10, "maximum": 60},
            },
        },
        "topic": {"type": "string", "minLength": 1},
        "available_media": {"type": "array"},
    },
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def emit(status: str, **payload: Any) -> None:
    print(json.dumps({"status": status, **payload}, ensure_ascii=False, indent=2))


def safe_detail(exc: BaseException) -> str:
    detail = str(exc)[:500]
    for name in ("OPENAI_API_KEY", "ELEVENLABS_API_KEY"):
        secret = os.getenv(name, "")
        if secret:
            detail = detail.replace(secret, "[REDACTED]")
    return re.sub(r"(?i)(bearer\s+|xi-api-key[=: ]+|api[_-]?key[=: ]+)[^\s,;]+", r"\1[REDACTED]", detail)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def value_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise NeedsInput(f"Không tìm thấy file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise NeedsInput(f"JSON không hợp lệ: {path}", [str(exc)]) from exc


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def load_env(workspace: Path) -> None:
    """Load a small .env subset without ever returning or logging values."""
    for path in (Path.cwd() / ".env", workspace / ".env"):
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) and key not in os.environ:
                os.environ[key] = value


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def resolve_workspace(raw: str | None) -> Path:
    path = Path(raw or Path.cwd()).expanduser().resolve()
    if path.exists() and not path.is_dir():
        raise NeedsInput(f"Workspace không phải thư mục: {path}")
    return path


def contained_path(workspace: Path, raw: str, label: str = "path") -> Path:
    if not raw or Path(raw).is_absolute():
        raise NeedsInput(f"{label} phải là đường dẫn tương đối trong workspace: {raw!r}")
    resolved = (workspace / raw).resolve()
    try:
        resolved.relative_to(workspace)
    except ValueError as exc:
        raise NeedsInput(f"{label} vượt ra ngoài workspace: {raw}") from exc
    return resolved


def argument_path(workspace: Path, raw: str, label: str) -> Path:
    path = Path(raw).expanduser()
    return path.resolve() if path.is_absolute() else contained_path(workspace, raw, label)


def json_pointer_get(document: Any, pointer: str) -> Any:
    if not pointer.startswith("/"):
        raise KeyError(pointer)
    current = document
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current


def trim_strings(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return [trim_strings(item) for item in value]
    if isinstance(value, dict):
        return {key: trim_strings(item) for key, item in value.items()}
    return value


def default_brief(profile: str, platform: str, variants: int, topic: str) -> dict[str, Any]:
    return {
        "profile": profile,
        "platform": platform,
        "distribution_mode": "organic",
        "campaign_goal": "reach",
        "primary_metric": "shares_per_view",
        "variant_count": variants,
        "duration_range_seconds": {"min": 15, "max": 35},
        "topic": topic,
        "brand_name": "",
        "location": "",
        "target_customer": "",
        "audience_problem_or_desire": "",
        "single_promise": topic,
        "tone": "",
        "pace_profile": "auto",
        "allow_goal_fallback": False,
        "featured_products": [],
        "menu": [],
        "prices": [],
        "real_selling_points": [],
        "proof_available": [],
        "promotion": {"name": "", "details": "", "conditions": "", "deadline": ""},
        "delivery": {"area": "", "order_time": "", "delivery_time": "", "fee": ""},
        "shop": {"address": "", "opening_hours": "", "has_dine_in": False},
        "order_method": "",
        "contact": "",
        "search_context": {"primary_keyword": "", "secondary_keywords": []},
        "trend_context": {"mode": "evergreen", "region": "VN", "observed_at": "", "references": []},
        "available_media": [],
        "voiceover_preference": "auto",
        "notes": "",
    }


def normalize_brief(raw: dict[str, Any], workspace: Path) -> tuple[dict[str, Any], list[str]]:
    if jsonschema is None:
        raise NeedsInput("Thiếu dependency jsonschema; cài package jsonschema rồi chạy lại.")
    brief = trim_strings(copy.deepcopy(raw))
    defaults = default_brief(
        str(brief.get("profile", "")),
        str(brief.get("platform", "")),
        brief.get("variant_count", 1),
        str(brief.get("topic", "")),
    )
    for key, value in defaults.items():
        brief.setdefault(key, value)
    errors = sorted(jsonschema.Draft202012Validator(BRIEF_SCHEMA).iter_errors(brief), key=lambda item: list(item.path))
    if errors:
        raise NeedsInput("Brief không hợp lệ.", [f"/{'/'.join(map(str, error.path))}: {error.message}" for error in errors])
    duration = brief["duration_range_seconds"]
    if duration["min"] > duration["max"]:
        raise NeedsInput("duration_range_seconds.min không được lớn hơn max.")
    metric = brief["primary_metric"]
    allowed_metrics = METRIC_COMPATIBILITY[brief["campaign_goal"]]
    if metric not in allowed_metrics:
        raise NeedsInput(
            f"primary_metric {metric!r} không phù hợp campaign_goal {brief['campaign_goal']!r}.",
            [f"Giá trị hỗ trợ: {', '.join(sorted(allowed_metrics))}"],
        )
    if brief.get("pace_profile") not in {"auto", "fast", "conversational", "sensory"}:
        raise NeedsInput("pace_profile phải là auto, fast, conversational hoặc sensory.")

    warnings: list[str] = []
    trend = brief.get("trend_context") or {}
    if trend.get("mode") == "referenced-trend":
        refs = trend.get("references") or []
        if not trend.get("observed_at") or not refs or any(not item.get("url") for item in refs):
            brief["trend_context"] = {"mode": "evergreen", "region": trend.get("region", "VN"), "observed_at": "", "references": []}
            warnings.append("Trend thiếu URL/thời điểm quan sát nên đã hạ về evergreen.")
    elif trend.get("mode") != "evergreen":
        raise NeedsInput("trend_context.mode phải là evergreen hoặc referenced-trend.")

    for index, media in enumerate(brief.get("available_media") or []):
        label = f"available_media[{index}]"
        if media.get("type") not in {"image", "video", "audio"}:
            raise NeedsInput(f"{label}.type không hợp lệ.")
        path = contained_path(workspace, str(media.get("path", "")), f"{label}.path")
        if not path.is_file() or not os.access(path, os.R_OK):
            raise NeedsInput(f"Media không tồn tại hoặc không đọc được: {media.get('path')}")
        if media.get("allowed_use") != "advertising":
            raise NeedsInput(f"Media chưa có quyền advertising: {media.get('path')}")
        if not str(media.get("description", "")).strip():
            raise NeedsInput(f"{label}.description bắt buộc; không suy nội dung từ tên file.")

    missing_sales: list[str] = []
    if brief["campaign_goal"] == "messages" and not brief.get("contact"):
        missing_sales.append("contact")
    if brief["campaign_goal"] == "orders":
        missing_sales.extend(key for key in ("order_method", "contact") if not brief.get(key))
    if missing_sales:
        if brief.get("allow_goal_fallback"):
            old_goal = brief["campaign_goal"]
            brief["campaign_goal"] = "reach"
            brief["primary_metric"] = "shares_per_view"
            brief["goal_fallback"] = {"from": old_goal, "to": "reach", "reason": f"Thiếu {', '.join(sorted(set(missing_sales)))}"}
            warnings.append("Đã đổi mục tiêu sang reach theo allow_goal_fallback.")
        else:
            raise NeedsInput("Thiếu dữ liệu bắt buộc cho mục tiêu bán hàng.", sorted(set(missing_sales)))
    return brief, warnings


def dependency_report() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "openai_sdk": _module_available("openai"),
        "jsonschema": jsonschema is not None,
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
    }


def _module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def require_paid(ctx: RunContext, required_env: Iterable[str]) -> None:
    if ctx.dry_run:
        raise FactoryError("Lỗi nội bộ: dry-run không được đi vào network adapter.")
    if not ctx.allow_paid:
        raise NeedsInput("Bước này cần API trả phí; chạy lại với --allow-paid.")
    missing = [name for name in required_env if not os.getenv(name)]
    if missing:
        raise NeedsInput("Thiếu cấu hình API.", missing)


HOOK_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "first_frame_vi", "visual_hook_vi", "spoken_hook_vi", "on_screen_hook_vi",
        "audio_hook_vi", "single_promise_vi", "hook_mechanism", "works_without_sound",
        "proof_or_payoff_due_at_second",
    ],
    "properties": {
        "first_frame_vi": {"type": "string"},
        "visual_hook_vi": {"type": "string"},
        "spoken_hook_vi": {"type": "string"},
        "on_screen_hook_vi": {"type": "string"},
        "audio_hook_vi": {"type": "string"},
        "single_promise_vi": {"type": "string"},
        "hook_mechanism": {"enum": ["result-first", "curiosity", "problem-solution", "sensory", "local-relevance", "offer"]},
        "works_without_sound": {"type": "boolean"},
        "proof_or_payoff_due_at_second": {"type": "number"},
    },
}

BEAT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["beat_id", "start_s", "end_s", "retention_role", "viewer_question_vi", "new_information_vi", "visual_action_vi", "audio_cue_vi", "retention_device_vi", "fact_refs"],
    "properties": {
        "beat_id": {"type": "string"},
        "start_s": {"type": "number"},
        "end_s": {"type": "number"},
        "retention_role": {"enum": ["hook", "context", "proof", "progress", "re_hook", "payoff", "cta"]},
        "viewer_question_vi": {"type": "string"},
        "new_information_vi": {"type": "string"},
        "visual_action_vi": {"type": "string"},
        "audio_cue_vi": {"type": "string"},
        "retention_device_vi": {"type": "string"},
        "fact_refs": {"type": "array", "items": {"type": "string"}},
    },
}

SCRIPT_LINE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["start_s", "end_s", "spoken_vi", "on_screen_text_vi", "fact_refs"],
    "properties": {
        "start_s": {"type": "number"},
        "end_s": {"type": "number"},
        "spoken_vi": {"type": "string"},
        "on_screen_text_vi": {"type": "string"},
        "fact_refs": {"type": "array", "items": {"type": "string"}},
    },
}

CANDIDATE_ITEM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["candidate_id", "angle", "duration_seconds", "pace_profile", "pace_reason_vi", "hook_plan", "beats", "engagement_plan", "claims", "script_lines", "payoff_promise_vi"],
    "properties": {
        "candidate_id": {"type": "string"},
        "angle": {"enum": [*ANGLES, FALLBACK_ANGLE]},
        "duration_seconds": {"type": "number"},
        "pace_profile": {"enum": ["fast", "conversational", "sensory"]},
        "pace_reason_vi": {"type": "string"},
        "hook_plan": HOOK_SCHEMA,
        "beats": {"type": "array", "items": BEAT_SCHEMA},
        "engagement_plan": {
            "type": "object", "additionalProperties": False,
            "required": ["primary_action", "earned_reason_vi", "cta_vi", "cta_fact_refs"],
            "properties": {
                "primary_action": {"enum": ["keep_watching", "share", "save", "comment", "profile_visit", "message", "order"]},
                "earned_reason_vi": {"type": "string"},
                "cta_vi": {"type": "string"},
                "cta_fact_refs": {"type": "array", "items": {"type": "string"}},
            },
        },
        "claims": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["text_vi", "brief_path", "source_value"],
                "properties": {"text_vi": {"type": "string"}, "brief_path": {"type": "string"}, "source_value": {}},
            },
        },
        "script_lines": {"type": "array", "items": SCRIPT_LINE_SCHEMA},
        "payoff_promise_vi": {"type": "string"},
    },
}

CANDIDATES_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["candidates"],
    "properties": {"candidates": {"type": "array", "minItems": 4, "maxItems": 4, "items": CANDIDATE_ITEM_SCHEMA}},
}

JUDGE_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["scores"],
    "properties": {
        "scores": {
            "type": "array", "minItems": 4, "maxItems": 4,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["anonymous_id", "criteria"],
                "properties": {
                    "anonymous_id": {"type": "string"},
                    "criteria": {
                        "type": "object", "additionalProperties": False,
                        "required": list(JUDGE_WEIGHTS),
                        "properties": {name: {"type": "number", "minimum": 0, "maximum": 10} for name in JUDGE_WEIGHTS},
                    },
                },
            },
        },
    },
}


def openai_json(ctx: RunContext, name: str, system: str, user: Any, schema: dict[str, Any]) -> dict[str, Any]:
    require_paid(ctx, ("OPENAI_API_KEY", "OPENAI_TEXT_MODEL"))
    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0)
        response = client.responses.create(
            model=os.environ["OPENAI_TEXT_MODEL"],
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            text={"format": {"type": "json_schema", "name": name, "strict": True, "schema": schema}},
            store=False,
        )
        return json.loads(response.output_text)
    except NeedsInput:
        raise
    except Exception as exc:
        raise FactoryError(f"OpenAI {name} thất bại.", [type(exc).__name__, safe_detail(exc)]) from exc


def openai_image(ctx: RunContext, prompt: str, output: Path) -> None:
    require_paid(ctx, ("OPENAI_API_KEY", "OPENAI_IMAGE_MODEL"))
    if not env_bool("OPENAI_IMAGE_ENABLED"):
        raise NeedsInput("OPENAI_IMAGE_ENABLED=false; cần media thật hoặc bật image generation.")
    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0)
        result = client.images.generate(model=os.environ["OPENAI_IMAGE_MODEL"], prompt=prompt, size="1024x1536")
        encoded = result.data[0].b64_json
        if not encoded:
            raise ValueError("API không trả b64_json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(base64.b64decode(encoded))
    except NeedsInput:
        raise
    except Exception as exc:
        raise FactoryError("OpenAI image generation thất bại.", [type(exc).__name__, safe_detail(exc)]) from exc


def eleven_tts(ctx: RunContext, text: str) -> dict[str, Any]:
    require_paid(ctx, ("ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID", "ELEVENLABS_MODEL"))
    voice_id = urllib.parse.quote(os.environ["ELEVENLABS_VOICE_ID"], safe="")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128"
    body = json.dumps({"text": text, "model_id": os.environ["ELEVENLABS_MODEL"], "language_code": "vi"}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise FactoryError("ElevenLabs TTS thất bại.", [type(exc).__name__, safe_detail(exc)]) from exc


def eleven_align(ctx: RunContext, audio_path: Path, transcript: str) -> dict[str, Any]:
    require_paid(ctx, ("ELEVENLABS_API_KEY",))
    boundary = f"----lvf{uuid.uuid4().hex}"
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"text\"\r\n\r\n{transcript}\r\n".encode("utf-8"),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{audio_path.name}\"\r\nContent-Type: application/octet-stream\r\n\r\n".encode("utf-8"),
        audio_path.read_bytes(),
        f"\r\n--{boundary}--\r\n".encode("utf-8"),
    ]
    request = urllib.request.Request(
        "https://api.elevenlabs.io/v1/forced-alignment",
        data=b"".join(parts), method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise FactoryError("ElevenLabs forced alignment thất bại.", [type(exc).__name__, safe_detail(exc)]) from exc


def read_reference(profile: str) -> str:
    profile_text = (SKILL_ROOT / "references" / f"{profile}.md").read_text(encoding="utf-8")
    platform_text = (SKILL_ROOT / "references" / "platforms.md").read_text(encoding="utf-8")
    return profile_text + "\n\n" + platform_text


def promotion_complete(brief: dict[str, Any]) -> bool:
    promotion = brief.get("promotion") or {}
    return all(promotion.get(key) for key in ("name", "details", "conditions", "deadline"))


def generate_candidates(ctx: RunContext, brief: dict[str, Any]) -> list[dict[str, Any]]:
    angles = ["product-first", "story-first", "process-first", "offer-first" if promotion_complete(brief) else FALLBACK_ANGLE]
    system = """Create exactly four genuinely different Vietnamese short-video script candidates. Follow the supplied profile rules. Ground every commercial claim with an RFC 6901 brief_path and exact source_value. Do not predict virality. Return only the schema. The four candidates must use the requested angles in order and cover the full duration with continuous beats and script lines."""
    result = openai_json(ctx, "video_candidates", system, {"brief": brief, "required_angles": angles, "rules": read_reference(brief["profile"])}, CANDIDATES_SCHEMA)
    return result["candidates"]


def _all_text(candidate: dict[str, Any]) -> str:
    values: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            for item in value.values():
                visit(item)

    visit(candidate)
    return " ".join(values).lower()


def _valid_refs(refs: Iterable[str], brief: dict[str, Any], errors: list[str], label: str) -> None:
    for pointer in refs:
        try:
            value = json_pointer_get(brief, pointer)
            if value in (None, "", [], {}):
                errors.append(f"{label}: fact ref rỗng {pointer}")
        except (KeyError, IndexError, TypeError, ValueError):
            errors.append(f"{label}: fact ref không tồn tại {pointer}")


def hard_gate_candidate(candidate: dict[str, Any], brief: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        if jsonschema is None:
            raise RuntimeError("jsonschema missing")
        jsonschema.validate(candidate, CANDIDATE_ITEM_SCHEMA)
    except Exception as exc:
        return [f"Schema candidate không hợp lệ: {exc}"]
    duration = float(candidate["duration_seconds"])
    limits = brief["duration_range_seconds"]
    if not limits["min"] <= duration <= limits["max"]:
        errors.append("Duration ngoài khoảng brief.")
    hook = candidate["hook_plan"]
    if float(hook["proof_or_payoff_due_at_second"]) > 3:
        errors.append("Hook chưa hứa proof/payoff trong 3 giây.")
    if not hook["works_without_sound"]:
        errors.append("Hook không hiểu được khi tắt tiếng.")
    first = hook["first_frame_vi"].lower()
    if not first or any(token in first for token in ("logo-only", "chỉ logo", "xin chào", "giới thiệu thương hiệu")):
        errors.append("First frame không hợp lệ.")
    layers = sum(bool(hook[key].strip()) for key in ("visual_hook_vi", "on_screen_hook_vi")) + bool(hook["spoken_hook_vi"].strip() or hook["audio_hook_vi"].strip())
    if layers < 2:
        errors.append("Hook cần ít nhất hai lớp visual/audio/text.")
    if hook["single_promise_vi"].strip() != candidate["payoff_promise_vi"].strip():
        errors.append("Payoff không trả đúng promise của Hook.")

    beats = candidate["beats"]
    if not beats or abs(float(beats[0]["start_s"])) > 0.05:
        errors.append("Retention beats phải bắt đầu tại 0.")
    for index, beat in enumerate(beats):
        start, end = float(beat["start_s"]), float(beat["end_s"])
        if end <= start:
            errors.append(f"{beat['beat_id']}: timestamp không tăng.")
        if index and abs(start - float(beats[index - 1]["end_s"])) > 0.05:
            errors.append(f"{beat['beat_id']}: timeline không liên tục.")
        if not (beat["new_information_vi"].strip() or beat["visual_action_vi"].strip()):
            errors.append(f"{beat['beat_id']}: không thêm thông tin/hành động.")
        _valid_refs(beat["fact_refs"], brief, errors, beat["beat_id"])
    if beats and abs(float(beats[-1]["end_s"]) - duration) > 0.05:
        errors.append("Retention beats không phủ đúng duration.")
    if duration > 20:
        rehooks = [beat for beat in beats if beat["retention_role"] == "re_hook" and duration * 0.35 <= float(beat["start_s"]) <= duration * 0.65]
        if not rehooks:
            errors.append("Video trên 20 giây thiếu re_hook ở 35–65% duration.")
    roles = [beat["retention_role"] for beat in beats]
    if "payoff" not in roles:
        errors.append("Thiếu payoff.")
    if "cta" in roles and ("payoff" not in roles or roles.index("payoff") > roles.index("cta")):
        errors.append("Payoff phải đến trước CTA.")

    for index, line in enumerate(candidate["script_lines"]):
        _valid_refs(line["fact_refs"], brief, errors, f"script_lines[{index}]")
    for index, claim in enumerate(candidate["claims"]):
        pointer = claim["brief_path"]
        try:
            actual = json_pointer_get(brief, pointer)
            if canonical_json(actual) != canonical_json(claim["source_value"]):
                errors.append(f"claims[{index}]: source_value không khớp brief_path.")
        except Exception:
            errors.append(f"claims[{index}]: brief_path không tồn tại.")
    engagement = candidate["engagement_plan"]
    _valid_refs(engagement["cta_fact_refs"], brief, errors, "CTA")
    if engagement["primary_action"] in {"message", "order"} and not engagement["cta_fact_refs"]:
        errors.append("CTA thương mại thiếu fact ref.")
    cta = engagement["cta_vi"].lower()
    if sum(token in cta for token in ("like", "thích", "share", "chia sẻ", "comment", "bình luận", "follow", "theo dõi", "đặt hàng")) > 1:
        errors.append("CTA stacking bị cấm.")

    text = _all_text(candidate)
    sensitive = ("sạch", "an toàn", "ít đường", "không chất bảo quản", "chữa", "điều trị", "freeship", "miễn phí giao")
    for phrase in sensitive:
        if phrase in text and not any(phrase in claim["text_vi"].lower() for claim in candidate["claims"]):
            errors.append(f"Claim nhạy cảm không được ground: {phrase}")
    if re.search(r"\bviral\b|đảm bảo trending|chắc chắn xu hướng", text):
        errors.append("Không được dự đoán hoặc bảo đảm viral/trending.")
    return sorted(set(errors))


def hard_gate_candidates(candidates: list[dict[str, Any]], brief: dict[str, Any]) -> dict[str, list[str]]:
    results = {candidate["candidate_id"]: hard_gate_candidate(candidate, brief) for candidate in candidates}
    expected = ["product-first", "story-first", "process-first", "offer-first" if promotion_complete(brief) else FALLBACK_ANGLE]
    actual = [candidate.get("angle") for candidate in candidates]
    if len(candidates) != 4 or actual != expected:
        results.setdefault("_package", []).append(f"Phải có đúng bốn angle theo thứ tự: {expected}")
    for field in ("hook_mechanism", "first_frame_vi", "single_promise_vi"):
        values = [candidate["hook_plan"][field].strip().lower() for candidate in candidates]
        if len(set(values)) != 4:
            results.setdefault("_package", []).append(f"Candidates chưa khác nhau thật sự ở {field}.")
    return results


def judge_candidates(ctx: RunContext, candidates: list[dict[str, Any]], hard_results: dict[str, list[str]], seed: str) -> list[dict[str, Any]]:
    order = list(candidates)
    random.Random(seed).shuffle(order)
    mapping = {f"A{index + 1}": candidate["candidate_id"] for index, candidate in enumerate(order)}
    anonymous = [{"anonymous_id": anon, "script": {key: value for key, value in candidate.items() if key not in {"candidate_id", "angle"}}} for anon, candidate in zip(mapping, order)]
    system = "Score each anonymous script from 0 to 10 on every criterion. Do not edit scripts, infer trends, or identify the angle. Return JSON only."
    raw = openai_json(ctx, "editorial_scores", system, {"scripts": anonymous, "criteria": list(JUDGE_WEIGHTS)}, JUDGE_SCHEMA)
    anonymous_ids = [item["anonymous_id"] for item in raw["scores"]]
    if len(set(anonymous_ids)) != 4 or set(anonymous_ids) != set(mapping):
        raise FactoryError("Judge phải trả đúng một bộ điểm cho mỗi candidate ẩn danh.")
    output: list[dict[str, Any]] = []
    for item in raw["scores"]:
        candidate_id = mapping.get(item["anonymous_id"])
        if not candidate_id:
            raise FactoryError("Judge trả anonymous_id không hợp lệ.")
        criteria = item["criteria"]
        total = round(sum(float(criteria[name]) / 10 * weight for name, weight in JUDGE_WEIGHTS.items()), 2)
        passed = total >= 78 and min(float(value) for value in criteria.values()) >= 6 and not hard_results.get(candidate_id)
        output.append({"candidate_id": candidate_id, "criteria": criteria, "editorial_quality_score": total, "passed": passed})
    return output


def revise_candidates(ctx: RunContext, brief: dict[str, Any], candidates: list[dict[str, Any]], hard: dict[str, list[str]], judge: list[dict[str, Any]]) -> list[dict[str, Any]]:
    system = "Revise the supplied candidates without changing IDs or angles. Fix only documented hard-gate and editorial issues. Preserve all factual values and return exactly four candidates in the original order."
    result = openai_json(ctx, "revised_video_candidates", system, {"brief": brief, "candidates": candidates, "hard_errors": hard, "judge": judge, "rules": read_reference(brief["profile"])}, CANDIDATES_SCHEMA)
    return result["candidates"]


def evaluate_scripts(ctx: RunContext, brief: dict[str, Any], initial: list[dict[str, Any]], seed: str) -> dict[str, Any]:
    current = initial
    history: list[dict[str, Any]] = []
    for round_index in range(3):
        hard = hard_gate_candidates(current, brief)
        judge = judge_candidates(ctx, current, hard, f"{seed}:{round_index}")
        history.append({"round": round_index, "candidates": copy.deepcopy(current), "hard_gate_results": hard, "judge_results": judge})
        if any(item["passed"] for item in judge) or round_index == 2:
            break
        current = revise_candidates(ctx, brief, current, hard, judge)
    final = history[-1]
    passed = [item for item in final["judge_results"] if item["passed"]]
    recommended = max(passed, key=lambda item: item["editorial_quality_score"])["candidate_id"] if passed else ""
    return {
        "initial_candidates": initial,
        "revision_history": history,
        "candidates": current,
        "hard_gate_results": final["hard_gate_results"],
        "judge_results": final["judge_results"],
        "recommended_candidate_id": recommended,
        "recommendation_passed": bool(recommended),
        "selection": None,
    }


def candidate_by_id(package: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    for candidate in package["candidates"]:
        if candidate["candidate_id"] == candidate_id:
            return candidate
    raise NeedsInput(f"candidate-id không tồn tại: {candidate_id}")


def select_candidate(package: dict[str, Any], candidate_id: str, force: bool = False) -> dict[str, Any]:
    candidate_by_id(package, candidate_id)
    hard = package["hard_gate_results"].get(candidate_id, []) + package["hard_gate_results"].get("_package", [])
    if hard:
        raise NeedsInput("Không thể --force candidate có hard/safety error.", hard)
    judged = next(item for item in package["judge_results"] if item["candidate_id"] == candidate_id)
    if not judged["passed"] and not force:
        raise NeedsInput("Candidate chưa đạt editorial threshold; dùng --force nếu chấp nhận điểm thấp.")
    package["selection"] = {"candidate_id": candidate_id, "forced": bool(force), "selected_at": now_iso()}
    return candidate_by_id(package, candidate_id)


def script_report(package: dict[str, Any], brief: dict[str, Any]) -> str:
    rows = []
    scores = {item["candidate_id"]: item for item in package["judge_results"]}
    for candidate in package["candidates"]:
        result = scores[candidate["candidate_id"]]
        errors = package["hard_gate_results"].get(candidate["candidate_id"], [])
        rows.append(
            "<tr>"
            f"<td>{html.escape(candidate['candidate_id'])}</td>"
            f"<td>{html.escape(candidate['angle'])}</td>"
            f"<td>{result['editorial_quality_score']:.2f}</td>"
            f"<td>{'Có' if result['passed'] else 'Không'}</td>"
            f"<td>{html.escape('; '.join(errors) or 'Không')}</td>"
            "</tr>"
        )
    return (
        "<!doctype html><html lang=\"vi\"><meta charset=\"utf-8\"><title>Script report</title>"
        "<style>body{font-family:system-ui;max-width:1100px;margin:2rem auto}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:.5rem;text-align:left}</style>"
        f"<h1>{html.escape(brief.get('topic', 'Script report'))}</h1>"
        "<p>Điểm là chất lượng biên tập, không phải dự đoán trending hoặc viral.</p>"
        "<table><thead><tr><th>ID</th><th>Angle</th><th>Điểm</th><th>Đạt</th><th>Hard errors</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></html>"
    )


EXPERIMENT_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["variants"],
    "properties": {
        "variants": {
            "type": "array", "minItems": 3, "maxItems": 3,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["variant_id", "script"],
                "properties": {"variant_id": {"enum": ["A", "B", "C"]}, "script": CANDIDATE_ITEM_SCHEMA},
            },
        }
    },
}

SHOT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["shot_id", "start_s", "end_s", "retention_role", "voiceover_vi", "on_screen_text_vi", "visual", "audio", "edit", "fact_refs"],
    "properties": {
        "shot_id": {"type": "string"}, "start_s": {"type": "number"}, "end_s": {"type": "number"},
        "retention_role": {"enum": ["hook", "context", "proof", "progress", "re_hook", "payoff", "cta"]},
        "voiceover_vi": {"type": "string"}, "on_screen_text_vi": {"type": "string"},
        "visual": {
            "type": "object", "additionalProperties": False,
            "required": ["source", "asset_path", "subject_vi", "action_vi", "framing_vi", "camera_motion_vi", "lighting_vi", "continuity_notes_vi", "image_prompt_en", "negative_prompt_en", "intentional_black"],
            "properties": {
                "source": {"enum": ["real-video", "real-image", "ai-image", "missing"]}, "asset_path": {"type": "string"},
                "subject_vi": {"type": "string"}, "action_vi": {"type": "string"}, "framing_vi": {"type": "string"},
                "camera_motion_vi": {"type": "string"}, "lighting_vi": {"type": "string"}, "continuity_notes_vi": {"type": "string"},
                "image_prompt_en": {"type": "string"}, "negative_prompt_en": {"type": "string"}, "intentional_black": {"type": "boolean"},
            },
        },
        "audio": {
            "type": "object", "additionalProperties": False,
            "required": ["voice_direction_vi", "natural_sound_vi", "natural_sound_asset_path", "sfx_vi", "sfx_asset_path", "music_cue_vi", "intentional_silence"],
            "properties": {key: {"type": "string"} for key in ("voice_direction_vi", "natural_sound_vi", "natural_sound_asset_path", "sfx_vi", "sfx_asset_path", "music_cue_vi")} | {"intentional_silence": {"type": "boolean"}},
        },
        "edit": {
            "type": "object", "additionalProperties": False,
            "required": ["transition_vi", "change_from_previous_vi", "subtitle_emphasis_vi"],
            "properties": {"transition_vi": {"type": "string"}, "change_from_previous_vi": {"type": "string"}, "subtitle_emphasis_vi": {"type": "string"}},
        },
        "fact_refs": {"type": "array", "items": {"type": "string"}},
    },
}

PRODUCTION_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["plans"],
    "properties": {
        "plans": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["variant_id", "duration_seconds", "shots"],
                "properties": {"variant_id": {"type": "string"}, "duration_seconds": {"type": "number"}, "shots": {"type": "array", "items": SHOT_SCHEMA}},
            },
        }
    },
}


def _strip_hook_package(candidate: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(candidate)
    value["hook_plan"] = None
    value["beats"] = [None if float(item["end_s"]) <= 5.05 else item for item in value["beats"]]
    value["script_lines"] = [None if float(item["end_s"]) <= 5.05 else item for item in value["script_lines"]]
    return value


def validate_experiment(experiment: dict[str, Any]) -> None:
    variants = experiment["variants"]
    expected = ["A"] if experiment["mode"] == "baseline" else ["A", "B", "C"]
    if [item["variant_id"] for item in variants] != expected:
        raise FactoryError(f"Variant IDs phải là {expected}.")
    if len(variants) == 1:
        return
    base = variants[0]["script"]
    changed = False
    for variant in variants[1:]:
        script = variant["script"]
        tolerance = max(0.5, float(base["duration_seconds"]) * 0.05)
        if abs(float(script["duration_seconds"]) - float(base["duration_seconds"])) > tolerance:
            raise FactoryError("Experiment variants lệch duration quá mức cho phép.")
        for field in ("claims", "engagement_plan", "payoff_promise_vi"):
            if canonical_json(script[field]) != canonical_json(base[field]):
                raise FactoryError(f"Experiment đã thay controlled field: {field}")
        if experiment["mode"] == "single-variable":
            left, right = copy.deepcopy(base), copy.deepcopy(script)
            left["hook_plan"]["on_screen_hook_vi"] = None
            right["hook_plan"]["on_screen_hook_vi"] = None
            if canonical_json(left) != canonical_json(right):
                raise FactoryError("single-variable chỉ được đổi on_screen_hook_vi.")
            if base["hook_plan"]["on_screen_hook_vi"] != script["hook_plan"]["on_screen_hook_vi"]:
                changed = True
        else:
            if canonical_json(_strip_hook_package(base)) != canonical_json(_strip_hook_package(script)):
                raise FactoryError("hook-package đã thay body sau 5 giây.")
            if canonical_json(base["hook_plan"]) != canonical_json(script["hook_plan"]):
                changed = True
    if not changed:
        raise FactoryError("Experiment variants không có thay đổi thử nghiệm thực sự.")


def create_experiment(ctx: RunContext, brief: dict[str, Any], candidate: dict[str, Any], job_id: str) -> dict[str, Any]:
    if brief["variant_count"] == 1:
        experiment = {
            "experiment_id": f"exp-{job_id}", "mode": "baseline", "single_variable_field": None,
            "platform": brief["platform"], "distribution_mode": brief["distribution_mode"], "primary_metric": brief["primary_metric"],
            "variants": [{"variant_id": "A", "script": copy.deepcopy(candidate)}],
            "controlled_fields": ["facts", "offer", "cta", "promise", "payoff", "body"],
        }
    else:
        mode = "hook-package" if brief["primary_metric"] in VIEW_METRICS else "single-variable"
        system = (
            "Create A/B/C experiment scripts from the supplied base. A must equal the base. "
            + ("For B/C change only hook_plan.on_screen_hook_vi; every other byte-level field must remain equal." if mode == "single-variable" else "For B/C change only hook_plan and beats/script lines ending by second 5; keep body after second 5 and all claims/CTA/payoff equal.")
        )
        raw = openai_json(ctx, "video_experiment", system, {"base": candidate, "mode": mode}, EXPERIMENT_SCHEMA)
        experiment = {
            "experiment_id": f"exp-{job_id}", "mode": mode,
            "single_variable_field": "hook_plan.on_screen_hook_vi" if mode == "single-variable" else None,
            "platform": brief["platform"], "distribution_mode": brief["distribution_mode"], "primary_metric": brief["primary_metric"],
            "variants": raw["variants"], "controlled_fields": ["facts", "offer", "cta", "promise", "payoff", "body"],
        }
    validate_experiment(experiment)
    return experiment


def media_registry(brief: dict[str, Any], workspace: Path) -> dict[str, dict[str, Any]]:
    return {str(item["path"]): {**item, "resolved": str(contained_path(workspace, item["path"], "media path"))} for item in brief.get("available_media", [])}


def validate_production_plan(plan: dict[str, Any], brief: dict[str, Any], workspace: Path) -> None:
    if jsonschema is None:
        raise NeedsInput("Thiếu jsonschema.")
    try:
        jsonschema.validate(plan, {"type": "object", "additionalProperties": False, "required": ["variant_id", "duration_seconds", "shots"], "properties": PRODUCTION_SCHEMA["properties"]["plans"]["items"]["properties"]})
    except Exception as exc:
        raise FactoryError("Production plan schema không hợp lệ.", [str(exc)]) from exc
    registry = media_registry(brief, workspace)
    shots = plan["shots"]
    if not shots or abs(float(shots[0]["start_s"])) > 0.05:
        raise FactoryError("Production shots phải bắt đầu tại 0.")
    for index, shot in enumerate(shots):
        if float(shot["end_s"]) <= float(shot["start_s"]):
            raise FactoryError(f"{shot['shot_id']}: timestamp không tăng.")
        if index and abs(float(shot["start_s"]) - float(shots[index - 1]["end_s"])) > 0.05:
            raise FactoryError(f"{shot['shot_id']}: timeline không liên tục.")
        _errors: list[str] = []
        _valid_refs(shot["fact_refs"], brief, _errors, shot["shot_id"])
        if _errors:
            raise FactoryError("Production plan có fact refs không hợp lệ.", _errors)
        visual = shot["visual"]
        if visual["intentional_black"]:
            raise FactoryError("MVP không render intentional black cho video sản phẩm.")
        if visual["source"] in {"real-video", "real-image"}:
            media = registry.get(visual["asset_path"])
            expected_type = "video" if visual["source"] == "real-video" else "image"
            if not media or media["type"] != expected_type:
                raise NeedsInput(f"{shot['shot_id']}: visual asset không nằm trong media registry đúng loại.")
        elif visual["source"] == "ai-image":
            if any(ref.startswith(("/featured_products", "/menu", "/brand_name", "/shop")) for ref in shot["fact_refs"]):
                raise FactoryError(f"{shot['shot_id']}: AI không được giả sản phẩm/cửa hàng thật.")
            if not visual["image_prompt_en"] or not visual["negative_prompt_en"]:
                raise FactoryError(f"{shot['shot_id']}: AI image thiếu prompt/negative prompt.")
        else:
            raise NeedsInput(f"{shot['shot_id']}: thiếu visual có thể sản xuất.")
        for key in ("natural_sound_asset_path", "sfx_asset_path"):
            path = shot["audio"][key]
            if path and (path not in registry or registry[path]["type"] != "audio"):
                raise NeedsInput(f"{shot['shot_id']}: {key} chưa có media audio với quyền advertising.")
    if abs(float(shots[-1]["end_s"]) - float(plan["duration_seconds"])) > 0.05:
        raise FactoryError("Production shots không phủ đúng duration.")


def create_production_plans(ctx: RunContext, brief: dict[str, Any], experiment: dict[str, Any]) -> list[dict[str, Any]]:
    system = """Create one production plan per variant. Cover the exact duration with continuous shots. Prefer registered real media. AI images may only be non-product illustration/B-roll. Audio asset paths must be registered audio. Hard-cut by default. Supply detailed Vietnamese voice direction and English image prompts without text/logo/watermark. Return JSON only."""
    raw = openai_json(ctx, "production_plans", system, {"brief": brief, "experiment": experiment, "rules": read_reference(brief["profile"])}, PRODUCTION_SCHEMA)
    expected = [item["variant_id"] for item in experiment["variants"]]
    if [item["variant_id"] for item in raw["plans"]] != expected:
        raise FactoryError("Production plan không đủ đúng variant IDs.")
    for plan in raw["plans"]:
        validate_production_plan(plan, brief, ctx.workspace)
    return raw["plans"]


def format_srt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def write_srt(path: Path, cues: list[tuple[float, float, str]]) -> None:
    lines: list[str] = []
    previous = -1.0
    for index, (start, end, text) in enumerate(cues, 1):
        if start < previous - 0.001 or end <= start:
            raise FactoryError("Subtitle timing không tăng hoặc bị chồng.")
        previous = end
        lines.extend([str(index), f"{format_srt_time(start)} --> {format_srt_time(end)}", text.strip(), ""])
    atomic_write_text(path, "\n".join(lines))


SRT_PATTERN = re.compile(r"(?ms)^\s*\d+\s*\n(\d\d:\d\d:\d\d[,.]\d{3})\s*-->\s*(\d\d:\d\d:\d\d[,.]\d{3})\s*\n(.+?)(?=\n\s*\n|\Z)")


def parse_srt_time(value: str) -> float:
    hours, minutes, rest = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(rest)


def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    text = path.read_text(encoding="utf-8-sig")
    cues = [(parse_srt_time(start), parse_srt_time(end), re.sub(r"\s+", " ", body).strip()) for start, end, body in SRT_PATTERN.findall(text)]
    if not cues:
        raise NeedsInput(f"SRT không hợp lệ hoặc rỗng: {path}")
    previous = -1.0
    for start, end, _ in cues:
        if start < previous - 0.001 or end <= start:
            raise NeedsInput(f"SRT timing chồng hoặc không tăng: {path}")
        previous = end
    return cues


def alignment_cues(alignment: dict[str, Any], offset: float, fallback_text: str) -> list[tuple[float, float, str]]:
    data = alignment.get("normalized_alignment") or alignment.get("alignment") or alignment
    chars = data.get("characters") or []
    starts = data.get("character_start_times_seconds") or []
    ends = data.get("character_end_times_seconds") or []
    if not chars or not (len(chars) == len(starts) == len(ends)):
        raise FactoryError("TTS alignment thiếu timing ký tự.")
    cues: list[tuple[float, float, str]] = []
    begin = 0
    for index, char in enumerate(chars):
        length = index - begin + 1
        if char in ".!?;,:\n" or length >= 34:
            text = "".join(chars[begin:index + 1]).strip()
            if text:
                cues.append((offset + float(starts[begin]), offset + float(ends[index]), text))
            begin = index + 1
    if begin < len(chars):
        text = "".join(chars[begin:]).strip() or fallback_text.strip()
        if text:
            cues.append((offset + float(starts[begin]), offset + float(ends[-1]), text))
    return cues


def forced_alignment_cues(data: dict[str, Any], offset: float, fallback_text: str) -> list[tuple[float, float, str]]:
    if "characters" in data or "alignment" in data:
        return alignment_cues(data, offset, fallback_text)
    words = data.get("words") or []
    cues: list[tuple[float, float, str]] = []
    bucket: list[dict[str, Any]] = []
    for word in words:
        bucket.append(word)
        text = " ".join(str(item.get("text") or item.get("word") or "") for item in bucket).strip()
        if len(text) >= 28 or text.endswith((".", "!", "?", ",")):
            cues.append((offset + float(bucket[0].get("start", bucket[0].get("start_time", 0))), offset + float(bucket[-1].get("end", bucket[-1].get("end_time", 0))), text))
            bucket = []
    if bucket:
        cues.append((offset + float(bucket[0].get("start", bucket[0].get("start_time", 0))), offset + float(bucket[-1].get("end", bucket[-1].get("end_time", 0))), " ".join(str(item.get("text") or item.get("word") or "") for item in bucket).strip()))
    if not cues:
        raise FactoryError("Forced alignment không trả timing dùng được.")
    return cues


def find_voice_file(root: Path, variant_id: str, shot_id: str) -> Path | None:
    folder = root / variant_id
    for suffix in (".wav", ".mp3", ".m4a", ".aac"):
        path = folder / f"{shot_id}{suffix}"
        if path.is_file():
            return path
    return None


def prepare_media_and_audio(ctx: RunContext, brief: dict[str, Any], plans: list[dict[str, Any]], voiceover_dir: Path | None, valid_cache: set[str] | None = None) -> dict[str, Any]:
    assert ctx.job_dir is not None
    valid_cache = valid_cache or set()
    registry = media_registry(brief, ctx.workspace)
    result: dict[str, Any] = {"variants": {}, "bgm_path": ""}
    bgm = os.getenv("VIDEO_BGM_PATH", "").strip()
    if bgm:
        bgm_resolved = Path(bgm).expanduser().resolve()
        matching = [item for item in registry.values() if Path(item["resolved"]) == bgm_resolved and item["type"] == "audio"]
        if not matching:
            raise NeedsInput("VIDEO_BGM_PATH chưa được khai báo trong available_media với quyền advertising.")
        result["bgm_path"] = str(bgm_resolved)

    for plan in plans:
        variant_id = plan["variant_id"]
        variant_dir = ctx.job_dir / "variants" / variant_id
        images_dir = variant_dir / "images"
        audio_dir = variant_dir / "audio"
        images_dir.mkdir(parents=True, exist_ok=True)
        audio_dir.mkdir(parents=True, exist_ok=True)
        state = {"visuals": {}, "voiceovers": {}, "natural_sounds": {}, "sfx": {}, "subtitle_cues": [], "manual_srt": ""}
        manual_srt = voiceover_dir / variant_id / "subtitles.srt" if voiceover_dir else None
        if manual_srt and manual_srt.is_file():
            cues = parse_srt(manual_srt)
            if cues[-1][1] > float(plan["duration_seconds"]) + 0.1:
                raise NeedsInput(f"SRT của variant {variant_id} vượt quá duration.")
            state["subtitle_cues"] = cues
            state["manual_srt"] = str(manual_srt.resolve())

        for shot in plan["shots"]:
            for field, state_key in (("natural_sound_asset_path", "natural_sounds"), ("sfx_asset_path", "sfx")):
                asset_path = shot["audio"][field]
                if asset_path:
                    state[state_key][shot["shot_id"]] = registry[asset_path]["resolved"]
            visual = shot["visual"]
            if visual["source"] in {"real-video", "real-image"}:
                state["visuals"][shot["shot_id"]] = registry[visual["asset_path"]]["resolved"]
            else:
                image_path = images_dir / f"{shot['shot_id']}.png"
                cache_key = value_hash({"prompt": visual["image_prompt_en"], "negative": visual["negative_prompt_en"], "model": os.getenv("OPENAI_IMAGE_MODEL", "")})
                relative_image = str(image_path.relative_to(ctx.job_dir)).replace("\\", "/")
                if relative_image not in valid_cache:
                    prompt = f"{visual['image_prompt_en']} Vertical 9:16 composition. No text, logo, or watermark. Avoid: {visual['negative_prompt_en']}"
                    openai_image(ctx, prompt, image_path)
                state["visuals"][shot["shot_id"]] = str(image_path)
                state.setdefault("image_cache", {})[shot["shot_id"]] = cache_key

            if not shot["voiceover_vi"].strip():
                if not any((shot["audio"]["natural_sound_asset_path"], shot["audio"]["sfx_asset_path"], bgm, shot["audio"]["intentional_silence"])):
                    raise NeedsInput(f"{variant_id}/{shot['shot_id']}: thiếu nguồn audio hoặc khai báo intentional_silence.")
                continue
            destination: Path
            voice_file = find_voice_file(voiceover_dir, variant_id, shot["shot_id"]) if voiceover_dir else None
            if voice_file:
                destination = audio_dir / f"{shot['shot_id']}{voice_file.suffix.lower()}"
                relative_audio = str(destination.relative_to(ctx.job_dir)).replace("\\", "/")
                if relative_audio not in valid_cache or not destination.is_file() or file_hash(destination) != file_hash(voice_file):
                    shutil.copy2(voice_file, destination)
                state["voiceovers"][shot["shot_id"]] = str(destination)
                if not state["manual_srt"]:
                    aligned = eleven_align(ctx, destination, shot["voiceover_vi"])
                    state["subtitle_cues"].extend(forced_alignment_cues(aligned, float(shot["start_s"]), shot["voiceover_vi"]))
            else:
                if voiceover_dir:
                    raise NeedsInput(f"Thiếu voiceover {variant_id}/{shot['shot_id']} trong {voiceover_dir}")
                destination = audio_dir / f"{shot['shot_id']}.mp3"
                alignment_path = audio_dir / f"{shot['shot_id']}.alignment.json"
                relative_audio = str(destination.relative_to(ctx.job_dir)).replace("\\", "/")
                relative_alignment = str(alignment_path.relative_to(ctx.job_dir)).replace("\\", "/")
                if relative_audio in valid_cache and relative_alignment in valid_cache and destination.is_file() and alignment_path.is_file():
                    data = load_json(alignment_path)
                else:
                    data = eleven_tts(ctx, shot["voiceover_vi"])
                    audio = data.get("audio_base64")
                    if not audio:
                        raise FactoryError("ElevenLabs không trả audio_base64.")
                    destination.write_bytes(base64.b64decode(audio))
                    atomic_write_json(alignment_path, {key: data.get(key) for key in ("alignment", "normalized_alignment")})
                state["voiceovers"][shot["shot_id"]] = str(destination)
                state["subtitle_cues"].extend(alignment_cues(data, float(shot["start_s"]), shot["voiceover_vi"]))
        result["variants"][variant_id] = state
    return result


def require_ffmpeg() -> tuple[str, str]:
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    missing = [name for name, value in (("ffmpeg", ffmpeg), ("ffprobe", ffprobe)) if not value]
    if missing:
        raise NeedsInput(
            "Thiếu FFmpeg/ffprobe trên PATH; chưa thể render hoặc technical QC.",
            ["Cài FFmpeg từ https://ffmpeg.org/download.html rồi mở terminal mới.", f"Thiếu: {', '.join(missing)}"],
        )
    encoders = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if "libx264" not in encoders.stdout or not re.search(r"\baac\b", encoders.stdout):
        raise NeedsInput("FFmpeg hiện tại thiếu encoder libx264 hoặc AAC.")
    return ffmpeg, ffprobe


def run_process(command: list[str], label: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if result.returncode:
        raise FactoryError(f"{label} thất bại.", [result.stderr[-1200:]])
    return result


def ass_time(seconds: float) -> str:
    centiseconds = max(0, round(seconds * 100))
    hours, centiseconds = divmod(centiseconds, 360000)
    minutes, centiseconds = divmod(centiseconds, 6000)
    secs, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02}:{secs:02}.{centiseconds:02}"


def ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")


def build_ass(plan: dict[str, Any], cues: list[tuple[float, float, str]], path: Path) -> None:
    font = "Arial"
    configured = os.getenv("SUBTITLE_FONT_PATH", "").strip()
    if configured:
        font = Path(configured).stem
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Subtitle,{font},58,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,2,80,80,250,1
Style: Headline,{font},66,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,5,1,8,80,80,180,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    rows = [f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Subtitle,,0,0,0,,{ass_escape(text)}" for start, end, text in cues]
    rows.extend(f"Dialogue: 1,{ass_time(float(shot['start_s']))},{ass_time(float(shot['end_s']))},Headline,,0,0,0,,{ass_escape(shot['on_screen_text_vi'])}" for shot in plan["shots"] if shot["on_screen_text_vi"].strip())
    atomic_write_text(path, header + "\n".join(rows) + "\n")


def ffmpeg_filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def render_variant(ffmpeg: str, plan: dict[str, Any], state: dict[str, Any], output: Path, fps: int, bgm_path: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    srt_path = output.parent / "subtitles.srt"
    cues = sorted((float(a), float(b), str(c)) for a, b, c in state["subtitle_cues"])
    write_srt(srt_path, cues)
    with tempfile.TemporaryDirectory(prefix="lvf-render-") as raw_tmp:
        temp = Path(raw_tmp)
        clips: list[Path] = []
        for index, shot in enumerate(plan["shots"]):
            duration = float(shot["end_s"]) - float(shot["start_s"])
            source = Path(state["visuals"][shot["shot_id"]])
            clip = temp / f"shot-{index:03}.mp4"
            common = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
            if shot["visual"]["source"] in {"real-image", "ai-image"}:
                command = common + ["-loop", "1", "-i", str(source), "-t", str(duration)]
            else:
                command = common + ["-stream_loop", "-1", "-i", str(source), "-t", str(duration)]
            command += ["-vf", f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps={fps}", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(clip)]
            run_process(command, f"Render shot {shot['shot_id']}")
            clips.append(clip)
        concat = temp / "concat.txt"
        atomic_write_text(concat, "".join(f"file '{str(path).replace("'", "'\\''")}'\n" for path in clips))
        visual = temp / "visual.mp4"
        run_process([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(visual)], "Concat visual")

        ass = temp / "overlay.ass"
        build_ass(plan, cues, ass)
        command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(visual)]
        filters: list[str] = []
        audio_labels: list[str] = []
        input_index = 1
        for shot in plan["shots"]:
            for path, volume in (
                (state["voiceovers"].get(shot["shot_id"], ""), "1.0"),
                (state.get("natural_sounds", {}).get(shot["shot_id"], ""), "0.35"),
                (state.get("sfx", {}).get(shot["shot_id"], ""), "0.4"),
            ):
                if not path:
                    continue
                command += ["-i", path]
                delay = round(float(shot["start_s"]) * 1000)
                label = f"a{input_index}"
                filters.append(f"[{input_index}:a]adelay={delay}|{delay},volume={volume}[{label}]")
                audio_labels.append(f"[{label}]")
                input_index += 1
        if bgm_path:
            command += ["-stream_loop", "-1", "-i", bgm_path]
            label = f"a{input_index}"
            filters.append(f"[{input_index}:a]atrim=duration={plan['duration_seconds']},volume=0.1[{label}]")
            audio_labels.append(f"[{label}]")
            input_index += 1
        if audio_labels:
            filters.append(f"{''.join(audio_labels)}amix=inputs={len(audio_labels)}:duration=longest:dropout_transition=0,atrim=duration={plan['duration_seconds']}[mix]")
            command += ["-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[mix]"]
        else:
            command += ["-f", "lavfi", "-t", str(plan["duration_seconds"]), "-i", "anullsrc=r=44100:cl=stereo", "-map", "0:v", "-map", f"{input_index}:a"]
        command += ["-vf", f"ass='{ffmpeg_filter_path(ass)}'", "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-t", str(plan["duration_seconds"]), str(output)]
        run_process(command, f"Render variant {plan['variant_id']}")


def qc_variant(ffmpeg: str, ffprobe: str, plan: dict[str, Any], video: Path, expected_fps: int = 30) -> dict[str, Any]:
    probe = run_process([ffprobe, "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(video)], "ffprobe")
    data = json.loads(probe.stdout)
    video_streams = [stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in data.get("streams", []) if stream.get("codec_type") == "audio"]
    errors: list[str] = []
    if not video_streams:
        errors.append("Thiếu video stream.")
    if not audio_streams:
        errors.append("Thiếu audio stream.")
    if video_streams:
        stream = video_streams[0]
        if (stream.get("width"), stream.get("height")) != (1080, 1920):
            errors.append("Sai kích thước 1080x1920.")
        if stream.get("pix_fmt") != "yuv420p":
            errors.append("Sai pixel format; cần yuv420p.")
        if stream.get("codec_name") != "h264":
            errors.append("Sai video codec; cần H.264.")
        try:
            actual_fps = float(Fraction(stream.get("avg_frame_rate") or "0"))
        except (ValueError, ZeroDivisionError):
            actual_fps = 0
        if abs(actual_fps - expected_fps) > 0.01:
            errors.append(f"Sai FPS; cần {expected_fps}.")
    if audio_streams and audio_streams[0].get("codec_name") != "aac":
        errors.append("Sai audio codec; cần AAC.")
    duration = float(data.get("format", {}).get("duration") or 0)
    if duration <= 0 or abs(duration - float(plan["duration_seconds"])) > 0.25:
        errors.append("Duration output không khớp production plan.")
    analysis = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(video), "-vf", "blackdetect=d=0.3:pix_th=0.10", "-af", "silencedetect=n=-50dB:d=0.5", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    if "black_start:" in analysis.stderr:
        errors.append("Phát hiện đoạn đen.")
    silence_starts = [float(value) for value in re.findall(r"silence_start:\s*([0-9.]+)", analysis.stderr)]
    silence_ends = [float(value) for value in re.findall(r"silence_end:\s*([0-9.]+)", analysis.stderr)]
    intentional = [(float(shot["start_s"]), float(shot["end_s"])) for shot in plan["shots"] if shot["audio"]["intentional_silence"]]
    for start, end in zip(silence_starts, silence_ends):
        if not any(start >= allowed_start - 0.1 and end <= allowed_end + 0.1 for allowed_start, allowed_end in intentional):
            errors.append(f"Phát hiện im lặng ngoài chủ ý: {start:.2f}-{end:.2f}s")
    if errors:
        raise FactoryError(f"Technical QC thất bại cho variant {plan['variant_id']}.", errors)
    return {"video_stream": True, "audio_stream": True, "codec": "h264/aac", "fps": expected_fps, "width": 1080, "height": 1920, "duration": duration, "black_segments": 0, "unexpected_silence_segments": 0}


def build_post_package(brief: dict[str, Any], experiment: dict[str, Any], job_dir: Path, used_ai: bool) -> dict[str, Any]:
    search = brief.get("search_context") or {}
    primary = search.get("primary_keyword") or " ".join(filter(None, [brief.get("topic"), brief.get("location")])).strip()
    secondary = [item for item in search.get("secondary_keywords", []) if item]
    hashtag_seeds = [primary, *secondary, brief.get("brand_name", ""), brief.get("location", ""), "món nhà làm" if brief["profile"] == "homemade" else "trà sữa", "ẩm thực Việt Nam"]
    hashtags: list[str] = []
    for seed in hashtag_seeds:
        tag = "#" + re.sub(r"[^\w]", "", seed, flags=re.UNICODE)
        if len(tag) > 1 and tag.casefold() not in {item.casefold() for item in hashtags}:
            hashtags.append(tag)
        if len(hashtags) == 5:
            break
    entries: list[dict[str, Any]] = []
    for variant in experiment["variants"]:
        script = variant["script"]
        hook = script["hook_plan"]
        engagement = script["engagement_plan"]
        common = {
            "variant_id": variant["variant_id"], "platform": brief["platform"],
            "video_path": str(Path("variants") / variant["variant_id"] / "final.mp4"),
            "cover_text": hook["on_screen_hook_vi"][:80], "primary_keyword": primary,
            "secondary_keywords": secondary, "cta": engagement["cta_vi"],
            "hashtags": hashtags[:5],
            "pinned_comment": engagement["earned_reason_vi"], "location": brief.get("location", ""),
            "disclosures": [item for item, include in (("AI-generated/altered content", used_ai), ("Commercial content", brief["distribution_mode"] in {"paid", "boosted"})) if include],
            "posting_checklist": ["Preview the final file on a real device", "Verify current safe areas and UI overlays", "Confirm every media/audio right before posting"],
        }
        if brief["platform"] == "tiktok":
            common["tiktok"] = {
                "caption": f"{hook['single_promise_vi']} {engagement['cta_vi']}".strip(),
                "search_phrase": primary, "sound_source": "licensed-user-media" if os.getenv("VIDEO_BGM_PATH") else "original-voice/natural-sound",
                "commercial_use_verified": True,
                "commercial_content_disclosure": "Check current Promotional content/Paid partnership label",
                "ai_generated_disclosure": used_ai, "safe_area_checklist": ["Use the current TikTok overlay", "Keep key text/product clear of dynamic controls"],
            }
        elif brief["platform"] == "instagram-reels":
            common["instagram_reels"] = {
                "caption": f"{hook['single_promise_vi']} {engagement['cta_vi']}".strip(), "cover_text": common["cover_text"],
                "share_reason": engagement["earned_reason_vi"] if engagement["primary_action"] == "share" else "",
                "save_reason": engagement["earned_reason_vi"] if engagement["primary_action"] == "save" else "",
                "originality_checklist": ["Original or licensed media", "No imported-platform watermark", "Check Account Status/recommendation eligibility"],
                "ai_disclosure": used_ai,
            }
        else:
            common["youtube_shorts"] = {
                "title": hook["single_promise_vi"][:100], "description": f"{primary}\n{engagement['cta_vi']}".strip(),
                "search_phrase": primary, "pinned_comment": common["pinned_comment"],
                "audience_setting_checklist": ["Select Made for Kids or Not Made for Kids; do not assume"],
                "altered_synthetic_disclosure": used_ai,
            }
        entries.append(common)
    return {"generated_at": now_iso(), "manual_posting_only": True, "variants": entries}


def artifact_descriptor(path: Path, job_dir: Path, pointer: str | None = None) -> dict[str, Any]:
    relative = str(path.resolve().relative_to(job_dir.resolve())).replace("\\", "/")
    if pointer:
        value = json_pointer_get(load_json(path), pointer)
        return {"path": relative, "json_pointer": pointer, "sha256": value_hash(value), "bytes": path.stat().st_size}
    return {"path": relative, "sha256": file_hash(path), "bytes": path.stat().st_size}


def artifact_valid(descriptor: dict[str, Any], job_dir: Path) -> bool:
    try:
        path = (job_dir / descriptor["path"]).resolve()
        path.relative_to(job_dir.resolve())
        if not path.is_file():
            return False
        actual = value_hash(json_pointer_get(load_json(path), descriptor["json_pointer"])) if descriptor.get("json_pointer") else file_hash(path)
        return actual == descriptor["sha256"]
    except Exception:
        return False


def stage_valid(manifest: dict[str, Any], stage: str, input_fingerprint: str, job_dir: Path) -> bool:
    record = manifest["steps"][stage]
    return record["status"] == "completed" and record.get("input_fingerprint") == input_fingerprint and all(artifact_valid(item, job_dir) for item in record.get("outputs", []))


def save_manifest(ctx: RunContext) -> None:
    assert ctx.job_dir is not None and ctx.manifest is not None
    ctx.manifest["updated_at"] = now_iso()
    atomic_write_json(ctx.job_dir / "manifest.json", ctx.manifest)


def set_stage(ctx: RunContext, stage: str, status: str, input_fingerprint: str = "", outputs: list[dict[str, Any]] | None = None, message: str = "", data: Any = None) -> None:
    if status not in STATUSES:
        raise ValueError(status)
    assert ctx.manifest is not None
    ctx.manifest["steps"][stage] = {
        "status": status, "input_fingerprint": input_fingerprint, "outputs": outputs or [],
        "message": message, "updated_at": now_iso(),
    }
    if data is not None:
        ctx.manifest["steps"][stage]["data"] = data
    ctx.manifest["status"] = status if status != "completed" else ctx.manifest.get("status", "pending")
    save_manifest(ctx)


def new_manifest(job_id: str, brief_path: Path, brief_hash: str, mode: str) -> dict[str, Any]:
    return {
        "schema_version": 1, "pipeline_version": PIPELINE_VERSION, "job_id": job_id,
        "created_at": now_iso(), "updated_at": now_iso(), "status": "pending", "mode": mode,
        "brief": {"path": str(brief_path.resolve()), "sha256": brief_hash}, "selection": None,
        "steps": {stage: {"status": "pending", "input_fingerprint": "", "outputs": [], "message": "", "updated_at": now_iso()} for stage in PIPELINE_STEPS},
    }


def create_job_context(workspace: Path, brief_path: Path, mode: str, allow_paid: bool) -> RunContext:
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    job_id = f"{timestamp}-{uuid.uuid4().hex[:8]}"
    job_dir = workspace / "outputs" / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    manifest = new_manifest(job_id, brief_path, file_hash(brief_path), mode)
    ctx = RunContext(workspace=workspace, allow_paid=allow_paid, job_dir=job_dir, manifest=manifest)
    save_manifest(ctx)
    return ctx


def run_script_pipeline(ctx: RunContext, brief: dict[str, Any], review: bool, candidate_id: str | None = None, force: bool = False) -> tuple[dict[str, Any], dict[str, Any] | None]:
    assert ctx.job_dir is not None and ctx.manifest is not None
    package_path = ctx.job_dir / "script-package.json"
    editorial_record = ctx.manifest["steps"]["editorial_judge_and_revision"]
    if package_path.is_file() and editorial_record["status"] == "completed" and all(artifact_valid(item, ctx.job_dir) for item in editorial_record.get("outputs", [])):
        package = load_json(package_path)
    else:
        input_fp = value_hash({"brief": brief, "pipeline": PIPELINE_VERSION})
        candidates = generate_candidates(ctx, brief)
        package = {"initial_candidates": candidates, "candidates": candidates}
        atomic_write_json(package_path, package)
        set_stage(ctx, "generate_candidates", "completed", input_fp, [artifact_descriptor(package_path, ctx.job_dir, "/initial_candidates")])

        hard = hard_gate_candidates(candidates, brief)
        package["hard_gate_results"] = hard
        atomic_write_json(package_path, package)
        set_stage(ctx, "script_hard_gate", "completed", value_hash(candidates), [artifact_descriptor(package_path, ctx.job_dir, "/hard_gate_results")])

        package = evaluate_scripts(ctx, brief, candidates, ctx.manifest["job_id"])
        package["initial_hard_gate_results"] = hard
        atomic_write_json(package_path, package)
        set_stage(ctx, "script_hard_gate", "completed", value_hash(candidates), [artifact_descriptor(package_path, ctx.job_dir, "/initial_hard_gate_results")])
        set_stage(ctx, "editorial_judge_and_revision", "completed", value_hash({"candidates": candidates, "hard": hard}), [
            artifact_descriptor(package_path, ctx.job_dir, "/hard_gate_results"),
            artifact_descriptor(package_path, ctx.job_dir, "/judge_results"),
            artifact_descriptor(package_path, ctx.job_dir, "/revision_history"),
            artifact_descriptor(package_path, ctx.job_dir, "/recommendation_passed"),
        ])

    report_path = ctx.job_dir / "script-report.html"
    if review and not candidate_id:
        atomic_write_text(report_path, script_report(package, brief))
        set_stage(ctx, "select_or_review", "waiting_review", value_hash(package.get("judge_results")), [artifact_descriptor(report_path, ctx.job_dir)], "Chọn candidate bằng resume --candidate-id.")
        return package, None
    selected_id = candidate_id or package.get("recommended_candidate_id", "")
    if not selected_id:
        raise FactoryError("Không có candidate đạt editorial threshold; dùng review rồi resume --force nếu hard gate sạch.")
    selected = select_candidate(package, selected_id, force)
    ctx.manifest["selection"] = package["selection"]
    atomic_write_json(package_path, package)
    atomic_write_text(report_path, script_report(package, brief))
    set_stage(ctx, "select_or_review", "completed", value_hash(package.get("judge_results")), [artifact_descriptor(package_path, ctx.job_dir, "/selection"), artifact_descriptor(report_path, ctx.job_dir)])
    return package, selected


def continue_production(ctx: RunContext, brief: dict[str, Any], selected: dict[str, Any], voiceover_dir: Path | None = None) -> None:
    assert ctx.job_dir is not None and ctx.manifest is not None
    job_dir = ctx.job_dir
    experiment_path = job_dir / "experiment.json"
    fp6 = value_hash({"selected": selected, "variants": brief["variant_count"], "metric": brief["primary_metric"]})
    if stage_valid(ctx.manifest, "create_experiment_variants", fp6, job_dir):
        experiment = load_json(experiment_path)
    else:
        experiment = create_experiment(ctx, brief, selected, ctx.manifest["job_id"])
        atomic_write_json(experiment_path, experiment)
        set_stage(ctx, "create_experiment_variants", "completed", fp6, [artifact_descriptor(experiment_path, job_dir)])

    fp7 = value_hash(experiment)
    plan_paths = [job_dir / "variants" / item["variant_id"] / "production-plan.json" for item in experiment["variants"]]
    if stage_valid(ctx.manifest, "create_variant_production_plans", fp7, job_dir):
        plans = [load_json(path) for path in plan_paths]
    else:
        plans = create_production_plans(ctx, brief, experiment)
        for plan, path in zip(plans, plan_paths):
            atomic_write_json(path, plan)
        set_stage(ctx, "create_variant_production_plans", "completed", fp7, [artifact_descriptor(path, job_dir) for path in plan_paths])

    voice_hash = ""
    if voiceover_dir:
        if not voiceover_dir.is_dir():
            raise NeedsInput(f"voiceover-dir không tồn tại: {voiceover_dir}")
        voice_hash = value_hash(sorted((str(path.relative_to(voiceover_dir)), file_hash(path)) for path in voiceover_dir.rglob("*") if path.is_file()))
    registry = media_registry(brief, ctx.workspace)
    media_hashes = sorted((key, file_hash(Path(item["resolved"]))) for key, item in registry.items())
    fp8 = value_hash({"plans": plans, "media": media_hashes, "voice": voice_hash, "image_model": os.getenv("OPENAI_IMAGE_MODEL", ""), "tts_model": os.getenv("ELEVENLABS_MODEL", "")})
    record8 = ctx.manifest["steps"]["prepare_media_and_audio"]
    if stage_valid(ctx.manifest, "prepare_media_and_audio", fp8, job_dir):
        prepared = record8["data"]
    else:
        valid_cache = {item["path"] for item in record8.get("outputs", []) if record8.get("input_fingerprint") == fp8 and artifact_valid(item, job_dir)}
        prepared = prepare_media_and_audio(ctx, brief, plans, voiceover_dir, valid_cache)
        prepared_files = [path for variant in prepared["variants"].values() for group in (variant.get("visuals", {}), variant.get("voiceovers", {})) for path in map(Path, group.values()) if path.is_file() and job_dir in path.parents]
        prepared_files.extend(path for path in job_dir.glob("variants/*/audio/*.alignment.json") if path.is_file())
        set_stage(ctx, "prepare_media_and_audio", "completed", fp8, [artifact_descriptor(path, job_dir) for path in sorted(set(prepared_files))], data=prepared)

    fps = int(os.getenv("VIDEO_FPS", "30") or "30")
    if fps < 1 or fps > 120:
        raise NeedsInput("VIDEO_FPS phải nằm trong 1–120.")
    fp9 = value_hash({"prepared": prepared, "fps": fps, "plans": plans})
    record9 = ctx.manifest["steps"]["subtitles_and_render"]
    render_outputs: list[dict[str, Any]] = []
    ffmpeg = ffprobe = ""
    for plan in plans:
        video = job_dir / "variants" / plan["variant_id"] / "final.mp4"
        cache_key = value_hash({"plan": plan, "prepared": prepared["variants"][plan["variant_id"]], "fps": fps, "bgm": prepared["bgm_path"]})
        old = [item for item in record9.get("outputs", []) if item.get("variant_id") == plan["variant_id"] and item.get("cache_key") == cache_key]
        if not (record9.get("input_fingerprint") == fp9 and len(old) == 2 and all(artifact_valid(item, job_dir) for item in old)):
            if not ffmpeg:
                ffmpeg, ffprobe = require_ffmpeg()
            render_variant(ffmpeg, plan, prepared["variants"][plan["variant_id"]], video, fps, prepared["bgm_path"])
        current = [artifact_descriptor(video, job_dir), artifact_descriptor(video.parent / "subtitles.srt", job_dir)]
        for item in current:
            item.update({"variant_id": plan["variant_id"], "cache_key": cache_key})
        render_outputs.extend(current)
    set_stage(ctx, "subtitles_and_render", "completed", fp9, render_outputs)

    fp10 = value_hash(render_outputs)
    if stage_valid(ctx.manifest, "technical_qc", fp10, job_dir):
        qc = ctx.manifest["steps"]["technical_qc"]["data"]
    else:
        if not ffmpeg:
            ffmpeg, ffprobe = require_ffmpeg()
        qc = {}
        for plan in plans:
            video = job_dir / "variants" / plan["variant_id"] / "final.mp4"
            qc[plan["variant_id"]] = qc_variant(ffmpeg, ffprobe, plan, video, fps)
        set_stage(ctx, "technical_qc", "completed", fp10, [], data=qc)

    used_ai = any(shot["visual"]["source"] == "ai-image" for plan in plans for shot in plan["shots"])
    package_path = job_dir / "post-package.json"
    fp11 = value_hash({"experiment": experiment, "qc": qc})
    if not stage_valid(ctx.manifest, "post_package", fp11, job_dir):
        package = build_post_package(brief, experiment, job_dir, used_ai)
        atomic_write_json(package_path, package)
        set_stage(ctx, "post_package", "completed", fp11, [artifact_descriptor(package_path, job_dir)])
    ctx.manifest["status"] = "completed"
    save_manifest(ctx)


def command_new(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    briefs = workspace / "briefs"
    outputs = workspace / "outputs"
    brief_path = briefs / "brief.json"
    workspace.mkdir(parents=True, exist_ok=True)
    briefs.mkdir(exist_ok=True)
    outputs.mkdir(exist_ok=True)
    env_example = workspace / ".env.example"
    if not env_example.exists():
        atomic_write_text(env_example, ENV_EXAMPLE)
    if brief_path.exists():
        raise NeedsInput(f"Không ghi đè brief có sẵn: {brief_path}")
    brief = default_brief(args.profile, args.platform, args.variants, args.topic)
    atomic_write_json(brief_path, brief)
    emit("completed", brief=str(brief_path), env_example=str(env_example))
    return 0


def command_dry_run(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    load_env(workspace)
    brief_path = argument_path(workspace, args.brief, "brief")
    brief, warnings = normalize_brief(load_json(brief_path), workspace)
    dependencies = dependency_report()
    missing: list[str] = []
    if not dependencies["ffmpeg"]:
        missing.append("ffmpeg: cài từ https://ffmpeg.org/download.html và thêm vào PATH")
    if not dependencies["ffprobe"]:
        missing.append("ffprobe: cài cùng FFmpeg và thêm vào PATH")
    for name in ("OPENAI_API_KEY", "OPENAI_TEXT_MODEL"):
        if not os.getenv(name):
            missing.append(f"{name}: cần khi chạy bước sinh nội dung")
    payload = {
        "network_requests": 0, "workspace": str(workspace), "brief": str(brief_path),
        "normalized": {key: brief[key] for key in ("profile", "platform", "distribution_mode", "campaign_goal", "primary_metric", "variant_count", "duration_range_seconds", "topic")},
        "candidate_count": 4, "steps": list(PIPELINE_STEPS), "warnings": warnings,
        "dependencies": dependencies, "needs_input": missing,
    }
    emit("needs_input" if missing else "completed", **payload)
    return 2 if missing else 0


def command_run(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    load_env(workspace)
    brief_path = argument_path(workspace, args.brief, "brief")
    brief, warnings = normalize_brief(load_json(brief_path), workspace)
    ctx = create_job_context(workspace, brief_path, "review" if args.review else "auto", args.allow_paid)
    normalized_path = ctx.job_dir / "normalized-brief.json"
    atomic_write_json(normalized_path, brief)
    set_stage(ctx, "preflight_and_normalize", "completed", value_hash({"brief": brief, "source": file_hash(brief_path)}), [artifact_descriptor(normalized_path, ctx.job_dir)], "; ".join(warnings))
    try:
        package, selected = run_script_pipeline(ctx, brief, args.review)
        if selected is None:
            emit("waiting_review", job=str(ctx.job_dir), recommended_candidate_id=package.get("recommended_candidate_id", ""))
            return 0
        continue_production(ctx, brief, selected)
        emit("completed", job=str(ctx.job_dir), candidate_id=selected["candidate_id"])
        return 0
    except FactoryError as exc:
        active = next((stage for stage in PIPELINE_STEPS if ctx.manifest["steps"][stage]["status"] == "pending"), PIPELINE_STEPS[-1])
        set_stage(ctx, active, exc.status, message=exc.message, data={"details": exc.details})
        emit(exc.status, job=str(ctx.job_dir), message=exc.message, details=exc.details)
        return exc.exit_code


def command_resume(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    load_env(workspace)
    job_dir = argument_path(workspace, args.job, "job")
    manifest = load_json(job_dir / "manifest.json")
    if manifest.get("schema_version") != 1:
        raise NeedsInput("Manifest schema không được hỗ trợ.")
    brief = load_json(job_dir / "normalized-brief.json")
    ctx = RunContext(workspace=workspace, allow_paid=args.allow_paid, job_dir=job_dir, manifest=manifest)
    try:
        package, selected = run_script_pipeline(ctx, brief, False, args.candidate_id, args.force)
        if selected is None:
            raise NeedsInput("Resume cần --candidate-id khi job đang chờ review.")
        voiceover_dir = argument_path(workspace, args.voiceover_dir, "voiceover-dir") if args.voiceover_dir else None
        continue_production(ctx, brief, selected, voiceover_dir)
        emit("completed", job=str(job_dir), candidate_id=selected["candidate_id"])
        return 0
    except FactoryError as exc:
        active = next((stage for stage in PIPELINE_STEPS if ctx.manifest["steps"][stage]["status"] in {"pending", "needs_input", "failed", "waiting_review"}), PIPELINE_STEPS[-1])
        set_stage(ctx, active, exc.status, message=exc.message, data={"details": exc.details})
        emit(exc.status, job=str(job_dir), message=exc.message, details=exc.details)
        return exc.exit_code


def metric_value(row: dict[str, Any], metric: str) -> float | None:
    if metric == "shares_per_view":
        numerator, denominator = row.get("shares"), row.get("views")
        return None if numerator is None or not denominator else float(numerator) / float(denominator)
    if metric == "saves_per_view":
        numerator, denominator = row.get("saves"), row.get("views")
        return None if numerator is None or not denominator else float(numerator) / float(denominator)
    key = "stayed_to_watch_rate" if metric == "viewed_vs_swiped" else metric
    value = row.get(key)
    return None if value is None else float(value)


def validate_metrics(metrics: dict[str, Any], experiment: dict[str, Any], brief: dict[str, Any]) -> None:
    for key in ("experiment_id", "platform", "distribution_mode", "captured_at", "observation_window_hours", "metric_source", "variants"):
        if key not in metrics:
            raise NeedsInput(f"Metrics thiếu trường: {key}")
    if metrics["experiment_id"] != experiment["experiment_id"]:
        raise NeedsInput("Metrics không thuộc cùng experiment.")
    if metrics["platform"] != brief["platform"] or metrics["distribution_mode"] != brief["distribution_mode"]:
        raise NeedsInput("Không được so chéo platform hoặc distribution_mode.")
    expected = {item["variant_id"] for item in experiment["variants"]}
    actual = {item.get("variant_id") for item in metrics["variants"]}
    if actual != expected:
        raise NeedsInput("Variant IDs trong metrics không khớp experiment.")
    for row in metrics["variants"]:
        for key, value in row.items():
            if key in {"variant_id", "published_at", "raw_platform_metrics", "retention_curve", "notes"} or value is None:
                continue
            if isinstance(value, (int, float)) and value < 0:
                raise NeedsInput(f"Metric âm không hợp lệ: {row['variant_id']}.{key}")


def map_retention_drops(curve: list[dict[str, Any]], plan: dict[str, Any]) -> list[dict[str, Any]]:
    points = [item for item in curve if item.get("retained_rate") is not None]
    drops: list[dict[str, Any]] = []
    for previous, current in zip(points, points[1:]):
        delta = float(current["retained_rate"]) - float(previous["retained_rate"])
        if delta >= 0:
            continue
        second = float(current["second"])
        shot = next((item for item in plan["shots"] if float(item["start_s"]) <= second <= float(item["end_s"]) + 0.001), None)
        drops.append({"second": second, "delta": delta, "shot_id": shot["shot_id"] if shot else None, "retention_role": shot["retention_role"] if shot else None})
    return sorted(drops, key=lambda item: item["delta"])


def command_learn(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    job_dir = argument_path(workspace, args.job, "job")
    brief = load_json(job_dir / "normalized-brief.json")
    experiment = load_json(job_dir / "experiment.json")
    metrics = load_json(argument_path(workspace, args.metrics, "metrics"))
    validate_metrics(metrics, experiment, brief)
    values = {row["variant_id"]: metric_value(row, brief["primary_metric"]) for row in metrics["variants"]}
    observed = [(variant_id, value) for variant_id, value in values.items() if value is not None]
    best: str | None = None
    if observed:
        top = max(value for _, value in observed)
        leaders = [variant_id for variant_id, value in observed if value == top]
        if len(leaders) == 1 and len(observed) > 1:
            best = leaders[0]
    drops: dict[str, Any] = {}
    for row in metrics["variants"]:
        plan = load_json(job_dir / "variants" / row["variant_id"] / "production-plan.json")
        drops[row["variant_id"]] = map_retention_drops(row.get("retention_curve") or [], plan)
    report = {
        "experiment_id": experiment["experiment_id"], "platform": brief["platform"], "distribution_mode": brief["distribution_mode"],
        "primary_metric": brief["primary_metric"], "metric_values": values, "best_observed_variant": best,
        "conclusion_strength": "directional", "causal_claim": False, "retention_drops": drops,
        "notes": "Observed comparison only; no composite score and no cross-platform comparison.",
    }
    next_brief = copy.deepcopy(brief)
    next_brief["learning_hypothesis"] = {
        "source_experiment_id": experiment["experiment_id"],
        "hypothesis_vi": (
            f"Giữ nguyên facts, offer, CTA và body; thử lại package Hook của variant {best} trong điều kiện đăng tương đương."
            if best else "Giữ nguyên facts, offer, CTA và body; lặp lại cùng biến thử nghiệm vì dữ liệu hiện tại chưa phân biệt được variant."
        ),
        "change_one_thing": experiment.get("single_variable_field") or "hook-package",
    }
    performance = job_dir / "performance"
    atomic_write_json(performance / "metrics.json", metrics)
    atomic_write_json(performance / "performance-report.json", report)
    atomic_write_json(performance / "next-brief.json", next_brief)
    manifest = load_json(job_dir / "manifest.json")
    manifest["learn"] = {
        "status": "completed", "updated_at": now_iso(), "input_fingerprint": value_hash(metrics),
        "outputs": [artifact_descriptor(performance / name, job_dir) for name in ("metrics.json", "performance-report.json", "next-brief.json")],
    }
    atomic_write_json(job_dir / "manifest.json", manifest)
    emit("completed", job=str(job_dir), best_observed_variant=best, conclusion_strength="directional")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local Video Factory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    new = subparsers.add_parser("new", help="Create a non-overwriting brief")
    new.add_argument("--profile", required=True, choices=["homemade", "milk-tea"])
    new.add_argument("--platform", required=True, choices=["tiktok", "instagram-reels", "youtube-shorts"])
    new.add_argument("--variants", required=True, type=int, choices=[1, 3])
    new.add_argument("--topic", required=True)
    new.add_argument("--workspace")
    new.set_defaults(handler=command_new)

    run = subparsers.add_parser("run", help="Run through review or full production")
    run.add_argument("--brief", required=True)
    mode = run.add_mutually_exclusive_group(required=True)
    mode.add_argument("--review", action="store_true")
    mode.add_argument("--auto", action="store_true")
    run.add_argument("--allow-paid", action="store_true")
    run.add_argument("--workspace")
    run.set_defaults(handler=command_run)

    resume = subparsers.add_parser("resume", help="Resume a job and reuse valid work")
    resume.add_argument("--job", required=True)
    resume.add_argument("--candidate-id")
    resume.add_argument("--voiceover-dir")
    resume.add_argument("--force", action="store_true")
    resume.add_argument("--allow-paid", action="store_true")
    resume.add_argument("--workspace")
    resume.set_defaults(handler=command_resume)

    dry = subparsers.add_parser("dry-run", help="Validate and plan without network or writes")
    dry.add_argument("--brief", required=True)
    dry.add_argument("--workspace")
    dry.set_defaults(handler=command_dry_run)

    learn = subparsers.add_parser("learn", help="Analyze manual metrics offline")
    learn.add_argument("--job", required=True)
    learn.add_argument("--metrics", required=True)
    learn.add_argument("--workspace")
    learn.set_defaults(handler=command_learn)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "resume" and args.force and not args.candidate_id:
        parser.error("--force chỉ hợp lệ cùng --candidate-id")
    try:
        return int(args.handler(args))
    except FactoryError as exc:
        emit(exc.status, message=exc.message, details=exc.details)
        return exc.exit_code
    except KeyboardInterrupt:
        emit("failed", message="Đã hủy bởi người dùng.")
        return 130
    except Exception as exc:  # Never expose environment or request headers.
        emit("failed", message=f"Lỗi không mong đợi: {type(exc).__name__}", details=[safe_detail(exc)])
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
