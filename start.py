#!/usr/bin/env python3
"""
FinanceGPT — One-Command Launcher
==================================

Usage:  python start.py

This script handles EVERYTHING automatically:
  1. Checks Python version
  2. Creates virtual environment (if missing)
  3. Installs pip dependencies
  4. Installs llama-cpp-python with correct GPU flags
  5. Downloads the right model (Q5 for GPU, Q4 for CPU)
  6. Launches the server

The user never needs to touch config.py or run separate commands.
"""
import os
import sys
import platform
import subprocess
import shutil

# ──────────────────────── Constants ────────────────────────

MIN_PYTHON = (3, 10)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(PROJECT_DIR, "venv")
REQUIREMENTS = os.path.join(PROJECT_DIR, "requirements.txt")
SERVER_PY = os.path.join(PROJECT_DIR, "server.py")

SYSTEM = platform.system()
MACHINE = platform.machine()


# ──────────────────────── Helpers ────────────────────────

def print_banner():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║        FinanceGPT — One-Command Launcher         ║")
    print("╚══════════════════════════════════════════════════╝")
    print()


def print_step(n, msg):
    print(f"  [{n}/5] {msg}")


def run(cmd, **kwargs):
    """Run a command, printing it if verbose."""
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"\n  ✗ Command failed (exit {result.returncode}): {' '.join(cmd)}")
        if result.stderr:
            print(f"    {result.stderr[:500]}")
    return result


# ──────────────────────── Step 1: Python Check ────────────────────────

def check_python():
    v = sys.version_info
    if (v.major, v.minor) < MIN_PYTHON:
        print(f"  ✗ Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required, found {v.major}.{v.minor}.{v.micro}")
        sys.exit(1)
    print_step(1, f"Python {v.major}.{v.minor}.{v.micro} ✓")


# ──────────────────────── Step 2: Virtual Environment ────────────────────────

def ensure_venv():
    """Create venv if missing, return path to its python."""
    venv_python = os.path.join(VENV_DIR, "bin", "python")
    if SYSTEM == "Windows":
        venv_python = os.path.join(VENV_DIR, "Scripts", "python.exe")

    if os.path.exists(venv_python):
        print_step(2, "Virtual environment found ✓")
        return venv_python

    print_step(2, "Creating virtual environment...")
    result = run([sys.executable, "-m", "venv", VENV_DIR],
                 capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ Failed to create venv: {result.stderr[:300]}")
        sys.exit(1)
    print(f"       Created at {VENV_DIR}")
    return venv_python


# ──────────────────────── Step 3: Dependencies ────────────────────────

def install_deps(venv_python):
    """Install requirements.txt if not already satisfied."""
    # Quick check: can we import key packages?
    check = run(
        [venv_python, "-c", "import fastapi; import llama_cpp; import langgraph"],
        capture_output=True, text=True,
    )
    if check.returncode == 0:
        print_step(3, "Dependencies already installed ✓")
        return True  # llama_cpp already installed

    print_step(3, "Installing dependencies (one-time, may take a few minutes)...")

    # Upgrade pip first
    run([venv_python, "-m", "pip", "install", "-q", "--upgrade", "pip"],
        capture_output=True, text=True)

    # Install non-llama dependencies first (these never fail)
    # Create a temp requirements without llama-cpp-python
    import tempfile
    with open(REQUIREMENTS) as f:
        lines = f.readlines()
    non_llama = [l for l in lines if "llama" not in l.lower()]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp.writelines(non_llama)
        tmp_path = tmp.name

    result = run(
        [venv_python, "-m", "pip", "install", "-q", "-r", tmp_path],
        capture_output=True, text=True,
    )
    os.unlink(tmp_path)

    if result.returncode != 0:
        print(f"       ⚠ Some dependencies failed: {result.stderr[:200]}")

    # Now handle llama-cpp-python separately with robust fallback
    check = run([venv_python, "-c", "import llama_cpp"], capture_output=True, text=True)
    return check.returncode == 0


def install_llama_cpp(venv_python):
    """Install llama-cpp-python with robust fallback strategy.

    Strategy:
    1. Try pre-built binary wheel (fast, no compiler needed)
    2. Try source build with GPU flags
    3. Try source build without GPU flags (CPU fallback)
    4. On failure, print clear instructions
    """
    gpu = detect_gpu_quick()

    # ── Step A: Try pre-built wheel first (works on most platforms, no compiler needed) ──
    print(f"       Trying pre-built binary wheel...")
    result = run(
        [venv_python, "-m", "pip", "install", "-q", "llama-cpp-python", "--prefer-binary"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode == 0:
        check = run([venv_python, "-c", "import llama_cpp"], capture_output=True, text=True)
        if check.returncode == 0:
            print(f"       llama-cpp-python installed (pre-built wheel) ✓")
            if gpu != "cpu":
                print(f"       ⚠ Pre-built wheel may not have {gpu.upper()} support.")
                print(f"         For GPU acceleration, reinstall with:")
                _print_gpu_install_hint(gpu)
            return

    # ── Step B: Check build tools before attempting source build ──
    has_cmake = shutil.which("cmake") is not None
    has_compiler = (
        shutil.which("gcc") is not None
        or shutil.which("clang") is not None
        or shutil.which("cl") is not None  # MSVC on Windows
    )

    if not has_cmake or not has_compiler:
        missing = []
        if not has_cmake:
            missing.append("cmake")
        if not has_compiler:
            missing.append("C/C++ compiler")
        print(f"\n  ✗ Cannot build llama-cpp-python from source.")
        print(f"    Missing: {', '.join(missing)}\n")
        _print_build_tools_hint()
        sys.exit(1)

    # ── Step C: Source build with GPU flags ──
    env = os.environ.copy()
    pip_cmd = [venv_python, "-m", "pip", "install", "llama-cpp-python",
               "--force-reinstall", "--no-cache-dir"]

    if gpu == "metal":
        print(f"       Building with Metal GPU support (Apple Silicon)...")
        env["CMAKE_ARGS"] = "-DGGML_METAL=on"
    elif gpu == "cuda":
        print(f"       Building with CUDA GPU support...")
        env["CMAKE_ARGS"] = "-DGGML_CUDA=on"
    elif gpu == "vulkan":
        print(f"       Building with Vulkan GPU support...")
        env["CMAKE_ARGS"] = "-DGGML_VULKAN=on"
    else:
        print(f"       Building for CPU-only mode...")

    result = run(pip_cmd, env=env, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        # ── Step D: If GPU build failed, try plain CPU build as fallback ──
        if gpu != "cpu":
            print(f"       ⚠ {gpu.upper()} build failed, trying CPU-only fallback...")
            env.pop("CMAKE_ARGS", None)
            result = run(pip_cmd, env=env, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            print(f"\n  ✗ llama-cpp-python build failed.")
            print(f"    Error: {result.stderr[-300:] if result.stderr else 'unknown'}\n")
            _print_build_tools_hint()
            sys.exit(1)

    # Verify import
    check = run([venv_python, "-c", "import llama_cpp"], capture_output=True, text=True)
    if check.returncode != 0:
        print("  ✗ llama-cpp-python installed but import failed.")
        sys.exit(1)
    mode = gpu.upper() if gpu != "cpu" else "CPU"
    print(f"       llama-cpp-python installed ({mode} build) ✓")


def _print_gpu_install_hint(gpu):
    """Print GPU-specific reinstall command."""
    flag_map = {"metal": "-DGGML_METAL=on", "cuda": "-DGGML_CUDA=on", "vulkan": "-DGGML_VULKAN=on"}
    flag = flag_map.get(gpu, "")
    print(f"         CMAKE_ARGS=\"{flag}\" pip install llama-cpp-python --force-reinstall --no-cache-dir")


def _print_build_tools_hint():
    """Print platform-specific instructions for installing build tools."""
    if SYSTEM == "Darwin":
        print("    Install build tools:")
        print("      xcode-select --install")
        print("      brew install cmake  (if cmake is missing)")
    elif SYSTEM == "Linux":
        print("    Install build tools:")
        print("      sudo apt install build-essential cmake  (Debian/Ubuntu)")
        print("      sudo dnf install gcc-c++ cmake          (Fedora/RHEL)")
    elif SYSTEM == "Windows":
        print("    Install build tools:")
        print("      1. Visual Studio Build Tools (C++ workload)")
        print("      2. CMake: https://cmake.org/download/")
    print(f"\n    Then run: python start.py again")


# ──────────────────────── Step 4: Model Download ────────────────────────

def ensure_model(venv_python):
    """Ensure a model is available: check existing → convert local files → download.

    Supports air-gapped environments: place SafeTensors/PyTorch model files
    in the models/ directory and they will be auto-converted to GGUF format.
    """
    # Check if a GGUF model already exists via config
    check = run(
        [venv_python, "-c", """
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))
from config import MODEL_PATH
if os.path.exists(MODEL_PATH):
    print("EXISTS:" + MODEL_PATH)
else:
    print("MISSING:" + MODEL_PATH)
"""],
        capture_output=True, text=True, cwd=PROJECT_DIR,
    )

    output = check.stdout.strip()
    if "EXISTS:" in output:
        path = output.split("EXISTS:", 1)[1]
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print_step(4, f"Model ready ({size_mb / 1024:.1f} GB) ✓")
        return

    # Check if there are convertible model files in models/ directory
    models_dir = os.path.join(PROJECT_DIR, "models")
    if os.path.isdir(models_dir):
        convert_result = run(
            [venv_python, "-c", f"""
import sys, os
sys.path.insert(0, '{PROJECT_DIR}')
from tools.model_converter import find_or_convert_model
gpu = '{detect_gpu_quick()}'
is_cpu = (gpu == 'cpu')
result = find_or_convert_model('{models_dir}', is_cpu_only=is_cpu)
if result:
    print("CONVERTED:" + result)
else:
    print("NO_LOCAL_MODEL")
"""],
            capture_output=True, text=True, cwd=PROJECT_DIR,
        )

        conv_output = convert_result.stdout.strip()
        if "CONVERTED:" in conv_output:
            gguf_path = conv_output.split("CONVERTED:", 1)[1]
            size_mb = os.path.getsize(gguf_path) / (1024 * 1024) if os.path.exists(gguf_path) else 0
            print_step(4, f"Model converted to GGUF ({size_mb / 1024:.1f} GB) ✓")
            return

    print_step(4, "Downloading model (one-time, ~5 GB)...")
    result = run(
        [venv_python, "setup_model.py"],
        cwd=PROJECT_DIR,
    )
    if result.returncode != 0:
        print("  ✗ Model download failed. Check your internet connection.")
        print("    You can also set HF_TOKEN for rate limit issues:")
        print("    export HF_TOKEN=your_token && python start.py")
        sys.exit(1)


# ──────────────────────── Step 5: Launch Server ────────────────────────

def launch_server(venv_python):
    print_step(5, "Starting FinanceGPT server...")
    print()
    print("  ┌────────────────────────────────────────────────┐")
    print("  │  Open http://localhost:8501 in your browser     │")
    print("  │  Press Ctrl+C to stop the server                │")
    print("  └────────────────────────────────────────────────┘")
    print()

    try:
        os.execv(venv_python, [venv_python, SERVER_PY])
    except Exception as e:
        # Fallback
        subprocess.run([venv_python, SERVER_PY], cwd=PROJECT_DIR)


# ──────────────────────── GPU Detection (minimal) ────────────────────────

def detect_gpu_quick():
    """Quick GPU detection — no heavy imports needed."""
    if SYSTEM == "Darwin" and MACHINE == "arm64":
        return "metal"
    if SYSTEM == "Darwin":
        try:
            out = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=5,
            )
            if out.returncode == 0 and "Metal" in out.stdout:
                return "metal"
        except Exception:
            pass
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5,
            )
            if out.returncode == 0 and out.stdout.strip():
                return "cuda"
        except Exception:
            pass
    if shutil.which("vulkaninfo"):
        try:
            out = subprocess.run(
                ["vulkaninfo", "--summary"],
                capture_output=True, text=True, timeout=5,
            )
            if out.returncode == 0 and "deviceName" in out.stdout:
                return "vulkan"
        except Exception:
            pass
    return "cpu"


# ──────────────────────── Main ────────────────────────

def main():
    print_banner()

    # Step 1: Python version
    check_python()

    # Step 2: Virtual environment
    venv_python = ensure_venv()

    # Step 3: Dependencies (includes llama-cpp-python with GPU flags)
    llama_ok = install_deps(venv_python)
    if not llama_ok:
        install_llama_cpp(venv_python)

    # Step 4: Model download
    ensure_model(venv_python)

    # Step 5: Launch
    launch_server(venv_python)


if __name__ == "__main__":
    main()
