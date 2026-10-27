#!/usr/bin/env bash
# 완성된 Wiki 를 Quartz 5 (https://quartz.jzhao.xyz) 정적 사이트로 만든다.
# hyeongrae-kim/LLM-Wiki 의 scripts/quartz.sh 를 이 저장소 폴더 구성에 맞춘 것.
#
#   scripts/quartz.sh serve   로컬 미리보기 http://localhost:${QUARTZ_PORT:-8080}
#   scripts/quartz.sh build   정적 사이트 → .quartz/public
#
# 보여 줄 Wiki: 루트 wiki_output/assembly/wiki (방금 실행한 결과)가 있으면 그것,
#               없으면 examples/demo/outputs/wiki_output/assembly/wiki (실행 결과 예시). WIKI=... 로 지정 가능.
# Quartz 는 처음 한 번 .quartz/ (git 제외)에 설치된다. Node >= 22, npm >= 10.9.2 필요.
# 설정: QUARTZ_BASE_URL (기본: origin 원격 저장소의 <owner>.github.io/<repo>), QUARTZ_TITLE, QUARTZ_PORT
#
# QUARTZ_REF 는 v5 브랜치 커밋이다. v5.0.0 태그는 <user>.github.io/<repo>/ 처럼 하위 경로에 배포하면
# 그래프·탐색기·검색 링크가 깨진다 (참고 저장소와 같은 커밋을 쓴다).
set -euo pipefail

ACTION=${1:-serve}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
if [ -z "${WIKI:-}" ]; then
  WIKI="$ROOT/wiki_output/assembly/wiki"
  [ -d "$WIKI" ] || WIKI="$ROOT/examples/demo/outputs/wiki_output/assembly/wiki"
fi
QZ="$ROOT/.quartz"
QUARTZ_REF=${QUARTZ_REF:-97a2d05f80c4c50534959b1d0d41cc4b3895625e}   # v5 branch, 2026-09-20
export QUARTZ_TITLE=${QUARTZ_TITLE:-"LLM-Wiki · 국회 AI 기본법"}
PY="$ROOT/.venv/bin/python"; [ -x "$PY" ] || PY=python3

[ -d "$WIKI" ] || { echo "❌ Wiki 가 없습니다: $WIKI"; exit 1; }
echo "📚 Wiki: $WIKI"

node_major=$(node -v 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/' || echo 0)
[ "${node_major:-0}" -ge 22 ] || { echo "❌ Node >= 22 필요 (현재 $(node -v 2>/dev/null || echo 없음))"; exit 1; }
npm_ver=$(npm -v)
if [ "$(printf '%s\n10.9.2\n' "$npm_ver" | sort -V | head -1)" != "10.9.2" ]; then
  echo "❌ npm >= 10.9.2 필요 (현재 $npm_ver). npm install -g npm@latest"; exit 1
fi

# 기본 주소: origin 원격 저장소에서 <owner>.github.io/<repo>
if [ -z "${QUARTZ_BASE_URL:-}" ]; then
  slug=$(git -C "$ROOT" remote get-url origin 2>/dev/null | sed -E 's#(git@|https://)github.com[:/]##; s#\.git$##')
  QUARTZ_BASE_URL="${slug%%/*}.github.io/${slug##*/}"
fi
export QUARTZ_BASE_URL
echo "🌐 Base URL: $QUARTZ_BASE_URL"

# .quartz/ 에는 생성 파일만 있다 (설정, 내용 사본, 빌드 결과)
if [ -d "$QZ" ] && [ "$(cat "$QZ/.quartz-ref" 2>/dev/null)" != "$QUARTZ_REF" ]; then
  echo "♻️  Quartz 버전이 바뀌어 .quartz/ 를 다시 설치합니다"
  rm -rf "$QZ"
fi
if [ ! -d "$QZ" ]; then
  echo "⬇️  Quartz $QUARTZ_REF 를 .quartz/ 에 설치합니다 ..."
  git init -q "$QZ"
  git -C "$QZ" fetch -q --depth 1 https://github.com/jackyzha0/quartz.git "$QUARTZ_REF"
  git -C "$QZ" checkout -q FETCH_HEAD
  (cd "$QZ" && npm ci --no-audit --no-fund)
  echo "$QUARTZ_REF" > "$QZ/.quartz-ref"
fi
if [ ! -f "$QZ/quartz.config.yaml" ]; then
  (cd "$QZ" && npx quartz create -t default -X new -l absolute -b "$QUARTZ_BASE_URL")
fi

# 사이트 제목, 한국어, 주소, [[dir/page]] 절대 링크
"$PY" "$ROOT/scripts/quartz_config.py" "$QZ/quartz.config.yaml" assembly

if [ ! -f "$QZ/.plugins-installed" ]; then
  (cd "$QZ" && npx quartz plugin install --from-config) || exit 1
  touch "$QZ/.plugins-installed"
fi

# Wiki → content/ (Markdown 만. error_book.yaml, lint_ledger.jsonl 같은 기록 파일은 뺀다)
rm -rf "$QZ/content"
mkdir -p "$QZ/content"
cp -r "$WIKI/." "$QZ/content/"
find "$QZ/content" \( -name '*.yaml' -o -name '*.jsonl' -o -name '.DS_Store' \) -delete
"$PY" "$ROOT/scripts/quartz_content.py" "$QZ/content" "$QUARTZ_TITLE"

cd "$QZ"
if [ "$ACTION" = "serve" ]; then
  npx quartz build --serve --port "${QUARTZ_PORT:-8080}"
else
  npx quartz build
  echo "✅ 사이트: $QZ/public"
fi
