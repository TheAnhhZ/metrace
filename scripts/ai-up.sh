#!/usr/bin/env bash
# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
#
# Optional: local LLM for incident report DRAFTS (Ollama, MIT; Qwen3-4B weights, Apache-2.0).
# Runs natively on the host (Docker on macOS has no GPU). Without it, drafts use a template.
set -euo pipefail
MODEL="${LLM_MODEL:-qwen3:4b}"
command -v ollama >/dev/null || { echo "Install Ollama first: https://ollama.com/download"; exit 1; }
if ! curl -fsS -m 2 http://127.0.0.1:11434/api/tags >/dev/null; then
  OLLAMA_HOST=127.0.0.1:11434 nohup ollama serve >/tmp/ollama.log 2>&1 &
  for _ in $(seq 1 20); do curl -fsS -m 2 http://127.0.0.1:11434/api/tags >/dev/null && break; sleep 1; done
fi
ollama list | grep -q "^${MODEL}" || ollama pull "$MODEL"
echo "Ollama ready with $MODEL on 127.0.0.1:11434 (the worker reaches it as host.docker.internal)."
