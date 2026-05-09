"""
FinanceGPT — Model & Dependency Setup
Downloads the platform-appropriate LLM model and provides install guidance.

GPU platforms (Metal/CUDA/Vulkan)  → Q5_K_M (~5.5 GB)  — best quality
CPU-only platforms (16 GB+ RAM)   → Q4_K_M (~4.6 GB)  — good quality
CPU-only platforms (<16 GB RAM)   → Q3_K_M (~3.9 GB)  — fastest CPU
"""
import os
import sys
import platform
import shutil
import subprocess


def detect_platform():
    """Detect platform and GPU availability."""
    system = platform.system()
    machine = platform.machine()
    gpu_backend = _detect_gpu_backend(system, machine)
    is_cpu_only = gpu_backend == "cpu"

    print(f"\n{'='*55}")
    print(f"  FinanceGPT Setup")
    print(f"  OS: {system} | Arch: {machine}")
    print(f"  GPU: {gpu_backend.upper()}" + (" (CPU-only mode)" if is_cpu_only else ""))
    print(f"{'='*55}\n")
    return system, machine, gpu_backend


def _detect_gpu_backend(system, machine):
    """Quick GPU detection for model selection."""
    # Apple Metal
    if system == "Darwin" and machine == "arm64":
        return "metal"
    if system == "Darwin":
        try:
            out = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=5,
            )
            if out.returncode == 0 and "Metal" in out.stdout:
                return "metal"
        except Exception:
            pass
    # NVIDIA CUDA
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
    # Vulkan (AMD/Intel)
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


def install_hint(system, machine):
    """Print the recommended llama-cpp-python install command."""
    print("─── llama-cpp-python Installation ───\n")
    if system == "Darwin" and machine == "arm64":
        print("  Apple Silicon detected — install with Metal GPU:")
        print('  CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python --force-reinstall --no-cache-dir\n')
    elif system == "Darwin":
        print("  Intel Mac detected — install CPU version:")
        print("  pip install llama-cpp-python --force-reinstall --no-cache-dir\n")
    elif system == "Linux":
        print("  Linux detected. Choose one:\n")
        print("  NVIDIA GPU (CUDA):")
        print('  CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --force-reinstall --no-cache-dir\n')
        print("  AMD GPU (Vulkan):")
        print('  CMAKE_ARGS="-DGGML_VULKAN=on" pip install llama-cpp-python --force-reinstall --no-cache-dir\n')
        print("  CPU only:")
        print("  pip install llama-cpp-python --force-reinstall --no-cache-dir\n")
    elif system == "Windows":
        print("  Windows detected. Choose one:\n")
        print("  NVIDIA GPU (CUDA) — from PowerShell:")
        print('  $env:CMAKE_ARGS="-DGGML_CUDA=on"; pip install llama-cpp-python --force-reinstall --no-cache-dir\n')
        print("  CPU only:")
        print("  pip install llama-cpp-python --force-reinstall --no-cache-dir\n")
    else:
        print("  Unknown platform — install CPU version:")
        print("  pip install llama-cpp-python\n")


def download_model(gpu_backend="cpu"):
    """Download the platform-appropriate LLM model from Hugging Face."""
    from config import MODEL_DIR

    model_repo = "bartowski/Qwen_Qwen3-8B-GGUF"
    is_cpu_only = gpu_backend == "cpu"

    if is_cpu_only:
        # Pick quantization based on available RAM
        try:
            import platform_setup
            ram_mb = platform_setup.get_total_ram_mb()
        except Exception:
            ram_mb = 16384  # assume 16 GB if detection fails

        if ram_mb < 16384:
            model_file = "Qwen_Qwen3-8B-Q3_K_M.gguf"
            quant_label = "Q3_K_M (CPU-fast, <16GB RAM)"
            size_label = "~3.9 GB"
        else:
            model_file = "Qwen_Qwen3-8B-Q4_K_M.gguf"
            quant_label = "Q4_K_M (CPU-optimized)"
            size_label = "~4.6 GB"
    else:
        model_file = "Qwen_Qwen3-8B-Q5_K_M.gguf"
        quant_label = "Q5_K_M (GPU-optimized)"
        size_label = "~5.5 GB"

    model_path = os.path.join(MODEL_DIR, model_file)

    print(f"  Platform     : {gpu_backend.upper()}")
    print(f"  Model        : Qwen3-8B {quant_label}")
    print(f"  Expected size: {size_label}\n")

    if os.path.exists(model_path):
        size_gb = os.path.getsize(model_path) / (1024 ** 3)
        print(f"✓ Model already exists at {model_path} ({size_gb:.1f} GB)")

        # Check if the OTHER model also exists (from a previous platform)
        other_file = "Qwen_Qwen3-8B-Q5_K_M.gguf" if is_cpu_only else "Qwen_Qwen3-8B-Q4_K_M.gguf"
        other_path = os.path.join(MODEL_DIR, other_file)
        if os.path.exists(other_path):
            other_gb = os.path.getsize(other_path) / (1024 ** 3)
            print(f"  ℹ  Other variant also found: {other_file} ({other_gb:.1f} GB)")
            print(f"     You can delete it to save disk space.")

        return model_path

    os.makedirs(MODEL_DIR, exist_ok=True)
    print(f"Downloading {model_file} from {model_repo}...")
    print(f"This is a one-time download ({size_label}). Please wait...\n")

    from huggingface_hub import hf_hub_download
    path = hf_hub_download(
        repo_id=model_repo,
        filename=model_file,
        local_dir=MODEL_DIR,
        local_dir_use_symlinks=False,
    )
    size_gb = os.path.getsize(path) / (1024 ** 3)
    print(f"\n✓ Model downloaded to {path} ({size_gb:.1f} GB)")
    return path


if __name__ == "__main__":
    system, machine, gpu_backend = detect_platform()

    if "--help" in sys.argv or "-h" in sys.argv:
        install_hint(system, machine)
        print("Usage:")
        print("  python setup_model.py          # Auto-detect platform & download model")
        print("  python setup_model.py --cpu     # Force CPU model (Q4_K_M or Q3_K_M by RAM)")
        print("  python setup_model.py --gpu     # Force GPU model (Q5_K_M)")
        print("  python setup_model.py --help    # Show install instructions")
        sys.exit(0)

    # Allow forcing model variant
    if "--cpu" in sys.argv:
        gpu_backend = "cpu"
        print("  ⚡ Forced CPU model\n")
    elif "--gpu" in sys.argv:
        gpu_backend = "gpu_override"
        print("  ⚡ Forced GPU model (Q5_K_M)\n")

    install_hint(system, machine)
    download_model(gpu_backend)
    print("\n✓ Setup complete! Run the app with: python server.py")
