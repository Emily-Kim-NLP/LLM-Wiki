#!/usr/bin/env bash
# Wiki 사이트를 Quartz 로 빌드해 origin 저장소의 gh-pages 브랜치에 올리고, GitHub Pages 가 그 브랜치를 쓰게 한다.
# hyeongrae-kim/LLM-Wiki 의 scripts/deploy_pages.sh 를 이 저장소에 맞춘 것.
#
#   scripts/deploy_pages.sh
#
# 정적 HTML 만 gh-pages (orphan 브랜치)에 올린다. main 브랜치에는 영향이 없다.
# 필요: origin 이 자기 GitHub 저장소, gh CLI 로그인. 무료 계정은 공개 저장소여야 Pages 를 쓸 수 있다.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
slug=$(git -C "$ROOT" remote get-url origin | sed -E 's#(git@|https://)github.com[:/]##; s#\.git$##')

"$ROOT/scripts/quartz.sh" build
PUBLIC="$ROOT/.quartz/public"
touch "$PUBLIC/.nojekyll"

WT=$(mktemp -d)
trap 'git -C "$ROOT" worktree remove --force "$WT" >/dev/null 2>&1 || true' EXIT
if git -C "$ROOT" fetch -q origin gh-pages 2>/dev/null; then
  git -C "$ROOT" worktree add -q -B gh-pages "$WT" FETCH_HEAD
else
  git -C "$ROOT" branch -D gh-pages >/dev/null 2>&1 || true
  git -C "$ROOT" worktree add -q --detach "$WT"
  git -C "$WT" checkout -q --orphan gh-pages
  git -C "$WT" rm -rq . >/dev/null 2>&1 || true
fi
# 이전 사이트 파일을 지우고 새 빌드로 바꾼다 (.git 은 남긴다)
find "$WT" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -r "$PUBLIC/." "$WT/"
git -C "$WT" add -A
if git -C "$WT" diff --cached --quiet; then
  echo "ℹ️  사이트가 바뀌지 않아 배포하지 않습니다"
else
  git -C "$WT" commit -q -m "Deploy LLM-Wiki site (assembly, $(date +%F))"
  git -C "$WT" -c http.postBuffer=524288000 push -q origin gh-pages
  echo "🚀 gh-pages 에 올렸습니다"
fi

if ! gh api "repos/$slug/pages" >/dev/null 2>&1; then
  # gh-pages 를 처음 올리면 GitHub 가 Pages 를 스스로 켜기도 한다 (그때는 409 already enabled)
  echo '{"source":{"branch":"gh-pages","path":"/"}}' | gh api -X POST "repos/$slug/pages" --input - >/dev/null 2>&1 \
    || gh api "repos/$slug/pages" >/dev/null
  echo "📄 GitHub Pages 켬 (source: gh-pages)"
fi
echo "🌐 https://${slug%%/*}.github.io/${slug##*/}/   (예: …/bills/)"
