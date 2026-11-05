"""Parent-owned Windows Job launcher for the isolated SDK fixture runner."""
import json
import os
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import threading
import time

from .auth import PublicError
from .worker_runtime import ROOT, WindowsJob


@dataclass(frozen=True)
class SdkProcessLimits:
    memory_bytes: int = 1024 * 1024 * 1024
    job_memory_bytes: int = 2 * 1024 * 1024 * 1024
    cpu_seconds: int = 120
    wall_seconds: int = 300
    processes: int = 10
    output_bytes: int = 2 * 1024 * 1024
    log_bytes: int = 250 * 1024


def run_sdk_process(config_path: Path, output_path: Path, stdout_path: Path, stderr_path: Path, env: dict[str, str], limits: SdkProcessLimits | None = None, cancel_event: threading.Event | None = None) -> dict:
    """Run only this new process tree in a Job; never attach to an existing PID."""
    limits = limits or SdkProcessLimits()
    if os.name != "nt":
        raise PublicError(503, "SDK_ISOLATION_UNAVAILABLE", "当前fixture只在已验证的Windows Job环境运行。")
    job = WindowsJob(limits)
    process = None
    timed_out = False
    cancelled = False
    peak_processes = 0
    try:
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            env = dict(env)
            env["SDK_RUNNER_JOB"] = "1"
            process = subprocess.Popen(
                [sys.executable, "-I", "-m", "data_workspace.sdk_runner_entry", str(config_path), str(output_path)],
                cwd=ROOT,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            job.assign(process)
            deadline = time.monotonic() + limits.wall_seconds
            while True:
                try:
                    returncode = process.wait(timeout=0.05)
                    break
                except subprocess.TimeoutExpired:
                    peak_processes = max(peak_processes, len(job.job.QueryInformationJobObject(job.handle, job.job.JobObjectBasicProcessIdList)))
                    if cancel_event is not None and cancel_event.is_set():
                        cancelled = True
                        job.stop()
                        returncode = process.wait(timeout=5)
                        break
                    if time.monotonic() >= deadline:
                        timed_out = True
                        job.stop()
                        returncode = process.wait(timeout=5)
                        break
        for path in (stdout_path, stderr_path):
            if path.stat().st_size > limits.log_bytes:
                raise PublicError(503, "SDK_LOG_LIMIT", "runner日志超过上限，未继续读取。")
        result = None
        if output_path.is_file():
            if output_path.stat().st_size > limits.output_bytes:
                raise PublicError(503, "SDK_OUTPUT_LIMIT", "runner输出超过上限。")
            result = json.loads(output_path.read_text(encoding="utf-8"))
        accounting = job.job.QueryInformationJobObject(job.handle, job.job.JobObjectBasicAccountingInformation)
        extended = job.job.QueryInformationJobObject(job.handle, job.job.JobObjectExtendedLimitInformation)
        process_ids = job.job.QueryInformationJobObject(job.handle, job.job.JobObjectBasicProcessIdList)
        return {
            "returncode": returncode,
            "timed_out": timed_out,
            "cancelled": cancelled,
            "result": result,
            "job_cpu_100ns": accounting["TotalUserTime"] + accounting["TotalKernelTime"],
            "job_process_limit": limits.processes,
            "job_active_processes": len(process_ids),
            "job_peak_processes": max(peak_processes, len(process_ids)),
            "job_peak_memory_bytes": extended.get("PeakJobMemoryUsed"),
            "process_peak_memory_bytes": extended.get("PeakProcessMemoryUsed"),
            "job_memory_limit": limits.job_memory_bytes,
            "process_memory_limit": limits.memory_bytes,
            "wall_seconds": limits.wall_seconds,
        }
    finally:
        try:
            if job.handle is not None:
                job.stop()
        finally:
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            job.close()
