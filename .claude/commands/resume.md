# Resume Pipeline

Resume an interrupted or paused ebook generation pipeline.

## Usage
```
/resume
```

## Execution

1. **Check for existing state**:
   - If `output/pipeline_state.json` does not exist:
     - "파이프라인 상태 파일이 없습니다. `/generate` 명령으로 새 파이프라인을 시작해주세요."
     - Exit

2. **Read and validate state**:
   - Read `output/pipeline_state.json`
   - Display current status:
     - Topic: {topic}
     - Plugin: {plugin or "없음"}
     - Last completed step: Step {N} ({name})
     - Started: {started_at}
     - Last updated: {updated_at}

3. **Validate artifacts**:
   - For each completed step, verify the output artifact exists on disk
   - If any artifact is missing, reset that step and all subsequent steps to "pending"
   - Report any reset steps to the user

4. **Resume execution**:
   - Identify the next pending step
   - Follow the Step Execution Protocol in CLAUDE.md from that step onward
   - If currently at a gate (Gate 1 or Gate 2), re-present the deliverables for review
