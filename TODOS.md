# TODOS

## v3 Ground Truth Architecture

### Phase 4에서 처리
- [ ] **build_pdf.py 하드코딩 날짜 수정** — `'2026. 3. 19. (v2)'`를 `datetime.now()` 기반 동적 생성으로 변경. line ~488 근처. Phase 4에서 build_pdf.py 각주/참고문헌 확장 시 함께 수정.

### 결정 완료
- [x] **인용 형식**: 간소화된 웹링크 형식 확정 (APA/MLA 아닌 실용적 형식). 기술서 독자 특성에 맞춤.
- [x] **교차 검증 범위**: 핵심 유형(통계/날짜/법률/API 스펙)만 검증. 70% threshold 안정 달성 시 확장 검토.
