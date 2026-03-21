# SKILL: Team Capacity Planning

## Purpose
Assess whether a team has sufficient capacity and skills to deliver a project phase, and recommend additions/modifications when gaps exist.

## When to Use
- Pre-sprint planning when scope is unclear
- After audit reports reveal technical debt
- Before committing to roadmap timelines
- When stakeholders ask "can we deliver X by Y?"

## Assessment Framework

### Step 1: Gap Inventory
For each audit finding, categorize:
- **CRITICAL:** Blocks deployment (security, data loss risk)
- **HIGH:** Blocks feature development (missing infrastructure)
- **MEDIUM:** Reduces quality (test coverage, documentation)
- **LOW:** Nice-to-have (polish, optimization)

### Step 2: Effort Estimation
Convert gaps to hours per team member:
```
Gap → Required Skill → Team Member → Effort (hours)
```

Use these multipliers for uncertainty:
- Known work: 1x estimate
- Partially explored: 1.5x estimate
- Unknown (R&D): 2x estimate

### Step 3: Capacity Analysis
Per-member weekly capacity: ~30 productive hours (40h - meetings/interrupts)

Calculate:
- Total effort required per member
- Weeks to complete at 80% allocation
- Identify bottlenecks (>6 weeks = risky)

### Step 4: Decision Matrix
For each identified gap, answer:
1. Is this skill within existing team?
2. Is it learnable in <1 week?
3. Does hiring add value > coordination cost?
4. Can it be outsourced/contracted?

### Step 5: Recommendations
- **KEEP:** Team sufficient, prioritize work
- **TRAIN:** Team has capacity, needs skill-up
- **CONTRACT:** Short-term specialist (4-8 weeks)
- **HIRE:** Long-term gap, justified by roadmap

## Output Template

```markdown
## Team Assessment Summary
{1-2 sentence verdict}

## Critical Gaps Analysis
| Gap | Impact | Owner | Effort | Can Handle? |
|-----|--------|-------|--------|-------------|
| ... | ... | ... | ... | ✅/⚠️/❌ |

## Workload Reality Check
{Per-member analysis}

## Recommended Modifications
{KEEP / ADD role / CONTRACT specialist}

## Roadmap Implications
{How team composition affects timeline}
```

## Red Flags to Watch
- Single-person bottleneck (>50% of critical work)
- Multiple members at >100% capacity
- Security work deprioritized for features
- Test debt growing faster than coverage
- No CI/CD automation

## Anti-Patterns
- Adding headcount to solve timeline problems (Brooks's Law)
- Assuming contractors ramp instantly
- Ignoring coordination overhead of new members
- Not accounting for onboarding time

## Success Metrics
- Work distributed across ≥2 members
- No member >120% capacity for >2 weeks
- Critical path has backup (no single points of failure)
- Timeline achievable with 20% buffer
