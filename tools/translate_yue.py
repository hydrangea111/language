"""광동어 데이터의 영어 뜻·번역을 내 PC의 오프라인 모델로 한국어로 옮긴다 (키·인터넷 불필요, 모델 내려받기 후).

사용법 (전용 가상환경의 파이썬으로 실행):
    python tools/translate_yue.py --model facebook/nllb-200-distilled-600M --sample 40
    python tools/translate_yue.py --model facebook/nllb-200-distilled-600M --write

  --sample N   데이터에서 골고루 N건만 번역해 tools/_translate_sample.txt 에 적는다 (파일은 수정하지 않음)
  --write      전체를 번역해 data/yue-*.json 의 한국어 칸을 채운다. 캐시(tools/_translate_cache.json)에
               저장하므로 중간에 멈췄다가 다시 실행해도 이어서 한다.
  --beams N    빔 크기 (기본 2, 클수록 느리고 조금 더 정확)

번역 결과는 모두 기계번역이다. 화면에 그렇게 표시한다.
"""
import argparse, json, re, sys, time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="facebook/nllb-200-distilled-600M")
ap.add_argument("--sample", type=int, default=0)
ap.add_argument("--write", action="store_true")
ap.add_argument("--beams", type=int, default=2)
ap.add_argument("--batch", type=int, default=16)
ap.add_argument("--existing", action="store_true", help="--sample 에 기존 일본어·중국어·스페인어 어휘의 영어도 포함")
args = ap.parse_args()
if not args.sample and not args.write:
    ap.error("--sample N 또는 --write 중 하나를 지정하세요")

root = Path(__file__).resolve().parent.parent
data = root / "data"
cache_path = root / "tools" / "_translate_cache.json"
files = {"words": (data / "yue-words.json", 2, 4),    # (파일, 영어 칸, 한국어 칸)
         "hanzi": (data / "yue-hanzi.json", 2, 5),
         "sent": (data / "yue-sent.json", 2, 3)}
tables = {k: json.loads(p.read_text(encoding="utf-8")) for k, (p, _, _) in files.items()}


def clean(en):
    """번역기에 넣기 전에 잡음을 걷어낸다 (중국어 병음 표기, 대괄호 주석, 중복 공백)."""
    en = re.sub(r"\[[^\]]*\]", "", en)
    en = re.sub(r"\s+", " ", en).strip(" ;,")
    return en


# 번역할 문자열 모으기
need = {}
for k, (_, ei, _) in files.items():
    for row in tables[k]:
        if row[ei]:
            need.setdefault(clean(row[ei]), None)
cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
todo = [s for s in need if s and s not in cache]


def existing_english():
    """기존 일본어·중국어·스페인어 어휘(BANK)의 영어 뜻과 영어 예문 번역을 읽는다."""
    schema = {"ja": (4, 9), "zh": (3, 8), "es": (2, 5)}      # 언어 -> (영어 뜻 칸, 영어 예문 번역 칸)
    dec, lang, found = json.JSONDecoder(), "ja", []
    for ln in (root / "js" / "lang.js").read_text(encoding="utf-8").split("\n"):
        if ln.startswith("const LANG="):
            lang = ln.split("'")[1]
        m = re.match(r"^\s*const\s+BANK\s*=\s*", ln)
        if m and lang in schema:
            rows, _ = dec.raw_decode(ln[m.end():])
            found.append((lang, rows, schema[lang]))
    return found


if args.sample:
    step = max(1, len(todo) // args.sample)
    todo = todo[::step][: args.sample]
    if args.existing:                                    # 기존 어휘에서도 골고루 뽑는다
        extra = []
        for lang, rows, (ie, ix) in existing_english():
            for r in rows[:: max(1, len(rows) // 12)][:12]:
                extra += [clean(r[ie])] + ([clean(r[ix])] if len(r) > ix and r[ix] else [])
        todo += [e for e in extra if e and e not in todo]
print(f"번역 대상 {len(todo):,}건 (이미 번역됨 {len(cache):,}건)", flush=True)

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

torch.set_num_threads(8)
print("모델 불러오는 중:", args.model, flush=True)
tok = AutoTokenizer.from_pretrained(args.model, **({"src_lang": "eng_Latn"} if "nllb" in args.model else {}))
model = AutoModelForSeq2SeqLM.from_pretrained(args.model).eval()
gen_kw = {"num_beams": args.beams, "max_new_tokens": 160}
if "nllb" in args.model:
    gen_kw["forced_bos_token_id"] = tok.convert_tokens_to_ids("kor_Hang")


def translate(batch):
    enc = tok(batch, return_tensors="pt", padding=True, truncation=True, max_length=200)
    with torch.inference_mode():
        out = model.generate(**enc, **gen_kw)
    return [t.strip() for t in tok.batch_decode(out, skip_special_tokens=True)]


todo.sort(key=len)                      # 길이순으로 묶으면 패딩이 줄어 빨라진다
t0, done = time.time(), 0
result = {}
for i in range(0, len(todo), args.batch):
    chunk = todo[i:i + args.batch]
    for en, ko in zip(chunk, translate(chunk)):
        result[en] = ko
    done += len(chunk)
    if args.write and (done % (args.batch * 10) == 0 or done == len(todo)):
        cache.update(result); result = {}
        cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    if done % (args.batch * 5) == 0 or done == len(todo):
        el = time.time() - t0
        print(f"  {done:,}/{len(todo):,}  경과 {el/60:.1f}분  남은 시간 약 {el/done*(len(todo)-done)/60:.1f}분", flush=True)

if args.sample:
    lines = [f"{en}\n    → {ko}" for en, ko in result.items()]
    (root / "tools" / "_translate_sample.txt").write_text("\n".join(lines), encoding="utf-8")
    print("샘플 저장: tools/_translate_sample.txt")
    sys.exit(0)

cache.update(result)
for k, (p, ei, ki) in files.items():
    for row in tables[k]:
        if row[ei]:
            row[ki] = cache.get(clean(row[ei]), "")
    p.write_text(json.dumps(tables[k], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
miss = sum(1 for k, (_, ei, ki) in files.items() for r in tables[k] if r[ei] and not r[ki])
print(f"완료. 한국어가 비어 있는 항목 {miss}건")
