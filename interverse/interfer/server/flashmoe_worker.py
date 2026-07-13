"""Flash-MoE worker: manages an external inference binary with its own HTTP API.

The flash-moe binary (a C++ executable) runs MoE models via mmap'd weights
with GPU-resident expert caching. This worker spawns the binary as a
subprocess and proxies inference requests to it via HTTP.

Unlike MetalWorker (which owns the Metal GPU via multiprocessing.Queue),
FlashMoeWorker communicates with its subprocess over HTTP since the binary
has its own server. The binary handles its own Metal context.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Generator

log = logging.getLogger("interfer.flashmoe_worker")

# Watchdog constants
_WATCHDOG_POLL_INTERVAL = 2.0
_MAX_CONSECUTIVE_RESTARTS = 3
_INITIAL_BACKOFF_S = 2.0
_MAX_BACKOFF_S = 30.0
_HEALTH_TIMEOUT = 5.0
_STARTUP_TIMEOUT = 30.0

# Health-probe liveness — catches wedged-but-running binary (Sylveste-6f0).
# Process-exit polling alone misses this failure mode; the binary stays alive
# but stops servicing /v1/chat/completions.
_HEALTH_PROBE_INTERVAL = 10.0
_HEALTH_PROBE_TIMEOUT = 5.0
_HEALTH_PROBE_MAX_FAILURES = 3
_STDERR_LOG_DIR = Path("~/.cache/interfer").expanduser()


class FlashMoeWorker:
    """Manages a flash-moe inference binary subprocess.

    The binary exposes an HTTP API for inference. This worker handles
    lifecycle management (start, shutdown, crash recovery) and proxies
    generate() calls to the binary's HTTP endpoint.

    Usage::

        worker = FlashMoeWorker(
            binary_path="/path/to/infer",
            model_path="/path/to/model",
        )
        worker.start()
        for token in worker.generate(model_name="flash-moe", messages=[...]):
            print(token, end="")
        worker.shutdown()
    """

    def __init__(
        self,
        binary_path: str,
        model_path: str,
        port: int = 0,
        extra_args: list[str] | None = None,
        malloc_cache: int = 0,
        predict: bool = False,
        q3_experts: bool = False,
        cache_io_split: int = 0,
        gguf_embedding: str = "",
        gguf_lm_head: str = "",
    ) -> None:
        self._binary_path = binary_path
        self._model_path = model_path
        self._port = port or _pick_free_port()
        self._extra_args = extra_args or []
        self._malloc_cache = malloc_cache
        self._predict = predict
        self._q3_experts = q3_experts
        self._cache_io_split = cache_io_split
        self._gguf_embedding = gguf_embedding
        self._gguf_lm_head = gguf_lm_head

        self._process: subprocess.Popen | None = None
        self._generate_lock = threading.Lock()
        self._last_metrics: dict[str, Any] = {}

        # Crash recovery state
        self._watchdog_thread: threading.Thread | None = None
        self._watchdog_stop = threading.Event()
        self._restart_count: int = 0
        self._consecutive_crashes: int = 0
        self._degraded = False
        self._is_restarting = False
        self._last_crash_time: float | None = None
        self._crash_history: list[dict[str, Any]] = []
        self._health_probe_failures: int = 0

        # Sylveste-6f0: drain the binary's stderr to a log file on a daemon
        # thread. Without this, stderr=PIPE fills its 64KB OS buffer after
        # enough binary output and the binary's write(2) blocks inside its
        # inference loop — invisible wedge that the exit-code watchdog cannot
        # detect.
        self._stderr_drainer: threading.Thread | None = None
        self._stderr_log_path: Path | None = None

    # -- lifecycle -----------------------------------------------------------

    def start(self) -> None:
        """Spawn the flash-moe binary subprocess."""
        if self._process is not None and self._process.poll() is None:
            raise RuntimeError("already running")

        if not os.path.isfile(self._binary_path):
            raise FileNotFoundError(f"flash-moe binary not found: {self._binary_path}")
        if not self._model_path:
            raise ValueError("model_path is required")

        cmd = [self._binary_path]

        # Model path args — binary expects --weights/--manifest/--vocab
        # or just positional model path depending on version
        if self._model_path:
            cmd.extend(["--model", self._model_path])

        cmd.extend(["--serve", str(self._port)])

        if self._malloc_cache > 0:
            cmd.extend(["--malloc-cache", str(self._malloc_cache)])

        if self._predict:
            cmd.append("--predict")

        if self._q3_experts:
            cmd.append("--q3-experts")

        if self._cache_io_split > 0:
            cmd.extend(["--cache-io-split", str(self._cache_io_split)])

        if self._gguf_embedding:
            cmd.extend(["--gguf-embedding", self._gguf_embedding])

        if self._gguf_lm_head:
            cmd.extend(["--gguf-lm-head", self._gguf_lm_head])

        cmd.extend(self._extra_args)

        # CWD must be the binary's parent directory so it can find shaders.metal
        binary_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(self._binary_path))
        )
        log.info("starting flash-moe: %s (cwd=%s)", " ".join(cmd), binary_dir)
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=binary_dir,
        )

        # Sylveste-6f0: drain stderr before anything that waits on the binary.
        # _wait_for_ready may need to read stderr on startup failure, so the
        # drainer captures output to a log file instead of leaving it queued
        # in the OS pipe buffer.
        self._start_stderr_drainer()

        # Wait for the HTTP API to become available
        self._wait_for_ready()

        # Reset crash counters on a clean start
        self._health_probe_failures = 0

        # Start watchdog
        if self._watchdog_thread is None:
            self._start_watchdog()

        log.info(
            "flash-moe started on port %d (pid %d, stderr=%s)",
            self._port,
            self._process.pid,
            self._stderr_log_path,
        )

    def _wait_for_ready(self, timeout: float = _STARTUP_TIMEOUT) -> None:
        """Poll the health endpoint until the binary is ready."""
        import urllib.request
        import urllib.error

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{self._port}/health",
                    method="GET",
                )
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        return
            except (urllib.error.URLError, OSError, TimeoutError):
                pass

            # Check if process died during startup
            if self._process is not None and self._process.poll() is not None:
                # Drainer owns the stderr pipe now; read the tail of the log
                stderr = self._read_stderr_tail(limit=500)
                raise RuntimeError(
                    f"flash-moe exited during startup (code {self._process.returncode}): "
                    f"{stderr}"
                )

            time.sleep(0.5)

        raise TimeoutError(f"flash-moe not ready after {timeout}s")

    def shutdown(self, timeout: float = 5.0) -> None:
        """Terminate the flash-moe subprocess."""
        self._stop_watchdog()

        if self._process is None or self._process.poll() is not None:
            self._process = None
            self._stop_stderr_drainer(timeout=1.0)
            return

        # Try graceful SIGTERM first
        self._process.terminate()
        try:
            self._process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait(timeout=2.0)

        self._process = None
        # Drainer's loop exits when the pipe closes (binary is gone now).
        self._stop_stderr_drainer(timeout=2.0)

    def is_alive(self) -> bool:
        """Return True if the binary subprocess is running."""
        return self._process is not None and self._process.poll() is None

    @property
    def is_degraded(self) -> bool:
        """True when max consecutive restarts exceeded."""
        return self._degraded

    @property
    def is_restarting(self) -> bool:
        """True during watchdog restart backoff."""
        return self._is_restarting

    @property
    def restart_count(self) -> int:
        """Total number of successful restarts."""
        return self._restart_count

    @property
    def last_crash(self) -> float | None:
        """Monotonic timestamp of most recent crash, or None."""
        return self._last_crash_time

    @property
    def crash_history(self) -> list[dict[str, Any]]:
        """List of crash records: {time, exit_code, consecutive}."""
        return list(self._crash_history)

    # -- commands ------------------------------------------------------------

    def health(self, timeout: float = _HEALTH_TIMEOUT) -> dict[str, Any]:
        """Query the binary's health endpoint.

        Returns a normalized dict with at least: status, backend, port,
        loaded_models.  Upstream formats are merged under these keys.
        """
        import urllib.error
        import urllib.request

        base = {"backend": "flash-moe", "port": self._port, "loaded_models": []}

        if not self.is_alive():
            return {**base, "status": "down"}

        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{self._port}/health",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
                # Upstream may provide model info under various keys
                data.pop("status", None)  # we set our own status
                models = data.pop("loaded_models", None)
                if models is None:
                    m = data.pop("model", None)
                    models = [m] if m else []
                return {**base, "status": "ready", "loaded_models": models, **data}
        except Exception as e:
            return {**base, "status": "error", "error": str(e)}

    def generate(
        self,
        model_name: str = "flash-moe",
        messages: list[dict] | None = None,
        prompt: str = "",
        max_tokens: int = 512,
        temperature: float = 0.7,
        timeout: float = 120.0,
        cancel: threading.Event | None = None,
    ) -> Generator[str, None, None]:
        """Stream tokens from the flash-moe binary via HTTP SSE.

        Yields decoded text segments. Concurrent calls are serialized.

        ``cancel``: optional Event. When set by the caller, the generator
        closes the underlying HTTP response and returns cleanly. Without
        this, breaking out of the for-loop leaves the socket read blocked
        and ``_generate_lock`` held — the Sylveste-6f0 wedge cascade.
        """
        import urllib.request
        import urllib.error

        with self._generate_lock:
            if not self.is_alive():
                raise RuntimeError("flash-moe not running")

            if messages is None and not prompt:
                raise ValueError("messages or prompt required")

            body = {
                "model": model_name,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
            }
            if messages is not None:
                body["messages"] = messages
            else:
                body["messages"] = [{"role": "user", "content": prompt}]

            req = urllib.request.Request(
                f"http://127.0.0.1:{self._port}/v1/chat/completions",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            self._last_metrics = {}
            token_count = 0
            t0 = time.monotonic()
            resp = None
            try:
                resp = urllib.request.urlopen(req, timeout=timeout)
                for line in resp:
                    if cancel is not None and cancel.is_set():
                        # Closing the response unblocks the socket read on
                        # this thread and signals the binary to abort.
                        try:
                            resp.close()
                        except Exception:
                            pass
                        return
                    line = line.decode().strip()
                    if not line or not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue

                    # Extract token from SSE chunk
                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            token_count += 1
                            yield content

                        # Capture finish metrics from final chunk
                        usage = chunk.get("usage")
                        if usage:
                            self._last_metrics.update(
                                {
                                    "generation_tps": usage.get("generation_tps", 0),
                                    "prompt_tps": usage.get("prompt_tps", 0),
                                    "peak_memory_gb": usage.get("peak_memory_gb", 0),
                                }
                            )

            except urllib.error.URLError as e:
                raise RuntimeError(f"flash-moe request failed: {e}") from e
            except GeneratorExit:
                # Caller broke out of the for-loop without setting cancel.
                # Close the response so the socket read unblocks now rather
                # than holding _generate_lock for the next caller.
                if resp is not None:
                    try:
                        resp.close()
                    except Exception:
                        pass
                raise
            finally:
                if resp is not None:
                    try:
                        resp.close()
                    except Exception:
                        pass
                elapsed = time.monotonic() - t0
                self._last_metrics["tokens_generated"] = token_count
                self._last_metrics["backend"] = "flash-moe"
                if "generation_tps" not in self._last_metrics and elapsed > 0:
                    self._last_metrics["generation_tps"] = token_count / elapsed

    @property
    def last_generation_metrics(self) -> dict:
        """Metrics from the most recent generate() call."""
        return self._last_metrics

    # -- watchdog ------------------------------------------------------------

    def _start_watchdog(self) -> None:
        self._watchdog_stop.clear()
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            daemon=True,
            name="interfer-flashmoe-watchdog",
        )
        self._watchdog_thread.start()

    def _stop_watchdog(self) -> None:
        self._watchdog_stop.set()
        if self._watchdog_thread is not None:
            self._watchdog_thread.join(timeout=5.0)
            self._watchdog_thread = None

    def _watchdog_loop(self) -> None:
        """Detect crashes and wedges, auto-restart with backoff.

        Two failure modes are distinguished:
          - exit-based: ``_process.poll()`` returns a code → binary died
          - wedge-based (Sylveste-6f0): binary is alive but ``/health``
            returns errors for ``_HEALTH_PROBE_MAX_FAILURES`` consecutive
            polls → binary is stuck inside its inference loop, SIGKILL it
            and let the exit-handling branch restart it on the next tick.
        """
        next_health_probe = time.monotonic() + _HEALTH_PROBE_INTERVAL
        while not self._watchdog_stop.is_set():
            self._watchdog_stop.wait(timeout=_WATCHDOG_POLL_INTERVAL)
            if self._watchdog_stop.is_set():
                break

            if self._degraded:
                continue

            # Wedge probe: skip if a generation holds the lock — a long
            # decode is not a wedge, and probing during one races with the
            # binary's HTTP handler thread for no benefit.
            if (
                self._process is not None
                and self._process.poll() is None
                and time.monotonic() >= next_health_probe
                and not self._generate_lock.locked()
            ):
                next_health_probe = time.monotonic() + _HEALTH_PROBE_INTERVAL
                if self._probe_health_once():
                    self._health_probe_failures = 0
                else:
                    self._health_probe_failures += 1
                    log.warning(
                        "flash-moe health probe failed (%d/%d)",
                        self._health_probe_failures,
                        _HEALTH_PROBE_MAX_FAILURES,
                    )
                    if self._health_probe_failures >= _HEALTH_PROBE_MAX_FAILURES:
                        log.error(
                            "flash-moe wedged — SIGKILL pid=%d to trigger restart",
                            self._process.pid,
                        )
                        self._health_probe_failures = 0
                        try:
                            self._process.kill()
                        except Exception as exc:
                            log.error("SIGKILL failed: %s", exc)
                        # Fall through to the exit-handling branch on the
                        # next tick once poll() observes the dead process.

            if self._process is not None and self._process.poll() is not None:
                self._consecutive_crashes += 1
                exit_code = self._process.returncode
                now = time.monotonic()
                self._last_crash_time = now
                self._crash_history.append(
                    {
                        "time": now,
                        "exit_code": exit_code,
                        "consecutive": self._consecutive_crashes,
                    }
                )
                log.warning(
                    "flash-moe crashed: exit_code=%s (consecutive: %d/%d)",
                    exit_code,
                    self._consecutive_crashes,
                    _MAX_CONSECUTIVE_RESTARTS,
                )

                if self._consecutive_crashes > _MAX_CONSECUTIVE_RESTARTS:
                    log.error("max restarts exceeded — entering degraded mode")
                    self._degraded = True
                    continue

                backoff = min(
                    _INITIAL_BACKOFF_S * (2 ** (self._consecutive_crashes - 1)),
                    _MAX_BACKOFF_S,
                )
                log.info("waiting %.1fs before restart", backoff)
                self._is_restarting = True
                self._watchdog_stop.wait(timeout=backoff)
                self._is_restarting = False
                if self._watchdog_stop.is_set():
                    break

                try:
                    self._process = None
                    self.start()
                    self._restart_count += 1
                except Exception as exc:
                    log.error("restart failed: %s", exc)

    def reset_consecutive_crashes(self) -> None:
        """Call after a successful request to reset the crash counter."""
        if self._consecutive_crashes > 0:
            self._consecutive_crashes = 0
        # A successful generation also clears any pending wedge suspicion.
        self._health_probe_failures = 0

    def _probe_health_once(self) -> bool:
        """Single /health round-trip. Returns True if the binary responds."""
        import urllib.error
        import urllib.request

        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{self._port}/health",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=_HEALTH_PROBE_TIMEOUT) as resp:
                return resp.status == 200
        except (urllib.error.URLError, OSError, TimeoutError):
            return False

    # -- stderr drainer ------------------------------------------------------
    #
    # Sylveste-6f0: stderr=subprocess.PIPE without a reader deadlocks the
    # binary once the OS pipe buffer (~64KB on macOS) fills. Drain on a
    # daemon thread to disk so forensic data survives without wedging the
    # subprocess.

    def _start_stderr_drainer(self) -> None:
        if self._process is None or self._process.stderr is None:
            return
        try:
            _STDERR_LOG_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            log.warning("failed to create stderr log dir %s: %s", _STDERR_LOG_DIR, exc)
            return
        self._stderr_log_path = _STDERR_LOG_DIR / f"flashmoe-{self._process.pid}.stderr"
        self._stderr_drainer = threading.Thread(
            target=self._drain_stderr_loop,
            args=(self._process.stderr, self._stderr_log_path),
            daemon=True,
            name=f"interfer-flashmoe-stderr-{self._process.pid}",
        )
        self._stderr_drainer.start()

    def _drain_stderr_loop(self, pipe: Any, log_path: Path) -> None:
        try:
            with open(log_path, "ab", buffering=0) as out:
                # Reading the underlying buffer in chunks avoids holding any
                # line longer than necessary and survives non-utf8 bytes.
                while True:
                    chunk = pipe.read(4096)
                    if not chunk:
                        return  # EOF — subprocess exited
                    out.write(chunk)
        except Exception as exc:
            log.warning("stderr drainer for %s exited: %s", log_path, exc)

    def _stop_stderr_drainer(self, timeout: float = 1.0) -> None:
        # The drainer exits naturally when the binary's stderr closes
        # (i.e. the process is gone). Just join so callers can rely on
        # the log file being flushed.
        if self._stderr_drainer is not None:
            self._stderr_drainer.join(timeout=timeout)
            self._stderr_drainer = None

    def _read_stderr_tail(self, limit: int = 500) -> str:
        """Return the tail of the drained stderr log, decoded best-effort."""
        if self._stderr_log_path is None:
            return ""
        try:
            with open(self._stderr_log_path, "rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - limit))
                return f.read().decode("utf-8", errors="replace")
        except FileNotFoundError:
            return ""
        except Exception as exc:
            return f"<stderr read failed: {exc}>"


def _pick_free_port() -> int:
    """Pick an ephemeral port that's currently free."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
