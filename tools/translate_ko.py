"""영어 뜻·예문 번역을 내 PC의 오프라인 모델(NLLB, CTranslate2 int8)로 한국어로 옮긴다.

대상
  yue  data/yue-words.json, yue-hanzi.json, yue-sent.json 의 한국어 칸을 채운다
  ja zh es  js/lang.js 의 어휘(BANK)에서 영어 뜻과 영어 예문 번역을 한국어로 옮겨
            data/ko-<언어>.json 에 저장한다. 행 번호가 BANK 와 같다: [한국어 뜻, 한국어 예문 번역]

사용법 (전용 가상환경의 파이썬으로):
    python tools/translate_ko.py --ct2 <변환된 모델 폴더> --sample 40     # 품질 확인 (파일 수정 없음)
    python tools/translate_ko.py --ct2 <변환된 모델 폴더> --write         # 전체 (캐시로 이어서 가능)

번역 결과는 기계번역이다. tools/_review_queue.json 에는 사람이 확인할 만한 항목(의심 항목)이 쌓인다.
"""
import argparse, json, re, sys, time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--ct2", required=True, help="ct2-transformers-converter 로 변환한 모델 폴더")
ap.add_argument("--tok", default="facebook/nllb-200-distilled-600M")
ap.add_argument("--targets", default="yue,ja,zh,es")
ap.add_argument("--sample", type=int, default=0)
ap.add_argument("--write", action="store_true")
ap.add_argument("--beams", type=int, default=2)
ap.add_argument("--batch", type=int, default=32)
args = ap.parse_args()
if not args.sample and not args.write:
    ap.error("--sample N 또는 --write 중 하나를 지정하세요")

root = Path(__file__).resolve().parent.parent
data, tools = root / "data", root / "tools"
cache_path = tools / "_translate_cache.json"
targets = args.targets.split(",")

# ---------------------------------------------------------------- 전처리 / 후처리
POS = {"noun": "명사", "verb": "동사", "adjective": "형용사", "adverb": "부사", "pronoun": "대명사",
       "preposition": "전치사", "conjunction": "접속사", "interjection": "감탄사", "particle": "조사",
       "final particle": "어기조사", "measure word": "양사", "classifier": "양사", "numeral": "수사",
       "auxiliary verb": "조동사", "slang": "속어", "internet slang": "인터넷 속어", "cantonese": "광동어",
       "colloquial": "구어", "literary": "문어", "idiom": "관용구", "dialect": "방언", "formal": "격식",
       "informal": "비격식", "polite": "공손한 말", "vulgar": "비속어", "classical": "고어", "suffix": "접미사",
       "prefix": "접두사", "expression": "표현", "phrase": "구"}
PAREN = re.compile(r"\(([^()]*)\)")


def prep_meaning(en):
    """영어 뜻 → (한국어 꼬리표, [번역할 뜻 조각]).  (noun) 같은 표시는 번역기에 넣지 않고 한국어로 바꾼다."""
    en = re.sub(r"\[[^\]]*\]", "", en)                       # [了] 같은 주석
    en = re.sub(r"\bM:.*$", "", en)                          # 양사 목록(M: 滴dī ; 头tóu …)
    tags, keep = [], []

    def grab(m):
        t = m.group(1).strip().lower().rstrip(".")
        if t in POS:
            tags.append(POS[t]); return ""
        return m.group(0)

    en = PAREN.sub(grab, en)
    en = re.sub(r"(?<![\w])\d+\.\s*", "", en)                # "1. city; 2. capital" 의 번호
    parts = [p.strip(" ,.") for p in re.split(r";|/(?=\s|$)", en)]
    for p in parts:
        if p and p.lower() not in {k.lower() for k in keep}:
            keep.append(p)
    tags = list(dict.fromkeys(tags))
    return tags, keep


RULES = [   # (패턴, 한국어) — 모델 없이 정확하게 옮길 수 있는 사전 표현
    (r"^(?:old |Japanese |ancient )?variant (?:form )?of (.+)$", r"\1의 이체자"),
    (r"^simplified (?:form|version) of (.+)$", r"\1의 간체자"),
    (r"^(?:traditional|old) form of (.+)$", r"\1의 번체자"),
    (r"^surname (.+)$", r"성씨 \1"),
    (r"^abbr\. (?:for|of) (.+)$", r"\1의 약어"),
    (r"^see (.+)$", r"\1 참조"),
]


OVERRIDES = json.loads((tools / "ko_overrides.json").read_text(encoding="utf-8")) if (tools / "ko_overrides.json").exists() else {}


def rule_translate(u):
    for pat, rep in RULES:
        m = re.match(pat, u.strip(), re.I)
        if m:
            return m.expand(rep)
    return None


def clean_sentence(s):
    return re.sub(r"\s+", " ", s).strip()


def fix_verb(en, ko):
    """'to eat' 가 '먹기 위해서' 로 나오는 모델 버릇을 사전식 '먹다' 형태로 고친다."""
    if not re.match(r"^to\s", en.strip(), re.I):
        return ko
    ko = re.sub(r"(?:하기\s*)?(?:위해서|위하여|위해|하려고|하려면)\s*$", "하다", ko)
    ko = re.sub(r"([가-힣])기$", r"\1다", ko)                # 먹기 → 먹다
    ko = re.sub(r"하하다$", "하다", ko)
    ko = re.sub(r"([가-힣])기 하다$", r"\1다", ko)          # 오기 하다 → 오다
    ko = re.sub(r"([가-힣])려고$", r"\1다", ko)            # 보려고 → 보다
    return ko


def join_korean(tags, kos):
    out, seen = [], set()
    for k in kos:
        k = k.strip(" ,;.")
        if k and k not in seen:
            seen.add(k); out.append(k)
    text = ", ".join(out)
    return ("(" + "·".join(tags) + ") " if tags else "") + text


def suspicious(en, ko):
    if not ko.strip():
        return "비어 있음"
    body = re.sub(r"^\([^)]*\)\s*", "", ko)
    if re.search(r"[A-Za-z]{3,}", body) and not re.search(r"[A-Za-z]{3,}", en.split(";")[0].upper()):
        return "영문 잔류"
    if re.match(r"^to\s", en.strip(), re.I) and re.search(r"(위해서|위해|위하여|하려면)\s*$", body):
        return "동사 어미 이상"
    if len(body) > 3 * len(en) + 12:
        return "너무 김"
    if body.strip().lower() == en.strip().lower():
        return "번역 안 됨"
    return ""


# ---------------------------------------------------------------- 번역할 문자열 수집
def existing_banks():
    """js/lang.js 의 어휘(BANK) → {언어: (행들, 영어 뜻 칸, 영어 예문 번역 칸, 등급 칸)}"""
    schema = {"ja": (4, 9, 6), "zh": (3, 8, 5), "es": (2, 5, 6)}
    dec, lang, found = json.JSONDecoder(), "ja", {}
    for ln in (root / "js" / "lang.js").read_text(encoding="utf-8").split("\n"):
        if ln.startswith("const LANG="):
            lang = ln.split("'")[1]
        m = re.match(r"^\s*const\s+BANK\s*=\s*", ln)
        if m and lang in schema:
            rows, _ = dec.raw_decode(ln[m.end():])
            found[lang] = (rows,) + schema[lang]
    return found


jobs = []          # (표 이름, 행 번호, 종류 'm'|'s', 영어 원문, 등급)
yue_tables = {}
if "yue" in targets:
    spec = {"words": ("yue-words.json", 2, 4, 3), "hanzi": ("yue-hanzi.json", 2, 5, 4), "sent": ("yue-sent.json", 2, 3, None)}
    for name, (f, ei, ki, ti) in spec.items():
        rows = json.loads((data / f).read_text(encoding="utf-8"))
        yue_tables[name] = (f, rows, ei, ki)
        for i, r in enumerate(rows):
            if r[ei]:
                jobs.append((f"yue:{name}", i, "s" if name == "sent" else "m", r[ei], r[ti] if ti is not None else 2))
banks = existing_banks()
for lang in [t for t in targets if t in banks]:
    rows, ie, ix, it = banks[lang]
    for i, r in enumerate(rows):
        if r[ie]:
            jobs.append((f"{lang}:meaning", i, "m", r[ie], r[it]))
        if len(r) > ix and r[ix]:
            jobs.append((f"{lang}:example", i, "s", r[ix], r[it]))

units = {}                                   # 번역할 최소 단위
plan = []                                    # (job, 꼬리표, [단위들])
for job in jobs:
    if job[2] == "m":
        tags, parts = prep_meaning(job[3])
        plan.append((job, tags, parts))
        units.update(dict.fromkeys(parts))
    else:
        s = clean_sentence(job[3])
        plan.append((job, [], [s]))
        units[s] = None
cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
for u in units:                                  # 규칙으로 되는 것은 모델에 보내지 않는다
    r = rule_translate(u) if u else None
    if r:
        cache[u] = r
todo = [u for u in units if u and u not in cache]
if args.sample:
    step = max(1, len(todo) // args.sample)
    todo = todo[::step][: args.sample]
print(f"작업 {len(jobs):,}건 → 번역 단위 {len(units):,}개 (캐시에 있음 {len(units) - len([u for u in units if u not in cache]):,}개), 이번에 번역 {len(todo):,}개", flush=True)

# ---------------------------------------------------------------- 번역 (CTranslate2)
import ctranslate2
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained(args.tok, src_lang="eng_Latn")
tr = ctranslate2.Translator(args.ct2, device="cpu", inter_threads=2, intra_threads=4, compute_type="int8")


def translate(batch):
    src = [tok.convert_ids_to_tokens(tok.encode(s, truncation=True, max_length=200)) for s in batch]
    res = tr.translate_batch(src, target_prefix=[["kor_Hang"]] * len(batch), beam_size=args.beams,
                             max_decoding_length=160, repetition_penalty=1.15, no_repeat_ngram_size=3)
    return [tok.decode(tok.convert_tokens_to_ids(r.hypotheses[0][1:]), skip_special_tokens=True).strip() for r in res]


todo.sort(key=len)
t0, done, fresh = time.time(), 0, {}
for i in range(0, len(todo), args.batch):
    chunk = todo[i:i + args.batch]
    fresh.update(zip(chunk, translate(chunk)))
    done += len(chunk)
    if args.write and (done % (args.batch * 20) == 0 or done == len(todo)):
        cache.update(fresh); fresh = {}
        cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    if done % (args.batch * 5) == 0 or done == len(todo):
        el = time.time() - t0
        print(f"  {done:,}/{len(todo):,}  경과 {el/60:.1f}분  초당 {done/el:.1f}개  남은 시간 약 {el/done*(len(todo)-done)/60:.1f}분", flush=True)
cache.update(fresh)

if args.sample:
    lines = [f"{u}\n    → {cache[u]}" for u in todo]
    (tools / "_translate_sample.txt").write_text("\n".join(lines), encoding="utf-8")
    print("샘플 저장: tools/_translate_sample.txt")
    sys.exit(0)

# ---------------------------------------------------------------- 조립 / 저장
korean = {}                                  # (표, 행, 종류) → 한국어
for (table, i, kind, en, prio), tags, parts in plan:
    korean[(table, i, kind)] = join_korean(tags, [OVERRIDES.get(p) or fix_verb(p, cache.get(p, "")) for p in parts])


def mismatch_with_example(table, i, ko):
    """한국어 뜻의 앞부분이 같은 행의 한국어 예문에 나오지 않으면 신뢰도 낮음 (pear→호박 같은 오역 후보)."""
    lang = table.split(":")[0]
    ex = korean.get((f"{lang}:example", i, "s"), "")
    body = re.sub(r"^\([^)]*\)\s*", "", ko).split(",")[0].strip()
    stem = re.sub(r"(하다|되다|이다|다)$", "", body)[:2]
    return bool(ex and len(stem) >= 2 and stem not in ex)


review = []
for (table, i, kind, en, prio), tags, parts in plan:
    ko = korean[(table, i, kind)]
    why = suspicious(en, ko)
    if not why and kind == "m" and table.endswith(":meaning") and mismatch_with_example(table, i, ko):
        why = "예문과 불일치"
    if why:
        review.append({"table": table, "row": i, "prio": prio, "why": why, "en": en, "ko": ko})

for name, (f, rows, ei, ki) in yue_tables.items():
    for i, r in enumerate(rows):
        r[ki] = korean.get((f"yue:{name}", i, "s" if name == "sent" else "m"), "")
    (data / f).write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
for lang in [t for t in targets if t in banks]:
    n = len(banks[lang][0])
    out = [[korean.get((f"{lang}:meaning", i, "m"), ""), korean.get((f"{lang}:example", i, "s"), "")] for i in range(n)]
    (data / f"ko-{lang}.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

review.sort(key=lambda x: (x["prio"], x["table"], x["row"]))
(tools / "_review_queue.json").write_text(json.dumps(review, ensure_ascii=False, indent=0), encoding="utf-8")
print(f"저장 완료. 의심 항목 {len(review):,}건 → tools/_review_queue.json")
