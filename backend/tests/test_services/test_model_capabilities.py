"""Tests for conservative model/task capability checks."""

from app.services.inference.capabilities import assess_model_for_task


def test_mimo_multimodal_profile_matches_vision_task() -> None:
    report = assess_model_for_task("mimo", "mimo-v2.5", "vision")

    assert report["status"] == "supported"
    assert report["capabilities"]["vision"] is True


def test_text_only_qwen_is_rejected_for_vision_but_allowed_for_translation() -> None:
    vision = assess_model_for_task("qwen", "qwen-plus", "vision")
    translation = assess_model_for_task("qwen", "qwen-plus", "translation")

    assert vision["status"] == "unsupported"
    assert translation["status"] == "supported"


def test_sensenova_u1_matches_diagram_task() -> None:
    report = assess_model_for_task("sensenova", "sensenova-u1-fast", "diagram")

    assert report["status"] == "supported"


def test_custom_image_capability_remains_unknown() -> None:
    report = assess_model_for_task("custom", "my-model", "diagram")

    assert report["status"] == "unknown"


def test_siliconflow_qwen_models_are_routed_by_actual_capability() -> None:
    text = assess_model_for_task("siliconflow", "Qwen/Qwen3-8B", "analysis")
    vision = assess_model_for_task(
        "siliconflow",
        "Qwen/Qwen3-VL-8B-Instruct",
        "vision",
    )

    assert text["status"] == "supported"
    assert text["capabilities"]["vision"] is False
    assert vision["status"] == "supported"
