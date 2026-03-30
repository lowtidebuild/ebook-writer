# TODOS

## v3 Ground Truth Architecture

### Eng Review 발견사항 (2026-03-30)
- [ ] **pytest 테스트 스위트** — 42개 코드 경로 커버리지. tests/ 디렉토리 신규. 우선순위: validate_code.py > validate_references.py > generate_prompts.py > build_pdf.py. 테스트 플랜: `~/.gstack/projects/lowtidebuild-ebook-writer/main-eng-review-test-plan-*.md`
- [ ] **citations.json ID 검증** — validate_references.py에 citation ID 존재 여부 검증 추가. Writer가 [^N]을 넣었는데 citations.json에 해당 ID가 없으면 에러 보고.
- [ ] **Gate 2 전 자동 검증** — CLAUDE.md Gate 2 직전에 체크리스트 추가: 모든 챕터 포함 여부, [IMAGE:] 마커 잔존 여부, 각주 렌더링 완전성.
- [ ] **코드 블록 파싱 공유 모듈** — validate_code.py와 validate_references.py의 코드 블록 파싱 로직을 공유 모듈(markdown_utils.py)로 추출. DRY + O(n²) 성능 개선.
- [ ] **순환 의존성 감지** — CLAUDE.md Step 3 웨이브 빌드에 DAG 순환 감지 추가. 순환 발견 시 에러 메시지 + 에스컬레이션.

### v4 검토사항
- [ ] **Docker 샌드박스** — :runnable 코드 실행 시 네트워크 격리/파일시스템 제한. 현재는 subprocess + 30초 타임아웃만 사용. 오픈소스 프로젝트로서 보안 강화 필요 시 Docker/nsjail 도입 검토.

### 완료
- [x] **build_pdf.py 하드코딩 날짜 수정** — `datetime.now()` 기반 동적 생성으로 변경 완료. build_pdf.py:527.
- [x] **인용 형식**: 간소화된 웹링크 형식 확정 (APA/MLA 아닌 실용적 형식). 기술서 독자 특성에 맞춤.
- [x] **교차 검증 범위**: 핵심 유형(통계/날짜/법률/API 스펙)만 검증. 70% threshold 안정 달성 시 확장 검토.
