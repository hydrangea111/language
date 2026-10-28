# language

한자 · 일본어 · 중국어 · 스페인어 학습 페이지입니다. 정적 파일이라 GitHub Pages로 그대로 동작합니다.

## 구조

| 경로 | 설명 |
| --- | --- |
| `index.html` | 바깥 틀: 탭 막대와 iframe 두 개 |
| `hanja.html` | 한자 학습 문서 |
| `lang.html` | 일본어 · 중국어 · 스페인어 학습 문서 (본문 클래스 `lang-ja` / `lang-zh` / `lang-es`로 전환) |
| `css/shell.css`, `hanja.css`, `lang.css` | 스타일 (흰 바탕 + 얇은 선, 탭마다 포인트 색) |
| `js/shell.js` | 탭 전환, 마지막 탭 복원, 자식 문서의 저장소 요청 중계 |
| `js/storage-bridge.js` | 자식 문서가 부모에게 저장소를 요청하는 공통 코드 |
| `js/hanja.js`, `js/lang.js` | 학습 로직과 데이터 |
| `js/lang-switch.js` | 바깥 탭 → 언어 전환 메시지 처리 |

문서끼리는 `postMessage`로만 통신합니다.

## 로컬 확인

```
python -m http.server
```

## 광동어 탭과 한국어 뜻

- `yue.html` + `js/yue.js` + `css/yue.css`: 광동어 탭. 한자·단어·예문을 카드, 문제, 목록으로 학습합니다. 처음 열 때만 `data/yue-*.json`을 내려받습니다.
- 자료: [CC-Canto](https://cantonese.org/) (CC BY-SA 3.0), [Tatoeba](https://tatoeba.org/) (CC BY 2.0 FR), Unicode Unihan. 예문의 Jyutping은 자동 생성한 참고용입니다.
- `data/ko-ja|zh|es.json`: 기존 일본어·중국어·스페인어 어휘의 한국어 뜻과 예문 번역(기계번역). 사용자가 저장한 번역이 있으면 그쪽이 우선합니다.
- 번역은 오프라인 모델(NLLB-200 distilled 600M)로 만들었고, `tools/ko_overrides.json`으로 눈에 띄는 오역을 고쳤습니다. 다시 만들 때는 `tools/translate_ko.py`를 씁니다. 모델 라이선스는 CC-BY-NC입니다.
- 학습 기록은 브라우저 `localStorage`에 저장됩니다(`language:` 접두사).
