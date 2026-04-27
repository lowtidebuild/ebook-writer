# TODOS

## 구현된 품질 제어

### Eng Review 발견사항 (2026-03-30)
- [x] **pytest 테스트 스위트** — `tests/` 디렉토리 신규. pipeline state, outline, claims, chapter packs, final preflight, image pipeline, PDF/viewer, validator 경로 테스트 추가 및 통과 완료.
- [x] **citations.json ID 검증** — `validate_references.py`에 citation ID 존재 여부 검증 추가. `--citations` 인자 및 `output/research/citations.json` 자동 탐지 지원.
- [x] **Gate 2 전 자동 검증** — `CLAUDE.md` Gate 2 직전에 체크리스트 추가: 모든 챕터 포함 여부, `[IMAGE:]` 마커 잔존 여부, 각주 렌더링 완전성.
- [x] **코드 블록 파싱 공유 모듈** — `validate_code.py`와 `validate_references.py`의 코드 블록 파싱 로직을 `markdown_utils.py`로 추출. DRY + O(n²) 성능 개선.
- [x] **순환 의존성 감지** — `CLAUDE.md` Step 3 웨이브 빌드에 DAG 순환 감지 절차 추가. 순환 발견 시 에러 메시지 + 에스컬레이션 명시.

### v4 검토사항
- [x] **Docker 샌드박스** — `validate_code.py --execute`에 Docker 백엔드 추가. `--network none`, read-only rootfs, tmpfs workspace, capability drop 적용. 로컬 process backend는 `--allow-unsafe-process` 명시 opt-in에서만 사용.
- [x] **문서/프롬프트 정리** — pipeline 밖 skill routing 제거, `.venv/bin/python3` 실행 예시 통일, README/design/migration guide를 실제 구현 기준으로 동기화.

### 완료
- [x] **build_pdf.py 하드코딩 날짜 수정** — `datetime.now()` 기반 동적 생성으로 변경 완료. build_pdf.py:527.
- [x] **인용 형식**: 간소화된 웹링크 형식 확정 (APA/MLA 아닌 실용적 형식). 기술서 독자 특성에 맞춤.
- [x] **교차 검증 범위**: 핵심 유형(통계/날짜/법률/API 스펙)만 검증. 70% threshold 안정 달성 시 확장 검토.
