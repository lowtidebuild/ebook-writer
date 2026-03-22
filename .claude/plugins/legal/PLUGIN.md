# Legal Domain Plugin

## Domain
Legal Technology / AI for Legal Practice — Claude Code for Lawyers

## Description
코딩 경험이 전혀 없는 변호사를 위한 Claude Code 완전 입문서.
"AI 챗봇과 뭐가 다른지"부터 시작해서 VS Code 설치, Claude Code 셋팅, 실전 에이전트 구축까지 안내하는 실용 가이드.

## Target Audience
- **코딩 경험 제로**인 변호사 및 법률 전문가
- 터미널, 코드 에디터를 처음 접하는 사람
- "ChatGPT는 써봤지만 Claude Code는 뭔지 모르는" 수준

## Book Concept
- `input/references/` 폴더의 기존 문서를 참고하되, 그보다 **훨씬 더 고품질 + 긴 분량**으로 작성
- 기존 문서는 짧은 가이드 수준 → 이 책은 **본격적인 입문서** 수준

## Content Requirements

### 필수 포함 내용

1. **Claude Code란 무엇인가**
   - 기존 LLM(ChatGPT, Claude.ai 등)과 Claude Code의 근본적 차이
   - "대화형 AI" vs "코딩 에이전트"의 차이를 변호사가 이해할 수 있게
   - Claude Code가 법률 업무에 특히 유용한 이유

2. **VS Code 환경 설정 (처음부터)**
   - VS Code가 뭔지, 왜 이걸 쓰는지 (다른 방법도 있지만, 가장 쉬운 방법이라서)
   - VS Code 설치 (macOS / Windows)
   - Claude Code 확장 설치 및 셋팅
   - 터미널 기초 사용법 (변호사 눈높이)

3. **Claude Code 기초 사용법**
   - 첫 번째 대화 시작하기
   - 파일 읽기/쓰기/수정
   - 프롬프트 작성 요령 (법률 업무 맥락)

4. **실전 에이전트 빌드 예시: 게임 산업 특화 Legal Research Agent**
   - 처음부터 끝까지 실제 에이전트를 만드는 과정을 단계별로 안내
   - 게임 산업 법률 리서치(게임법, 확률형 아이템 규제, EULA 분석 등) 에이전트를 예시로
   - 디자인 문서 작성 → CLAUDE.md 구성 → 에이전트 파일 작성 → 테스트 → 개선
   - 변호사가 따라하면 자신의 업무에 맞는 에이전트를 직접 만들 수 있도록

5. **Design Document 작성법 (매우 중요)**
   - 왜 Design Doc이 에이전트 품질을 결정하는지
   - 아래 Prompt Library 링크를 안내:
     - **https://lowtidebuild.github.io/prompt-library/**
     - **Agent Builder 탭** → **8-11번 에이전트 설계자 프롬프트**
   - 이 프롬프트를 **Claude Project의 Instructions에 넣고**, Claude와 대화하며 Design Doc을 만드는 구체적 워크플로우
   - 좋은 Design Doc의 구조와 예시

6. **법률 윤리 & AI 사용 주의사항**
   - 비밀유지의무와 AI 도구
   - AI 출력물 검증 책임
   - 면책 조항

### Writing Guidelines

#### Tone & Approach
- 기술 용어를 처음 사용할 때 반드시 법률적 비유를 통해 설명
  - 예: "API는 법률 사무소 간 공문서 교환 프로토콜과 같습니다"
  - 예: "터미널은 법원 서기에게 구두로 지시하는 것과 같습니다"
- "여러 방법이 있지만, 가장 쉬운 이 방법을 알려드립니다" 취지 유지
- 전문적이되 접근 가능한 톤
- 각 단계에서 "이걸 왜 하는지" 설명 먼저, "어떻게 하는지" 그 다음

#### Code Examples
- 법률 업무 맥락의 예시 사용 (계약 검토, 판례 검색, 규제 분석 등)
- 코드 예시 전에 "이 코드가 하는 일"을 자연어로 먼저 설명
- 실행 결과를 함께 보여주어 직접 실행하지 않아도 이해 가능하게
- 스크린샷이 필요한 부분에 `[IMAGE: ...]` 마커 적극 사용

#### Legal-Specific Requirements
- AI 도구 사용 시 윤리적 주의사항을 적절한 곳에 자연스럽게 포함
- 면책 조항: AI 도구는 법률 자문을 대체하지 않음을 명시
- 실제 사건/판례 인용 시 정확한 형식 준수

## Verification Policy

When the Researcher agent performs cross-verification of factual claims, the following authoritative sources are treated as "super-sources" — a single source from this list satisfies the verification requirement without needing a second independent source:

- **국가법령정보센터** (law.go.kr) — Korean legislation database
- **대한민국 법원 종합법률정보** (glaw.scourt.go.kr) — Korean court decisions
- **Anthropic official documentation** (docs.anthropic.com) — Claude/Claude Code documentation
- **VS Code official documentation** (code.visualstudio.com) — VS Code documentation

All other sources require standard cross-verification (2+ independent sources).
