#!/usr/bin/env python3
# Copyright 2026 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Automated performance benchmark for Android Emulator dynamic display listener lifecycle.

Measures host CPU utilization and streaming telemetry across multiple scenarios:
  1. Direct gRPC Protobuf streaming (streamScreenshot).
  2. Zero-copy Shared Memory / MMAP streaming (ImageTransport.MMAP).
  3. Interactive / WebRTC live mode with real-time rolling terminal CPU timeline.
"""

import argparse
import glob
import os
import subprocess
import sys
import tempfile
import threading
import time

import grpc
from google.protobuf import empty_pb2
from aemu.discovery.emulator_discovery import EmulatorDiscovery
from aemu.proto.emulator_controller_pb2 import ImageFormat, ImageTransport
from aemu.proto.emulator_controller_pb2_grpc import EmulatorControllerStub

os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "0"


PACKAGE_NAME = "com.android.emulator.cube"
ACTIVITY_NAME = f"{PACKAGE_NAME}/.MainActivity"


def wait_for_emulator_boot(
    port: int, token: str | None = None, timeout_sec: float = 120.0
) -> bool:
    """Waits for the emulator gRPC server and guest Android OS to finish booting."""
    print(
        f"[*] Waiting up to {timeout_sec}s for emulator (port {port}) to complete Android boot...",
        end="",
        flush=True,
    )
    start_time = time.time()
    conn = EmulatorDiscovery.connection(f"localhost:{port}", token=token)
    with conn.client() as client:
        if not client.wait_for_ready(timeout=timeout_sec):
            print("\n[-] Error: Emulator gRPC server failed to become ready.")
            return False

        while time.time() - start_time < timeout_sec:
            try:
                status = client.controller.getStatus(empty_pb2.Empty(), timeout=1.0)
                if status.booted:
                    elapsed = time.time() - start_time
                    print(
                        f"\n[+] Emulator boot completed in {elapsed:.1f}s (uptime: {status.uptime}ms)!"
                    )
                    return True
            except Exception:
                pass
            print(".", end="", flush=True)
            time.sleep(1.0)

    print("\n[-] Error: Timed out waiting for emulator boot_completed.")
    return False


def wait_for_host_settled(
    pid: int, timeout_sec: float = 60.0, target_cpu: float = 240.0
) -> float:
    """Waits until host CPU utilization settles below target_cpu% (after Android OS package dexing/optimization)."""
    print(
        f"\n[*] Settling host process CPU (PID {pid}) below {target_cpu:.0f}% for up to {timeout_sec:.0f}s...",
        end="",
        flush=True,
    )
    start_time = time.time()
    last_cpu = 0.0
    while time.time() - start_time < timeout_sec:
        samples = sample_process_cpu(pid, duration_sec=1.5, interval_sec=0.5)
        if samples:
            avg_cpu = sum(samples) / len(samples)
            last_cpu = avg_cpu
            print(
                f"\r[*] Settling host CPU (PID {pid}): {avg_cpu:5.1f}% CPU (target < {target_cpu:.0f}%)   ",
                end="",
                flush=True,
            )
            if avg_cpu < target_cpu:
                print(f"\n[+] Host CPU settled at {avg_cpu:.1f}%!")
                return avg_cpu
        time.sleep(0.5)
    print(f"\n[!] Settled at {last_cpu:.1f}% CPU after {timeout_sec:.0f}s.")
    return last_cpu


def run_adb_cmd(adb_path: str, serial: str | None, args: list[str]) -> str:
    cmd = [adb_path]
    if serial:
        cmd.extend(["-s", serial])
    cmd.extend(args)
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


class GuestGfxStats:
    def __init__(
        self,
        fps: float = 0.0,
        jank_pct: float = 0.0,
        p50_ms: int = 0,
        p90_ms: int = 0,
        missed_vsync: int = 0,
    ):
        self.fps = fps
        self.jank_pct = jank_pct
        self.p50_ms = p50_ms
        self.p90_ms = p90_ms
        self.missed_vsync = missed_vsync


def reset_guest_gfxinfo(adb_path: str, serial: str | None, package: str):
    try:
        run_adb_cmd(adb_path, serial, ["shell", "dumpsys", "gfxinfo", package, "reset"])
        run_adb_cmd(adb_path, serial, ["logcat", "-c"])
    except Exception:
        pass


def collect_guest_gfxinfo(
    adb_path: str, serial: str | None, package: str, duration_sec: float
) -> GuestGfxStats:
    stats = GuestGfxStats()
    import re

    # 1. Read true GLSurfaceView 3D render FPS from RotatingCube logcat tag
    try:
        l_out = run_adb_cmd(adb_path, serial, ["logcat", "-d", "-s", "RotatingCube:D"])
        gl_fps_matches = [
            float(val) for val in re.findall(r"Rendering at ([\d.]+) FPS", l_out)
        ]
        if gl_fps_matches:
            stats.fps = sum(gl_fps_matches) / len(gl_fps_matches)
    except Exception:
        pass

    # 2. Read jank % and frame percentiles from dumpsys gfxinfo
    try:
        out = run_adb_cmd(adb_path, serial, ["shell", "dumpsys", "gfxinfo", package])
        if stats.fps == 0.0:
            m_frames = re.search(r"Total frames rendered:\s*(\d+)", out)
            if m_frames and duration_sec > 0:
                stats.fps = float(m_frames.group(1)) / duration_sec

        m_jank = re.search(r"Janky frames:\s*\d+\s*\(([\d.]+)%\)", out)
        if m_jank:
            stats.jank_pct = float(m_jank.group(1))

        m_p50 = re.search(r"50th percentile:\s*(\d+)ms", out)
        if m_p50:
            stats.p50_ms = int(m_p50.group(1))

        m_p90 = re.search(r"90th percentile:\s*(\d+)ms", out)
        if m_p90:
            stats.p90_ms = int(m_p90.group(1))

        m_vsync = re.search(r"Number Missed Vsync:\s*(\d+)", out)
        if m_vsync:
            stats.missed_vsync = int(m_vsync.group(1))
    except Exception:
        pass
    return stats


def discover_emulator() -> tuple[int | None, int | None, str | None]:
    """Discovers running emulator PID, gRPC port, and token using aemu-grpc."""
    discovery = EmulatorDiscovery()
    for emu in discovery._discover_running():
        try:
            pid = emu.pid()
            port = int(emu.get("grpc.port", 8554))
            token = emu.get("grpc.token", None)
            return pid, port, token
        except Exception:
            continue

    # Fallback to pgrep
    try:
        out = subprocess.check_output(["pgrep", "-f", "qemu-system"], text=True)
        pids = [int(p) for p in out.strip().splitlines() if p.isdigit()]
        if pids:
            return pids[0], 8554, None
    except Exception:
        pass

    return None, None, None


def sample_process_cpu(
    pid: int, duration_sec: float, interval_sec: float = 0.5
) -> list[float]:
    """Samples CPU utilization percentage of a target process over time."""
    samples: list[float] = []
    end_time = time.time() + duration_sec
    while time.time() < end_time:
        try:
            out = subprocess.check_output(
                ["ps", "-p", str(pid), "-o", "%cpu"], text=True
            )
            lines = [line.strip() for line in out.strip().splitlines() if line.strip()]
            if len(lines) >= 2:
                samples.append(float(lines[1]))
        except Exception:
            pass
        time.sleep(interval_sec)
    return samples


def render_sparkline_bar(cpu: float, max_cpu: float = 800.0, width: int = 30) -> str:
    """Renders a terminal bar visualization for CPU %."""
    filled = int(min(max(cpu / max_cpu, 0.0), 1.0) * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {cpu:5.1f}% CPU"


class GrpcStreamClient:
    """Client for running background gRPC streamScreenshot sessions."""

    def __init__(
        self,
        port: int,
        token: str | None = None,
        mode: str = "grpc",
        mmap_path: str | None = None,
    ):
        self.port = port
        self.token = token
        self.mode = mode
        self.mmap_path = mmap_path
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.frame_count = 0
        self.unique_frame_count = 0
        self.connection_startup_ms: float | None = None
        self.frame_latencies_ms: list[float] = []
        self.start_time: float | None = None
        self.stream = None
        self.error: Exception | None = None

    def start(self):
        self._stop_event.clear()
        self.frame_count = 0
        self.unique_frame_count = 0
        self.connection_startup_ms = None
        self.frame_latencies_ms = []
        self.start_time = time.time()
        self.error = None
        self.proc: subprocess.Popen | None = None
        self._thread = threading.Thread(target=self._run_stream, daemon=True)
        self._thread.start()

    def _run_stream(self):
        try:
            conn = EmulatorDiscovery.connection(
                f"localhost:{self.port}", token=self.token
            )
            with conn.client() as client:
                req = ImageFormat(format=ImageFormat.RGB888)
                if self.mode == "mmap" and self.mmap_path:
                    req.transport.CopyFrom(
                        ImageTransport(
                            channel=ImageTransport.MMAP,
                            handle=f"file://{self.mmap_path}",
                        )
                    )

                self.stream = client.controller.streamScreenshot(req)
                last_seq = None
                last_ts = None
                for frame in self.stream:
                    now = time.time()
                    if self._stop_event.is_set():
                        break
                    if self.connection_startup_ms is None and self.start_time:
                        self.connection_startup_ms = (now - self.start_time) * 1000.0

                    is_unique = (frame.seq != last_seq) or (
                        frame.timestampUs > 0 and frame.timestampUs != last_ts
                    )
                    last_seq = frame.seq
                    last_ts = frame.timestampUs
                    if is_unique:
                        self.unique_frame_count += 1

                    if frame.timestampUs > 0 and is_unique:
                        lat_ms = (now * 1_000_000.0 - frame.timestampUs) / 1000.0
                        if lat_ms > 0:
                            self.frame_latencies_ms.append(lat_ms)

                    self.frame_count += 1
        except Exception as e:
            self.error = e

    def stop(self) -> tuple[float, float, float, float]:
        self._stop_event.set()
        if self.stream:
            try:
                self.stream.cancel()
            except Exception:
                pass
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1.0)
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=2.0)
        if self.error and self.frame_count == 0:
            print(f"[!] GrpcStreamClient stream error: {self.error}")
        elapsed = time.time() - (self.start_time or time.time())
        fps = self.frame_count / elapsed if elapsed > 0 else 0.0
        unique_fps = self.unique_frame_count / elapsed if elapsed > 0 else 0.0
        avg_frame_lat = (
            sum(self.frame_latencies_ms) / len(self.frame_latencies_ms)
            if self.frame_latencies_ms
            else (1000.0 / unique_fps if unique_fps > 0 else 0.0)
        )
        startup_ms = self.connection_startup_ms or 0.0
        return fps, unique_fps, avg_frame_lat, startup_ms


def run_interactive_timeline(pid: int, stop_event: threading.Event):
    """Runs a continuous real-time CPU timeline."""
    print("\n[*] Starting Live CPU Monitor (Press [Enter] to advance/finish)...")
    while not stop_event.is_set():
        samples = sample_process_cpu(pid, 0.5, 0.5)
        if samples:
            cpu = samples[-1]
            bar = render_sparkline_bar(cpu)
            timestamp = time.strftime("%H:%M:%S")
            print(f"\r  [{timestamp}] {bar}", end="", flush=True)
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure emulator display streaming performance."
    )
    parser.add_argument("--adb", default="adb", help="Path to adb binary.")
    parser.add_argument("--serial", default=None, help="ADB device serial.")
    parser.add_argument("--apk", default=None, help="Path to rotating_cube.apk.")
    parser.add_argument("--pid", type=int, default=None, help="Emulator host PID.")
    parser.add_argument(
        "--grpc-port", type=int, default=None, help="Emulator gRPC port."
    )
    parser.add_argument(
        "--phase-duration",
        type=float,
        default=5.0,
        help="Duration (sec) per benchmark phase.",
    )
    parser.add_argument(
        "--scenario",
        choices=["grpc", "mmap", "interactive", "all"],
        default="all",
        help="Streaming simulation scenario to evaluate.",
    )
    args = parser.parse_args()

    disc_pid, disc_port, disc_token = discover_emulator()
    pid = args.pid or disc_pid
    port = args.grpc_port or disc_port or 8554

    if not pid:
        print(
            "[-] Error: Could not locate running emulator host process. Pass --pid explicitly.",
            file=sys.stderr,
        )
        return 1

    print(f"[*] Target Emulator Host PID: {pid} | gRPC Port: {port}")

    if not wait_for_emulator_boot(port, disc_token):
        print(
            "[-] Aborting benchmark: target emulator did not complete boot.",
            file=sys.stderr,
        )
        return 1

    # Install APK
    apk_path = args.apk
    if not apk_path:
        candidates = [
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "apps",
                "rotating_cube",
                "rotating_cube.apk",
            ),
            os.path.expanduser(
                "~/src/emu-main-next/bazel-bin/external/goldfish_test+/apps/rotating_cube/rotating_cube.apk"
            ),
            "bazel-bin/external/goldfish_test+/apps/rotating_cube/rotating_cube.apk",
        ]
        for cand in candidates:
            if os.path.isfile(cand):
                apk_path = cand
                break

    if apk_path and os.path.isfile(apk_path):
        print(f"[*] Installing workload APK: {apk_path}")
        run_adb_cmd(args.adb, args.serial, ["install", "-r", apk_path])
    else:
        print(
            "[!] Warning: rotating_cube.apk not found. Assuming already installed on guest device."
        )

    try:
        # Start rotating cube
        print("\n[*] Launching 60 FPS rotating cube guest workload...")
        run_adb_cmd(args.adb, args.serial, ["shell", "am", "force-stop", PACKAGE_NAME])
        run_adb_cmd(
            args.adb, args.serial, ["shell", "am", "start", "-W", "-n", ACTIVITY_NAME]
        )
        time.sleep(2.0)

        # Wait for host process CPU to settle after guest APK startup/dexing
        wait_for_host_settled(pid)

        # Baseline Phase 1: 0 Listeners
        print("\n=== Phase 1: Guest 60 FPS Active (0 Host Listeners) ===")
        reset_guest_gfxinfo(args.adb, args.serial, PACKAGE_NAME)
        print(f"[*] Sampling Phase 1 CPU for {args.phase_duration}s...")
        p1_samples = sample_process_cpu(pid, args.phase_duration)
        p1_avg = sum(p1_samples) / len(p1_samples) if p1_samples else 0.0
        p1_gfx = collect_guest_gfxinfo(
            args.adb, args.serial, PACKAGE_NAME, args.phase_duration
        )
        print(
            f"[+] Phase 1 Host CPU: {p1_avg:.1f}% | Guest App FPS: {p1_gfx.fps:.1f} | Guest Jank: {p1_gfx.jank_pct:.1f}%"
        )

        results = [
            (
                "Phase 1 (Guest 0 Listeners)",
                p1_avg,
                f"{p1_gfx.fps:.1f} FPS",
                f"{p1_gfx.jank_pct:.1f}%",
                "-",
                "-",
                "-",
            )
        ]

        scenarios_to_run = (
            ["mmap", "grpc"] if args.scenario == "all" else [args.scenario]
        )

        for sc in scenarios_to_run:
            if sc == "interactive":
                print("\n=== Interactive Scenario: WebRTC / Browser Stream ===")
                input(
                    "--> Start WebRTC/browser stream, then press [Enter] to begin sampling..."
                )
                p2_samples = sample_process_cpu(pid, args.phase_duration)
                p2_avg = sum(p2_samples) / len(p2_samples) if p2_samples else 0.0
                print(f"\n[+] Interactive Stream CPU: {p2_avg:.1f}%")
                input("--> Stop stream, then press [Enter] to measure post-teardown...")
                p3_samples = sample_process_cpu(pid, args.phase_duration)
                p3_avg = sum(p3_samples) / len(p3_samples) if p3_samples else 0.0
                print(f"[+] Post-Teardown CPU: {p3_avg:.1f}%")
                results.append(
                    ("Interactive WebRTC Stream", p2_avg, "Live", "-", "-", "-", "-")
                )
                results.append(("Post-Teardown Idle", p3_avg, "-", "-", "-", "-", "-"))

            elif sc in ("grpc", "mmap"):
                mmap_file = None
                if sc == "mmap":
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".img")
                    tmp.truncate(1920 * 1080 * 4 + 1024)
                    tmp.close()
                    mmap_file = tmp.name

                label = (
                    "gRPC MMAP Zero-Copy Stream"
                    if sc == "mmap"
                    else "gRPC Protobuf Pixel Stream"
                )
                print(f"\n=== Active Stream Scenario: {label} ===")
                reset_guest_gfxinfo(args.adb, args.serial, PACKAGE_NAME)
                client = GrpcStreamClient(
                    port=port, token=disc_token, mode=sc, mmap_path=mmap_file
                )
                client.start()

                print(
                    f"[*] Streaming active. Sampling CPU for {args.phase_duration}s..."
                )
                p2_samples = sample_process_cpu(pid, args.phase_duration)
                p2_avg = sum(p2_samples) / len(p2_samples) if p2_samples else 0.0
                fps, unique_fps, avg_frame_lat, startup_ms = client.stop()
                p2_gfx = collect_guest_gfxinfo(
                    args.adb, args.serial, PACKAGE_NAME, args.phase_duration
                )
                stream_fps_str = (
                    f"{unique_fps:.1f} ({fps:.0f})"
                    if abs(unique_fps - fps) > 1.0
                    else f"{unique_fps:.1f}"
                )
                print(
                    f"[+] {label} CPU: {p2_avg:.1f}% | Guest App: {p2_gfx.fps:.1f} FPS ({p2_gfx.jank_pct:.1f}% Jank) | Unique Frames Delivered: {unique_fps:.1f} FPS (poll rate: {fps:.0f}/s) | Frame Lat: {avg_frame_lat:.2f}ms"
                )

                # Sample post-teardown
                time.sleep(0.5)
                p3_samples = sample_process_cpu(pid, args.phase_duration)
                p3_avg = sum(p3_samples) / len(p3_samples) if p3_samples else 0.0
                print(f"[+] Post-Teardown Idle CPU: {p3_avg:.1f}%")

                results.append(
                    (
                        f"Active {label}",
                        p2_avg,
                        f"{p2_gfx.fps:.1f} FPS",
                        f"{p2_gfx.jank_pct:.1f}%",
                        f"{stream_fps_str} FPS",
                        f"{avg_frame_lat:.2f}ms",
                        f"{startup_ms:.1f}ms",
                    )
                )
                results.append(
                    (f"Post-Teardown ({label})", p3_avg, "-", "-", "-", "-", "-")
                )

                if mmap_file and os.path.exists(mmap_file):
                    os.remove(mmap_file)

        # Print Final Scorecard
        print("\n" + "=" * 115)
        print(
            "                                PERFORMANCE SUMMARY SCORECARD                                "
        )
        print("=" * 115)
        print(
            f"{'Scenario Phase':<30} | {'Host CPU %':<10} | {'Guest App FPS':<13} | {'Guest Jank':<10} | {'Stream FPS':<11} | {'Frame Lat':<10} | {'Startup TTFF':<12}"
        )
        print("-" * 115)
        for (
            name,
            cpu,
            g_fps,
            g_jank,
            s_fps,
            lat_str,
            ttff_str,
        ) in results:
            print(
                f"{name:<30} | {cpu:8.1f}%  | {g_fps:<13} | {g_jank:<10} | {s_fps:<11} | {lat_str:<10} | {ttff_str:<12}"
            )
        print("=" * 115)

    finally:
        print("\n[*] Stopping rotating cube guest workload...")
        run_adb_cmd(args.adb, args.serial, ["shell", "am", "force-stop", PACKAGE_NAME])
        print("[+] Benchmark complete.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
