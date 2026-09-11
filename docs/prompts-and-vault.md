# Prompt Engineering and Vault Markdown Format

This document details how VoxLocal structures meeting prompts and writes notes into your local knowledge base.

## Obsidian Frontmatter Format

Every meeting note created by VoxLocal begins with standard YAML frontmatter:

```yaml
---
title: "Architecture Review: Payment Gateway Redesign"
date: 2026-09-12
time: "14:30:00"
duration: "00:42:15"
preset: architecture_review
participants:
  - "You (Local)"
  - "Remote Speaker 1"
  - "Remote Speaker 2"
stats:
  total_words: 4120
  talk_time_you: "35%"
  talk_time_remote: "65%"
tags:
  - meeting
  - architecture_review
  - voxlocal
---
```

## Prompt Presets

VoxLocal structures meeting prompts according to the selected meeting type.

### 1. General (`general`)
Standard technical meeting template:
- Context and meeting objective
- Discussion summary
- Decisions reached
- Action items checklist with assignees and context

### 2. Standup (`standup`)
Sprint sync format:
- Yesterday's accomplishments
- Today's plan
- Identified blockers and dependencies

### 3. Architecture Review (`architecture_review`)
System design and technical evaluation:
- Proposed technical design
- Evaluated options and trade-offs
- Accepted consensus decisions
- Open questions and follow-up investigations
- Implementation tasks

### 4. One-on-One (`1on1`)
Manager or peer alignment:
- Project updates and milestones
- Feedback points
- Career and skill goals
- Personal action items

### 5. Client Discovery (`client_discovery`)
External business conversations:
- Client background and goals
- Identified pain points and requirements
- Proposed technical solutions
- Budget and timeline notes
- Next commercial or technical steps

## Offline Extractive Fallback

When an Ollama server is unreachable, VoxLocal runs an internal deterministic extractor:
- Detects action items through regular expression patterns (e.g., "I will", "let's make sure to", "assign this to").
- Identifies questions asked during the call.
- Calculates exact speaking ratios between your microphone and remote participants.
- Embeds the full verbatim transcript with timestamps.
