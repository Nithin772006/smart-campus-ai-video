"""
Unit tests for Hugging Face Cloud Video generation proof of concept (Task 9A).
Tests configuration, error handling, validation, and mocked API responses without consuming real HF credits.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.config import settings
from app.schemas.cloud_video import (
    CloudVideoRequest,
    CloudVideoResponse,
    CloudVideoStatusResponse,
)
from app.services.huggingface_video_service import (
    HuggingFaceVideoService,
    HuggingFaceVideoConfigError,
    HuggingFaceVideoDisabledError,
    HuggingFaceAPIError,
    HuggingFaceTimeoutError,
    slugify_prompt,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def dummy_mp4_bytes():
    # Valid MP4 box header prefix followed by padding bytes
    return b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 4096


# 1. Configuration loading
def test_huggingface_config_loading():
    assert hasattr(settings, "HF_TOKEN")
    assert hasattr(settings, "HF_VIDEO_ENABLED")
    assert hasattr(settings, "HF_VIDEO_PROVIDER")
    assert hasattr(settings, "HF_VIDEO_MODEL")
    assert hasattr(settings, "HF_VIDEO_TIMEOUT")
    assert hasattr(settings, "CLOUD_VIDEO_DIR")
    assert settings.CLOUD_VIDEO_DIR.exists()
    assert settings.HF_VIDEO_PROVIDER in ["fal-ai", "together", "replicate", "hf-inference"]


# 2. Missing token handling
def test_missing_token_handling(tmp_path):
    svc = HuggingFaceVideoService(token="", output_dir=tmp_path)
    assert not svc.is_configured()
    with pytest.raises(HuggingFaceVideoConfigError) as exc_info:
        svc.generate_video(prompt="Test prompt", check_enabled=False)
    assert "HF_TOKEN is not configured" in str(exc_info.value) or "missing or empty" in str(exc_info.value)


# 3. Disabled feature handling
def test_disabled_feature_handling(tmp_path):
    svc = HuggingFaceVideoService(token="hf_mock_token_12345", output_dir=tmp_path)
    with patch.object(svc, "is_enabled", return_value=False):
        with pytest.raises(HuggingFaceVideoDisabledError) as exc_info:
            svc.generate_video(prompt="Test prompt", check_enabled=True)
        assert "disabled" in str(exc_info.value).lower()


# 4. Request validation
def test_request_validation():
    # Valid request
    valid_req = CloudVideoRequest(
        prompt="A falling apple illustrating gravitational acceleration",
        model="Wan-AI/Wan2.2-TI2V-5B",
        provider="fal-ai",
        num_frames=49,
        num_inference_steps=30,
        guidance_scale=5.0,
    )
    assert valid_req.prompt.startswith("A falling apple")
    assert valid_req.num_frames == 49

    # Empty prompt fails validation
    with pytest.raises(ValidationError):
        CloudVideoRequest(prompt="")

    # Excessively large step count fails validation
    with pytest.raises(ValidationError):
        CloudVideoRequest(prompt="Valid prompt", num_inference_steps=500)

    # Excessively large frame count fails validation
    with pytest.raises(ValidationError):
        CloudVideoRequest(prompt="Valid prompt", num_frames=1000)


# 5. Service initialization and status
def test_service_initialization(tmp_path):
    svc = HuggingFaceVideoService(
        token="hf_test_token",
        default_provider="fal-ai",
        default_model="Wan-AI/Wan2.2-TI2V-5B",
        timeout=120.0,
        output_dir=tmp_path,
    )
    assert svc.is_configured()
    status = svc.get_status()
    assert "enabled" in status
    assert status["provider"] == "fal-ai"
    assert status["model"] == "Wan-AI/Wan2.2-TI2V-5B"
    assert status["token_configured"] is True


# 6. Slugify prompt helper
def test_slugify_prompt():
    slug = slugify_prompt("A cinematic educational visualization of gravity!")
    assert slug == "a_cinematic_educational_visualization_of"
    assert "_" in slug


# 7. Successful API response handling using mocked client
def test_successful_mocked_generation(tmp_path, dummy_mp4_bytes):
    svc = HuggingFaceVideoService(token="hf_mock_token", output_dir=tmp_path)

    mock_client = MagicMock()
    mock_client.text_to_video.return_value = dummy_mp4_bytes

    with patch.object(svc, "_get_client", return_value=mock_client):
        result = svc.generate_video(
            prompt="A ball bouncing on the floor",
            model="Wan-AI/Wan2.2-TI2V-5B",
            provider="fal-ai",
            guidance_scale=6.0,
            num_frames=45,
            check_enabled=False,
        )

    assert result["success"] is True
    assert result["provider"] == "fal-ai"
    assert result["model"] == "Wan-AI/Wan2.2-TI2V-5B"
    assert Path(result["absolute_path"]).exists()
    assert result["output_size_mb"] > 0
    assert result["generation_time_seconds"] >= 0

    # Ensure mock client was called with correct parameters
    mock_client.text_to_video.assert_called_once()
    _, kwargs = mock_client.text_to_video.call_args
    assert kwargs["prompt"] == "A ball bouncing on the floor"
    assert kwargs["model"] == "Wan-AI/Wan2.2-TI2V-5B"
    assert kwargs["guidance_scale"] == 6.0
    assert kwargs["num_frames"] == 45


# 8. File saving and non-overwrite collision avoidance
def test_file_saving_collision_avoidance(tmp_path, dummy_mp4_bytes):
    svc = HuggingFaceVideoService(token="hf_mock_token", output_dir=tmp_path)
    mock_client = MagicMock()
    mock_client.text_to_video.return_value = dummy_mp4_bytes

    with patch.object(svc, "_get_client", return_value=mock_client):
        res1 = svc.generate_video(prompt="Gravity demonstration", check_enabled=False)
        res2 = svc.generate_video(prompt="Gravity demonstration", check_enabled=False)

    p1 = Path(res1["absolute_path"])
    p2 = Path(res2["absolute_path"])
    assert p1.exists()
    assert p2.exists()
    # Paths must be distinct to prevent overwriting
    assert p1 != p2


# 9. Error handling: Timeout and API errors
def test_error_handling(tmp_path):
    svc = HuggingFaceVideoService(token="hf_mock_token", output_dir=tmp_path)

    # Test Timeout
    mock_client_timeout = MagicMock()
    mock_client_timeout.text_to_video.side_effect = TimeoutError("Request timed out")

    with patch.object(svc, "_get_client", return_value=mock_client_timeout):
        with pytest.raises(HuggingFaceTimeoutError):
            svc.generate_video(prompt="Slow query", check_enabled=False)

    # Test generic exception mapping to HuggingFaceAPIError
    mock_client_err = MagicMock()
    mock_client_err.text_to_video.side_effect = RuntimeError("Service 503 unavailable")

    with patch.object(svc, "_get_client", return_value=mock_client_err):
        with pytest.raises(HuggingFaceAPIError):
            svc.generate_video(prompt="Failed query", check_enabled=False)


# 10. API GET /api/video/cloud/status endpoint
def test_api_status_endpoint(client):
    response = client.get("/api/video/cloud/status")
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "provider" in data
    assert "model" in data
    assert "token_configured" in data
    # Token value must never be leaked
    assert "token" not in data
    assert "HF_TOKEN" not in str(data)


# 11. API POST /api/video/cloud/generate disabled behavior
def test_api_generate_disabled(client):
    # When HF_VIDEO_ENABLED is False (default), endpoint rejects with 400
    response = client.post(
        "/api/video/cloud/generate",
        json={"prompt": "A test visual of an apple"}
    )
    assert response.status_code == 400
    assert "disabled" in response.json()["detail"].lower()
