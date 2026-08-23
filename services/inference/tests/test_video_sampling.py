import importlib.util
from pathlib import Path

import cv2
import numpy as np
import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "main.py"
SPEC = importlib.util.spec_from_file_location("pba_inference_main", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
sample_video_one_frame_per_second = MODULE.sample_video_one_frame_per_second


def test_video_sampling_returns_one_frame_for_each_started_second(tmp_path):
    path = tmp_path / "sample.mp4"
    fps = 5.0
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (64, 48)
    )
    assert writer.isOpened()
    for index in range(12):  # 2.4 seconds -> frames at t=0, 1 and 2 seconds.
        frame = np.full((48, 64, 3), index * 10, dtype=np.uint8)
        writer.write(frame)
    writer.release()

    frames = sample_video_one_frame_per_second(path)
    assert len(frames) == 3
    assert all(frame.shape == (48, 64, 3) for frame in frames)


def test_invalid_video_is_rejected(tmp_path):
    path = tmp_path / "broken.mp4"
    path.write_bytes(b"not a video")
    with pytest.raises(ValueError, match="cannot be decoded"):
        sample_video_one_frame_per_second(path)
