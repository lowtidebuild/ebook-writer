<div align="center">

# Ebook Writer Agent

**주제를 입력하면 전문 수준의 ebook을 자동으로 만들어주는 멀티 에이전트 시스템**

리서치 &rarr; 목차 &rarr; 집필 &rarr; 편집 &rarr; 이미지 &rarr; 번역 &rarr; PDF &rarr; 웹 뷰어

[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blueviolet?logo=anthropic)](https://claude.ai/claude-code)
[![WeasyPrint](https://img.shields.io/badge/PDF%20엔진-WeasyPrint-blue)](https://weasyprint.org/)
[![Gemini](https://img.shields.io/badge/이미지-Gemini%20API-orange?logo=google)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[**English README**](README.md)

</div>

---

## 결과물 예시

> **"변호사를 위한 Claude Code 완전 정복"** &mdash; 13장, 250+ 페이지 분량의 ebook이 이 에이전트 시스템으로 자동 생성되었습니다.

**[온라인으로 읽기 &rarr; lowtidebuild.github.io/ebook-writer](https://lowtidebuild.github.io/ebook-writer/)**

웹 뷰어에서 실제 조판된 PDF를 2페이지 펼침 레이아웃으로 볼 수 있고, 한/영 전환도 가능합니다.

---

## 이 시스템이 하는 일

**주제** 하나와 (선택) **도메인 플러그인**을 입력하면:

| 산출물 | 설명 |
|--------|------|
| `book_{ko}.pdf` | 조판된 PDF &mdash; B5 판형, 명조체 본문, 챕터 오프닝, 러닝 헤더 |
| `book_{en}.pdf` | 번역된 PDF (2차 언어) |
| `web-viewer/` | 브라우저 기반 책 뷰어 (페이지 넘김, 한/영 전환) |

사람이 개입하는 지점은 **딱 두 번**: 목차 승인 + 최종 리뷰.

---

## 아키텍처

`CLAUDE.md`가 8단계 파이프라인을 관리하며, 각 단계에서 전문 서브 에이전트를 디스패치하거나 스크립트를 실행합니다.

```
                         +-----------------+
                         |    CLAUDE.md    |
                         |   오케스트레이터  |
                         +--------+--------+
                                  |
          +-----------+-----------+-----------+-----------+
          |           |           |           |           |
     +----+----+ +----+----+ +----+----+ +----+----+ +----+----+
     | 리서처   | | 아키텍트 | |  라이터  | |  에디터  | |  번역가  |
     | Agent   | | Agent   | | Agent   | | Agent   | | Agent   |
     |         | |         | |  (x N)  | |         | |  (x N)  |
     +----+----+ +----+----+ +----+----+ +----+----+ +----+----+
          |           |           |           |           |
          v           v           v           v           v
     리서치 리포트   목차(ToC)    챕터들     검증된 챕터   번역된 챕터
                                  |
                    +-------------+-------------+
                    |             |             |
              +-----+-----+ +----+----+ +------+------+
              | 이미지 생성 | |  PDF    | |  웹 뷰어    |
              |  (Gemini)  | | 빌더    | |   빌더      |
              +------------+ +---------+ +-------------+
```

### 오케스트레이터: `CLAUDE.md`

시스템의 두뇌. 다음을 관리합니다:

- **파이프라인 상태** &mdash; `pipeline_state.json`으로 체크포인트/재개
- **서브 에이전트 디스패치** &mdash; 전문 에이전트를 병렬 Task로 스폰
- **의존성 웨이브** &mdash; 독립 챕터는 동시 작성, 의존 챕터는 순차 대기
- **품질 게이트** &mdash; 목차/최종 리뷰에서 사람 승인 대기
- **재시도 프로토콜** &mdash; 단계당 최대 2회 재시도, 초과 시 사용자 에스컬레이션
- **플러그인 주입** &mdash; 도메인 플러그인 감지 후 관련 단계에 설정 주입

### 서브 에이전트 (5개)

각 에이전트는 전용 `AGENT.md` 지시 파일과 집중된 역할을 가집니다:

| 에이전트 | 역할 | 실행 방식 |
|---------|------|----------|
| **Researcher** | 웹 검색 + 레퍼런스 분석 &rarr; 구조화된 리서치 리포트 | 단일 |
| **Architect** | 리서치 리포트 &rarr; 챕터 의존성 포함 목차 설계 | 단일 |
| **Writer** | 목차 섹션 &rarr; 지정 언어로 챕터 전문 작성 | 병렬 (챕터별) |
| **Editor** | 2-pass 리뷰: 챕터별 품질 + 교차 일관성. 프로덕션 잔재 탐지. | 단일 |
| **Translator** | 양방향 번역 (KO&harr;EN), 코드 블록/구조 보존 | 병렬 (챕터별) |

### 스킬 (7개)

에이전트와 오케스트레이터가 호출하는 재사용 가능한 기능:

| 스킬 | 용도 | 핵심 스크립트 |
|------|------|-------------|
| `web-research` | 검색 전략, 소스 신뢰도 평가, 중복 제거 | &mdash; |
| `reference-analyzer` | .md/.pdf/.docx 레퍼런스 파일 파싱 | `parse_references.py` |
| `code-example-validator` | 코드 블록 문법 검증 (Python, JS, Bash) | `validate_code.py` |
| `quality-checker` | 품질 루브릭 + 도메인 플러그인 기준 적용 | &mdash; |
| `image-generator` | `[IMAGE:]` 마커 추출 &rarr; Gemini API &rarr; 챕터에 삽입 | `extract_markers.py`, `generate_images.py`, `insert_images.py` |
| `pdf-builder` | Markdown &rarr; HTML &rarr; WeasyPrint PDF (B5, 단행본 수준) | `build_pdf.py` |
| `web-viewer-builder` | PDF.js 기반 브라우저 뷰어 (2페이지 펼침) | `build_viewer.py` |

### 도메인 플러그인

플러그인은 코어 엔진을 수정하지 않고 도메인 전문 지식을 주입합니다:

```
.claude/plugins/legal/
  ├── PLUGIN.md              # 도메인 메타데이터, 대상 독자, 작성 가이드라인
  ├── research_sources.md    # 도메인별 리서치 질문과 소스
  ├── quality_criteria.md    # 용어 기준, 인용 형식, 면책 조항
  └── references/            # 소스 자료 (.md, .pdf, .docx)
```

포함된 `legal` 플러그인은 법률 전문가용으로 &mdash; 윤리 가이드라인, 법률 용어 검증, 인용 형식 체크를 추가합니다.

**자신만의 플러그인 만들기**: `legal/` 폴더를 복사하고, 이름을 바꾸고, 세 개의 `.md` 파일을 원하는 도메인(의료, 금융, 공학 등)에 맞게 수정하면 됩니다.

---

## 파이프라인 흐름

```
Step 1  ── 리서치 ───────────── Researcher Agent (웹 검색 + 레퍼런스)
Step 2  ── 목차 설계 ─────────── Architect Agent
        ══ Gate 1: 목차 승인 ══   (사용자 확인)
Step 3  ── 챕터 작성 ─────────── Writer Agent x N (병렬, 의존성 웨이브)
Step 4  ── 편집 & 검증 ────────── Editor Agent (2-pass + 잔재 탐지)
Step 5  ── 이미지 생성 ────────── Scripts (Gemini 3.1 Flash)
Step 6  ── 번역 ─────────────── Translator Agent x N (병렬, 양방향)
Step 7  ── PDF 조판 ─────────── Scripts (WeasyPrint, B5, 단행본 CSS)
Step 8  ── 웹 뷰어 ──────────── Scripts (PDF.js 기반)
        ══ Gate 2: 최종 리뷰 ══   (사용자 확인)
```

**핵심 동작:**

- Gate 1 거부 &rarr; 목차만 재실행 (리서치 보존)
- Gate 2 거부 &rarr; 지적된 챕터만 재편집 (부분 재생성)
- 이미지 생성 실패는 **non-blocking** (placeholder 삽입, 파이프라인 계속)
- Writer는 챕터당 최대 2&ndash;3개 이미지 마커 (유용한 다이어그램만)
- Editor가 프로덕션 잔재를 탐지하고 제거

---

## PDF 조판 품질

PDF 산출물은 **한국어 단행본 출판 기준**을 따릅니다:

| 항목 | 스펙 |
|------|------|
| 판형 | B5 (176 &times; 250 mm) |
| 여백 | 비대칭 &mdash; 안쪽 22mm &gt; 바깥쪽 18mm (제본용) |
| 본문 폰트 | Noto Serif CJK KR, 10pt, 행간 1.75 |
| 제목 폰트 | Pretendard (산세리프 대비) |
| 코드 폰트 | Fira Code, 9pt |
| 챕터 시작 | 오른쪽 페이지, 상단 30% 공백, 챕터 번호 + 제목 + 장식선 |
| 러닝 헤더 | 짝수 페이지: 책 제목(좌상) &bull; 홀수 페이지: 챕터 제목(우상) |
| 페이지 번호 | 짝수: 좌하 &bull; 홀수: 우하 |
| 목차 | 점선 리더 + 페이지 번호 |
| 본문 정렬 | 양쪽 정렬, `word-break: keep-all`, 문단 들여쓰기 1em |
| 테이블 | 가로선만 (세로선 없음) |
| 특수 페이지 | 표지, 속표지, 판권 페이지 |

---

## 빠른 시작

### 사전 준비

```bash
# macOS
brew install pango cairo gdk-pixbuf
brew install --cask font-noto-serif-cjk-kr font-fira-code

# 가상 환경 생성
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 환경 변수

```bash
# 이미지 생성(Step 5)에 필요 — 선택사항, 없으면 placeholder로 대체
echo 'GEMINI_API_KEY=your-key-here' > .env
echo 'IMAGE_MODEL=gemini-3.1-flash-image-preview' >> .env
```

### 실행

```bash
# 한국어 ebook + 법률 도메인 플러그인
/generate "Claude Code for Lawyers" --plugin legal --author "저자명"

# 영어 ebook, 범용 모드
/generate "Introduction to Python" --language en --author "Author Name"

# 중단된 파이프라인 재개
/resume
```

---

## 프로젝트 구조

```
.
├── CLAUDE.md                              # 오케스트레이터 — 파이프라인 상태 머신
│
├── .claude/
│   ├── agents/
│   │   ├── researcher/AGENT.md            # 리서치 에이전트
│   │   ├── architect/AGENT.md             # 목차 설계 에이전트
│   │   ├── writer/AGENT.md                # 챕터 작성 에이전트 (병렬)
│   │   ├── editor/AGENT.md                # 품질 검증 + 잔재 탐지 에이전트
│   │   └── translator/AGENT.md            # 양방향 KO/EN 번역 에이전트
│   │
│   ├── skills/
│   │   ├── web-research/                  # 웹 검색 전략
│   │   ├── reference-analyzer/scripts/    # .md/.pdf/.docx 파서
│   │   ├── code-example-validator/scripts/# 문법 검증
│   │   ├── quality-checker/               # 품질 루브릭
│   │   ├── image-generator/scripts/       # Gemini API 이미지 파이프라인
│   │   ├── pdf-builder/scripts/           # WeasyPrint 단행본 수준 PDF
│   │   └── web-viewer-builder/scripts/    # PDF.js 브라우저 뷰어
│   │
│   ├── plugins/
│   │   └── legal/                         # 법률 도메인 플러그인 (예시)
│   │       ├── PLUGIN.md
│   │       ├── research_sources.md
│   │       ├── quality_criteria.md
│   │       └── references/
│   │
│   └── commands/
│       ├── generate.md                    # /generate 진입점
│       └── resume.md                      # /resume 진입점
│
├── input/references/                      # 사용자 제공 소스 자료
├── output/                                # 파이프라인 산출물 (gitignored)
├── docs/                                  # GitHub Pages 배포
└── requirements.txt
```

---

## 도메인 플러그인 만드는 법

1. `.claude/plugins/legal/`을 `.claude/plugins/your-domain/`으로 복사
2. **`PLUGIN.md`** 수정 &mdash; 도메인 설명, 대상 독자, 작성 가이드라인
3. **`research_sources.md`** 수정 &mdash; 도메인별 리서치 질문과 소스
4. **`quality_criteria.md`** 수정 &mdash; 용어 기준, 필수 면책 조항, 검증 규칙
5. **`references/`**에 레퍼런스 자료 추가
6. 실행: `/generate "원하는 주제" --plugin your-domain`

---

## License

MIT
