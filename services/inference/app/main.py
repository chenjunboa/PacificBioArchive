from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from threading import Lock

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel


def normalize_tag(value: str) -> str:
    return re.sub(r"[\s-]+", "_", value.strip().lower())


def sample_video_one_frame_per_second(path: Path) -> list[np.ndarray]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError("Video cannot be decoded")
    fps = capture.get(cv2.CAP_PROP_FPS)
    frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
    if fps <= 0 or frame_count <= 0:
        capture.release()
        raise ValueError("Video metadata is invalid")
    duration_seconds = frame_count / fps
    frames: list[np.ndarray] = []
    for second in range(math.ceil(duration_seconds)):
        capture.set(cv2.CAP_PROP_POS_MSEC, second * 1000.0)
        ok, frame = capture.read()
        if ok:
            frames.append(frame)
    capture.release()
    if not frames:
        raise ValueError("Video contains no decodable frames")
    return frames


class InferenceResponse(BaseModel):
    tags: dict[str, int]
    modelVersion: str
    sampledFrames: int = 1


class Runtime:
    def __init__(self) -> None:
        self.mode = os.getenv("MODEL_MODE", "stub")
        self.version = os.getenv("MODEL_VERSION", "local-stub-v1")
        self._real = None
        self._load_lock = Lock()

    def infer(self, path: Path, filename: str, content_type: str) -> InferenceResponse:
        if self.mode != "real":
            tag = normalize_tag(re.sub(r"[_-]?\d+$", "", Path(filename).stem))
            sampled = (
                len(sample_video_one_frame_per_second(path))
                if content_type.startswith("video/")
                else 1
            )
            return InferenceResponse(
                tags={tag: 1}, modelVersion=self.version, sampledFrames=sampled
            )
        if self._real is None:
            with self._load_lock:
                if self._real is None:
                    self._real = RealModelRuntime.from_environment()
                    self.version = self._real.version
        return self._real.infer(path, content_type)


class RealModelRuntime:
    def __init__(self, detector_path: Path, classifier_path: Path, labels_path: Path, version: str):
        import torch
        import torchvision.transforms as transforms

        self.version = version
        self.detector_path = detector_path
        self.labels = self._read_labels(labels_path)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = torch.load(classifier_path, map_location=self.device, weights_only=False)
        self.model.eval().to(self.device)
        self.transform = transforms.Compose([transforms.Resize((480, 480)), transforms.ToTensor()])
        self.torch = torch
        if len(self.labels) != 46:
            raise RuntimeError(f"Expected 46 labels, found {len(self.labels)}")

    @classmethod
    def from_environment(cls) -> "RealModelRuntime":
        manifest_path = materialize_manifest(
            os.getenv("MODEL_MANIFEST", "/models/manifest.json")
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        base = manifest_path.parent
        paths = {
            name: base / manifest[name]["path"] for name in ("detector", "classifier", "labels")
        }
        for name, path in paths.items():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != manifest[name]["sha256"]:
                raise RuntimeError(f"{name} checksum does not match manifest")
        return cls(paths["detector"], paths["classifier"], paths["labels"], manifest["version"])

    @staticmethod
    def _read_labels(path: Path) -> list[str]:
        labels = []
        for line in path.read_text(encoding="utf-8").splitlines():
            fields = line.split(";")
            if len(fields) >= 6:
                labels.append(normalize_tag(f"{fields[4]}_{fields[5]}"))
        return labels

    def infer(self, path: Path, content_type: str) -> InferenceResponse:
        if content_type.startswith("video/"):
            frames = sample_video_one_frame_per_second(path)
        else:
            image = cv2.imread(str(path))
            if image is None:
                raise ValueError("Image cannot be decoded")
            frames = [image]
        per_frame = [self._infer_frame(frame) for frame in frames]
        tags = {
            tag: max(counts.get(tag, 0) for counts in per_frame)
            for tag in set().union(*(counts.keys() for counts in per_frame))
        }
        return InferenceResponse(tags=tags, modelVersion=self.version, sampledFrames=len(frames))

    def _infer_frame(self, frame: np.ndarray) -> Counter:
        from megadetector.detection import run_detector_batch
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            frame_path = Path(directory) / "frame.jpg"
            cv2.imwrite(str(frame_path), frame)
            output = run_detector_batch.load_and_run_detector_batch(
                image_file_names=[str(frame_path)], model_file=str(self.detector_path)
            )
            entries = output.get("images", output) if isinstance(output, dict) else output
            detections = entries[0].get("detections", []) if entries else []
            rgb = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            width, height = rgb.size
            crops = []
            for detection in detections:
                if detection.get("category") != "1" or detection.get("conf", 0) < 0.05:
                    continue
                x, y, w, h = detection["bbox"]
                crops.append(rgb.crop((x * width, y * height, (x + w) * width, (y + h) * height)))
            if not crops:
                return Counter()
            batch = self.torch.stack([self.transform(crop) for crop in crops])
            batch = batch.permute(0, 2, 3, 1).to(self.device)
            with self.torch.no_grad():
                indexes = self.model(batch).argmax(dim=1).cpu().tolist()
            return Counter(self.labels[index] for index in indexes)


def materialize_manifest(reference: str) -> Path:
    """Return a local, checksum-verifiable model manifest.

    A local path is preserved for development. In cloud mode a gs:// manifest and
    every file referenced by it are downloaded into a generation-specific cache
    directory, so a container never mixes files from two model generations.
    """
    if not reference.startswith("gs://"):
        return Path(reference)
    from google.cloud import storage

    bucket_name, _, blob_name = reference[5:].partition("/")
    if not bucket_name or not blob_name:
        raise RuntimeError("MODEL_MANIFEST must be a gs://bucket/object URI")
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(blob_name)
    blob.reload()
    generation = str(blob.generation)
    cache_root = Path(os.getenv("MODEL_CACHE_DIR", "/tmp/models"))
    target_dir = cache_root / generation
    target_manifest = target_dir / Path(blob_name).name
    if target_manifest.exists():
        return target_manifest
    cache_root.mkdir(parents=True, exist_ok=True)
    temporary_dir = Path(tempfile.mkdtemp(prefix="model-", dir=cache_root))
    try:
        temporary_manifest = temporary_dir / Path(blob_name).name
        blob.download_to_filename(temporary_manifest)
        manifest = json.loads(temporary_manifest.read_text(encoding="utf-8"))
        base_prefix = str(Path(blob_name).parent).replace("\\", "/")
        if base_prefix == ".":
            base_prefix = ""
        for name in ("detector", "classifier", "labels"):
            relative_path = Path(manifest[name]["path"])
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise RuntimeError(f"Unsafe {name} path in model manifest")
            object_name = "/".join(part for part in (base_prefix, relative_path.as_posix()) if part)
            destination = temporary_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            client.bucket(bucket_name).blob(object_name).download_to_filename(destination)
            digest = hashlib.sha256(destination.read_bytes()).hexdigest()
            if digest != manifest[name]["sha256"]:
                raise RuntimeError(f"{name} checksum does not match manifest")
        try:
            temporary_dir.replace(target_dir)
        except FileExistsError:
            shutil.rmtree(temporary_dir)
        return target_manifest
    except Exception:
        if temporary_dir.exists():
            shutil.rmtree(temporary_dir)
        raise


app = FastAPI(title="Pacific BioArchive Inference", version="0.1.0")
runtime = Runtime()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": runtime.mode, "modelVersion": runtime.version}


@app.post("/infer", response_model=InferenceResponse)
async def infer(file: UploadFile = File(...)) -> InferenceResponse:
    suffix = Path(file.filename or "upload.bin").suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
        while chunk := await file.read(1024 * 1024):
            temporary.write(chunk)
        path = Path(temporary.name)
    try:
        return runtime.infer(
            path, file.filename or path.name, file.content_type or "application/octet-stream"
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        path.unlink(missing_ok=True)
