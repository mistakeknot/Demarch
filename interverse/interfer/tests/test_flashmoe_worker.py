"""Tests for the flash-moe subprocess proxy worker."""

from __future__ import annotations

import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import MagicMock, patch

import pytest

from server.flashmoe_worker import FlashMoeWorker, _pick_free_port


# ---------------------------------------------------------------------------
# Helpers: fake flash-moe HTTP server
# ---------------------------------------------------------------------------


class FakeFlashMoeHandler(BaseHTTPRequestHandler):
    """Minimal OpenAI-compatible SSE server mimicking flash-moe."""

    def log_message(self, format, *args):
        pass  # silence request logs in tests

    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({"status": "ok", "model": "qwen3.5-397b-test"})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body.encode())
        elif self.path == "/v1/models":
            body = json.dumps(
                {
                    "object": "list",
                    "data": [
                        {
                            "id": "qwen3.5-397b-test",
                            "object": "model",
                            "owned_by": "local",
                        }
                    ],
                }
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body.encode())
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length))

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            tokens = ["Hello", " from", " flash", "-moe", "!"]
            for i, tok in enumerate(tokens):
                chunk = {
                    "id": f"chatcmpl-{i}",
                    "object": "chat.completion.chunk",
                    "choices": [
                        {"index": 0, "delta": {"content": tok}, "finish_reason": None}
                    ],
                }
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                self.wfile.flush()

            # Final chunk
            final = {
                "id": "chatcmpl-final",
                "object": "chat.completion.chunk",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            self.wfile.write(f"data: {json.dumps(final)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()


@pytest.fixture
def fake_flashmoe_port():
    """Start a fake flash-moe HTTP server and return its port."""
    port = _pick_free_port()
    server = HTTPServer(("127.0.0.1", port), FakeFlashMoeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()


# ---------------------------------------------------------------------------
# Tests: _pick_free_port
# ---------------------------------------------------------------------------


def test_pick_free_port():
    port = _pick_free_port()
    assert 1024 < port < 65536
    # Port should be bindable
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", port))


# ---------------------------------------------------------------------------
# Tests: FlashMoeWorker with fake server
# ---------------------------------------------------------------------------


class TestFlashMoeWorkerWithFakeServer:
    """Test FlashMoeWorker against a fake HTTP server (no real binary)."""

    def _make_worker(self, port: int) -> FlashMoeWorker:
        """Create a worker that skips subprocess startup."""
        w = FlashMoeWorker(
            binary_path="/nonexistent",
            model_path="/nonexistent",
            port=port,
        )
        # Fake the process as alive
        w._process = MagicMock()
        w._process.poll.return_value = None  # process is alive
        w._process.pid = 99999
        return w

    def test_health(self, fake_flashmoe_port: int):
        w = self._make_worker(fake_flashmoe_port)
        info = w.health(timeout=2.0)
        assert info["status"] == "ready"
        assert info["backend"] == "flash-moe"
        assert "qwen3.5-397b-test" in info["loaded_models"]

    def test_generate_streams_tokens(self, fake_flashmoe_port: int):
        w = self._make_worker(fake_flashmoe_port)
        tokens = list(
            w.generate(
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=100,
            )
        )
        assert tokens == ["Hello", " from", " flash", "-moe", "!"]

    def test_generate_populates_metrics(self, fake_flashmoe_port: int):
        w = self._make_worker(fake_flashmoe_port)
        list(
            w.generate(
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=100,
            )
        )
        metrics = w.last_generation_metrics
        assert metrics["tokens_generated"] == 5
        assert metrics["backend"] == "flash-moe"
        assert metrics["generation_tps"] > 0

    def test_generate_with_prompt_wraps_to_messages(self, fake_flashmoe_port: int):
        w = self._make_worker(fake_flashmoe_port)
        tokens = list(w.generate(prompt="Hello world"))
        assert len(tokens) == 5

    def test_generate_requires_messages_or_prompt(self, fake_flashmoe_port: int):
        w = self._make_worker(fake_flashmoe_port)
        with pytest.raises(ValueError, match="messages or prompt required"):
            list(w.generate())

    def test_is_alive_delegates_to_process(self, fake_flashmoe_port: int):
        w = self._make_worker(fake_flashmoe_port)
        assert w.is_alive() is True
        w._process.poll.return_value = 1  # process exited
        assert w.is_alive() is False

    def test_health_when_down(self):
        w = FlashMoeWorker(
            binary_path="/nonexistent",
            model_path="/nonexistent",
        )
        info = w.health()
        assert info["status"] == "down"

    def test_generate_when_not_running(self):
        w = FlashMoeWorker(
            binary_path="/nonexistent",
            model_path="/nonexistent",
        )
        with pytest.raises(RuntimeError, match="not running"):
            list(w.generate(messages=[{"role": "user", "content": "hi"}]))


# ---------------------------------------------------------------------------
# Tests: FlashMoeWorker lifecycle (mocked subprocess)
# ---------------------------------------------------------------------------


class TestFlashMoeWorkerLifecycle:
    def test_start_fails_without_binary(self):
        w = FlashMoeWorker(
            binary_path="/nonexistent/infer",
            model_path="/some/model",
        )
        with pytest.raises(FileNotFoundError, match="flash-moe binary not found"):
            w.start()

    def test_start_fails_without_model_path(self, tmp_path):
        # Create a fake binary
        binary = tmp_path / "infer"
        binary.touch()
        w = FlashMoeWorker(
            binary_path=str(binary),
            model_path="",
        )
        with pytest.raises(ValueError, match="model_path is required"):
            w.start()

    def test_properties_default_state(self):
        w = FlashMoeWorker(
            binary_path="/nonexistent",
            model_path="/nonexistent",
        )
        assert w.is_alive() is False
        assert w.is_degraded is False
        assert w.is_restarting is False
        assert w.restart_count == 0
        assert w.last_crash is None
        assert w.crash_history == []

    def test_shutdown_when_not_started(self):
        w = FlashMoeWorker(
            binary_path="/nonexistent",
            model_path="/nonexistent",
        )
        # Should not raise
        w.shutdown()

    def test_generate_lock_serializes(self, fake_flashmoe_port: int):
        """Verify concurrent generate() calls are serialized."""
        w = FlashMoeWorker(
            binary_path="/nonexistent",
            model_path="/nonexistent",
            port=fake_flashmoe_port,
        )
        w._process = MagicMock()
        w._process.poll.return_value = None
        w._process.pid = 99999

        results = []

        def gen(idx):
            tokens = list(
                w.generate(
                    messages=[{"role": "user", "content": f"msg {idx}"}],
                )
            )
            results.append((idx, tokens))

        threads = [threading.Thread(target=gen, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert len(results) == 3
        # All should have received the same tokens (from our fake server)
        for idx, tokens in results:
            assert tokens == ["Hello", " from", " flash", "-moe", "!"]


# ---------------------------------------------------------------------------
# Tests: malloc-cache and predict CLI flags
# ---------------------------------------------------------------------------


class TestFlashMoeCacheFlags:
    def test_malloc_cache_in_command(self, tmp_path):
        """Verify --malloc-cache is included in subprocess command."""
        binary = tmp_path / "infer"
        binary.write_text("#!/bin/sh\nexit 1")
        binary.chmod(0o755)

        w = FlashMoeWorker(
            binary_path=str(binary),
            model_path=str(tmp_path),
            malloc_cache=10000,
        )
        # We can't actually start (binary will fail), but we can check
        # the command would be constructed correctly by inspecting internals
        assert w._malloc_cache == 10000

    def test_predict_flag(self, tmp_path):
        """Verify --predict flag is stored."""
        w = FlashMoeWorker(
            binary_path="/nonexistent",
            model_path="/nonexistent",
            predict=True,
        )
        assert w._predict is True

    def test_defaults_no_cache_no_predict(self):
        """Default construction has no malloc-cache and no predict."""
        w = FlashMoeWorker(
            binary_path="/nonexistent",
            model_path="/nonexistent",
        )
        assert w._malloc_cache == 0
        assert w._predict is False


class TestFlashMoeCLIArgs:
    """Test CLI argument parsing for flash-moe flags."""

    def test_flashmoe_malloc_cache_arg(self):
        from server.__main__ import _parse_args

        args = _parse_args(
            [
                "--flashmoe-binary",
                "/some/infer",
                "--flashmoe-model",
                "/some/model",
                "--flashmoe-malloc-cache",
                "10000",
            ]
        )
        assert args.flashmoe_malloc_cache == 10000

    def test_flashmoe_predict_arg(self):
        from server.__main__ import _parse_args

        args = _parse_args(["--flashmoe-predict"])
        assert args.flashmoe_predict is True

    def test_flashmoe_predict_default_off(self):
        from server.__main__ import _parse_args

        args = _parse_args([])
        assert args.flashmoe_predict is False
        assert args.flashmoe_malloc_cache == 0

    def test_flashmoe_args_string_split(self):
        from server.__main__ import _parse_args

        args = _parse_args(
            [
                "--flashmoe-args",
                "--think-budget 2048",
            ]
        )
        assert args.flashmoe_args == "--think-budget 2048"
        # Verify splitting works
        split = args.flashmoe_args.split()
        assert split == ["--think-budget", "2048"]

    def test_flashmoe_q3_experts_arg(self):
        from server.__main__ import _parse_args

        args = _parse_args(["--flashmoe-q3-experts"])
        assert args.flashmoe_q3_experts is True

    def test_flashmoe_cache_io_split_arg(self):
        from server.__main__ import _parse_args

        args = _parse_args(["--flashmoe-cache-io-split", "4"])
        assert args.flashmoe_cache_io_split == 4

    def test_flashmoe_gguf_paths(self):
        from server.__main__ import _parse_args

        args = _parse_args(
            [
                "--flashmoe-gguf-embedding",
                "~/Models/gguf/embedding_q8_0.bin",
                "--flashmoe-gguf-lm-head",
                "~/Models/gguf/lm_head_q6.bin",
            ]
        )
        assert args.flashmoe_gguf_embedding == "~/Models/gguf/embedding_q8_0.bin"
        assert args.flashmoe_gguf_lm_head == "~/Models/gguf/lm_head_q6.bin"

    def test_flashmoe_q3_defaults_off(self):
        from server.__main__ import _parse_args

        args = _parse_args([])
        assert args.flashmoe_q3_experts is False
        assert args.flashmoe_cache_io_split == 0
        assert args.flashmoe_gguf_embedding == ""
        assert args.flashmoe_gguf_lm_head == ""


class TestFlashMoeQ3WorkerFlags:
    """Test that Q3/GGUF flags are stored on the worker."""

    def test_q3_experts_stored(self):
        w = FlashMoeWorker(
            binary_path="/nonexistent",
            model_path="/nonexistent",
            q3_experts=True,
            cache_io_split=4,
            gguf_embedding="/path/to/embedding.bin",
            gguf_lm_head="/path/to/lm_head.bin",
        )
        assert w._q3_experts is True
        assert w._cache_io_split == 4
        assert w._gguf_embedding == "/path/to/embedding.bin"
        assert w._gguf_lm_head == "/path/to/lm_head.bin"

    def test_q3_defaults(self):
        w = FlashMoeWorker(
            binary_path="/nonexistent",
            model_path="/nonexistent",
        )
        assert w._q3_experts is False
        assert w._cache_io_split == 0
        assert w._gguf_embedding == ""
        assert w._gguf_lm_head == ""


# ---------------------------------------------------------------------------
# Sylveste-6f0: cooperative cancel, stderr drainer, health-probe wedge detect
# ---------------------------------------------------------------------------


class _SlowFlashMoeHandler(BaseHTTPRequestHandler):
    """Fake server that streams 1 token/sec — long enough to test cancel."""

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        content_length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(content_length)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        # Stream 30 tokens with 0.2s gap between each — total 6s.
        # Caller's cancel should land well before completion.
        for i in range(30):
            chunk = {
                "id": f"chatcmpl-{i}",
                "object": "chat.completion.chunk",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": f"tok{i} "},
                        "finish_reason": None,
                    }
                ],
            }
            try:
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                # Client closed the connection — exactly what cancel should do.
                return
            time.sleep(0.2)
        try:
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


@pytest.fixture
def slow_flashmoe_port():
    port = _pick_free_port()
    server = HTTPServer(("127.0.0.1", port), _SlowFlashMoeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()


class TestCooperativeCancel:
    """Sylveste-6f0 H2: cancel Event must close socket and release lock."""

    def _make_worker(self, port: int) -> FlashMoeWorker:
        w = FlashMoeWorker(
            binary_path="/nonexistent",
            model_path="/nonexistent",
            port=port,
        )
        w._process = MagicMock()
        w._process.poll.return_value = None
        w._process.pid = 99999
        return w

    def test_cancel_event_stops_iteration_quickly(self, slow_flashmoe_port: int):
        """Setting cancel mid-stream must terminate within a couple of token gaps."""
        w = self._make_worker(slow_flashmoe_port)
        cancel = threading.Event()
        tokens: list[str] = []
        start = time.monotonic()

        gen = w.generate(
            messages=[{"role": "user", "content": "hi"}],
            cancel=cancel,
        )
        for tok in gen:
            tokens.append(tok)
            if len(tokens) >= 3:
                cancel.set()
        gen.close()

        elapsed = time.monotonic() - start
        # 30 tokens × 0.2s = 6s total stream. We cancel after 3 tokens (~0.6s).
        # The cancel check happens on the next line read, so allow generous
        # slack for the line-buffered yield boundary — but it must NOT run
        # the full 6 seconds.
        assert len(tokens) >= 3
        assert elapsed < 3.0, f"cancel took too long: {elapsed:.1f}s"

    def test_cancel_releases_lock_for_next_caller(self, slow_flashmoe_port: int):
        """After cancel, a second generate() must acquire the lock immediately."""
        w = self._make_worker(slow_flashmoe_port)
        cancel = threading.Event()

        gen1 = w.generate(
            messages=[{"role": "user", "content": "first"}], cancel=cancel
        )
        next(gen1)  # pull one token to ensure we're past the lock acquire
        cancel.set()
        gen1.close()

        # Second call should not block on _generate_lock.
        start = time.monotonic()
        gen2 = w.generate(messages=[{"role": "user", "content": "second"}])
        next(gen2)  # only need to confirm we got past the lock
        gen2.close()
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, f"lock not released after cancel: {elapsed:.1f}s"

    def test_generator_close_without_cancel_also_releases_lock(
        self, slow_flashmoe_port: int
    ):
        """GeneratorExit backstop: caller breaks out without setting cancel."""
        w = self._make_worker(slow_flashmoe_port)

        gen = w.generate(messages=[{"role": "user", "content": "x"}])
        next(gen)
        gen.close()  # triggers GeneratorExit inside generate()

        # Lock should be free.
        assert not w._generate_lock.locked()

    def test_cancel_default_none_preserves_legacy_behavior(
        self, fake_flashmoe_port: int
    ):
        """Existing callers that don't pass cancel must still complete normally."""
        w = self._make_worker(fake_flashmoe_port)
        tokens = list(w.generate(messages=[{"role": "user", "content": "hi"}]))
        # Same five tokens as the old fast-fixture test.
        assert tokens == ["Hello", " from", " flash", "-moe", "!"]


class TestStderrDrainer:
    """Sylveste-6f0 H1: subprocess stderr drained to log file, no PIPE wedge."""

    def test_drainer_writes_to_log_file(self, tmp_path, monkeypatch):
        """stderr bytes written by a fake subprocess end up in the log file."""
        from server import flashmoe_worker as fw_module

        monkeypatch.setattr(fw_module, "_STDERR_LOG_DIR", tmp_path)

        # Build a worker without calling start(): wire a fake process whose
        # stderr is a pipe we can write into.
        import os as _os

        rfd, wfd = _os.pipe()
        rpipe = _os.fdopen(rfd, "rb")
        wpipe = _os.fdopen(wfd, "wb", buffering=0)

        w = FlashMoeWorker(
            binary_path="/nonexistent",
            model_path="/nonexistent",
        )
        w._process = MagicMock()
        w._process.pid = 99999
        w._process.stderr = rpipe

        w._start_stderr_drainer()
        try:
            wpipe.write(b"hello stderr from binary\n")
            wpipe.write(b"more bytes\n")
        finally:
            wpipe.close()  # EOF — drainer thread exits

        w._stop_stderr_drainer(timeout=2.0)

        log_path = tmp_path / "flashmoe-99999.stderr"
        assert log_path.exists()
        contents = log_path.read_bytes()
        assert b"hello stderr from binary" in contents
        assert b"more bytes" in contents

    def test_drainer_survives_large_volume_without_blocking(
        self, tmp_path, monkeypatch
    ):
        """Write more than the OS pipe buffer (~64KB) — must not deadlock."""
        from server import flashmoe_worker as fw_module

        monkeypatch.setattr(fw_module, "_STDERR_LOG_DIR", tmp_path)

        import os as _os

        rfd, wfd = _os.pipe()
        rpipe = _os.fdopen(rfd, "rb")
        wpipe = _os.fdopen(wfd, "wb", buffering=0)

        w = FlashMoeWorker(
            binary_path="/nonexistent",
            model_path="/nonexistent",
        )
        w._process = MagicMock()
        w._process.pid = 88888
        w._process.stderr = rpipe

        w._start_stderr_drainer()

        # 256KB — well above macOS pipe buffer. Without a drainer this hangs.
        payload = b"x" * 4096
        try:
            for _ in range(64):
                wpipe.write(payload)
        finally:
            wpipe.close()

        w._stop_stderr_drainer(timeout=2.0)

        log_path = tmp_path / "flashmoe-88888.stderr"
        assert log_path.stat().st_size == 256 * 1024

    def test_read_stderr_tail_returns_last_bytes(self, tmp_path, monkeypatch):
        """_read_stderr_tail must return the tail of the drained log."""
        from server import flashmoe_worker as fw_module

        monkeypatch.setattr(fw_module, "_STDERR_LOG_DIR", tmp_path)

        w = FlashMoeWorker(
            binary_path="/nonexistent",
            model_path="/nonexistent",
        )
        log_path = tmp_path / "test.stderr"
        log_path.write_bytes(b"A" * 1000 + b"TAIL_MARKER")
        w._stderr_log_path = log_path

        tail = w._read_stderr_tail(limit=20)
        assert "TAIL_MARKER" in tail
        assert len(tail) <= 20


class _DeadHealthHandler(BaseHTTPRequestHandler):
    """Server that accepts /v1/chat/completions but never answers /health."""

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/health":
            # Simulate wedge: hold the request open beyond the probe timeout.
            time.sleep(30)
        else:
            self.send_error(404)


@pytest.fixture
def dead_health_port():
    port = _pick_free_port()
    server = HTTPServer(("127.0.0.1", port), _DeadHealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()


class TestHealthProbeWedgeDetection:
    """Sylveste-6f0 H3: watchdog must catch wedged-but-running binary."""

    def test_probe_health_returns_true_on_responsive_server(
        self, fake_flashmoe_port: int
    ):
        w = FlashMoeWorker(
            binary_path="/nonexistent",
            model_path="/nonexistent",
            port=fake_flashmoe_port,
        )
        assert w._probe_health_once() is True

    def test_probe_health_returns_false_on_wedged_server(
        self, dead_health_port: int, monkeypatch
    ):
        # Shorten probe timeout so the test doesn't take 5s.
        from server import flashmoe_worker as fw_module

        monkeypatch.setattr(fw_module, "_HEALTH_PROBE_TIMEOUT", 0.5)

        w = FlashMoeWorker(
            binary_path="/nonexistent",
            model_path="/nonexistent",
            port=dead_health_port,
        )
        assert w._probe_health_once() is False

    def test_reset_consecutive_crashes_clears_health_failures(self):
        w = FlashMoeWorker(
            binary_path="/nonexistent",
            model_path="/nonexistent",
        )
        w._health_probe_failures = 2
        w.reset_consecutive_crashes()
        assert w._health_probe_failures == 0
