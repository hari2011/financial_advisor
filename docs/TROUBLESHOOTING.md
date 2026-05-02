# Troubleshooting Guide

Solutions for common issues when installing and running FinanceGPT.

---

## Table of Contents

- [Installation Issues](#installation-issues)
- [Startup Issues](#startup-issues)
- [Performance Issues](#performance-issues)
- [Runtime Issues](#runtime-issues)
- [Market Data Issues](#market-data-issues)
- [Calculator Issues](#calculator-issues)
- [GPU Issues](#gpu-issues)
- [Getting Help](#getting-help)

---

## Installation Issues

### llama-cpp-python fails to install

**Symptoms**: Build errors, cmake errors, compiler not found

**Cause**: Missing C/C++ build tools

**Fix by platform:**

| Platform | Command |
|----------|---------|
| **macOS** | `xcode-select --install` (installs Xcode command line tools) |
| **Ubuntu/Debian** | `sudo apt install build-essential cmake` |
| **Fedora/RHEL** | `sudo dnf install gcc-c++ cmake` |
| **Windows** | Install [Visual Studio Build Tools](https://aka.ms/vs/17/release/vs_BuildTools.exe) (select "C++ build tools" workload) + [CMake](https://cmake.org/download/) |

**Quick workaround** (no compiler needed):
```bash
pip install llama-cpp-python --prefer-binary
```
This installs a pre-built wheel. It may not have GPU support, but will work for CPU mode.

---

### pip install -r requirements.txt fails

**Symptoms**: Various dependency errors

**Common fixes:**

```bash
# Upgrade pip first
pip install --upgrade pip

# If specific packages fail, install the rest first
pip install fastapi uvicorn yfinance pandas numpy langgraph aiosqlite
pip install llama-cpp-python --prefer-binary
```

---

### Python version too old

**Symptoms**: `SyntaxError` or `Python 3.10+ required`

**Fix**: Install Python 3.11+ from [python.org](https://www.python.org/downloads/)

Check your version:
```bash
python3 --version
```

---

### venv creation fails

**Symptoms**: `Error: Command 'python3 -m venv' returned non-zero exit`

**Fix:**
```bash
# Ubuntu/Debian — install venv module
sudo apt install python3-venv

# macOS — ensure python3 is from python.org or homebrew
brew install python@3.11
```

---

## Startup Issues

### Model download fails

**Symptoms**: Timeout, rate limit, connection error during model download

**Fixes:**

1. **HuggingFace rate limit**: Get a free token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
   ```bash
   export HF_TOKEN=hf_your_token_here   # macOS/Linux
   $env:HF_TOKEN="hf_your_token_here"   # Windows PowerShell
   python3 start.py
   ```

2. **Slow connection**: The model is ~5 GB. On slow connections, try downloading manually:
   ```bash
   pip install huggingface-hub
   python -c "
   from huggingface_hub import hf_hub_download
   hf_hub_download(
       repo_id='bartowski/Qwen_Qwen3-8B-GGUF',
       filename='Qwen_Qwen3-8B-Q5_K_M.gguf',
       local_dir='models/'
   )
   "
   ```

3. **Behind a proxy**: Set proxy environment variables:
   ```bash
   export HTTPS_PROXY=http://proxy.company.com:8080
   python3 start.py
   ```

---

### Port 8501 already in use

**Symptoms**: `Address already in use` error

**Fix:**

```bash
# macOS / Linux — find and kill the process using port 8501
lsof -ti:8501 | xargs kill

# Windows
netstat -ano | findstr :8501
# Note the PID, then:
taskkill /PID <pid> /F
```

---

### ModuleNotFoundError

**Symptoms**: `ModuleNotFoundError: No module named 'fastapi'` (or similar)

**Cause**: Virtual environment not activated

**Fix:**
```bash
# Activate the venv first
source venv/bin/activate        # macOS/Linux
.\venv\Scripts\Activate.ps1     # Windows PowerShell

# Then run
python server.py
```

If using `start.py`, it handles the venv automatically.

---

### Model file not found

**Symptoms**: `FileNotFoundError` for model path

**Fixes:**

1. Check the `models/` directory exists and has a `.gguf` file:
   ```bash
   ls -la models/    # Should show a ~4-5 GB .gguf file
   ```

2. If empty, download the model:
   ```bash
   python setup_model.py
   ```

3. If you have a model with a different name, update `config.py`:
   ```python
   MODEL_FILE = "your-model-name.gguf"
   ```

---

## Performance Issues

### Responses are very slow on CPU

**Expected behavior**: CPU mode takes 15-40 seconds per response. This is normal for an 8B parameter model on CPU.

**Why it's slower than GPU**: CPUs process matrix multiplications sequentially, while GPUs process them in parallel. An Apple M3 Pro achieves ~20 tok/s on GPU vs ~8 tok/s on the same chip's CPU.

**Tips to speed up:**

| Tip | How | Speedup |
|-----|-----|---------|
| Use GPU | Already auto-detected — check startup banner | 3-5x |
| Reduce context | `LLM_CONFIG["n_ctx"] = 4096` in config.py | ~20% |
| Shorter responses | `RESPONSE_MAX_TOKENS = 1024` in config.py | Proportional |
| Close other apps | Free up RAM and CPU | Variable |

---

### Responses are slow even with GPU

**Check these:**

1. **Is GPU actually being used?** Check the startup banner:
   ```
   ║  GPU Backend : METAL                             ║
   ║  Pipeline    : GPU-accelerated (full)            ║
   ```
   If it shows `CPU`, llama-cpp-python wasn't compiled with GPU support. Reinstall:
   ```bash
   CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
   ```

2. **Is context window too large?** A 32K context window takes more time to process. For faster responses:
   ```python
   LLM_CONFIG["n_ctx"] = 16384
   ```

3. **First request is always slower**: The model needs to load into memory (~5-10 seconds). Subsequent requests are faster.

---

### Out of memory errors

**Symptoms**: Process killed, `OOM`, or system becomes unresponsive

**Fixes:**

```python
# In config.py — reduce memory usage:
LLM_CONFIG["n_ctx"] = 8192          # Smaller context window
LLM_CONFIG["n_gpu_layers"] = 20     # Partial GPU offload (instead of all)
```

Or use the smaller model:
```python
MODEL_FILE = "Qwen_Qwen3-8B-Q4_K_M.gguf"   # 4.6 GB instead of 5.5 GB
```

**RAM requirements:**

| Model | RAM Needed (approx) |
|-------|-------------------|
| Q4_K_M + 4K context | ~6 GB |
| Q4_K_M + 8K context | ~8 GB |
| Q5_K_M + 16K context | ~12 GB |
| Q5_K_M + 24K context | ~15 GB |
| Q5_K_M + 32K context | ~18 GB |

---

## Runtime Issues

### "LLM not loaded" error

**Cause**: Model failed to initialize

**Check:**
1. Model file exists in `models/` directory
2. Model file is not corrupted (re-download if < expected size)
3. Check server logs for initialization errors

---

### Responses contain incorrect ₹ amounts

**This should not happen** — calculator formulas are verified against production platforms.

If you suspect a calculation error:
```bash
python test_cross_ref.py
```

Expected: `53/53 cross-reference checks passed`

If any test fails, check `tools/financial_calc.py` for recent changes.

---

### Flash attention warning in logs

**Message**: `Flash attention not supported` or similar warning

**This is safe to ignore.** Flash attention requires specific llama-cpp-python build flags. The app falls back gracefully to standard attention with no impact on output quality — only a ~20% slower prefill speed.

---

## Market Data Issues

### Market data not loading / ticker empty

**Cause**: No internet connection, or yfinance API issues

**Fixes:**
1. Check internet: `ping google.com`
2. Check if yfinance works: `python -c "import yfinance; print(yfinance.Ticker('^NSEI').info.get('regularMarketPrice'))"`
3. Check firewall/proxy settings — yfinance needs access to `query1.finance.yahoo.com`

**Note**: The AI still works without market data — it just won't include live prices.

---

### Gold prices showing as 0 or N/A

**Cause**: COMEX gold futures (GC=F) or USD/INR (USDINR=X) fetch failed

**This resolves on its own** — yfinance occasionally has temporary API issues. The market prefetch retries every hour.

---

### Stock symbol not found

**Fix**: Use the correct suffix:
- NSE stocks: append `.NS` (e.g., `RELIANCE.NS`, `TCS.NS`)
- BSE stocks: append `.BO` (e.g., `RELIANCE.BO`)

---

## Calculator Issues

### Calculator returns unexpected result

1. Check inputs are in the correct units:
   - Amounts: in ₹ (not lakhs or crores)
   - Rates: as percentage (12, not 0.12)
   - Time: in years (not months)

2. Run the test suite to verify formulas:
   ```bash
   python test_cross_ref.py
   ```

---

### Calculator not found in grid

All 36 calculators should be visible. Try:
- Clear the search box
- Hard refresh the browser (`Cmd+Shift+R` / `Ctrl+Shift+R`)

---

## GPU Issues

### GPU detected but not used

**Symptoms**: Startup banner shows GPU, but inference is slow

**Cause**: llama-cpp-python compiled without GPU support

**Fix**: Reinstall with correct flags:

```bash
# Apple Silicon (Metal)
CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python --force-reinstall --no-cache-dir

# NVIDIA (CUDA)
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --force-reinstall --no-cache-dir

# AMD (Vulkan)
CMAKE_ARGS="-DGGML_VULKAN=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```

---

### CUDA out of memory

**Symptoms**: `CUDA out of memory` error

**Fix**: Reduce GPU memory usage:
```python
# In config.py:
LLM_CONFIG["n_gpu_layers"] = 20    # Partial offload instead of all layers
LLM_CONFIG["n_ctx"] = 8192         # Smaller context window
```

---

### Metal performance warnings

**Symptoms**: `Metal validation warning` messages in logs

**Safe to ignore.** These are diagnostic messages from Apple's Metal framework. They don't affect output quality or correctness.

---

## Getting Help

If none of the above resolves your issue:

1. **Check server logs**: Look at terminal output for error messages
2. **Run health check**: `curl http://localhost:8501/api/health`
3. **Run calculator tests**: `python test_cross_ref.py`
4. **Check hardware detection**: Look at the startup banner output
5. **Verify model**: `ls -la models/` should show a ~4-5 GB `.gguf` file
