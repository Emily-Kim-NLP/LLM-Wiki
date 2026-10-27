#!/usr/bin/env python3
"""[국회 시연] 국회 CSV 4개 → Markdown 원문(articles) + QA 파일.

원본 preprocess_bench.py 의 process_hotpotqa() 와 같은 자리에 꽂히는 처리기다.
preprocess_bench.DATASET_PROCESSORS["assembly"] 로 등록되어, 원본 실행 경로
`python -m llm_wiki_bench.run --dataset assembly` 에서 그대로 호출된다.

  HotpotQA                               국회 (이 파일)
  ─────────────────────────────────────  ─────────────────────────────────────────
  dev.json 의 QA 항목                     examples/demo/questions.jsonl 의 QA 항목
  QA 항목의 context 문단 (정답+방해)       QA 항목의 context_bills 에서 출발해 CSV 키로 이어진 레코드
                                         (법안·표결·본회의 회의록·발언자 의원 + 방해 법안)
  문단 하나 → raw/<ds>/articles/<제목>.md  CSV 레코드 하나 → raw/assembly/articles/<문서ID>.md
  data/<ds>/qa_pairs.jsonl               data/assembly/qa_pairs.jsonl

원칙
  - data/*.csv 는 읽기만 한다. 표준 라이브러리 csv 만 쓴다(원본 requirements 그대로).
  - 문서마다 출처(파일·레코드 번호·시작 줄)를 frontmatter 와 본문 "## 출처" 에 남긴다.
    레코드 번호 = 헤더 제외 1부터, 시작 줄 = 실제 파일 줄 번호 (bills.csv 는 셀 안 줄바꿈 때문에 다름)
  - JSON 셀(detail, agenda, speakers, career 등)은 키·값을 버리지 않고 한국어 라벨로 편다.
  - 원본 엔진은 본문 15,000자(INGEST_MAX_CONTENT_LEN) 초과분을 조용히 자른다.
    그래서 8,000자 넘는 문서는 절 경계에서 part 로 나눈다.
  - 정답·계산 결과(경과일수 등)는 문서에 넣지 않는다. CSV 키로 확인한 연결만 적는다.
"""

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
QUESTIONS_FILE = REPO_DIR / "examples" / "demo" / "questions.jsonl"
SPEAKER_PREFIX = "RivSix"       # minutes.speakers 의 name = "RivSix" + 의원 코드(members.unique_id)
MAX_PART_CHARS = 8000

csv.field_size_limit(sys.maxsize)   # bills.detail 은 한 셀이 6만 자 가까이 된다


# ─── CSV 읽기 ─────────────────────────────────────────────────────────────

def read_csv(path: Path) -> list[dict]:
    """레코드마다 _rec(레코드 번호)·_line(시작 줄)·_file 을 붙여 읽는다."""
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        prev_end = reader.line_num            # 헤더를 읽기 전 0
        for i, row in enumerate(reader, 1):
            if i == 1:
                prev_end = 1                  # 헤더는 1줄
            row["_rec"], row["_line"], row["_file"] = i, prev_end + 1, path.name
            prev_end = reader.line_num
            rows.append(row)
    return rows


def loc(row: dict) -> str:
    return f"data/{row['_file']} 레코드 {row['_rec']} (파일 {row['_line']}번째 줄)"


def clean(v) -> str:
    return str(v).replace("\r\n", "\n").replace("\r", "\n").strip()


def flat(obj) -> str:
    """중첩 JSON 을 한 줄로 편다(키·값 보존)."""
    if isinstance(obj, dict):
        return ", ".join(f"{k} {flat(v)}" for k, v in obj.items()) or "(빈 값)"
    if isinstance(obj, list):
        return "; ".join(f"[{flat(v)}]" if isinstance(v, (dict, list)) else clean(v) for v in obj) or "(빈 목록)"
    return "(null)" if obj is None else clean(obj)


def field(label: str, col: str, row: dict, fmt=None) -> str:
    v = row.get(col, "")
    return f"- {label}({col}): " + ("(빈 값)" if v == "" else (fmt(v) if fmt else clean(v)))


# ─── 문서 절 만들기 ───────────────────────────────────────────────────────

def bill_sections(b, rc_by_code, minute_by_id) -> list[tuple[str, str]]:
    d = json.loads(b["detail"])
    secs = [("기본 정보 (bills.csv 열)", "\n".join([
        field("의안번호", "billcode", b), field("의안명", "bill_name", b), field("의안 고유 ID", "bill_id", b),
        field("대수", "daenum", b, lambda v: f"제{v}대 국회"), field("제안자 구분", "sponsor_type", b),
        field("제안일", "proposal_date", b), field("의결일", "passed_date", b), field("처리 결과", "result", b),
        field("상태", "status", b), field("처리 단계", "stage", b), field("소관위원회", "committee", b),
        field("tracking", "tracking", b), field("상세정보 유무", "with_detail", b),
        field("요약", "summary", b), field("legislature", "legislature", b)]))]

    steps, reason = [], None
    for key, val in d.items():
        if key in ("대안정보", "표결정보"):
            continue
        if key == "접수정보" and isinstance(val, dict):
            val = dict(val)
            reason = val.pop("제안이유 및 주요내용", None)
        for sub, v in (val.items() if isinstance(val, dict) else [("", val)]):
            if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
                steps += [f"- {key} › {sub} [{i}/{len(v)}]: {flat(x)}" for i, x in enumerate(v, 1)]
            else:
                steps.append(f"- {key} › {sub}: {flat(v)}")
    secs.append(("접수·심사·처리 경과 (detail 열 JSON)", "\n".join(steps) or "- (없음)"))

    alt = []
    for k, v in (d.get("대안정보") or {}).items():
        if isinstance(v, list):
            alt.append(f"- {k}: {len(v)}건")
            alt += [f"  - 의안번호 {x.get('billcode')} {x.get('bill_name')} (고유 ID {x.get('unique_id')})" for x in v]
        elif isinstance(v, dict) and v:
            alt.append(f"- {k}: 의안번호 {v.get('billcode')} {v.get('bill_name')} (고유 ID {v.get('unique_id')})")
    secs.append(("대안 관계 (detail.대안정보)", "\n".join(alt) or "- (없음)"))

    vote = d.get("표결정보") or {}
    if vote:
        lines = [f"- {k}: {flat(v)}" for k, v in vote.items() if k != "표결의원"]
        secs.append(("본회의 표결 집계 (detail.표결정보)", "\n".join(lines)))
        roster = vote.get("표결의원") or {}
        if roster:
            rl = ["형식: 이름(정당, 의원코드). 의원코드는 members.csv unique_id."]
            for choice, people in roster.items():
                rl.append(f"- {choice} {len(people)}명: " + ", ".join(
                    f"{p.get('name')}({p.get('party')}, {c}" + (f", id_link={p['id_link']}" if p.get("id_link") else "") + ")"
                    for c, p in people.items()))
            secs.append(("본회의 표결 의원 명단 (detail.표결정보.표결의원)", "\n".join(rl)))

    rcol = clean(b["proposal_reason"])
    if reason is not None and clean(reason) != rcol:
        secs.append(("제안이유 및 주요내용 (detail.접수정보)", clean(reason)))
        note = ""
    else:
        note = "(detail.접수정보 '제안이유 및 주요내용' 과 같은 내용이라 한 번만 싣는다)\n"
    secs.append(("제안이유 및 주요내용 (proposal_reason 열)", note + (rcol or "(빈 값)")))

    links = [f"- 본회의 표결 기록: rollcalls.csv rollcall_id {r['rollcall_id']} ({loc(r)}), 문서 ID rollcall-{r['rollcall_id']}"
             for r in rc_by_code.get(b["billcode"], [])]
    for mid in minute_ids(d):
        m = minute_by_id.get(mid)
        links.append(f"- 본회의 회의록: detail '본회의 심의' 회의록 URL id={mid[1:]} → minutes.csv minute_id {mid}"
                     + (f" ({loc(m)}), 문서 ID minute-{mid}" if m else " (이번 문서 묶음에 없음)"))
    secs.append(("확인된 연결 관계 (전처리 코드가 CSV 키로 확인)", "\n".join(links) or "- (없음)"))
    return secs


def rollcall_sections(r, bill_by_code) -> list[tuple[str, str]]:
    secs = [("본회의 표결 (rollcalls.csv 열)", "\n".join([
        field("표결 ID", "rollcall_id", r), field("의안번호", "billcode", r), field("의안 고유 ID", "site_id", r),
        field("의안명", "name", r), field("대수", "daenum", r, lambda v: f"제{v}대 국회"), field("구분", "category", r),
        field("소관위원회", "committee", r), field("처리일", "process_date", r), field("표결 결과", "result", r),
        field("재적", "member", r), field("찬성", "pros", r), field("반대", "cons", r), field("기권", "abst", r),
        field("불참(재적−찬성−반대−기권)", "nons", r), field("명단 완전 여부", "roster_complete", r),
        field("회기", "session", r), field("차수", "period", r)]))]
    b = bill_by_code.get(r["billcode"])
    if b:
        secs.append(("확인된 연결 관계 (전처리 코드가 CSV 키로 확인)",
                     f"- 법안: bills.csv billcode {r['billcode']} ({loc(b)}), 문서 ID bill-{r['billcode']}"))
    return secs


def minute_sections(m, bill_by_code, member_doc) -> list[tuple[str, str]]:
    secs = [("회의 정보 (minutes.csv 열)", "\n".join([
        field("회의록 ID", "minute_id", m), field("회의명", "shortinfo", m, lambda v: v.strip('"')),
        field("회의 종류", "meeting_kind", m), field("위원회", "committee", m), field("회의일", "meeting_date", m),
        field("회기", "session", m, lambda v: f"제{v}회"), field("차수", "period", m, lambda v: f"제{v}차"),
        field("회기 구분", "status", m), field("type", "type", m), field("대수", "daenum", m, lambda v: f"제{v}대 국회"),
        field("장소", "location", m), field("작성", "writer", m), field("제목", "title", m),
        field("category", "category", m), field("회의록 URL", "url", m), field("HWP", "hwp_link", m),
        field("PDF", "pdf_link", m), field("요약 URL", "summary_link", m), field("영상", "vod_link", m),
        field("file_here", "file_here", m)]))]
    agenda = json.loads(m["agenda"])
    secs.append((f"안건 목록 (agenda 열, {len(agenda)}개, 원문 그대로)", "\n".join(f"- {clean(a)}" for a in agenda)))
    secs.append(("의사일정 (schedule 열)", "- schedule 열은 agenda 열과 글자 단위로 같다" if m["schedule"] == m["agenda"]
                 else "\n".join(f"- {clean(a)}" for a in json.loads(m["schedule"]))))
    sp = json.loads(m["speakers"])
    lines = [f"이 회의 전체 발언자 {len(sp)}명 (speakers 열 순서). 형식: 순번. name 원문 | 직책(position, 회의 당시 표기) | 의원 코드",
             f"name 이 '{SPEAKER_PREFIX}' 로 시작하면 뒷부분이 members.csv unique_id 다."]
    for i, s in enumerate(sp, 1):
        code = s["name"][len(SPEAKER_PREFIX):] if s["name"].startswith(SPEAKER_PREFIX) else None
        ref = ("코드 아님(이름 원문)" if code is None else
               f"의원 코드 {code} → 문서 ID {member_doc[code]}" if code in member_doc else f"의원 코드 {code} → members.csv 에 없음")
        lines.append(f"{i}. {s['name']} | {s['position']} | {ref}")
    secs.append(("발언자 목록 (speakers 열)", "\n".join(lines)))
    links = [f"- 안건 '{a.split('(')[0]}…' 의안번호 {c} → bills.csv ({loc(bill_by_code[c])}), 문서 ID bill-{c}"
             for a in agenda for c in re.findall(r"의안번호\s*(\d{7})", a) if c in bill_by_code]
    secs.append(("확인된 연결 관계 (전처리 코드가 CSV 키로 확인)", "\n".join(links) or "- 이번 문서 묶음의 법안과 연결된 안건 없음"))
    return secs


def member_sections(rows) -> list[tuple[str, str]]:
    """한 사람(member_id)의 행(새 코드·옛 코드)을 한 문서로 묶는다."""
    rows = sorted(rows, key=lambda r: r["is_primary_code"] != "True")
    m = rows[0]
    secs = [("의원 코드 (같은 member_id 로 묶인 행 전부)",
             f"- member_id: {m['member_id']} / person_id: {m['person_id'] or '(빈 값)'}\n" +
             "\n".join(f"- 의원 코드 {r['unique_id']} (is_primary_code={r['is_primary_code']}, {loc(r)})" for r in rows))]
    secs.append((f"기본 정보 (대표 행 unique_id {m['unique_id']}; 정당은 수집 시점 값)", "\n".join([
        field("이름", "name", m), field("영문 이름", "english", m), field("한자", "hanja", m),
        field("생년월일", "birthday", m), field("성별", "sex", m), field("정당(수집 시점)", "party", m),
        field("최근 정당", "party_latest", m), field("정당 변경 횟수", "party_changes", m),
        field("당선 구분", "elected", m), field("선거구", "district", m), field("선수", "seniority", m),
        field("이메일", "official_email", m), field("전화", "official_phone", m),
        field("홈페이지", "official_webpage", m), field("num", "num", m), field("사진", "link_jpg", m),
        field("사진 파일", "jpg_file", m)])))
    for r in rows[1:]:
        diff = [f"- {c}: {r[c] or '(빈 값)'}" for c in r if not c.startswith("_") and r[c] != m[c]]
        secs.append((f"다른 코드 행에서 값이 다른 열 (unique_id {r['unique_id']})", "\n".join(diff) or "- 차이 없음"))
    for label, c in (("소속 위원회", "committee"), ("경력", "career"), ("보좌관", "secretary"),
                     ("비서", "aide"), ("취미", "hobby")):
        try:
            val = json.loads(m[c]) if m[c] else []
        except json.JSONDecodeError:
            val = [m[c]]
        secs.append((f"{label} ({c} 열)", "\n".join(f"- {clean(v)}" for v in val) or "- (빈 목록)"))
    return secs


def minute_ids(detail: dict) -> list[str]:
    ids = []
    for item in detail.get("본회의 심의", {}).get("본회의 심의정보", []):
        for v in (item.get("회의록") or {}).values():
            mm = re.search(r"minutes/.*?id=(\d+)", str(v))
            if mm and f"T{mm.group(1)}" not in ids:
                ids.append(f"T{mm.group(1)}")
    return ids


# ─── part 나누기와 파일 쓰기 ──────────────────────────────────────────────

def split_parts(secs, limit):
    parts, cur, size = [], [], 0
    for head, body in secs:
        s = len(head) + len(body) + 6
        if cur and size + s > limit:
            parts.append(cur)
            cur, size = [], 0
        cur.append((head, body))
        size += s
    return parts + ([cur] if cur else [])


def write_doc(out_dir, doc_id, kind, prefix, rest, date, rows, secs) -> list[dict]:
    parts = split_parts(secs, MAX_PART_CHARS - 1000)
    written = []
    for i, ps in enumerate(parts, 1):
        tag = f" ({i}/{len(parts)})" if len(parts) > 1 else ""
        title = f"{prefix}{tag} {rest}"      # 원본은 제목 앞 60자로 원문 보관 파일명을 만든다 → ID 를 앞에
        fname = f"{doc_id}-p{i}.md" if len(parts) > 1 else f"{doc_id}.md"
        where = "; ".join(loc(r) for r in rows)
        body = (f"# {title}\n\n## 출처\n- 문서 ID: {doc_id} (종류: {kind}, part {i}/{len(parts)})\n"
                f"- 출처 파일·위치: {where}\n- 날짜: {date or '(없음)'}\n\n"
                + "\n".join(f"## {h}\n{b}\n" for h, b in ps))
        fm = (f"---\nsource_id: {doc_id}\nsource_type: {kind}\ntitle: \"{title.replace(chr(34), chr(39))}\"\n"
              f"dataset: assembly\nsource_file: data/{rows[0]['_file']}\n"
              f"source_records: [{', '.join(str(r['_rec']) for r in rows)}]\n"
              f"source_lines: [{', '.join(str(r['_line']) for r in rows)}]\ndate: {date or ''}\n---\n\n")
        (out_dir / fname).write_text(fm + body, encoding="utf-8")
        written.append({"file": fname, "source_id": doc_id, "title": title, "kind": kind,
                        "source": where, "chars": len(body)})
    return written


# ─── 처리기 (preprocess_bench 의 process_* 와 같은 형식) ──────────────────

def process_assembly(input_path: Path, output_dir: Path, data_dir: Path, limit: int = None) -> dict:
    """input_path = data/bills.csv (같은 폴더의 rollcalls/minutes/members.csv 도 읽음)."""
    src = input_path.parent
    print(f"  📖 Reading {src}/{{bills,rollcalls,minutes,members}}.csv ...")
    bills, rollcalls, minutes, members = (read_csv(src / f"{n}.csv") for n in ("bills", "rollcalls", "minutes", "members"))
    qa = [json.loads(l) for l in open(QUESTIONS_FILE, encoding="utf-8") if l.strip()]
    if limit:
        qa = qa[:limit]

    bill_by_code = {b["billcode"]: b for b in bills}
    rc_all = defaultdict(list)
    for r in rollcalls:
        rc_all[r["billcode"]].append(r)
    minute_all = {m["minute_id"]: m for m in minutes}

    # 1) QA 항목의 context_bills (HotpotQA 의 정답 문단에 해당) + 방해 법안
    #    방해 법안 = 같은 날 같은 위원회에서 표결된 '(대안)' 법안 (이름이 비슷해 헷갈리기 쉬움)
    log, sel_codes = [], []
    for item in qa:
        for code in item["context_bills"]:
            seed = bill_by_code[code]
            same = [r["billcode"] for r in rollcalls if r["process_date"] == seed["passed_date"]
                    and r["committee"] == seed["committee"] and "(대안)" in r["name"]]
            log.append(f"{item['id']}: 의안 {code} + 같은 날({seed['passed_date']})·같은 위원회 '(대안)' 표결 법안 {len(same)}건")
            for c in [code] + same:          # 씨앗 법안도 same 에 들어 있으므로 하나씩 중복 확인
                if c not in sel_codes:
                    sel_codes.append(c)
    sel_bills = [bill_by_code[c] for c in sel_codes]
    sel_rc = [r for c in sel_codes for r in rc_all.get(c, [])]

    # 2) 씨앗 법안 detail 이 가리키는 본회의 + 같은 회기 바로 다음 차수 본회의(방해 문서)
    sel_min_ids = []
    for item in qa:
        for code in item["context_bills"]:
            for mid in minute_ids(json.loads(bill_by_code[code]["detail"])):
                m = minute_all[mid]
                nxt = [x["minute_id"] for x in minutes if x["meeting_kind"] == "본회의" and x["session"] == m["session"]
                       and x["period"].isdigit() and int(x["period"]) == int(m["period"]) + 1]
                for i in [mid] + nxt:
                    if i not in sel_min_ids:
                        sel_min_ids.append(i)
    sel_min = [minute_all[i] for i in sel_min_ids]
    log.append(f"본회의 회의록: {', '.join(sel_min_ids)} (법안 detail 의 회의록 id + 같은 회기 다음 차수)")

    # 3) 회의록 발언자 코드 → 의원 (같은 member_id 의 새 코드·옛 코드 행 전부)
    codes = {s["name"][len(SPEAKER_PREFIX):] for m in sel_min for s in json.loads(m["speakers"])
             if s["name"].startswith(SPEAKER_PREFIX)}
    pids = sorted({r["member_id"] for r in members if r["unique_id"] in codes})
    sel_mem = defaultdict(list)
    for r in members:
        if r["member_id"] in pids:
            sel_mem[r["member_id"]].append(r)
    member_doc = {r["unique_id"]: f"member-{r['member_id']}" for rs in sel_mem.values() for r in rs}
    log.append(f"의원: 발언자 코드 {len(codes)}개 → 사람 {len(pids)}명 (members.csv {sum(map(len, sel_mem.values()))}행)")

    # 4) 문서 쓰기
    articles_dir = output_dir / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)
    for old in articles_dir.glob("*.md"):
        old.unlink()
    rc_by_code = defaultdict(list)
    for r in sel_rc:
        rc_by_code[r["billcode"]].append(r)
    minute_by_id = {m["minute_id"]: m for m in sel_min}
    sel_bill_by_code = {b["billcode"]: b for b in sel_bills}
    docs = []
    for b in sel_bills:
        docs += write_doc(articles_dir, f"bill-{b['billcode']}", "bill", f"법안 {b['billcode']}", b["bill_name"],
                          b["proposal_date"], [b], bill_sections(b, rc_by_code, minute_by_id))
    for r in sel_rc:
        docs += write_doc(articles_dir, f"rollcall-{r['rollcall_id']}", "rollcall", f"표결 {r['rollcall_id']}",
                          f"의안번호 {r['billcode']} {r['name']}", r["process_date"], [r], rollcall_sections(r, sel_bill_by_code))
    for m in sel_min:
        docs += write_doc(articles_dir, f"minute-{m['minute_id']}", "minute", f"회의록 {m['minute_id']}",
                          m["shortinfo"].strip('"'), m["meeting_date"], [m], minute_sections(m, sel_bill_by_code, member_doc))
    for pid, rows in sel_mem.items():
        main = next((r for r in rows if r["is_primary_code"] == "True"), rows[0])
        docs += write_doc(articles_dir, f"member-{pid}", "member", f"의원 {pid}",
                          f"{main['name']}({main['english']})", "", rows, member_sections(rows))

    # 5) QA 파일 (원본 형식: id, question, answer, type, supporting_titles + 시연용 evidence)
    title_of = defaultdict(list)
    for d in docs:
        title_of[d["source_id"]].append(d["title"])
    data_dir.mkdir(parents=True, exist_ok=True)
    with open(data_dir / "qa_pairs.jsonl", "w", encoding="utf-8") as f:
        for item in qa:
            rec = {k: v for k, v in item.items() if k != "context_bills"}
            rec["supporting_titles"] = [t for sid in item.get("supporting_docs", []) for t in title_of[sid][:1]]
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    for line in log:
        print(f"  🔎 {line}")
    print(f"  📏 Longest article body: {max(d['chars'] for d in docs):,} chars (split at {MAX_PART_CHARS:,})")
    return {"qa_count": len(qa), "paragraph_count": len(docs), "unique_titles": len(docs)}
