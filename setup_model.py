"""
FinanceGPT — Model & Dependency Setup
Downloads the LLM model and provides cross-platform installation guidance.
"""
import os
import sys
import platform


def detect_platform():
    """Print detected platform and recommended install commands."""
    system = platform.system()
    machine = platform.machine()
    print(f"\n{'='*55}")
    print(f"  FinanceGPT Setup")
    print(f"  OS: {system} | Arch: {machine}")
    print(f"{'='*55}\n")
    return system, machine


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


def download_model():
    """Download the LLM model from Hugging Face."""
    from config import MODEL_DIR, MODEL_REPO, MODEL_FILE, MODEL_PATH

    if os.path.exists(MODEL_PATH):
        size_gb = os.path.getsize(MODEL_PATH) / (1024 ** 3)
        print(f"✓ Model already exists at {MODEL_PATH} ({size_gb:.1f} GB)")
        return MODEL_PATH

    os.makedirs(MODEL_DIR, exist_ok=True)
    print(f"Downloading {MODEL_FILE} from {MODEL_REPO}...")
    print("This is a one-time download (~5.5 GB). Please wait...\n")

    from huggingface_hub import hf_hub_download
    path = hf_hub_download(
        repo_id=MODEL_REPO,
        filename=MODEL_FILE,
        local_dir=MODEL_DIR,
        local_dir_use_symlinks=False,
    )
    size_gb = os.path.getsize(path) / (1024 ** 3)
    print(f"\n✓ Model downloaded to {path} ({size_gb:.1f} GB)")
    return path


if __name__ == "__main__":
    system, machine = detect_platform()

    if "--help" in sys.argv or "-h" in sys.argv:
        install_hint(system, machine)
        print("Usage:")
        print("  python setup_model.py          # Download the model")
        print("  python setup_model.py --help    # Show install instructions")
        sys.exit(0)

    install_hint(system, machine)
    download_model()
    print("\n✓ Setup complete! Run the app with: python server.py")
