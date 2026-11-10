from __future__ import annotations

import copy
import io
import json
import os
import subprocess
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import video_factory as vf


def brief(profile: str = "homemade", platform: str = "tiktok", variants: int = 1) -> dict:
    return vf.default_brief(profile, platform, variants, "Bánh thật cho gia đình")


def candidate(candidate_id: str = "C1", angle: str = "product-first", mechanism: str = "result-first", first: str = "Cận cảnh bánh được cắt", promise: str = "Thấy phần nhân bánh thật") -> dict:
    return {
        "candidate_id": candidate_id,
        "angle": angle,
        "duration_seconds": 20,
        "pace_profile": "sensory",
        "pace_reason_vi": "Cho thấy texture thật",
        "hook_plan": {
            "first_frame_vi": first,
            "visual_hook_vi": first,
            "spoken_hook_vi": promise,
            "on_screen_hook_vi": promise,
            "audio_hook_vi": "Âm thanh cắt bánh",
            "single_promise_vi": promise,
            "hook_mechanism": mechanism,
            "works_without_sound": True,
            "proof_or_payoff_due_at_second": 3,
        },
        "beats": [
            {"beat_id": "B01", "start_s": 0, "end_s": 3, "retention_role": "hook", "viewer_question_vi": "Nhân thế nào?", "new_information_vi": promise, "visual_action_vi": first, "audio_cue_vi": "Cắt", "retention_device_vi": "result-first", "fact_refs": []},
            {"beat_id": "B02", "start_s": 3, "end_s": 12, "retention_role": "proof", "viewer_question_vi": "Bằng chứng?", "new_information_vi": "Cho thấy bánh thật", "visual_action_vi": "Xoay miếng bánh", "audio_cue_vi": "Tự nhiên", "retention_device_vi": "progress", "fact_refs": []},
            {"beat_id": "B03", "start_s": 12, "end_s": 18, "retention_role": "payoff", "viewer_question_vi": "Kết quả?", "new_information_vi": promise, "visual_action_vi": "Cận nhân", "audio_cue_vi": "Nhấn", "retention_device_vi": "payoff", "fact_refs": []},
            {"beat_id": "B04", "start_s": 18, "end_s": 20, "retention_role": "cta", "viewer_question_vi": "Gửi ai?", "new_information_vi": "Gợi ý chia sẻ", "visual_action_vi": "Giữ cận cảnh", "audio_cue_vi": "Nhẹ", "retention_device_vi": "cta", "fact_refs": []},
        ],
        "engagement_plan": {"primary_action": "share", "earned_reason_vi": "Gửi người thích bánh", "cta_vi": "Gửi cho người thích bánh", "cta_fact_refs": []},
        "claims": [],
        "script_lines": [
            {"start_s": 0, "end_s": 3, "spoken_vi": promise, "on_screen_text_vi": promise, "fact_refs": []},
            {"start_s": 3, "end_s": 18, "spoken_vi": "Xem phần bánh thật", "on_screen_text_vi": "", "fact_refs": []},
            {"start_s": 18, "end_s": 20, "spoken_vi": "Gửi cho người thích bánh", "on_screen_text_vi": "", "fact_refs": []},
        ],
        "payoff_promise_vi": promise,
    }


def four_candidates() -> list[dict]:
    return [
        candidate("C1", "product-first", "result-first", "Cắt đôi chiếc bánh thật", "Nhìn rõ phần nhân thật"),
        candidate("C2", "story-first", "curiosity", "Một hộp bánh đang được mở", "Biết câu chuyện của hộp bánh"),
        candidate("C3", "process-first", "sensory", "Tay đang đóng khuôn bánh", "Thấy một bước làm bánh"),
        candidate("C4", vf.FALLBACK_ANGLE, "local-relevance", "Đơn bánh chuẩn bị giao trong xã", "Thấy cách chuẩn bị đơn địa phương"),
    ]


def media_brief(root: Path) -> dict:
    value = brief()
    path = root / "media" / "real.png"
    path.parent.mkdir()
    path.write_bytes(b"png")
    value["available_media"] = [{"path": "media/real.png", "type": "image", "description": "Ảnh bánh thật", "product": "bánh", "allowed_use": "advertising"}]
    return value


def production_plan() -> dict:
    return {
        "variant_id": "A", "duration_seconds": 20,
        "shots": [{
            "shot_id": "S01", "start_s": 0, "end_s": 20, "retention_role": "hook",
            "voiceover_vi": "Nhìn rõ phần nhân thật", "on_screen_text_vi": "Bánh thật",
            "visual": {"source": "real-image", "asset_path": "media/real.png", "subject_vi": "Bánh", "action_vi": "Cắt", "framing_vi": "Cận", "camera_motion_vi": "Tĩnh", "lighting_vi": "Ấm", "continuity_notes_vi": "Giữ màu", "image_prompt_en": "", "negative_prompt_en": "", "intentional_black": False},
            "audio": {"voice_direction_vi": "Ấm, rõ", "natural_sound_vi": "", "natural_sound_asset_path": "", "sfx_vi": "", "sfx_asset_path": "", "music_cue_vi": "", "intentional_silence": False},
            "edit": {"transition_vi": "hard-cut", "change_from_previous_vi": "Mở đầu", "subtitle_emphasis_vi": "Nhân"},
            "fact_refs": [],
        }],
    }


class FactoryTests(unittest.TestCase):
    def test_parser_and_mutual_exclusion(self):
        parser = vf.build_parser()
        self.assertEqual(parser.parse_args(["new", "--profile", "homemade", "--platform", "tiktok", "--variants", "1", "--topic", "x"]).command, "new")
        for command in ("new", "run", "resume", "dry-run", "learn"):
            self.assertIn(command, parser.format_help() + " ".join(parser._subparsers._group_actions[0].choices))
        with self.assertRaises(SystemExit):
            parser.parse_args(["run", "--brief", "x", "--auto", "--review"])
        with self.assertRaises(SystemExit):
            vf.main(["resume", "--job", "x", "--force"])

    def test_new_is_non_overwriting(self):
        with tempfile.TemporaryDirectory() as raw:
            args = Namespace(workspace=raw, profile="homemade", platform="tiktok", variants=1, topic="Bánh")
            self.assertEqual(vf.command_new(args), 0)
            self.assertTrue((Path(raw) / ".env.example").is_file())
            with self.assertRaises(vf.NeedsInput):
                vf.command_new(args)

    def test_validate_and_normalize_brief(self):
        with tempfile.TemporaryDirectory() as raw:
            normalized, warnings = vf.normalize_brief(brief(), Path(raw))
            self.assertEqual(normalized["candidate_count"] if "candidate_count" in normalized else 4, 4)
            self.assertEqual(warnings, [])
            bad = brief()
            bad["duration_range_seconds"] = {"min": 40, "max": 20}
            with self.assertRaises(vf.NeedsInput):
                vf.normalize_brief(bad, Path(raw))

    def test_media_rights_and_traversal(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            value = media_brief(root)
            value["available_media"][0]["allowed_use"] = "personal"
            with self.assertRaises(vf.NeedsInput):
                vf.normalize_brief(value, root)
            value["available_media"][0]["path"] = "../escape.png"
            value["available_media"][0]["allowed_use"] = "advertising"
            with self.assertRaises(vf.NeedsInput):
                vf.normalize_brief(value, root)

    def test_incomplete_trend_becomes_evergreen(self):
        with tempfile.TemporaryDirectory() as raw:
            value = brief()
            value["trend_context"] = {"mode": "referenced-trend", "region": "VN", "observed_at": "", "references": []}
            normalized, warnings = vf.normalize_brief(value, Path(raw))
            self.assertEqual(normalized["trend_context"]["mode"], "evergreen")
            self.assertTrue(warnings)

    def test_sales_goal_needs_input_or_falls_back(self):
        with tempfile.TemporaryDirectory() as raw:
            value = brief()
            value["campaign_goal"], value["primary_metric"] = "orders", "orders"
            with self.assertRaises(vf.NeedsInput):
                vf.normalize_brief(value, Path(raw))
            value["allow_goal_fallback"] = True
            normalized, _ = vf.normalize_brief(value, Path(raw))
            self.assertEqual(normalized["campaign_goal"], "reach")

    def test_fact_and_cta_grounding(self):
        value = candidate()
        value["claims"] = [{"text_vi": "Giá 50k", "brief_path": "/prices/0", "source_value": "50k"}]
        value["script_lines"][0]["fact_refs"] = ["/prices/0"]
        errors = vf.hard_gate_candidate(value, brief())
        self.assertTrue(any("brief_path" in item or "fact ref" in item for item in errors))
        value = candidate()
        value["engagement_plan"] = {"primary_action": "order", "earned_reason_vi": "Đặt", "cta_vi": "Đặt hàng", "cta_fact_refs": []}
        self.assertTrue(any("CTA thương mại" in item for item in vf.hard_gate_candidate(value, brief())))

    def test_hook_and_retention_gates(self):
        value = candidate()
        self.assertEqual(vf.hard_gate_candidate(value, brief()), [])
        value["hook_plan"]["proof_or_payoff_due_at_second"] = 4
        value["beats"][1]["start_s"] = 4
        value["payoff_promise_vi"] = "Khác"
        errors = vf.hard_gate_candidate(value, brief())
        self.assertTrue(any("3 giây" in item for item in errors))
        self.assertTrue(any("timeline" in item for item in errors))
        self.assertTrue(any("Payoff" in item for item in errors))

    def test_package_has_four_distinct_angles(self):
        result = vf.hard_gate_candidates(four_candidates(), brief())
        self.assertNotIn("_package", result)
        values = four_candidates()
        values[1]["hook_plan"]["first_frame_vi"] = values[0]["hook_plan"]["first_frame_vi"]
        self.assertIn("_package", vf.hard_gate_candidates(values, brief()))

    def test_force_never_bypasses_hard_error(self):
        value = candidate()
        package = {"candidates": [value], "hard_gate_results": {"C1": ["unsafe"]}, "judge_results": [{"candidate_id": "C1", "passed": False}]}
        with self.assertRaises(vf.NeedsInput):
            vf.select_candidate(package, "C1", True)
        package["hard_gate_results"] = {"C1": []}
        selected = vf.select_candidate(package, "C1", True)
        self.assertEqual(selected["candidate_id"], "C1")

    def test_experiment_baseline_and_modes(self):
        with tempfile.TemporaryDirectory() as raw:
            ctx = vf.RunContext(Path(raw), dry_run=False)
            one = vf.create_experiment(ctx, brief(variants=1), candidate(), "job")
            self.assertEqual(one["mode"], "baseline")
            base = candidate()
            single = {"experiment_id": "x", "mode": "single-variable", "single_variable_field": "hook_plan.on_screen_hook_vi", "platform": "tiktok", "distribution_mode": "organic", "primary_metric": "shares_per_view", "controlled_fields": [], "variants": []}
            for variant_id, text in zip("ABC", ("A", "B", "C")):
                script = copy.deepcopy(base)
                script["hook_plan"]["on_screen_hook_vi"] = text
                single["variants"].append({"variant_id": variant_id, "script": script})
            vf.validate_experiment(single)
            hook = copy.deepcopy(single)
            hook["mode"] = "hook-package"
            hook["single_variable_field"] = None
            for item, text in zip(hook["variants"], ("Một", "Hai", "Ba")):
                item["script"]["hook_plan"]["visual_hook_vi"] = text
            vf.validate_experiment(hook)

    def test_dry_run_never_calls_network_or_writes_outputs(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = root / "brief.json"
            vf.atomic_write_json(path, brief())
            args = Namespace(workspace=raw, brief="brief.json")
            with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "redacted", "OPENAI_TEXT_MODEL": "configured"}, clear=False), mock.patch.object(vf, "dependency_report", return_value={"python": "x", "openai_sdk": True, "jsonschema": True, "ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}), mock.patch.object(vf.urllib.request, "urlopen") as network:
                self.assertEqual(vf.command_dry_run(args), 0)
                network.assert_not_called()
            self.assertFalse((root / "outputs").exists())

    def test_paid_guard(self):
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(vf.NeedsInput):
                vf.require_paid(vf.RunContext(Path(raw), allow_paid=False), ["OPENAI_API_KEY"])
            with self.assertRaises(vf.FactoryError):
                vf.require_paid(vf.RunContext(Path(raw), allow_paid=True, dry_run=True), [])

    def test_review_stops_before_media_or_tts(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = root / "brief.json"
            vf.atomic_write_json(path, brief())
            args = Namespace(workspace=raw, brief=str(path), review=True, auto=False, allow_paid=True)
            scores = [{"candidate_id": item["candidate_id"], "criteria": {name: 8 for name in vf.JUDGE_WEIGHTS}, "editorial_quality_score": 80, "passed": True, "notes_vi": ""} for item in four_candidates()]
            with mock.patch.object(vf, "generate_candidates", return_value=four_candidates()), mock.patch.object(vf, "judge_candidates", return_value=scores), mock.patch.object(vf, "prepare_media_and_audio") as prepare:
                self.assertEqual(vf.command_run(args), 0)
                prepare.assert_not_called()

    def test_forward_full_pipeline_with_mocked_paid_and_ffmpeg(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            value = media_brief(root)
            brief_path = root / "brief.json"
            vf.atomic_write_json(brief_path, value)
            scores = [{"candidate_id": item["candidate_id"], "criteria": {name: 8 for name in vf.JUDGE_WEIGHTS}, "editorial_quality_score": 80, "passed": True} for item in four_candidates()]
            prepared = {"variants": {"A": {"visuals": {"S01": str(root / "media" / "real.png")}, "voiceovers": {}, "natural_sounds": {}, "sfx": {}, "subtitle_cues": [(0, 2, "Bánh thật")], "manual_srt": ""}}, "bgm_path": ""}

            def fake_render(_ffmpeg, _plan, _state, output, _fps, _bgm):
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"mp4")
                (output.parent / "subtitles.srt").write_text("1\n00:00:00,000 --> 00:00:02,000\nBánh thật\n", encoding="utf-8")

            args = Namespace(workspace=raw, brief="brief.json", review=False, auto=True, allow_paid=True)
            with mock.patch.object(vf, "generate_candidates", return_value=four_candidates()), mock.patch.object(vf, "judge_candidates", return_value=scores), mock.patch.object(vf, "create_production_plans", return_value=[production_plan()]), mock.patch.object(vf, "prepare_media_and_audio", return_value=prepared), mock.patch.object(vf, "require_ffmpeg", return_value=("ffmpeg", "ffprobe")), mock.patch.object(vf, "render_variant", side_effect=fake_render), mock.patch.object(vf, "qc_variant", return_value={"video_stream": True, "audio_stream": True}):
                self.assertEqual(vf.command_run(args), 0)
            jobs = list((root / "outputs").iterdir())
            manifest = vf.load_json(jobs[0] / "manifest.json")
            self.assertEqual(manifest["status"], "completed")
            self.assertTrue((jobs[0] / "post-package.json").is_file())

    def test_artifact_fingerprint_detects_corruption(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = root / "data.json"
            vf.atomic_write_json(path, {"x": 1})
            descriptor = vf.artifact_descriptor(path, root, "/x")
            self.assertTrue(vf.artifact_valid(descriptor, root))
            vf.atomic_write_json(path, {"x": 2})
            self.assertFalse(vf.artifact_valid(descriptor, root))

    def test_variant_production_plan_and_media_rules(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            value = media_brief(root)
            vf.validate_production_plan(production_plan(), value, root)
            invalid = production_plan()
            invalid["shots"][0]["visual"]["source"] = "ai-image"
            invalid["shots"][0]["visual"]["image_prompt_en"] = "real shop product"
            invalid["shots"][0]["visual"]["negative_prompt_en"] = "text watermark"
            invalid["shots"][0]["fact_refs"] = ["/brand_name"]
            value["brand_name"] = "Brand"
            with self.assertRaises(vf.FactoryError):
                vf.validate_production_plan(invalid, value, root)

    def test_subtitle_roundtrip_and_validation(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "subtitles.srt"
            cues = [(0, 1.2, "Xin chào"), (1.2, 2.5, "Bánh thật")]
            vf.write_srt(path, cues)
            self.assertEqual(vf.parse_srt(path), cues)
            with self.assertRaises(vf.FactoryError):
                vf.write_srt(path, [(1, 2, "A"), (1.5, 3, "B")])

    def test_ffprobe_and_black_silence_qc(self):
        probe = {"streams": [{"codec_type": "video", "codec_name": "h264", "avg_frame_rate": "30/1", "width": 1080, "height": 1920, "pix_fmt": "yuv420p"}, {"codec_type": "audio", "codec_name": "aac"}], "format": {"duration": "20.0"}}
        completed = subprocess.CompletedProcess([], 0, json.dumps(probe), "")
        analysis = subprocess.CompletedProcess([], 0, "", "")
        with tempfile.TemporaryDirectory() as raw, mock.patch.object(vf, "run_process", return_value=completed), mock.patch.object(vf.subprocess, "run", return_value=analysis):
            result = vf.qc_variant("ffmpeg", "ffprobe", production_plan(), Path(raw) / "final.mp4")
            self.assertTrue(result["video_stream"])

    def test_post_packages_have_platform_fields_and_escaped_report(self):
        for platform, field in (("tiktok", "tiktok"), ("instagram-reels", "instagram_reels"), ("youtube-shorts", "youtube_shorts")):
            value = brief(platform=platform)
            experiment = {"variants": [{"variant_id": "A", "script": candidate()}]}
            package = vf.build_post_package(value, experiment, Path("."), False)
            self.assertIn(field, package["variants"][0])
            self.assertGreaterEqual(len(package["variants"][0]["hashtags"]), 3)
            self.assertLessEqual(len(package["variants"][0]["hashtags"]), 5)
            if platform == "youtube-shorts":
                self.assertLessEqual(len(package["variants"][0][field]["title"]), 100)
        value = candidate()
        value["candidate_id"] = "<script>"
        package = {"candidates": [value], "judge_results": [{"candidate_id": "<script>", "editorial_quality_score": 80, "passed": True}], "hard_gate_results": {}}
        self.assertNotIn("<script>", vf.script_report(package, {"topic": "<b>x</b>"}))

    def test_learn_preserves_null_and_one_hypothesis(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            job = root / "outputs" / "job"
            plan_path = job / "variants" / "A" / "production-plan.json"
            vf.atomic_write_json(job / "normalized-brief.json", brief())
            experiment = {"experiment_id": "exp", "mode": "baseline", "single_variable_field": None, "platform": "tiktok", "distribution_mode": "organic", "primary_metric": "shares_per_view", "variants": [{"variant_id": "A", "script": candidate()}]}
            vf.atomic_write_json(job / "experiment.json", experiment)
            vf.atomic_write_json(plan_path, production_plan())
            vf.atomic_write_json(job / "manifest.json", {"schema_version": 1})
            metrics = {"experiment_id": "exp", "platform": "tiktok", "distribution_mode": "organic", "captured_at": "2026-08-31T00:00:00Z", "observation_window_hours": 72, "metric_source": "manual-export", "variants": [{"variant_id": "A", "published_at": "", "video_duration_seconds": None, "views": 10, "shares": None, "retention_curve": [{"second": 0, "retained_rate": None}], "raw_platform_metrics": {"Views": 10}, "notes": ""}]}
            metrics_path = root / "metrics.json"
            vf.atomic_write_json(metrics_path, metrics)
            self.assertEqual(vf.command_learn(Namespace(workspace=raw, job=str(job), metrics=str(metrics_path))), 0)
            saved = vf.load_json(job / "performance" / "metrics.json")
            self.assertIsNone(saved["variants"][0]["shares"])
            next_brief = vf.load_json(job / "performance" / "next-brief.json")
            self.assertEqual(list(key for key in next_brief if key == "learning_hypothesis"), ["learning_hypothesis"])

    def test_output_never_contains_secret(self):
        buffer = io.StringIO()
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "super-secret-value"}, clear=False), redirect_stdout(buffer):
            code = vf.main(["dry-run", "--brief", "missing.json"])
        self.assertEqual(code, 2)
        self.assertNotIn("super-secret-value", buffer.getvalue())
        buffer = io.StringIO()
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "super-secret-value"}, clear=False), mock.patch.object(vf, "command_dry_run", side_effect=RuntimeError("bad super-secret-value")), redirect_stdout(buffer):
            self.assertEqual(vf.main(["dry-run", "--brief", "ignored.json"]), 1)
        self.assertNotIn("super-secret-value", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
