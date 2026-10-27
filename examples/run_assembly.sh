#!/usr/bin/env bash
# 국회 CSV 4개로 LLM-Wiki 실행 (원본 examples/run_hotpotqa.sh 와 같은 구성):
#   (1) 전처리  (2) Wiki 구축 + Error Book  (3) 검색 에이전트 + 답변  (4) EM / F1
# 저장소 루트에서:  bash examples/run_assembly.sh
# 서버 연결이 끊겨도 계속:  tmux new -s llmwiki 'bash examples/run_assembly.sh; exec bash'

set -euo pipefail
cd "$(dirname "$0")/.."

# 0. LLM 설정. API 키는 저장소 루트 .env 에 둔다 (OPENAI_API_KEY, OPENAI_BASE_URL).
if [ -f .env ]; then set -a; . ./.env; set +a; fi
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.openai.com/v1}"
export LLM_PREMIUM_MODEL="${LLM_PREMIUM_MODEL:-gpt-6-luna}"
export LLM_FAST_MODEL="${LLM_FAST_MODEL:-gpt-6-luna}"
export LLM_REASONING_EFFORT="${LLM_REASONING_EFFORT:-low}"
PY=${PY:-.venv/bin/python}

# 1. 전처리: data/*.csv → raw/assembly/articles/*.md, data/assembly/qa_pairs.jsonl
$PY -m llm_wiki_bench.run --dataset assembly --skip-download --only-preprocess

# 2. Wiki 구축 + Error Book: → wiki_output/assembly/wiki/
rm -rf wiki_output/assembly .wiki-cache-bench-assembly.json     # 처음부터 다시 구축
$PY -m llm_wiki_bench.run --dataset assembly --skip-download --only-ingest

# 3~4. 검색 에이전트 + 답변 + 평가: → results/assembly/
$PY -m llm_wiki_bench.run_qa --dataset assembly --evaluate --verbose

echo
echo "Done."
echo "  Wiki        : wiki_output/assembly/wiki/"
echo "  Predictions : results/assembly/predictions.jsonl"
echo "  Summary     : results/assembly/assembly_summary.json"
