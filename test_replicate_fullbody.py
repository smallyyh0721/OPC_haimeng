#!/usr/bin/env python3
"""Test Replicate image-edit API with a reference image to generate a full-body photo.

Usage:
  REPLICATE_API_TOKEN=... python test_replicate_fullbody.py \
    --reference /path/to/reference.jpg
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import pathlib
import time
import urllib.error
import urllib.request

API_BASE = "https://api.replicate.com/v1"
DEFAULT_MODEL = "black-forest-labs/flux-kontext-max"
DEFAULT_PROMPT = (
    "Use the reference person identity and generate a realistic, natural full-body portrait, "
    "standing pose, clean background, high detail, 35mm photography style."
)


def _request_json(url: str, method: str, token: str, payload: dict | None = None) -> dict:
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url=url, method=method, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def upload_file(token: str, path: pathlib.Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    content = path.read_bytes()

    boundary = "----ReplicateBoundary12345"
    body = b""
    body += (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"content\"; filename=\"{path.name}\"\r\n"
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8")
    body += content
    body += f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        url=f"{API_BASE}/files",
        method="POST",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload["urls"]["get"]


def create_prediction(token: str, model: str, image_url: str, prompt: str) -> dict:
    payload = {
        "input": {
            "prompt": prompt,
            "input_image": image_url,
            "aspect_ratio": "2:3",
        }
    }
    return _request_json(
        url=f"{API_BASE}/models/{model}/predictions",
        method="POST",
        token=token,
        payload=payload,
    )


def wait_prediction(token: str, get_url: str, max_wait_seconds: int = 600) -> dict:
    start = time.time()
    while True:
        result = _request_json(get_url, "GET", token)
        status = result.get("status")
        if status in {"succeeded", "failed", "canceled"}:
            return result
        if time.time() - start > max_wait_seconds:
            raise TimeoutError(f"Prediction did not finish in {max_wait_seconds}s")
        time.sleep(2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True, help="Path to reference image")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    args = parser.parse_args()

    token = os.getenv("REPLICATE_API_TOKEN")
    if not token:
        raise SystemExit("REPLICATE_API_TOKEN is required")

    ref_path = pathlib.Path(args.reference).expanduser().resolve()
    if not ref_path.exists():
        raise SystemExit(f"Reference image not found: {ref_path}")

    print(f"Uploading reference: {ref_path}")
    image_url = upload_file(token, ref_path)
    print(f"Uploaded URL: {image_url}")

    print(f"Creating prediction with model: {args.model}")
    pred = create_prediction(token, args.model, image_url, args.prompt)
    print(f"Prediction ID: {pred['id']}")

    result = wait_prediction(token, pred["urls"]["get"])
    print(f"Final status: {result['status']}")

    if result["status"] != "succeeded":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    output = result.get("output")
    if isinstance(output, list):
        for idx, item in enumerate(output, start=1):
            print(f"Output[{idx}]: {item}")
    else:
        print(f"Output: {output}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as e:
        details = e.read().decode("utf-8", errors="replace")
        print(f"HTTPError {e.code}: {details}")
        raise
