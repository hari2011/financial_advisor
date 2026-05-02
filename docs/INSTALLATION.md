# Installation Guide

Complete step-by-step installation for every platform. Choose **Option A** (automatic) or **Option B** (manual) based on your preference.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Option A — Automatic Setup (Recommended)](#option-a--automatic-setup-recommended)
- [Option B — Manual Setup](#option-b--manual-setup)
  - [macOS (Apple Silicon)](#macos-apple-silicon)
  - [macOS (Intel)](#macos-intel)
  - [Linux with NVIDIA GPU](#linux-with-nvidia-gpu)
  - [Linux with AMD GPU](#linux-with-amd-gpu)
  - [Linux CPU-Only](#linux-cpu-only)
  - [Windows with NVIDIA GPU](#windows-with-nvidia-gpu)
  - [Windows CPU-Only](#windows-cpu-only)
- [Air-Gapped / Offline Installation](#air-gapped--offline-installation)
- [Model Options](#model-options)
- [Verifying Your Installation](#verifying-your-installation)
- [Updating](#updating)
- [Uninstalling](#uninstalling)

---

## Prerequisites

| Requirement   | Details                                              |
|---------------|------------------------------------------------------|
| **Python**    | 3.10 or higher (check: `python3 --version`)          |
| **Disk Space**| ~8 GB free (code + model)                             |
| **RAM**       | 8 GB minimum, 16 GB+ recommended                     |
| **Internet**  | Needed for first-time model download (~5 GB)          |
| **GPU**       | Optional — app works on CPU. GPU gives 3-5x speed    |

### Supported GPUs

| GPU Type             | Framework | Supported? |
|----------------------|-----------|:----------:|
| Apple Silicon (M1-M4)| Metal     | ✅         |
| NVIDIA (RTX, GTX)   | CUDA      | ✅         |
| AMD (Radeon, RX)    | Vulkan    | ✅         |
| Intel ARC            | Vulkan    | ⚠️ Partial |
| No GPU / Integrated | CPU       | ✅         |

---

## Option A — Automatic Setup (Recommended)

The launcher script handles **everything** — no decisions required.

### Step 1: Download the project

```bash
git clone <repo-url>
cd financial_advisor
```

### Step 2: Run the launcher

```bash
python3 start.py
```

That's it. The script will:

```
  [1/5] Python 3.11.9 ✓
  [2/5] Creating virtual environment...
        Created at /path/to/financial_advisor/venv
  [3/5] Installing dependencies (one-time, may take a few minutes)...
        llama-cpp-python installed (METAL build) ✓
  [4/5] Downloading model (one-time, ~5 GB)...
  [5/5] Starting FinanceGPT server...

  ┌────────────────────────────────────────────────┐
  │  Open http://localhost:8501 in your browser     │
  │  Press Ctrl+C to stop the server                │
  └────────────────────────────────────────────────┘
```

### What `start.py` does automatically

| Step | What Happens | Time |
|------|-------------|------|
| 1. Python check | Verifies Python 3.10+ | Instant |
| 2. Virtual environment | Creates `venv/` folder with isolated Python | ~5s |
| 3. Dependencies | Installs all pip packages | ~1-2 min |
| 4. llama-cpp-python | Detects GPU → installs with correct build flags | ~1-5 min |
| 5. Model download | Downloads Qwen3-8B GGUF (~5 GB) | ~5-15 min |
| 6. Server launch | Starts FastAPI on port 8501 | ~10s |

**Second run onwards**: Steps 1-5 are skipped (everything cached). Server starts in ~10 seconds.

### If model download is rate-limited

HuggingFace may throttle large downloads. Set a free token:

```bash
# Get a free token at https://huggingface.co/settings/tokens

# macOS / Linux
export HF_TOKEN=hf_your_token_here
python3 start.py

# Windows PowerShell
$env:HF_TOKEN="hf_your_token_here"
python3 start.py
```

---

## Option B — Manual Setup

For users who prefer full control over each step.

### macOS (Apple Silicon)

Apple Silicon Macs (M1, M2, M3, M4) get GPU acceleration via Metal — no additional drivers needed.

```bash
# 1. Clone
git clone <repo-url>
cd financial_advisor

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install llama-cpp-python with Metal GPU support
CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python --force-reinstall --no-cache-dir

# 5. Download the model
python setup_model.py

# 6. Launch
python server.py
```

> **Build failing?** Install Xcode command line tools first: `xcode-select --install`

---

### macOS (Intel)

Intel Macs run in CPU mode. Still fully functional, just slower responses.

```bash
# 1. Clone
git clone <repo-url>
cd financial_advisor

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install llama-cpp-python (CPU mode)
pip install llama-cpp-python --force-reinstall --no-cache-dir

# 5. Download the model
python setup_model.py

# 6. Launch
python server.py
```

---

### Linux with NVIDIA GPU

Requires NVIDIA drivers + CUDA toolkit installed.

```bash
# 0. Verify CUDA is available
nvidia-smi        # Should show your GPU
nvcc --version    # Should show CUDA version

# 1. Clone
git clone <repo-url>
cd financial_advisor

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install llama-cpp-python with CUDA
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --force-reinstall --no-cache-dir

# 5. Download the model
python setup_model.py

# 6. Launch
python server.py
```

> **CUDA not found?** Install NVIDIA drivers + CUDA toolkit:
> ```bash
> # Ubuntu/Debian
> sudo apt install nvidia-driver-535 nvidia-cuda-toolkit
> # Fedora
> sudo dnf install akmod-nvidia xorg-x11-drv-nvidia-cuda
> ```

---

### Linux with AMD GPU

AMD GPUs use Vulkan for acceleration.

```bash
# 0. Verify Vulkan is available
vulkaninfo --summary    # Should show your GPU

# 1. Clone
git clone <repo-url>
cd financial_advisor

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install llama-cpp-python with Vulkan
CMAKE_ARGS="-DGGML_VULKAN=on" pip install llama-cpp-python --force-reinstall --no-cache-dir

# 5. Download the model
python setup_model.py

# 6. Launch
python server.py
```

> **Vulkan not found?** Install Vulkan SDK:
> ```bash
> # Ubuntu/Debian
> sudo apt install vulkan-tools libvulkan-dev
> # Fedora
> sudo dnf install vulkan-tools vulkan-loader-devel
> ```

---

### Linux CPU-Only

No GPU required. The app auto-detects CPU mode and optimizes accordingly.

```bash
# 0. Install build tools (needed to compile llama-cpp-python)
# Ubuntu/Debian:
sudo apt install build-essential cmake
# Fedora/RHEL:
sudo dnf install gcc-c++ cmake

# 1. Clone
git clone <repo-url>
cd financial_advisor

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install llama-cpp-python (CPU mode)
pip install llama-cpp-python --force-reinstall --no-cache-dir

# If build fails, try the pre-built wheel:
pip install llama-cpp-python --prefer-binary

# 5. Download the model
python setup_model.py

# 6. Launch
python server.py
```

---

### Windows with NVIDIA GPU

```powershell
# 0. Prerequisites
# - Python 3.10+ from python.org (check "Add to PATH" during install)
# - Visual Studio Build Tools (C++ workload): https://aka.ms/vs/17/release/vs_BuildTools.exe
# - CMake: https://cmake.org/download/
# - NVIDIA drivers + CUDA toolkit

# 1. Clone
git clone <repo-url>
cd financial_advisor

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install llama-cpp-python with CUDA
$env:CMAKE_ARGS="-DGGML_CUDA=on"
pip install llama-cpp-python --force-reinstall --no-cache-dir

# 5. Download the model
python setup_model.py

# 6. Launch
python server.py
```

---

### Windows CPU-Only

```powershell
# 0. Prerequisites
# - Python 3.10+ from python.org (check "Add to PATH")
# - Visual Studio Build Tools (C++ workload) OR use --prefer-binary

# 1. Clone
git clone <repo-url>
cd financial_advisor

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install llama-cpp-python
# Try pre-built wheel first (no compiler needed):
pip install llama-cpp-python --prefer-binary

# If that doesn't work (or you want optimal CPU performance):
pip install llama-cpp-python --force-reinstall --no-cache-dir

# 5. Download the model
python setup_model.py

# 6. Launch
python server.py
```

---

## Air-Gapped / Offline Installation

For environments with no internet access (corporate networks, secure systems).

### What you need to bring

On a machine **with** internet, download these files:

```bash
# 1. The project code (USB/network transfer)
git clone <repo-url>

# 2. Python packages (create an offline bundle)
cd financial_advisor
pip download -r requirements.txt -d ./pip_packages/
pip download llama-cpp-python -d ./pip_packages/

# 3. The model file (~5 GB)
python -c "
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='bartowski/Qwen_Qwen3-8B-GGUF',
    filename='Qwen_Qwen3-8B-Q5_K_M.gguf',  # or Q4_K_M for CPU
    local_dir='./models/'
)
"
```

Transfer the entire `financial_advisor/` folder to the air-gapped machine.

### On the air-gapped machine

```bash
cd financial_advisor

# Create venv
python3 -m venv venv
source venv/bin/activate    # or .\venv\Scripts\Activate.ps1 on Windows

# Install from local packages
pip install --no-index --find-links=./pip_packages/ -r requirements.txt
pip install --no-index --find-links=./pip_packages/ llama-cpp-python

# Launch (model is already in models/)
python server.py
```

### Using your own model (SafeTensors / PyTorch)

If you have a model in SafeTensors or PyTorch format instead of GGUF:

1. Place the model files in the `models/` directory
2. The app will **auto-detect** the format and **convert to GGUF** on first run
3. Conversion requires `transformers`, `torch`, and `gguf` packages (installed automatically if needed)

**Supported formats:**
- `.gguf` — Used directly (no conversion needed)
- `.safetensors` — Auto-converted to GGUF
- `.bin` / `.pth` — Auto-converted to GGUF (PyTorch format)

```
models/
├── config.json              # HuggingFace model config
├── tokenizer.json           # Tokenizer
├── model.safetensors        # Model weights (SafeTensors)
└── ...
```

The converter auto-selects quantization: Q5_K_M for GPU systems, Q4_K_M for CPU-only.

---

## Model Options

The app auto-selects the best model for your hardware, but you can override:

| Quantization | File Size | Quality    | Speed   | Best For |
|-------------|-----------|-----------|---------|----------|
| Q8_0        | ~8.5 GB   | Excellent | Slower  | 32 GB+ RAM, maximum accuracy |
| **Q5_K_M**  | **~5.5 GB** | **Very Good** | **Good** | **GPU systems (auto-selected)** |
| **Q4_K_M**  | **~4.6 GB** | **Good** | **Faster** | **CPU systems (auto-selected)** |
| Q3_K_M      | ~3.5 GB   | Reduced   | Fastest | Not recommended for finance |

### Using a different model

Edit `config.py`:

```python
MODEL_REPO = "bartowski/Qwen_Qwen3-8B-GGUF"   # HuggingFace repo
MODEL_FILE = "Qwen_Qwen3-8B-Q8_0.gguf"         # Override quantization
```

Or place any compatible GGUF file in the `models/` directory.

---

## Verifying Your Installation

### Quick health check

After launching, open a browser and visit:

```
http://localhost:8501/api/health
```

You should see:

```json
{
  "status": "ok",
  "llm_loaded": true,
  "agents": 10,
  "cache": { "response_cache_size": 0, "calculator_cache_size": 0 }
}
```

### Run the test suite

```bash
# Activate venv first
source venv/bin/activate      # macOS/Linux
# .\venv\Scripts\Activate.ps1  # Windows

# Run all 53 calculator accuracy tests
python test_cross_ref.py
```

Expected output:
```
53/53 cross-reference checks passed
```

### Check GPU detection

The startup banner shows your detected hardware:

```
╔══════════════════════════════════════════════════╗
║          FinanceGPT — System Detection           ║
╠══════════════════════════════════════════════════╣
║  OS          : Darwin (arm64)                    ║
║  RAM         : 18,432 MB (18 GB)                 ║
║  GPU Backend : METAL                             ║
║  GPU Name    : Apple M3 Pro                      ║
║  Context     : 24,576 tokens                     ║
║  Pipeline    : GPU-accelerated (full)            ║
╚══════════════════════════════════════════════════╝
```

If it shows `CPU` when you have a GPU, check llama-cpp-python was installed with the correct flags (Step 4 in manual setup).

---

## Updating

```bash
cd financial_advisor
git pull origin main

# Re-run launcher (it only installs what's new)
python3 start.py
```

Or manually:
```bash
source venv/bin/activate
pip install -r requirements.txt    # picks up new dependencies
python server.py                   # launch
```

---

## Uninstalling

```bash
# Remove the project (code + model + sessions)
rm -rf financial_advisor/

# Or keep code, just remove large files
rm -rf financial_advisor/models/
rm -rf financial_advisor/venv/
rm -rf financial_advisor/sessions/
```

No system-level changes are made — everything lives inside the project folder.
