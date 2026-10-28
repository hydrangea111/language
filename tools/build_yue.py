"""광동어 학습 데이터를 공개 자료에서 만든다.

사용법:
    python tools/build_yue.py <자료 폴더> <Unihan 폴더> <hanja.json> [출력 폴더]

자료 폴더에 필요한 파일:
    yue_sentences.tsv.bz2, yue-eng_links.tsv.bz2, eng_sentences.tsv.bz2   (Tatoeba, CC BY 2.0 FR)
    cccanto-170202.zip                                                   (CC-Canto, CC BY-SA 3.0)
Unihan 폴더: Unihan_Readings.txt (kCantonese, kDefinition)
hanja.json : 한자 → 한국 한자음 (korean-text-tools 저장소의 data/hanja.json)

출력 (한국어 뜻은 비워 두고, tools/translate_yue.py 가 채운다)
    data/yue-words.json  [단어, 발음, 영어 뜻, 등급, 한국어 뜻]
    data/yue-hanzi.json  [글자, 발음들, 영어 뜻, 한국 한자음, 등급, 한국어 뜻]
    data/yue-sent.json   [문장, 발음, 영어 번역, 한국어 번역]
"""
import bz2, collections, json, random, re, sys, zipfile
from pathlib import Path

src, unihan, hanja_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
out = Path(sys.argv[4]) if len(sys.argv) > 4 else Path(__file__).resolve().parent.parent / "data"
out.mkdir(parents=True, exist_ok=True)

N_WORDS, N_HANZI, N_SENT, MAX_SENT_LEN = 2500, 1500, 3000, 25
HAN = re.compile(r"[㐀-鿿豈-﫿]")


def tsv(path):
    return [r.split("\t") for r in bz2.open(src / path, "rt", encoding="utf-8").read().splitlines()]


# ---------- 예문 (영어 번역이 있는 것만) ----------
yue = {r[0]: r[2] for r in tsv("yue_sentences.tsv.bz2")}
eng = {r[0]: r[2] for r in tsv("eng_sentences.tsv.bz2")}
seen, pairs = set(), []
for a, b in tsv("yue-eng_links.tsv.bz2"):
    if a in yue and b in eng and yue[a] not in seen and len(yue[a]) <= MAX_SENT_LEN:
        seen.add(yue[a])
        pairs.append((yue[a], eng[b]))

# ---------- CC-Canto ----------
# ---------- Unihan 광동어 발음·뜻 ----------
cant, defn = {}, {}
for ln in (unihan / "Unihan_Readings.txt").read_text(encoding="utf-8").splitlines():
    if ln.startswith("#") or not ln:
        continue
    cp, f, v = ln.split("\t", 2)
    ch = chr(int(cp[2:], 16))
    if f == "kCantonese":
        cant[ch] = v.split()
    elif f == "kDefinition":
        defn[ch] = v.split(";")[0].strip()
kr_sound = {c: r.split(",")[0] for c, r in json.loads(hanja_path.read_text(encoding="utf-8"))["chars"].items()}

# ---------- CC-Canto ----------
# 한 단어에 항목이 여러 개다("# adapted from cc-cedict" 꼬리표가 붙은 항목이 뜻이 더 풍부하다).
# 같은 발음의 항목끼리 뜻을 합치고, 긴 뜻부터 보여 준다.
# 한 글자 단어의 발음은 Unihan의 첫 발음을 우선한다.
pat = re.compile(r"^(\S+) (\S+) \[([^\]]*)\] \{([^}]*)\} /(.*?)/?(?: # .*)?$")
raw = collections.defaultdict(lambda: collections.defaultdict(list))   # 단어 -> 발음 -> [뜻 묶음]
for ln in zipfile.ZipFile(src / "cccanto-170202.zip").read("cccanto-webdist.txt").decode("utf-8").splitlines():
    m = pat.match(ln)
    if not m or ln.startswith("#"):
        continue
    senses = [s.strip() for s in m.group(5).split("/") if s.strip() and not s.startswith("CL:")]
    if senses:
        raw[m.group(1)][m.group(4)].append(senses)

canto = {}
for w, by_read in raw.items():
    reads = list(by_read)
    if len(w) == 1 and w in cant and cant[w][0] in by_read:
        read = cant[w][0]
    else:
        read = max(reads, key=lambda r: sum(len("/".join(s)) for s in by_read[r]))
    merged, seen_s = [], set()
    for senses in sorted(by_read[read], key=lambda s: -len("/".join(s))):
        for s in senses:
            if s.lower() not in seen_s:
                seen_s.add(s.lower()); merged.append(s)
    canto[w] = (read, "; ".join(merged[:4])[:120])

# ---------- 단어 빈도 (사전 최장 일치) ----------
LATIN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.'’-]*")


def segment(s, maxlen=4):
    i, toks = 0, []
    while i < len(s):
        m = LATIN.match(s, i)
        if m:                      # 영문·숫자는 한 덩어리로 둔다 (Tom, 8)
            toks.append(m.group()); i = m.end(); continue
        for L in range(min(maxlen, len(s) - i), 0, -1):
            w = s[i:i + L]
            if w in canto:
                toks.append(w); i += L; break
        else:
            toks.append(s[i]); i += 1
    return toks


freq = collections.Counter()
for y, _ in pairs:
    freq.update(t for t in segment(y) if t in canto)
ranked = [w for w, _ in freq.most_common(N_WORDS)]
rank = {w: i for i, w in enumerate(ranked)}
tier = lambda r: 1 if r < 300 else 2 if r < 800 else 3 if r < 1500 else 4
words = [[w, canto[w][0], canto[w][1], tier(rank[w]), ""] for w in ranked]

# ---------- 예문: 쉬운 단어로만 된 것부터 ----------
def difficulty(y):
    ranks = [rank.get(t, N_WORDS) for t in segment(y) if HAN.match(t[0])]
    return max(ranks) if ranks else N_WORDS


def jyutping(y):
    out = []
    for t in segment(y):
        if t in canto:
            out.append(canto[t][0])
        elif t in cant:
            out.append(cant[t][0])
        else:
            out.append(t)
    return re.sub(r" ([，。？！、：；）」』])", r"\1", " ".join(out))


random.seed(7)
pairs.sort(key=lambda p: (difficulty(p[0]), random.random()))
sents = [[y, jyutping(y), e, ""] for y, e in pairs[:N_SENT]]

# ---------- 한자: 선택한 단어·예문에 나온 글자 빈도 ----------
cf = collections.Counter()
for w in ranked:
    cf.update(c for c in w if HAN.match(c))
for y, *_ in sents:
    cf.update(c for c in y if HAN.match(c))
chars = [c for c, _ in cf.most_common() if c in cant][:N_HANZI]
hanzi = [[c, " ".join(cant[c][:3]), defn.get(c, ""), kr_sound.get(c, ""), 1 if i < 300 else 2 if i < 800 else 3, ""]
         for i, c in enumerate(chars)]

dump = lambda name, obj: (out / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
dump("yue-words.json", words); dump("yue-hanzi.json", hanzi); dump("yue-sent.json", sents)
kb = lambda n: (out / n).stat().st_size // 1024
print(f"words {len(words)} ({kb('yue-words.json')} KB), hanzi {len(hanzi)} ({kb('yue-hanzi.json')} KB), "
      f"sentences {len(sents)} ({kb('yue-sent.json')} KB)")
tr_chars = (sum(len(w[2]) for w in words) + sum(len(h[2]) for h in hanzi) + sum(len(s[2]) for s in sents))
print(f"번역할 영어 글자 수 약 {tr_chars:,}자")
