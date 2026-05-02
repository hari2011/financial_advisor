"""
FinanceGPT — Model Format Detection & Conversion
==================================================

Supports loading models in any common format:
  1. GGUF (native, no conversion needed)
  2. SafeTensors (HuggingFace standard) → auto-converts to GGUF
  3. PyTorch .bin / .pth → auto-converts to GGUF

For air-gapped environments: place your model files in the models/ directory.
The app will auto-detect the format and convert to GGUF if needed.

Conversion requires: pip install transformers torch safetensors gguf sentencepiece
These are installed automatically when conversion is needed.
"""
import glob
import json
import logging
import os
import shutil
import subprocess
import sys

logger = logging.getLogger("financegpt.model_converter")


# ──────────────────────── Format Detection ────────────────────────

def detect_model_format(model_dir: str) -> dict:
    """Scan model_dir and detect what model files are available.

    Returns dict with:
        - "format": "gguf" | "safetensors" | "pytorch" | "none"
        - "files": list of matching files
        - "gguf_file": path to preferred GGUF file (if format is "gguf")
        - "hf_dir": path to HF model directory (if format is "safetensors" or "pytorch")
    """
    result = {"format": "none", "files": [], "gguf_file": None, "hf_dir": None}

    # 1. Check for GGUF files (preferred)
    gguf_files = sorted(glob.glob(os.path.join(model_dir, "*.gguf")))
    if gguf_files:
        # Prefer Q5_K_M > Q4_K_M > any other
        preferred = None
        for pref in ["Q5_K_M", "Q4_K_M", "Q6_K", "Q8_0", "Q4_K_S", "Q3_K_M"]:
            for f in gguf_files:
                if pref in f:
                    preferred = f
                    break
            if preferred:
                break
        if not preferred:
            preferred = gguf_files[0]  # Take whatever is there

        result["format"] = "gguf"
        result["files"] = gguf_files
        result["gguf_file"] = preferred
        return result

    # 2. Check for SafeTensors files
    # Could be directly in model_dir or in a subdirectory
    for search_dir in _find_model_subdirs(model_dir):
        st_files = glob.glob(os.path.join(search_dir, "*.safetensors"))
        if st_files:
            config_json = os.path.join(search_dir, "config.json")
            if os.path.exists(config_json):
                result["format"] = "safetensors"
                result["files"] = st_files
                result["hf_dir"] = search_dir
                return result

    # 3. Check for PyTorch .bin files
    for search_dir in _find_model_subdirs(model_dir):
        pt_files = glob.glob(os.path.join(search_dir, "*.bin"))
        pt_files += glob.glob(os.path.join(search_dir, "*.pth"))
        if pt_files:
            config_json = os.path.join(search_dir, "config.json")
            if os.path.exists(config_json):
                result["format"] = "pytorch"
                result["files"] = pt_files
                result["hf_dir"] = search_dir
                return result

    return result


def _find_model_subdirs(model_dir: str) -> list:
    """Find directories that might contain model files.
    Checks model_dir itself and one level of subdirectories."""
    dirs = [model_dir]
    try:
        for entry in os.scandir(model_dir):
            if entry.is_dir() and not entry.name.startswith("."):
                dirs.append(entry.path)
    except OSError:
        pass
    return dirs


def get_model_info(hf_dir: str) -> dict:
    """Read config.json to get model architecture info."""
    config_path = os.path.join(hf_dir, "config.json")
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


# ──────────────────────── Conversion ────────────────────────

def _ensure_conversion_deps(python_exe: str = None):
    """Install conversion dependencies if missing."""
    python_exe = python_exe or sys.executable
    deps = ["transformers", "torch", "safetensors", "gguf", "sentencepiece", "protobuf"]
    missing = []

    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)

    if not missing:
        return True

    logger.info(f"Installing conversion dependencies: {missing}")
    print(f"\n  Installing conversion tools: {', '.join(missing)}")
    print(f"  This is needed once to convert your model to GGUF format...")

    # For torch, use CPU-only to keep download small
    pip_deps = []
    for dep in missing:
        if dep == "torch":
            pip_deps.append("torch --index-url https://download.pytorch.org/whl/cpu")
        else:
            pip_deps.append(dep)

    cmd = [python_exe, "-m", "pip", "install", "-q"] + pip_deps
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Try installing one by one
        for dep in missing:
            if dep == "torch":
                subprocess.run(
                    [python_exe, "-m", "pip", "install", "-q",
                     "torch", "--index-url", "https://download.pytorch.org/whl/cpu"],
                    capture_output=True, text=True,
                )
            else:
                subprocess.run(
                    [python_exe, "-m", "pip", "install", "-q", dep],
                    capture_output=True, text=True,
                )

    # Verify
    for dep in missing:
        try:
            __import__(dep)
        except ImportError:
            logger.error(f"Failed to install {dep}")
            return False
    return True


def convert_to_gguf(hf_dir: str, output_dir: str,
                    quantization: str = "Q4_K_M") -> str | None:
    """Convert a HuggingFace model (safetensors/pytorch) to GGUF format.

    Args:
        hf_dir: Path to directory containing model files + config.json
        output_dir: Where to write the .gguf file
        quantization: Target quantization (Q4_K_M, Q5_K_M, Q8_0, etc.)

    Returns:
        Path to the output .gguf file, or None on failure.
    """
    if not _ensure_conversion_deps():
        print("\n  ✗ Cannot install conversion dependencies.")
        print("    Please install manually: pip install transformers torch safetensors gguf sentencepiece")
        return None

    # Read model config
    config = get_model_info(hf_dir)
    model_type = config.get("model_type", "unknown")
    model_name = os.path.basename(hf_dir.rstrip("/")) or "model"
    logger.info(f"Converting {model_type} model from {hf_dir}")

    # Determine output filename
    output_file = os.path.join(output_dir, f"{model_name}-{quantization}.gguf")
    if os.path.exists(output_file):
        logger.info(f"Converted model already exists: {output_file}")
        return output_file

    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Convert to FP16 GGUF first
    fp16_file = os.path.join(output_dir, f"{model_name}-f16.gguf")

    print(f"\n  Converting model to GGUF format...")
    print(f"    Source: {hf_dir}")
    print(f"    Model type: {model_type}")
    print(f"    Target: {quantization}")

    try:
        # Try using llama-cpp-python's built-in conversion if available
        success = _convert_with_llama_cpp(hf_dir, fp16_file)
        if not success:
            # Fall back to manual conversion via gguf library
            success = _convert_with_gguf_lib(hf_dir, fp16_file, config)

        if not success:
            print("  ✗ FP16 conversion failed")
            return None

        # Step 2: Quantize FP16 → target quantization
        if quantization != "f16":
            print(f"    Quantizing to {quantization}...")
            quantized = _quantize_gguf(fp16_file, output_file, quantization)
            # Clean up FP16 file (it's large)
            if quantized and os.path.exists(fp16_file):
                os.remove(fp16_file)
                logger.info(f"Removed intermediate FP16 file")
            if not quantized:
                # If quantization fails, use FP16 directly
                print(f"    ⚠ Quantization to {quantization} failed, using FP16")
                output_file = fp16_file
        else:
            output_file = fp16_file

        if os.path.exists(output_file):
            size_gb = os.path.getsize(output_file) / (1024 ** 3)
            print(f"  ✓ Conversion complete: {output_file} ({size_gb:.1f} GB)")
            return output_file
        else:
            print("  ✗ Conversion produced no output file")
            return None

    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        print(f"  ✗ Conversion failed: {e}")
        return None


def _convert_with_llama_cpp(hf_dir: str, output_file: str) -> bool:
    """Try converting using llama.cpp's convert script (if installed)."""
    # Look for convert_hf_to_gguf.py in common locations
    convert_script = shutil.which("convert_hf_to_gguf.py")

    # Also check if llama-cpp-python ships with it
    if not convert_script:
        try:
            import llama_cpp
            pkg_dir = os.path.dirname(llama_cpp.__file__)
            candidate = os.path.join(pkg_dir, "convert_hf_to_gguf.py")
            if os.path.exists(candidate):
                convert_script = candidate
        except ImportError:
            pass

    if not convert_script:
        # Try pip-installed llama-cpp package scripts
        for name in ["convert_hf_to_gguf", "convert-hf-to-gguf"]:
            path = shutil.which(name)
            if path:
                convert_script = path
                break

    if convert_script:
        logger.info(f"Using convert script: {convert_script}")
        result = subprocess.run(
            [sys.executable, convert_script, hf_dir,
             "--outfile", output_file, "--outtype", "f16"],
            capture_output=True, text=True, timeout=1800,
        )
        if result.returncode == 0 and os.path.exists(output_file):
            return True
        logger.warning(f"convert script failed: {result.stderr[:300]}")

    return False


def _convert_with_gguf_lib(hf_dir: str, output_file: str, config: dict) -> bool:
    """Convert using the gguf Python library + transformers directly.
    This is the fallback when llama.cpp convert script isn't available."""
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        print("    Loading model (this may take a few minutes)...")
        model = AutoModelForCausalLM.from_pretrained(
            hf_dir,
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
            trust_remote_code=False,
        )

        # Export to a temporary safetensors if needed, then use gguf writer
        # The cleanest path is to save as HF format and use convert script
        # Since we're already loaded, let's try the gguf write path

        # For now, save the model back to HF format (normalized) and retry convert
        temp_dir = output_file + ".tmp_hf"
        os.makedirs(temp_dir, exist_ok=True)
        model.save_pretrained(temp_dir, safe_serialization=True)

        # Copy tokenizer files
        for fname in os.listdir(hf_dir):
            if fname.startswith("tokenizer") or fname in ("special_tokens_map.json",
                                                           "vocab.json", "merges.txt",
                                                           "sentencepiece.bpe.model"):
                src = os.path.join(hf_dir, fname)
                dst = os.path.join(temp_dir, fname)
                if os.path.isfile(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)

        # Try convert script again with cleaned model
        success = _convert_with_llama_cpp(temp_dir, output_file)

        # Clean up temp
        shutil.rmtree(temp_dir, ignore_errors=True)
        del model
        if "torch" in sys.modules:
            torch.cuda.empty_cache() if torch.cuda.is_available() else None

        return success

    except Exception as e:
        logger.error(f"gguf lib conversion failed: {e}")
        return False


def _quantize_gguf(input_file: str, output_file: str, quant_type: str) -> bool:
    """Quantize a FP16 GGUF to a smaller quantization.
    Uses llama-quantize if available, otherwise keeps FP16."""
    # Look for llama-quantize binary
    quantize_bin = shutil.which("llama-quantize") or shutil.which("quantize")

    # Check in llama_cpp package directory
    if not quantize_bin:
        try:
            import llama_cpp
            pkg_dir = os.path.dirname(llama_cpp.__file__)
            for name in ["llama-quantize", "quantize"]:
                candidate = os.path.join(pkg_dir, name)
                if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                    quantize_bin = candidate
                    break
        except ImportError:
            pass

    if quantize_bin:
        logger.info(f"Quantizing with: {quantize_bin}")
        result = subprocess.run(
            [quantize_bin, input_file, output_file, quant_type],
            capture_output=True, text=True, timeout=1800,
        )
        if result.returncode == 0 and os.path.exists(output_file):
            return True
        logger.warning(f"Quantization failed: {result.stderr[:300]}")

    return False


# ──────────────────────── Main Discovery Flow ────────────────────────

def find_or_convert_model(model_dir: str, is_cpu_only: bool = False) -> str | None:
    """Main entry point: find a usable GGUF model, converting if necessary.

    Checks in order:
    1. GGUF files in model_dir → use directly
    2. SafeTensors/PyTorch in model_dir → convert to GGUF
    3. None found → return None (caller should download)

    Args:
        model_dir: Directory to search for models
        is_cpu_only: If True, prefer Q4_K_M; otherwise Q5_K_M

    Returns:
        Path to usable .gguf file, or None
    """
    detection = detect_model_format(model_dir)
    target_quant = "Q4_K_M" if is_cpu_only else "Q5_K_M"

    if detection["format"] == "gguf":
        gguf_file = detection["gguf_file"]
        size_gb = os.path.getsize(gguf_file) / (1024 ** 3)
        logger.info(f"Found GGUF model: {gguf_file} ({size_gb:.1f} GB)")
        return gguf_file

    if detection["format"] in ("safetensors", "pytorch"):
        hf_dir = detection["hf_dir"]
        fmt = detection["format"]
        n_files = len(detection["files"])
        logger.info(f"Found {fmt} model ({n_files} files) at {hf_dir}")
        print(f"\n  Found {fmt} model ({n_files} files) in {hf_dir}")
        print(f"  Converting to GGUF ({target_quant}) — this is a one-time operation...")

        return convert_to_gguf(hf_dir, model_dir, quantization=target_quant)

    return None
