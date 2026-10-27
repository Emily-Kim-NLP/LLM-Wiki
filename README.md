# LLM-Wiki 국회 CSV 시연 — 데이터에서 답변까지

논문 *Retrieval as Reasoning: Self-Evolving Agent-Native Retrieval via LLM-Wiki* 의 원본 코드
([WeAgentAI/LLM-Wiki](https://github.com/WeAgentAI/LLM-Wiki))를 그대로 실행한다.
원본이 HotpotQA 를 넣는 자리에 **국회 CSV 4개**와 **질문 3개**를 넣었다.

- **완성된 위키 사이트:** https://emily-kim-nlp.github.io/LLM-Wiki/ (예: [bills/](https://emily-kim-nlp.github.io/LLM-Wiki/bills/))
- **실행 결과 예시:** [examples/demo/outputs](examples/demo/outputs) (전처리 원문, Wiki, 답변·점수)
- **질문과 정답:** [examples/demo/questions.jsonl](examples/demo/questions.jsonl)
- **원본 README (영어):** [README_original.md](README_original.md), [WeAgentAI/LLM-Wiki](https://github.com/WeAgentAI/LLM-Wiki#readme)
- 국회 CSV 원본(`data/*.csv`, 211MB)은 용량 때문에 저장소에 넣지 않았다. 단계 1~4 를 다시 돌리려면 `data/` 에 CSV 4개를 둔다.

```
 data/*.csv  ──1 전처리──▶  raw/assembly/articles/  ──2 Wiki 구축──▶  wiki_output/assembly/wiki/  ──3 질문·답변──▶  results/assembly/
 (CSV 4개)                  (Markdown 원문 45개)                     (Wiki + Error Book)                         (답변 + 점수 4)
 examples/demo/questions.jsonl ─────────▶ data/assembly/qa_pairs.jsonl ──────────────────────────────────────────┘
 (질문 + 정답)
```

---

## 0. 폴더 — 어디에 무엇이 있나

### 입력 (사람이 준 것)

| 경로 | 내용 |
|---|---|
| `data/bills.csv` `rollcalls.csv` `minutes.csv` `members.csv` | 국회 법안·표결·회의록·의원. **수정하지 않는다** |
| `examples/demo/questions.jsonl` | 질문 3개 + CSV 로 확인한 정답(`answer`)과 근거 위치(`evidence`) |
| `.env` | `OPENAI_API_KEY`, `OPENAI_BASE_URL` (git 제외) |

`data/*.csv` 와 `.env` 는 저장소에 없다 (용량, API 키).

### 코드

`llm_wiki_bench/` 의 파일 이름 앞 번호 = **시연에서 보여 주는 순서** (실행 흐름과 같다).

| 번호 | 파일 | 단계 | 하는 일 |
|---|---|---|---|
| 1 | `1_preprocess_assembly.py` | 1 전처리 | 국회 CSV 4개 → Markdown 원문 45개 (새 코드) |
| 2 | `2_run.py` | 1·2 | 전처리·구축 실행 명령 (`--only-preprocess`, `--only-ingest`) |
| 3 | `3_bench_config.py` | 2 구축 | 경로·모델·Wiki 폴더 설정 |
| 4 | `4_bench_ingest.py` | 2 구축 | Step 1 페이지 선택 → Step 2 페이지 작성, 검사·수선 |
| 5 | `5_llm_client.py` | 2·3 | LLM 호출 (gpt-6-luna) |
| 6 | `6_bench_error_book.py` | 2 구축 | Error Book: 기록 → 규칙 주입 → 닫기 |
| 7 | `7_run_qa.py` | 3 질문 | 질문 실행 명령, 답변 작성 |
| 8 | `8_wiki_retriever.py` | 3 질문 | 도구 `wiki_search` · `wiki_read` |
| 9 | `9_wiki_agent.py` | 3 질문 | 도구를 골라 부르는 검색 에이전트 |
| 10 | `10_evaluate.py` | 4 평가 | EM / F1 |
| — | `preprocess_bench.py` | 1 | 원본의 데이터셋 등록표 (2 → 여기 → 1 을 부른다) |
| — | `download_datasets.py` | — | 원본의 HotpotQA 등 다운로드. 이 시연은 `--skip-download` 로 쓰지 않는다 |

숫자로 시작하는 이름은 `import` 할 수 없어서, `__init__.py` 가 원본 코드의 `import bench_config` 같은 문장을 번호 붙은 파일로 연결한다. 원본 코드의 import 문은 그대로다.


| 경로 | 내용 |
|---|---|
| `llm_wiki_bench/` | **원본 코드**. 바꾼 곳은 `# [국회 시연]` 주석 (5절) |
| `llm_wiki_bench/1_preprocess_assembly.py` | 파이프라인의 유일한 새 코드. 국회 CSV 처리기 (원본 `process_hotpotqa` 와 같은 자리) |
| `examples/run_assembly.sh` | 1~4 단계 한 번에 실행. 원본 `examples/run_hotpotqa.sh` 를 국회용으로 바꾼 것 |
| `configs/` | 원본 설정 (페이지 유형, Wiki 스키마) |
| `scripts/` | Wiki 를 웹사이트로 만들어 GitHub Pages 에 올리는 스크립트 (단계 5). hyeongrae-kim/LLM-Wiki 에서 가져옴 |

### 출력 (실행하면 원본 코드가 저장소 루트에 만든다)

출력 위치는 원본 코드가 정한다 (`bench_config.set_dataset()`, `7_run_qa.py`, 원본 README "Quickstart").
원본 `.gitignore` 는 이 폴더들을 모두 git 에서 제외하고, 원본 `examples/` 에는 실행 스크립트만 있다.
이 저장소는 **처음 받은 상태에는 출력이 없고**, 실행하면 아래 위치에 생긴다.

| 경로 (루트 기준) | 만드는 단계 | 내용 |
|---|---|---|
| `raw/assembly/articles/*.md` | 1 | CSV 레코드를 펼친 Markdown 원문 45개 |
| `data/assembly/qa_pairs.jsonl` | 1 | 질문 파일을 원본 QA 형식으로 바꾼 것 (`supporting_titles` 추가) |
| `purpose_assembly.md` | 2 | 원본 엔진이 LLM 으로 정한 Wiki 목적 (있으면 다음 실행에서 다시 쓴다) |
| `wiki_output/assembly/wiki/` | 2 | 완성된 Wiki, `error_book.yaml`, `lint_ledger.jsonl` |
| **`results/assembly/predictions.jsonl`** | 3 | **질문의 답은 여기**. `prediction` = 모델 답, `retrieval_trace` = 검색·읽기 순서 |
| `results/assembly/assembly_details.jsonl` | 4 | 질문별 EM / F1 |
| `results/assembly/assembly_summary.json` | 4 | 전체 EM / F1 |

`wiki_output` 은 **지식 저장소**(2단계 결과), `results` 는 **질문에 대한 답과 점수**(3·4단계 결과)다.

### 실행 결과 예시 (`examples/demo/outputs/`)

2026-10-27 실제 실행(gpt-6-luna)의 출력을 **위 표와 같은 폴더 구조 그대로** 옮겨 둔 것이다. 4절의 결과는 모두 이 파일에서 나왔다.

```
examples/demo/
├── questions.jsonl                       질문 + 정답
└── outputs/
    ├── raw/assembly/articles/            단계 1
    ├── data/assembly/qa_pairs.jsonl      단계 1
    ├── purpose_assembly.md               단계 2
    ├── wiki_output/assembly/wiki/        단계 2
    └── results/assembly/                 단계 3·4  ← predictions.jsonl
```

두 곳에 비슷한 파일이 있는 것은 원본 설계다.
- 원문 `raw/assembly/articles/` 를 원본 엔진이 `wiki/sources/articles/` 에 이름을 바꿔 복사해 둔다. 에이전트가 원문까지 읽을 수 있게 하기 위해서다.
- `questions.jsonl` 은 사람이 쓴 질문이고, `qa_pairs.jsonl` 은 전처리가 원본 형식으로 바꾼 사본이다.

---

## 1. 데이터

### 1-1. CSV 4개

| 파일 | 레코드 | 한 줄이 뜻하는 것 | 주요 열 |
|---|---|---|---|
| `bills.csv` | 21,988 | 법안 1건 | `billcode`(의안번호), `bill_name`, `proposal_date`, `result`, `committee`, `detail`(JSON: 접수·심사·본회의 심의·표결) |
| `rollcalls.csv` | 1,911 | 본회의 표결 1건 | `billcode`, `process_date`, `result`, `pros`/`cons`/`abst`(찬성/반대/기권) |
| `minutes.csv` | 2,180 | 회의록 1건 | `minute_id`(T+숫자), `session`/`period`(회기/차수), `agenda`(안건 JSON), `speakers`(발언자 JSON) |
| `members.csv` | 478 | 의원 코드 1개 | `unique_id`, `member_id`, `name`, `english`, `party` |

- 네 파일 모두 UTF-8 + BOM 이다. `bills.csv` 는 셀 안 줄바꿈 때문에 레코드 21,988개가 129,710줄에 걸쳐 있어서, 문서마다 **레코드 번호**와 **시작 줄**을 따로 적는다.
- 한 의원이 새 코드 행과 옛 7자리 코드 행을 함께 가질 수 있다. 두 행은 `member_id` 가 같아 전처리에서 한 사람으로 묶는다.
- `members.party` 는 데이터 **수집 시점** 정당이다.

### 1-2. 파일 사이 연결 키

```
bills.billcode ──────────────────────────────── rollcalls.billcode        법안 → 표결
bills.detail['본회의 심의'] 회의록 URL id=52677 ──── minutes.minute_id T52677    법안 → 회의록
minutes.speakers[i].name  "RivSix"+의원코드 ────── members.unique_id         회의록 → 의원
```

### 1-3. 질문과 정답 (`examples/demo/questions.jsonl`)

| 질문 | 유형 | 정답 (CSV 확인) | CSV 위치 |
|---|---|---|---|
| Q1. AI 기본법 대안의 본회의 의결일과 의결 결과, 찬성·반대·기권 수는? | 1-hop | 2024-12-26, 원안가결, 찬성 260·반대 1·기권 3 | `rollcalls.csv` 레코드 288 |
| Q2. 제안 후 며칠 만에 본회의 의사일정에 올랐으며, 회기·차수와 안건 번호는? | 2-hop | 6일, 제420회 임시회 제1차 본회의, 제25항 | `bills.csv` 6796 → `minutes.csv` 617 |
| Q3. 의결한 본회의 발언자 목록에서 '과학기술정보방송통신위원장대리'의 실명·영문명은? | multi-hop | 조인철(CHO INCHEUL), 최수진(CHOI SOOJIN) | `minutes.csv` 617 → `members.csv` 143, 401 |

정답은 평가에만 쓰인다. Wiki 를 만드는 원문과 모델 입력에는 들어가지 않는다.

---

## 2. 실행 준비

```bash
cd LLM_Wiki-demo
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# .env (저장소 루트)
#   OPENAI_API_KEY="sk-..."
#   OPENAI_BASE_URL="https://api.openai.com/v1"

set -a; . ./.env; set +a
export LLM_PREMIUM_MODEL=gpt-6-luna LLM_FAST_MODEL=gpt-6-luna LLM_REASONING_EFFORT=low
```

한 번에 실행 (약 17분. 서버 연결이 끊겨도 계속되게 tmux 안에서):

```bash
tmux new -s llmwiki 'bash examples/run_assembly.sh; exec bash'
# 다시 보기: tmux attach -t llmwiki   (빠져나오기: Ctrl-b 다음 d)
```

영상에서는 아래 단계를 하나씩 실행한다.

Wiki 구축(16분)을 건너뛰고 단계 3 만 보여 줄 때는, 예시 출력을 루트로 복사한 뒤 단계 3 을 실행한다:

```bash
cp -r examples/demo/outputs/{raw,wiki_output,purpose_assembly.md} .
mkdir -p data && cp -r examples/demo/outputs/data/assembly data/
```

---

## 3. 시연 단계와 코드 설명

### 단계 1. 전처리 — CSV → Markdown 원문 (LLM 없음, 1초)

```bash
.venv/bin/python -m llm_wiki_bench.2_run --dataset assembly --skip-download --only-preprocess
```

| 순서 | 코드 | 하는 일 |
|---|---|---|
| 1-1 | `2_run.py` `main()` → `step_preprocess()` | 데이터셋 이름으로 처리기를 고른다 |
| 1-2 | `preprocess_bench.py` `DATASET_PROCESSORS["assembly"]` | 원본의 데이터셋 등록 표. 여기에 국회 처리기를 꽂았다 |
| 1-3 | `1_preprocess_assembly.py` `process_assembly()` | 질문의 `context_bills`(AI 기본법 대안)에서 출발해 연결 키로 문서를 고른다 |
| 1-4 | `bill_sections()` `rollcall_sections()` `minute_sections()` `member_sections()` | CSV 열과 JSON 셀을 "한국어 라벨(원래 열 이름): 값" 으로 펼친다 |
| 1-5 | `write_doc()` → `split_parts()` | 문서마다 `## 출처`(파일·레코드·줄)를 붙이고, 8,000자가 넘으면 part 로 나눈다 |

문서는 원본 HotpotQA 의 "정답 문단 + 헷갈리게 하는 문단" 방식으로 고른다. 화면에 `🔎` 줄로 출력된다.

1. AI 기본법 대안 + 같은 날·같은 위원회에서 표결된 `(대안)` 법안 4건 → 법안 5건 (긴 법안은 3 part)
2. 그 법안들의 본회의 표결 5건
3. 법안 `detail` 이 가리키는 본회의 회의록 T52677 + 다음 차수 본회의 T52678
4. 두 회의록 발언자 코드가 가리키는 의원 23명

출력 예 `raw/assembly/articles/rollcall-1317.md`:

```markdown
## 출처
- 출처 파일·위치: data/rollcalls.csv 레코드 288 (파일 289번째 줄)

## 본회의 표결 (rollcalls.csv 열)
- 처리일(process_date): 2024-12-26
- 표결 결과(result): 원안가결
- 찬성(pros): 260
```

### 단계 2. Wiki 구축 + Error Book (LLM, 약 16분)

```bash
rm -rf wiki_output/assembly .wiki-cache-bench-assembly.json   # 처음부터 다시 만들 때
.venv/bin/python -m llm_wiki_bench.2_run --dataset assembly --skip-download --only-ingest
```

`2_run.py` `step_ingest()` → `4_bench_ingest.py` `ingest_batch()` 가 원문을 3개씩 묶어 처리한다 (논문 Algorithm 1).

| 순서 | 코드 | 논문 이름 | 하는 일 |
|---|---|---|---|
| 2-0 | `bench_config.auto_init_purpose()` | — | 원문 일부를 LLM 이 읽고 Wiki 목적을 정한다 → `purpose_assembly.md` |
| 2-1 | `bench_ingest.build_select_pages_batch_prompt()` + LLM | Step 1 SELECTPAGES | 새 원문과 관련된 기존 페이지를 고른다 |
| 2-2 | `_read_selected_pages()` | — | 고른 페이지를 읽어 온다 |
| 2-3 | `build_ingest_prompt_batch()` + LLM | Step 2 COMPILEWIKIPAGES | 지식 페이지·digest 를 만들거나 고친다. **Error Book 의 열린 규칙이 프롬프트에 들어간다** |
| 2-4 | `write_wiki_files()`, `_save_article_original()` | — | 페이지 저장, 원문을 `sources/articles/` 에 보관, 목차·링크 갱신 |
| 2-5 | `quick_lint_bench()` → `bench_error_book.record_lint_issues()` | STRUCTURALVALIDATE | 빠진 섹션·깨진 링크 등을 검사해 Error Book 에 기록 |
| 2-6 | `auto_fix_bench()` | CODEAUTOFIX (1층) | 코드로 고칠 수 있는 것을 바로 고친다 |
| 2-7 | `periodic_maintenance()` | LLMPERIODICFIX (2층) | 일정 문서 수마다 LLM 이 구조·내용을 고친다 |
| 2-8 | `finalize_wiki()` | — | 코드 수선 ↔ LLM 수선 3회 → 최종 점검 → Error Book 출력 |

**Error Book** (`6_bench_error_book.py`, 논문 3.3절): 발견(`record_lint_issues`) → 원인 기록 → 규칙 만들기 → 다음 배치 프롬프트에 주입(`get_active_constraints`, 화면에 `📔 Error Book 규칙 주입` 출력) → 2회 연속 안 나오면 닫기.

출력 `wiki_output/assembly/wiki/`:

```
wiki/
├── index.md                전체 목차
├── bills/      5개         법안 (Artificial_Intelligence_Basic_Act_Bill_2206772.md …)
├── rollcalls/  5개         표결 (Roll_Call_1317.md …)
├── minutes/    2개         회의록 (Plenary_Minutes_T52677.md, T52678.md)
├── members/    23개        의원 (Cho_Incheul.md, Choi_Soojin.md …)
├── sources/digests/        원문별 요약
├── sources/articles/       원문 사본 (단계 1 의 Markdown, ## 출처 포함)
├── error_book.yaml         Error Book
└── lint_ledger.jsonl       수선 기록
```

페이지 이름이 영어인 것은 원본 프롬프트가 그렇게 만들기 때문이다.

### 단계 3·4. 질문 → 검색 에이전트 → 답변 → 평가 (LLM, 약 30초)

```bash
.venv/bin/python -m llm_wiki_bench.7_run_qa --dataset assembly --evaluate --verbose
```

| 순서 | 코드 | 하는 일 |
|---|---|---|
| 3-1 | `7_run_qa.py` `main()` | `data/assembly/qa_pairs.jsonl` 의 질문을 하나씩 처리 |
| 3-2 | `8_wiki_retriever.py` `WikiRetriever.load()` | Wiki 페이지·목차를 읽고 BM25 색인을 만든다 |
| 3-3 | `9_wiki_agent.py` `WikiAgent.retrieve()` | 모델이 도구를 골라 부르며 Wiki 를 돌아다닌다 (최대 15회, 한 번에 3개, 검색 결과 5개). 화면의 `[agent] [n/15]` 줄이 실제 도구 호출이다 |
| 3-4 | `WikiRetriever.search()` | 도구 `wiki_search`: 페이지 이름·태그·본문으로 검색. 페이지 목록만 돌려준다 |
| 3-5 | `WikiRetriever.read()` | 도구 `wiki_read`: 페이지 본문을 읽는다. 본문 안 `[[링크]]` 를 보고 다음 페이지를 고른다 |
| 3-6 | `7_run_qa.py` `_format_context()` → `_answer()` | 읽은 페이지만 근거로 짧은 답을 만든다 |
| 4 | `10_evaluate.py` `evaluate()` | 정답과 비교해 EM / F1 |

**답 확인** (영상에서):

```bash
.venv/bin/python -c "import json
for d in map(json.loads, open('results/assembly/predictions.jsonl')):
    print(d['id'], '|', d['prediction']); print('   ', *d['retrieval_trace'], sep='\n    ')"
```

실행 전에 예시 결과를 볼 때는 경로를 `examples/demo/outputs/results/assembly/predictions.jsonl` 로 바꾼다.

**답의 근거를 CSV 까지 따라가기** (Wiki 링크만 따라가면 된다):

```
읽은 지식 페이지   wiki/rollcalls/Roll_Call_1317.md
   └ 본문의 [[sources/digests/표결-1317-…]] 링크
읽은 digest       wiki/sources/digests/표결-1317-….md
   └ frontmatter source_article
원문 사본         wiki/sources/articles/표결-1317-….md
   └ ## 출처 → data/rollcalls.csv 레코드 288 (파일 289번째 줄)
```

### 단계 5. Wiki 를 웹사이트로 보기 (Quartz, GitHub Pages)

[hyeongrae-kim/LLM-Wiki](https://github.com/hyeongrae-kim/LLM-Wiki) 의 배포 방식(https://hyeongrae-kim.github.io/LLM-Wiki/bills/)을 그대로 쓴다.
원본 LLM-Wiki 코드에는 없는 부분이라 `scripts/` 에 따로 두었다. Wiki 파일은 바꾸지 않고 사본만 사이트로 만든다.

| 코드 | 하는 일 |
|---|---|
| `scripts/quartz.sh` | Quartz 5 를 `.quartz/` 에 설치(처음 한 번) → Wiki 를 `.quartz/content/` 로 복사 → 정적 사이트 빌드. 루트 `wiki_output/assembly/wiki` 가 있으면 그것을, 없으면 `examples/demo/outputs/` 의 예시 Wiki 를 쓴다 |
| `scripts/quartz_config.py` | 사이트 제목, 한국어, 주소, `[[bills/…]]` 절대 링크 설정 |
| `scripts/quartz_content.py` | 사본의 페이지마다 첫 `# 제목` 을 title 로 넣고, `_index.md` 안의 폴더 상대 링크를 고친다 |
| `scripts/deploy_pages.sh` | 빌드한 HTML 을 `gh-pages` 브랜치에 올리고 GitHub Pages 를 켠다 |

```bash
# 필요: Node 22 이상, npm 10.9.2 이상
scripts/quartz.sh serve           # 로컬 미리보기 http://localhost:8080  (bills/ , members/ , minutes/ …)
scripts/deploy_pages.sh           # 배포 → https://<계정>.github.io/<저장소>/bills/
```

배포된 사이트: **https://emily-kim-nlp.github.io/LLM-Wiki/** (저장소 https://github.com/Emily-Kim-NLP/LLM-Wiki, `gh-pages` 브랜치).
`examples/demo/outputs/` 의 예시 Wiki 로 만든 것이다. Wiki 를 새로 만든 뒤 다시 배포하면 루트 `wiki_output/` 의 새 Wiki 로 바뀐다.

배포 사이트에서 보여 줄 곳:
- `bills/` → `Artificial_Intelligence_Basic_Act_Bill_2206772`: 한 줄 요약, Key Facts, Related Pages(표결·회의록·의원 링크), Related Sources(digest)
- `minutes/Plenary_Minutes_T52677` → `sources/articles/회의록-t52677-…`: 요약에는 조인철만, 원문 사본에는 위원장대리 두 명 (Q3 이야기)
- 홈 그래프: 법안·표결·회의록·의원이 링크로 이어진 구조

---

## 4. 실제 실행 결과 (2026-10-27, gpt-6-luna) — `examples/demo/outputs/`

### Wiki 구축 (단계 2)

- 원문 45개 모두 처리, 지식 페이지 35개 (법안 5, 표결 5, 회의록 2, 의원 23).
- Error Book (`outputs/wiki_output/assembly/wiki/error_book.yaml`):

| 항목 | 내용 | 수선 | 상태 |
|---|---|---|---|
| E01 | 필수 섹션 누락 | LLM 수선 2건 | open, 2건 남음 (`Digital_Inclusion…2206761`, `Roll_Call_1320`) |
| E02 | 깨진 링크 (2건) | 코드 수선 2건 | open (원본 규칙상 LLM 이 페이지를 만들 때까지 닫지 않음) |
| E03 | 페이지 유형·폴더 불일치 (1건) | 코드 수선 1건 | **closed** (2회 연속 미탐지) |

- 내용 수선이 "원문 근거 없음"으로 판단해 지운 사실 128개 (같은 폴더 `lint_ledger.jsonl`).

### 답변 (단계 3·4) — `outputs/results/assembly/predictions.jsonl`

EM 0.000 / F1 0.530. EM 은 글자가 똑같아야 1 이라 `2024-12-26` 과 `2024년 12월 26일` 처럼 표기만 달라도 0 이 된다. 그래서 내용 판정을 함께 적는다.

| 질문 | 모델 답변 | 내용 판정 | F1 | 탐색 경로 (`retrieval_trace`) | 근거 CSV 위치 |
|---|---|---|---|---|---|
| Q1 | 2024년 12월 26일, 원안가결, 찬성 260명·반대 1명·기권 3명 | **정답** | 0.25 | 검색 1회 → `Roll_Call_1317`·법안 페이지 읽기 | `rollcalls.csv` 레코드 288 |
| Q2 | 6일, 제420회 임시회 제1차 본회의, 안건 제25호 | **정답** | 0.77 | 검색 1회 → 법안 페이지·회의록 T52677·T52678 읽기 | `bills.csv` 6796 → `minutes.csv` 617 |
| Q3 | Cho Incheul (CHO INCHEUL), Choi Soojin (CHOI SOOJIN) | **두 명 모두 찾음** (실명을 한글 대신 영문으로 씀) | 0.57 | 검색 → 회의록·법안 페이지 → digest → **원문 사본** → `WJG74792` 검색 → `Choi_Soojin` | `minutes.csv` 617 → `members.csv` 143, 401 |

Q3 에서 에이전트는 회의록 요약 페이지에 조인철만 있는 것을 보고, **원문 사본**(`sources/articles/회의록-t52677-…`)을 직접 읽었다.
거기서 두 번째 위원장대리 코드 `WJG74792` 를 찾아 다시 검색해 최수진 페이지까지 갔다(도구 호출 7회).
요약이 놓친 세부를 원문으로 되돌아가 확인한 것이다. 논문 5.2절이 말한 "구조화 페이지는 세부를 가끔 빠뜨린다"는 한계와, 그것을 보완하는 원문 보관 설계가 함께 드러난다.

같은 Wiki 로 질문 단계를 이전에 한 번 더 돌렸을 때 Q3 는 원문을 읽지 않아 조인철만 답했다. LLM 탐색은 실행마다 달라질 수 있다.

---

## 5. 원본 코드에서 바꾼 곳

전부 `# [국회 시연]` 주석이 붙어 있다. `git diff` 로 볼 수 있다 (9개 파일, +78 −15줄, 새 파일 1개).

| 파일 | 바꾼 내용 | 이유 |
|---|---|---|
| `1_preprocess_assembly.py` (새 파일) | 국회 CSV 처리기 | 원본 HotpotQA 처리기와 같은 형식 |
| `preprocess_bench.py` | `DATASET_PROCESSORS` 에 `assembly` 등록 | 원본의 데이터셋 추가 지점 |
| `2_run.py`, `7_run_qa.py`, `10_evaluate.py` | `--dataset` 선택지에 `assembly` | |
| `5_llm_client.py` | gpt-6 같은 추론 모델이면 `max_completion_tokens`, `reasoning_effort` 사용 | gpt-6-luna 는 `max_tokens` 를 거부한다 |
| `8_wiki_retriever.py` | 한글 2글자 단위 색인, `.md` 없는 `[[링크]]` 경로 읽기 | 원본은 영문·숫자만 색인해 한글 검색 결과가 0건 |
| `preprocess_bench.py` | 출력 경로를 저장소 루트로 | **원본 버그**: 전처리 출력과 Wiki 구축 입력 경로가 달라 이어지지 않음 |
| `2_run.py` | `args.only` 설정 | **원본 버그**: `--only-preprocess` 를 줘도 모든 단계가 실행됨 |
| `4_bench_ingest.py` | 배치 경로에도 Error Book 규칙 주입 | **원본 불일치**: 규칙 주입이 단건 경로에만 있었음 |
| `3_bench_config.py` | `DIR_CHANGES` 항목이 객체가 아니면 건너뜀 | **원본 버그**: LLM 출력 형식에 따라 구축 전체가 멈춤 (실제로 발생) |
| `__init__.py`, 파일 이름 | 시연 순서대로 번호(`1_` ~ `10_`)를 붙이고, 원래 이름으로 import 되게 연결 | 시연 영상에서 코드를 순서대로 보여 주기 위함. import 문은 원본 그대로 |
| `.gitignore` | `.env` 제외, `examples/demo/outputs/` 의 결과 예시는 포함 | API 키 보호. 원본 규칙(`raw/`, `results/` 등 제외)이 하위 폴더에도 걸려 예시가 빠지므로 예외를 둠 |

프롬프트, Wiki 구조, 에이전트, Error Book 규칙·수선, 답변·평가 방식은 원본 그대로다.

---

## 6. 알아 둘 점

- 질문 3개를 각 1회 실행한 결과다. 다시 실행하면 답과 점수가 달라질 수 있다.
- 내용 수선(`llm_verify_source_grounding`)이 지운 128개 사실 중에는 맞는 사실도 섞여 있을 수 있다. 원본 동작이라 그대로 두었다.
- 지금 Wiki 는 전처리 중복 버그를 고치기 전 원문으로 만들었다. AI 기본법 part 3 원문에 표결 연결 줄 하나가 두 번 들어갔었는데 내용이 같아 답에는 영향이 없다. 단계 2 를 다시 돌리면 고친 원문으로 만들어진다.
- `purpose_assembly.md` 는 원본 엔진이 만든 파일이다. 지우면 다음 실행 때 다시 만든다.
