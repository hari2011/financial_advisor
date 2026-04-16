"""
Cross-platform detection for FinanceGPT.
Auto-detects OS, architecture, GPU availability, and optimal settings.
Runs at import time — used by config.py and engine.py.
"""
import os
import platform
import shutil
import subprocess
import logging

logger = logging.getLogger("financegpt.platform")

# ──────────────────────── OS & Architecture ────────────────────────

SYSTEM = platform.system()          # "Darwin", "Linux", "Windows"
MACHINE = platform.machine()        # "arm64", "x86_64", "AMD64"
IS_MACOS = SYSTEM == "Darwin"
IS_LINUX = SYSTEM == "Linux"
IS_WINDOWS = SYSTEM == "Windows"
IS_ARM = MACHINE in ("arm64", "aarch64")
IS_X86 = MACHINE in ("x86_64", "AMD64", "x86")


# ──────────────────────── GPU Detection ────────────────────────

class GPUInfo:
    """Detected GPU capabilities."""

    def __init__(self):
        self.backend = "cpu"       # "metal", "cuda", "vulkan", "cpu"
        self.name = "CPU"
        self.vram_mb = 0
        self.layers = 0            # recommended n_gpu_layers

    def __repr__(self):
        return f"GPUInfo(backend={self.backend}, name={self.name}, vram={self.vram_mb}MB, layers={self.layers})"


def _detect_metal() -> GPUInfo | None:
    """Detect Apple Metal GPU on macOS."""
    if not IS_MACOS:
        return None
    try:
        out = subprocess.run(
            ["system_profiler", "SPDisplaysDataType"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and ("Metal" in out.stdout or "Apple" in out.stdout):
            info = GPUInfo()
            info.backend = "metal"
            # Extract chipset name
            for line in out.stdout.splitlines():
                line = line.strip()
                if "Chipset Model:" in line or "Chip:" in line:
                    info.name = line.split(":", 1)[1].strip()
                    break
            # Apple Silicon shares system RAM; estimate usable VRAM
            try:
                mem_out = subprocess.run(
                    ["sysctl", "-n", "hw.memsize"],
                    capture_output=True, text=True, timeout=3,
                )
                total_bytes = int(mem_out.stdout.strip())
                # ~75% of system RAM is usable by Metal on Apple Silicon
                info.vram_mb = int(total_bytes * 0.75 / (1024 * 1024))
            except Exception:
                info.vram_mb = 8192  # conservative fallback
            info.layers = -1  # offload all layers
            return info
    except Exception:
        pass
    return None


def _detect_cuda() -> GPUInfo | None:
    """Detect NVIDIA CUDA GPU."""
    # Check if nvidia-smi exists
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            parts = out.stdout.strip().split(",")
            info = GPUInfo()
            info.backend = "cuda"
            info.name = parts[0].strip()
            info.vram_mb = int(float(parts[1].strip())) if len(parts) > 1 else 4096
            # Estimate layers: ~0.5 GB per layer for 8B model
            # Q5_K_M ≈ 5.5 GB total, ~65 layers → ~85 MB/layer
            max_layers = min(65, int(info.vram_mb / 85))
            info.layers = -1 if info.vram_mb >= 6000 else max_layers
            return info
    except Exception:
        pass
    return None


def _detect_vulkan() -> GPUInfo | None:
    """Detect Vulkan GPU (AMD/Intel on Linux/Windows)."""
    if not shutil.which("vulkaninfo"):
        return None
    try:
        out = subprocess.run(
            ["vulkaninfo", "--summary"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and "deviceName" in out.stdout:
            info = GPUInfo()
            info.backend = "vulkan"
            for line in out.stdout.splitlines():
                if "deviceName" in line:
                    info.name = line.split("=")[-1].strip()
                    break
            info.vram_mb = 4096  # conservative default
            info.layers = 20    # partial offload for safety
            return info
    except Exception:
        pass
    return None


def detect_gpu() -> GPUInfo:
    """Auto-detect the best available GPU backend."""
    # Priority: Metal (macOS) > CUDA (NVIDIA) > Vulkan (AMD/Intel) > CPU
    for detector in [_detect_metal, _detect_cuda, _detect_vulkan]:
        result = detector()
        if result:
            return result
    return GPUInfo()  # CPU fallback


# ──────────────────────── System Resources ────────────────────────

def get_total_ram_mb() -> int:
    """Get total system RAM in MB."""
    try:
        if IS_MACOS:
            out = subprocess.run(["sysctl", "-n", "hw.memsize"],
                                 capture_output=True, text=True, timeout=3)
            return int(out.stdout.strip()) // (1024 * 1024)
        elif IS_LINUX:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) // 1024  # kB to MB
        elif IS_WINDOWS:
            out = subprocess.run(
                ["wmic", "ComputerSystem", "get", "TotalPhysicalMemory"],
                capture_output=True, text=True, timeout=5,
            )
            for line in out.stdout.strip().splitlines():
                line = line.strip()
                if line.isdigit():
                    return int(line) // (1024 * 1024)
    except Exception:
        pass
    return 8192  # 8 GB fallback


def get_cpu_count() -> int:
    """Get number of CPU cores (physical)."""
    try:
        count = os.cpu_count() or 4
        # Leave some cores for system — use ~70%
        return max(2, int(count * 0.7))
    except Exception:
        return 4


# ──────────────────────── Optimal Config ────────────────────────

def compute_optimal_config(gpu: GPUInfo, ram_mb: int, cpu_threads: int) -> dict:
    """Compute optimal LLM config based on detected hardware."""

    # Context window: scale with available memory
    if ram_mb >= 32768:
        n_ctx = 32768       # 32K for 32GB+ RAM
    elif ram_mb >= 16384:
        n_ctx = 24576       # 24K for 16GB+ RAM
    elif ram_mb >= 10240:
        n_ctx = 16384       # 16K for 10GB+ RAM
    else:
        n_ctx = 8192        # 8K for <10 GB

    # GPU layers
    n_gpu_layers = gpu.layers

    # Max tokens: scale with context
    max_tokens = 4096 if n_ctx >= 16384 else 2048

    return {
        "n_ctx": n_ctx,
        "n_gpu_layers": n_gpu_layers,
        "n_threads": cpu_threads,
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 20,
        "max_tokens": max_tokens,
        "repeat_penalty": 1.15,
    }


# ──────────────────────── Run Detection ────────────────────────

# These are computed once at import time and cached
GPU = detect_gpu()
TOTAL_RAM_MB = get_total_ram_mb()
CPU_THREADS = get_cpu_count()
OPTIMAL_CONFIG = compute_optimal_config(GPU, TOTAL_RAM_MB, CPU_THREADS)


def print_system_info():
    """Pretty-print detected system info (called at startup)."""
    lines = [
        "╔══════════════════════════════════════════════════╗",
        "║          FinanceGPT — System Detection           ║",
        "╠══════════════════════════════════════════════════╣",
        f"║  OS          : {SYSTEM} ({MACHINE})",
        f"║  RAM         : {TOTAL_RAM_MB:,} MB ({TOTAL_RAM_MB // 1024} GB)",
        f"║  CPU Threads : {CPU_THREADS}",
        f"║  GPU Backend : {GPU.backend.upper()}",
        f"║  GPU Name    : {GPU.name}",
        f"║  GPU VRAM    : {GPU.vram_mb:,} MB" if GPU.vram_mb else "║  GPU VRAM    : N/A (CPU mode)",
        f"║  GPU Layers  : {GPU.layers} (-1 = all)",
        "╠══════════════════════════════════════════════════╣",
        f"║  Context     : {OPTIMAL_CONFIG['n_ctx']:,} tokens",
        f"║  Max Output  : {OPTIMAL_CONFIG['max_tokens']:,} tokens",
        f"║  Threads     : {OPTIMAL_CONFIG['n_threads']}",
        "╚══════════════════════════════════════════════════╝",
    ]
    for line in lines:
        # Pad to fixed width
        if not line.startswith("╔") and not line.startswith("╠") and not line.startswith("╚"):
            line = line.ljust(51) + "║"
        logger.info(line)


# Auto-detect and print on first import from server
if os.environ.get("FINANCEGPT_STARTUP") == "1":
    print_system_info()
