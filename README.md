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
