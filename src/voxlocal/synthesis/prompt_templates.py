"""Prompt templates and preset instructions for meeting synthesis."""


SYSTEM_INSTRUCTION = """You are VoxLocal, an offline ambient audio intelligence system.
Your job is to read meeting transcripts with timestamped speaker tags and generate clean, structured Markdown notes.

Strict Formatting Rules:
1. Write clearly and concisely in active voice.
2. Extract all concrete action items as checklist items: - [ ] @Person: Task description.
3. Capture key technical and architectural decisions, trade-offs, and agreements.
4. Do not invent details not mentioned in the transcript.
5. Do not include introductory phrases like "Here is the summary".
"""

PRESET_TEMPLATES: dict[str, str] = {
    "general": """Please analyze the following meeting transcript and produce a structured Markdown document:

# {title}

## Executive Summary
Brief paragraph summarizing the primary purpose and conclusions of this meeting.

## Key Discussion Points
- Detailed bullet points highlighting major discussion topics.

## Decisions Made
- Specific decisions confirmed by participants.

## Action Items
- [ ] @Owner: Action item description with context.

## Transcript Reference
(Summarized key quotes or timestamps if relevant)

Transcript:
{transcript}
""",
    "standup": """Please analyze the following sprint standup transcript and produce a structured Markdown document:

# {title}

## Quick Sync Overview
Summary of team progress and immediate goals.

## Updates by Participant
### {local_user} (You)
- Accomplishments:
- Today's focus:
- Blockers:

### Team / Remote Participants
- Updates and blockers:

## Blockers and Risks
- [ ] Immediate blockers requiring resolution:

## Action Items
- [ ] @Owner: Follow-up tasks.

Transcript:
{transcript}
""",
    "architecture_review": """Please analyze the following architecture review transcript and produce a structured Markdown document:

# {title}

## System Overview and Context
Context of the technical changes or architectural proposal.

## Evaluated Alternatives and Trade-offs
- Option A: Pros and cons discussed.
- Option B: Pros and cons discussed.

## Consensus Architectural Decisions
- Final technical choices agreed upon by the team.

## Open Questions and Unresolved Risks
- Items needing research, benchmarking, or follow-up discussion.

## Implementation Plan and Action Items
- [ ] @Owner: Technical task with delivery scope.

Transcript:
{transcript}
""",
    "1on1": """Please analyze the following 1-on-1 alignment transcript and produce a structured Markdown document:

# {title}

## Alignment Summary
High-level summary of discussion, progress, and morale.

## Project and Milestone Updates
- Current project deliverables and timeline tracking.

## Feedback and Discussion Points
- Key feedback, observations, or guidance shared.

## Professional Growth and Goals
- Learning goals, skill areas, or career topics discussed.

## Commitments and Action Items
- [ ] @Owner: Agreed next steps.

Transcript:
{transcript}
""",
    "client_discovery": """Please analyze the following client discovery transcript and produce a structured Markdown document:

# {title}

## Client Overview and Objectives
Primary business problem and goals stated by the client.

## Pain Points and Technical Constraints
- Existing bottlenecks, technical requirements, and limitations.

## Proposed Solutions and Scope
- Solutions presented, architecture alignment, and delivery phases.

## Commercial and Timeline Considerations
- Budget constraints, milestones, and target delivery dates.

## Immediate Next Steps
- [ ] @Owner: Deliverables, proposal updates, or meeting follow-ups.

Transcript:
{transcript}
""",
}


def get_prompt_template(preset: str = "general") -> str:
    """Retrieve prompt template by preset name, defaulting to 'general'."""
    return PRESET_TEMPLATES.get(preset.lower(), PRESET_TEMPLATES["general"])
