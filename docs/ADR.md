# 아키텍처 결정 기록

## 운영 규칙
- 첫 세 개의 ADR은 이 파일에 유지합니다.
- 네 번째 ADR이 필요해지면 `docs/adr/0001-title.md` 형식으로 분리하고, 이 파일은 인덱스로 유지합니다.
- 기록된 기술 결정을 뒤집기 전에 ADR을 추가하거나 갱신합니다.

## ADR 목록

### ADR-001: Local-first MVP 저장 방식
**상태**: accepted

**맥락**: MVP는 단일 개인 사용자를 위한 것이며, 기밀 샘플 도면을 cloud deployment 없이 다룰 수 있어야 합니다.

**결정**: 구조화된 상태에는 SQLite를 사용하고, 업로드 PDF, 렌더링된 페이지 이미지, export된 Excel workbook에는 로컬 파일 시스템을 사용합니다.

**이유**: 설정이 단순하고 외부 인프라가 필요 없으며, 개인용 MVP에 맞습니다.

**트레이드오프**: 다중 사용자 워크플로우, 원격 협업, production-grade migration 운영은 의도적으로 미룹니다.

### ADR-002: Draft-first 산출 워크플로우
**상태**: accepted

**맥락**: PDF extraction, finish schedule parsing, drawing measurement는 모호할 수 있습니다.

**결정**: 시스템은 수정 가능한 draft를 생성하고 불확실한 데이터는 `DRAFT` 또는 `NEEDS_REVIEW`로 표시합니다. 사용자의 행동만 row를 `CONFIRMED`로 바꿀 수 있습니다.

**이유**: 사용자가 export 전에 takeoff를 검증한다는 제품 원칙에 맞습니다.

**트레이드오프**: 워크플로우가 덜 자동적이지만, 불확실한 추출 결과를 최종 견적 데이터처럼 보여주는 위험을 피합니다.

### ADR-003: Sheet title과 page evidence 기반 역할 분류
**상태**: accepted

**맥락**: Finish schedule과 plan은 도면 세트마다 다른 sheet number를 사용할 수 있습니다.

**결정**: hard-coded sheet number가 아니라 title/page-text keyword와 supporting table evidence를 사용해 sheet role을 분류합니다.

**이유**: 같은 역할이 프로젝트에 따라 AE401, AE402, AE601 또는 다른 sheet number로 나타날 수 있습니다.

**트레이드오프**: 일반적이지 않은 sheet title에는 manual correction이 필요할 수 있습니다. confidence와 review status는 data model에 계속 남깁니다.
