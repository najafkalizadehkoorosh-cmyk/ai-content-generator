# AI Router Studio — Architecture

USER REQUEST
→ PROMPT COMPILER
→ TASK PLANNER
→ DIFFICULTY ENGINE
→ TOKEN OPTIMIZER
→ PREVIEW
→ USER APPROVAL
→ EXECUTOR
→ REVIEWER
→ FINAL OUTPUT

## Non-negotiable
- Zero-cost by default
- No silent build/change/deploy
- Reuse existing open-source components before custom code
- Cache and summarize between workers
- Send only relevant context
- Choose model by difficulty and capability fit
- Paid providers are disabled by default

## Approval gates
- Build/create/modify
- Delete
- Deploy/publish
- Material plan changes

## Provider abstraction

ProviderAdapter:
- id
- capabilities
- estimate(input)
- execute(task, context)
- available()