"""LLM inference engine using llama-cpp-python with Metal acceleration."""
import os
import re
import time
import logging
from llama_cpp import Llama
from config import MODEL_PATH, LLM_CONFIG, MODEL_DIR, MODEL_REPO, MODEL_FILE

logger = logging.getLogger("financegpt.llm")


def _strip_think_tags(text: str) -> str:
    """Strip Qwen3 <think>...</think> blocks from output.
    In non-thinking mode Qwen3 may still emit empty think blocks."""
    return re.sub(r'<think>.*?</think>\s*', '', text, flags=re.DOTALL).strip()


class LLMEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def _ensure_model(self):
        if os.path.exists(MODEL_PATH):
            logger.info(f"Model found at {MODEL_PATH}")
            return
        os.makedirs(MODEL_DIR, exist_ok=True)
        logger.info(f"Downloading {MODEL_FILE} (~4.9 GB one-time download)...")
        from huggingface_hub import hf_hub_download
        hf_hub_download(
            repo_id=MODEL_REPO,
            filename=MODEL_FILE,
            local_dir=MODEL_DIR,
            local_dir_use_symlinks=False,
        )
        logger.info("Model downloaded successfully.")

    def initialize(self):
        if self._initialized:
            return
        self._ensure_model()
        from platform_setup import GPU, print_system_info
        print_system_info()
        backend_label = GPU.backend.upper() if GPU.backend != "cpu" else "CPU-only"
        logger.info(f"Loading LLM ({backend_label}, {LLM_CONFIG['n_gpu_layers']} GPU layers, "
                     f"ctx={LLM_CONFIG['n_ctx']}, threads={LLM_CONFIG['n_threads']})...")
        t0 = time.time()
        self.model = Llama(
            model_path=MODEL_PATH,
            n_ctx=LLM_CONFIG["n_ctx"],
            n_gpu_layers=LLM_CONFIG["n_gpu_layers"],
            n_threads=LLM_CONFIG["n_threads"],
            verbose=False,
        )
        self._initialized = True
        logger.info(f"LLM loaded in {time.time()-t0:.1f}s — ready for inference")

    def _build_messages(self, system_prompt: str, user_message: str,
                        context: str = "", history: list = None) -> list:
        """Build the messages array with system prompt, history, context, and user query.
        Appends /no_think to system prompt to keep Qwen3 in non-thinking mode."""
        # Ensure non-thinking mode: append /no_think if not already present
        if "/no_think" not in system_prompt and "/think" not in system_prompt:
            system_prompt = system_prompt.rstrip() + " /no_think"
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (already trimmed by caller)
        if history:
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current context data
        if context:
            messages.append({"role": "user", "content": f"[CONTEXT DATA]\n{context}"})
            messages.append({"role": "assistant", "content": "I've reviewed the data. Please go ahead with your question."})

        messages.append({"role": "user", "content": user_message})
        return messages

    def generate(self, system_prompt: str, user_message: str,
                 context: str = "", history: list = None) -> str:
        self.initialize()
        messages = self._build_messages(system_prompt, user_message, context, history)

        total_chars = sum(len(m["content"]) for m in messages)
        logger.info(f"Generating response | messages={len(messages)} | total_chars={total_chars}")
        t0 = time.time()

        response = self.model.create_chat_completion(
            messages=messages,
            temperature=LLM_CONFIG["temperature"],
            top_p=LLM_CONFIG["top_p"],
            top_k=LLM_CONFIG.get("top_k", 40),
            max_tokens=LLM_CONFIG["max_tokens"],
            repeat_penalty=LLM_CONFIG["repeat_penalty"],
        )

        result = _strip_think_tags(response["choices"][0]["message"]["content"])
        usage = response.get("usage", {})
        logger.info(
            f"Response generated in {time.time()-t0:.1f}s | "
            f"tokens_in={usage.get('prompt_tokens','?')} | "
            f"tokens_out={usage.get('completion_tokens','?')} | "
            f"response_len={len(result)}"
        )
        return result

    def generate_stream(self, system_prompt: str, user_message: str,
                        context: str = "", history: list = None):
        """Stream tokens from the LLM one at a time. Yields (token_text, is_final) tuples."""
        self.initialize()
        messages = self._build_messages(system_prompt, user_message, context, history)

        total_chars = sum(len(m["content"]) for m in messages)
        logger.info(f"Streaming response | messages={len(messages)} | total_chars={total_chars}")
        t0 = time.time()
        token_count = 0

        # Track and strip <think> blocks from streamed output
        in_think_block = False
        think_buffer = ""

        for chunk in self.model.create_chat_completion(
            messages=messages,
            temperature=LLM_CONFIG["temperature"],
            top_p=LLM_CONFIG["top_p"],
            top_k=LLM_CONFIG.get("top_k", 40),
            max_tokens=LLM_CONFIG["max_tokens"],
            repeat_penalty=LLM_CONFIG["repeat_penalty"],
            stream=True,
        ):
            delta = chunk["choices"][0].get("delta", {})
            content = delta.get("content", "")
            if content:
                token_count += 1
                # Filter out <think>...</think> blocks in streaming
                if "<think>" in content:
                    in_think_block = True
                    think_buffer = content
                    continue
                if in_think_block:
                    think_buffer += content
                    if "</think>" in think_buffer:
                        # Emit anything after the closing tag
                        after = think_buffer.split("</think>", 1)[1]
                        in_think_block = False
                        think_buffer = ""
                        if after.strip():
                            yield after
                    continue
                yield content

        logger.info(f"Stream completed in {time.time()-t0:.1f}s | tokens_out={token_count}")

    def classify(self, query: str, categories: dict) -> str:
        self.initialize()
        cats_text = "\n".join(f"- {k}: {v}" for k, v in categories.items())
        prompt = (
            f"Classify the following user query into exactly ONE category. "
            f"Reply with ONLY the category key, nothing else.\n\n"
            f"Categories:\n{cats_text}\n\nQuery: {query}\n\nCategory key:"
        )
        response = self.model.create_chat_completion(
            messages=[
                {"role": "system", "content": "You are a query classifier. Respond with only the category key. /no_think"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=20,
        )
        result = _strip_think_tags(response["choices"][0]["message"]["content"]).strip().lower()
        # Find the best match
        for key in categories:
            if key in result:
                return key
        return "general_advisor"


# Singleton
llm = LLMEngine()
