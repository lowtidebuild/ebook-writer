# Generate Ebook

Generate a complete ebook from the given topic.

## Usage
```
/generate <topic> [--plugin <domain>] [--language <ko|en>]
```

## Examples
```
/generate "Claude Code for Lawyers" --plugin legal
/generate "Claude Code for Lawyers" --plugin legal --language ko
/generate "Introduction to Python Programming" --language en
/generate "Modern Web Development with React"
```

## Execution

1. **Parse arguments**:
   - Extract the topic from $ARGUMENTS
   - If `--plugin <domain>` is specified, verify `.claude/plugins/<domain>/PLUGIN.md` exists
   - If no plugin specified, auto-detect: check if any plugin directory exists in `.claude/plugins/`
   - If `--language <code>` is specified, set as `primary_language` (default: `ko`)
     - `ko` → primary: Korean, secondary: English
     - `en` → primary: English, secondary: Korean

2. **Check for existing pipeline**:
   - If `output/pipeline_state.json` exists, offer to resume:
     - "기존 파이프라인이 감지되었습니다 (토픽: {topic}, 마지막 완료 단계: Step {N}). 이어서 진행할까요, 아니면 새로 시작할까요?"
     - If resume: follow the Startup Protocol in CLAUDE.md
     - If restart: delete `output/pipeline_state.json` and all output subdirectory contents

3. **Initialize new pipeline**:
   - Create `output/pipeline_state.json` per the schema in CLAUDE.md
   - Ensure all output subdirectories exist

4. **Execute pipeline**:
   - Follow the Step Execution Protocol in CLAUDE.md (Steps 1-8 with Gates)
   - Each step updates the state file upon completion
   - At each gate, pause and wait for user input

5. **Completion**:
   - When Gate 2 is approved, display final summary with all deliverable paths
