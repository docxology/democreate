"""Real loopback HTTP transfers must not poison or replace model-cache files."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import ContentTooShortError

import pytest


@contextmanager
def _server(
    payload: bytes, *, reported: int | None = None, publish: Path | None = None
) -> Iterator[str]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if publish is not None:
                publish.write_bytes(b"earlier owner")
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload) if reported is None else reported))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/asset"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            raise RuntimeError("fixture HTTP server did not stop")


def test_interrupted_transfer_does_not_occupy_model_cache(tmp_path: Path) -> None:
    from democreate.narration._tts_kokoro import _download_kokoro_asset

    destination = tmp_path / "model.onnx"
    with _server(b"partial", reported=1000) as url:
        with pytest.raises(ContentTooShortError):
            _download_kokoro_asset(url, destination)
    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []


def test_complete_transfer_publishes_exact_bytes_without_temporary_files(tmp_path: Path) -> None:
    from democreate.narration._tts_kokoro import _download_kokoro_asset

    payload = b"deterministic transport fixture; not an actual neural model"
    destination = tmp_path / "model.onnx"
    with _server(payload) as url:
        _download_kokoro_asset(url, destination)
    assert destination.read_bytes() == payload
    assert list(tmp_path.iterdir()) == [destination]


def test_concurrent_model_publisher_is_preserved(tmp_path: Path) -> None:
    from democreate.narration._tts_kokoro import _download_kokoro_asset

    destination = tmp_path / "model.onnx"
    with _server(b"later download", publish=destination) as url:
        with pytest.raises(FileExistsError):
            _download_kokoro_asset(url, destination)
    assert destination.read_bytes() == b"earlier owner"
    assert list(tmp_path.iterdir()) == [destination]
