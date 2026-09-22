---
title: "ARCHITECTURE.md | alexeykrol/claude-code-starter"
source: "https://deepwiki.com/alexeykrol/claude-code-starter/4.5-architecture.md"
author:
  - "[[DeepWiki]]"
published: 2025-10-26
created: 2026-09-23
description: "This page documents the `ARCHITECTURE.md` template file, which serves as the authoritative source for design decisions and architectural rationale in the Claude Code Starter framework. ARCHITECTURE.md"
tags:
  - "clippings"
---
[DeepWiki](https://deepwiki.com/)

Index your code with

Devin

- [Overview](https://deepwiki.com/alexeykrol/claude-code-starter/1-overview)
- [Getting Started](https://deepwiki.com/alexeykrol/claude-code-starter/2-getting-started)
- [Installation](https://deepwiki.com/alexeykrol/claude-code-starter/2.1-installation)
- [First Steps](https://deepwiki.com/alexeykrol/claude-code-starter/2.2-first-steps)
- [Core Concepts](https://deepwiki.com/alexeykrol/claude-code-starter/3-core-concepts)
- [Meta-Documentation Framework](https://deepwiki.com/alexeykrol/claude-code-starter/3.1-meta-documentation-framework)
- [Cold Start Protocol](https://deepwiki.com/alexeykrol/claude-code-starter/3.2-cold-start-protocol)
- [Modular Architecture](https://deepwiki.com/alexeykrol/claude-code-starter/3.3-modular-architecture)
- [Token Economics](https://deepwiki.com/alexeykrol/claude-code-starter/3.4-token-economics)
- [Template Files](https://deepwiki.com/alexeykrol/claude-code-starter/4-template-files)
- [CLAUDE.md](https://deepwiki.com/alexeykrol/claude-code-starter/4.1-claude.md)
- [PROJECT\_SNAPSHOT.md](https://deepwiki.com/alexeykrol/claude-code-starter/4.2-project_snapshot.md)
- [BACKLOG.md](https://deepwiki.com/alexeykrol/claude-code-starter/4.3-backlog.md)
- [PROJECT\_INTAKE.md](https://deepwiki.com/alexeykrol/claude-code-starter/4.4-project_intake.md)
- [ARCHITECTURE.md](https://deepwiki.com/alexeykrol/claude-code-starter/4.5-architecture.md)
- [SECURITY.md](https://deepwiki.com/alexeykrol/claude-code-starter/4.6-security.md)
- [Supporting Templates](https://deepwiki.com/alexeykrol/claude-code-starter/4.7-supporting-templates)
- [Migration System](https://deepwiki.com/alexeykrol/claude-code-starter/5-migration-system)
- [Migration Overview](https://deepwiki.com/alexeykrol/claude-code-starter/5.1-migration-overview)
- [Migration Process](https://deepwiki.com/alexeykrol/claude-code-starter/5.2-migration-process)
- [Conflict Resolution](https://deepwiki.com/alexeykrol/claude-code-starter/5.3-conflict-resolution)
- [Slash Commands](https://deepwiki.com/alexeykrol/claude-code-starter/6-slash-commands)
- [Development Commands](https://deepwiki.com/alexeykrol/claude-code-starter/6.1-development-commands)
- [Migration Commands](https://deepwiki.com/alexeykrol/claude-code-starter/6.2-migration-commands)
- [Release and Security Commands](https://deepwiki.com/alexeykrol/claude-code-starter/6.3-release-and-security-commands)
- [Development Workflows](https://deepwiki.com/alexeykrol/claude-code-starter/7-development-workflows)
- [Sprint Lifecycle](https://deepwiki.com/alexeykrol/claude-code-starter/7.1-sprint-lifecycle)
- [Sprint Completion Enforcement](https://deepwiki.com/alexeykrol/claude-code-starter/7.2-sprint-completion-enforcement)
- [Documentation Synchronization](https://deepwiki.com/alexeykrol/claude-code-starter/7.3-documentation-synchronization)
- [Advanced Topics](https://deepwiki.com/alexeykrol/claude-code-starter/8-advanced-topics)
- [Token Optimization Strategies](https://deepwiki.com/alexeykrol/claude-code-starter/8.1-token-optimization-strategies)
- [v2.0 Roadmap](https://deepwiki.com/alexeykrol/claude-code-starter/8.2-v2.0-roadmap)
- [Reference](https://deepwiki.com/alexeykrol/claude-code-starter/9-reference)
- [Complete File Structure](https://deepwiki.com/alexeykrol/claude-code-starter/9.1-complete-file-structure)
- [Version History](https://deepwiki.com/alexeykrol/claude-code-starter/9.2-version-history)

## ARCHITECTURE.md

Relevant source files
- [Init/ARCHITECTURE.md](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/Init/ARCHITECTURE.md?plain=1)
- [Init/BACKLOG.md](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/Init/BACKLOG.md?plain=1)
- [README.md](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/README.md?plain=1)
- [init\_eng/ARCHITECTURE.md](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1)
- [init\_eng/BACKLOG.md](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/BACKLOG.md?plain=1)

## Purpose and Scope

This page documents the template file, which serves as the authoritative source for **design decisions and architectural rationale** in the Claude Code Starter framework. ARCHITECTURE.md answers the question "WHY" - explaining technology choices, design principles, and system structure - rather than "WHAT" operational tasks need completion.

**Scope boundaries:**

- **This file covers:** Technology stack justification, module design philosophy, architectural patterns, decision rationale
- **For operational tasks and checklists:** See [BACKLOG.md](https://deepwiki.com/alexeykrol/claude-code-starter/4.3-backlog.md)
- **For current project state:** See [PROJECT\_SNAPSHOT.md](https://deepwiki.com/alexeykrol/claude-code-starter/4.2-project_snapshot.md)
- **For security practices:** See [SECURITY.md](https://deepwiki.com/alexeykrol/claude-code-starter/4.6-security.md)

**Key distinction:** ARCHITECTURE.md is a **reference document** (design rationale), while BACKLOG.md is an **action plan** (implementation tasks). This separation prevents AI agents from confusing "why we chose React" with "implement React component X."

Sources: [init\_eng/ARCHITECTURE.md1-24](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L1-L24) [README.md109-125](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/README.md?plain=1#L109-L125)

---

## Role in the Meta-Documentation Framework

ARCHITECTURE.md occupies Layer 4 (Reference & Standards) in the documentation hierarchy, designated with 🔑 as a "Single Source of Truth" for architectural decisions.

### Architectural Decision Authority Diagram

```
#mermaid-o2o0ywloflr{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;fill:#333;}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#mermaid-o2o0ywloflr .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#mermaid-o2o0ywloflr .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#mermaid-o2o0ywloflr .error-icon{fill:#dddddd;}#mermaid-o2o0ywloflr .error-text{fill:#222222;stroke:#222222;}#mermaid-o2o0ywloflr .edge-thickness-normal{stroke-width:1px;}#mermaid-o2o0ywloflr .edge-thickness-thick{stroke-width:3.5px;}#mermaid-o2o0ywloflr .edge-pattern-solid{stroke-dasharray:0;}#mermaid-o2o0ywloflr .edge-thickness-invisible{stroke-width:0;fill:none;}#mermaid-o2o0ywloflr .edge-pattern-dashed{stroke-dasharray:3;}#mermaid-o2o0ywloflr .edge-pattern-dotted{stroke-dasharray:2;}#mermaid-o2o0ywloflr .marker{fill:#999;stroke:#999;}#mermaid-o2o0ywloflr .marker.cross{stroke:#999;}#mermaid-o2o0ywloflr svg{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;}#mermaid-o2o0ywloflr p{margin:0;}#mermaid-o2o0ywloflr .label{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;color:#333;}#mermaid-o2o0ywloflr .cluster-label text{fill:#444;}#mermaid-o2o0ywloflr .cluster-label span{color:#444;}#mermaid-o2o0ywloflr .cluster-label span p{background-color:transparent;}#mermaid-o2o0ywloflr .label text,#mermaid-o2o0ywloflr span{fill:#333;color:#333;}#mermaid-o2o0ywloflr .node rect,#mermaid-o2o0ywloflr .node circle,#mermaid-o2o0ywloflr .node ellipse,#mermaid-o2o0ywloflr .node polygon,#mermaid-o2o0ywloflr .node path{fill:#ffffff;stroke:#dddddd;stroke-width:1px;}#mermaid-o2o0ywloflr .rough-node .label text,#mermaid-o2o0ywloflr .node .label text,#mermaid-o2o0ywloflr .image-shape .label,#mermaid-o2o0ywloflr .icon-shape .label{text-anchor:middle;}#mermaid-o2o0ywloflr .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#mermaid-o2o0ywloflr .rough-node .label,#mermaid-o2o0ywloflr .node .label,#mermaid-o2o0ywloflr .image-shape .label,#mermaid-o2o0ywloflr .icon-shape .label{text-align:center;}#mermaid-o2o0ywloflr .node.clickable{cursor:pointer;}#mermaid-o2o0ywloflr .root .anchor path{fill:#999!important;stroke-width:0;stroke:#999;}#mermaid-o2o0ywloflr .arrowheadPath{fill:#0b0b0b;}#mermaid-o2o0ywloflr .edgePath .path{stroke:#999;stroke-width:2.0px;}#mermaid-o2o0ywloflr .flowchart-link{stroke:#999;fill:none;}#mermaid-o2o0ywloflr .edgeLabel{background-color:#ffffff;text-align:center;}#mermaid-o2o0ywloflr .edgeLabel p{background-color:#ffffff;}#mermaid-o2o0ywloflr .edgeLabel rect{opacity:0.5;background-color:#ffffff;fill:#ffffff;}#mermaid-o2o0ywloflr .labelBkg{background-color:rgba(255, 255, 255, 0.5);}#mermaid-o2o0ywloflr .cluster rect{fill:#f8f8f8;stroke:#dddddd;stroke-width:1px;}#mermaid-o2o0ywloflr .cluster text{fill:#444;}#mermaid-o2o0ywloflr .cluster span{color:#444;}#mermaid-o2o0ywloflr div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:12px;background:#dddddd;border:1px solid hsl(0, 0%, 76.6666666667%);border-radius:2px;pointer-events:none;z-index:100;}#mermaid-o2o0ywloflr .flowchartTitleText{text-anchor:middle;font-size:18px;fill:#333;}#mermaid-o2o0ywloflr rect.text{fill:none;stroke-width:0;}#mermaid-o2o0ywloflr .icon-shape,#mermaid-o2o0ywloflr .image-shape{background-color:#ffffff;text-align:center;}#mermaid-o2o0ywloflr .icon-shape p,#mermaid-o2o0ywloflr .image-shape p{background-color:#ffffff;padding:2px;}#mermaid-o2o0ywloflr .icon-shape rect,#mermaid-o2o0ywloflr .image-shape rect{opacity:0.5;background-color:#ffffff;fill:#ffffff;}#mermaid-o2o0ywloflr .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#mermaid-o2o0ywloflr .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#mermaid-o2o0ywloflr .nodeLabel p,#mermaid-o2o0ywloflr .edgeLabel p{color:inherit;}#mermaid-o2o0ywloflr :root{--mermaid-font-family:"trebuchet ms",verdana,arial,sans-serif;}AI Agent Consultation FlowLayer 3: PlanningLayer 4: Reference & StandardsLayer 2: Operational StateInforms design decisionsDesign patterns forModule structure forPlanning methodology1. Check tasks2. Understand WHY3. Follow patterns4. Apply securityBACKLOG.md
(WHAT to build)PROJECT_SNAPSHOT.md
(WHERE we are)ARCHITECTURE.md
(WHY & HOW)SECURITY.md
(Security rules)WORKFLOW.md
(Processes)PROJECT_INTAKE.md
(Requirements)DEVELOPMENT_PLAN_TEMPLATE.md
(Planning methodology)AI Agent
```

**Consultation sequence during development:**

1. **BACKLOG.md** - "What task am I working on?"
2. **ARCHITECTURE.md** - "What design patterns should I follow?"
3. **SECURITY.md** - "What security rules apply?"
4. Implementation begins only after consulting reference layer

Sources: [init\_eng/ARCHITECTURE.md9-23](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L9-L23) [README.md116](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/README.md?plain=1#L116-L116)

---

## File Structure and Sections

ARCHITECTURE.md follows a hierarchical structure with 15+ major sections, each serving a specific documentation purpose.

### Section Hierarchy Table

| Section | Purpose | Update Trigger | Template Lines |
| --- | --- | --- | --- |
| **Technology Stack** | Document frontend/backend choices | Initial setup, major tech changes | [init\_eng/ARCHITECTURE.md25-58](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L25-L58) |
| **Project Structure** | Directory layout and organization | Project initialization, refactoring | [init\_eng/ARCHITECTURE.md60-88](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L60-L88) |
| **Core Architecture Decisions** | ADR-style decision log | Every architectural decision | [init\_eng/ARCHITECTURE.md90-139](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L90-L139) |
| **Key Services & Components** | Document major system components | New service creation | [init\_eng/ARCHITECTURE.md140-181](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L140-L181) |
| **Data Flow & Integration Patterns** | User flows and data pipelines | New integration, flow changes | [init\_eng/ARCHITECTURE.md183-217](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L183-L217) |
| **Development Standards** | Code organization, naming, patterns | Standards evolution | [init\_eng/ARCHITECTURE.md219-248](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L219-L248) |
| **Module Architecture** | LEGO block philosophy, module catalog | Core to token optimization | [init\_eng/ARCHITECTURE.md250-446](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L250-L446) |
| **Module Testing** | Isolated testing approach | Testing methodology changes | [init\_eng/ARCHITECTURE.md571-733](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L571-L733) |
| **Database Schema** | Tables, relationships, security | Schema changes | [init\_eng/ARCHITECTURE.md448-473](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L448-L473) |
| **Security Architecture** | Auth, authorization, data protection | Security model changes | [init\_eng/ARCHITECTURE.md475-499](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L475-L499) |
| **Deployment Architecture** | Environments, CI/CD, variables | Deployment changes | [init\_eng/ARCHITECTURE.md501-525](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L501-L525) |
| **State Management** | Global/local state patterns | State architecture changes | [init\_eng/ARCHITECTURE.md527-547](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L527-L547) |
| **ADR (Architecture Decision Records)** | Formal decision documentation | Major architectural decisions | [init\_eng/ARCHITECTURE.md749-758](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L749-L758) |
| **Design Patterns** | Repository, Factory, Observer, etc. | Pattern adoption | [init\_eng/ARCHITECTURE.md762-771](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L762-L771) |

Sources: [init\_eng/ARCHITECTURE.md1-789](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L1-L789)

### Information Flow Between Sections

```
#mermaid-rrzifms0hi{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;fill:#333;}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#mermaid-rrzifms0hi .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#mermaid-rrzifms0hi .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#mermaid-rrzifms0hi .error-icon{fill:#dddddd;}#mermaid-rrzifms0hi .error-text{fill:#222222;stroke:#222222;}#mermaid-rrzifms0hi .edge-thickness-normal{stroke-width:1px;}#mermaid-rrzifms0hi .edge-thickness-thick{stroke-width:3.5px;}#mermaid-rrzifms0hi .edge-pattern-solid{stroke-dasharray:0;}#mermaid-rrzifms0hi .edge-thickness-invisible{stroke-width:0;fill:none;}#mermaid-rrzifms0hi .edge-pattern-dashed{stroke-dasharray:3;}#mermaid-rrzifms0hi .edge-pattern-dotted{stroke-dasharray:2;}#mermaid-rrzifms0hi .marker{fill:#999;stroke:#999;}#mermaid-rrzifms0hi .marker.cross{stroke:#999;}#mermaid-rrzifms0hi svg{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;}#mermaid-rrzifms0hi p{margin:0;}#mermaid-rrzifms0hi .label{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;color:#333;}#mermaid-rrzifms0hi .cluster-label text{fill:#444;}#mermaid-rrzifms0hi .cluster-label span{color:#444;}#mermaid-rrzifms0hi .cluster-label span p{background-color:transparent;}#mermaid-rrzifms0hi .label text,#mermaid-rrzifms0hi span{fill:#333;color:#333;}#mermaid-rrzifms0hi .node rect,#mermaid-rrzifms0hi .node circle,#mermaid-rrzifms0hi .node ellipse,#mermaid-rrzifms0hi .node polygon,#mermaid-rrzifms0hi .node path{fill:#ffffff;stroke:#dddddd;stroke-width:1px;}#mermaid-rrzifms0hi .rough-node .label text,#mermaid-rrzifms0hi .node .label text,#mermaid-rrzifms0hi .image-shape .label,#mermaid-rrzifms0hi .icon-shape .label{text-anchor:middle;}#mermaid-rrzifms0hi .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#mermaid-rrzifms0hi .rough-node .label,#mermaid-rrzifms0hi .node .label,#mermaid-rrzifms0hi .image-shape .label,#mermaid-rrzifms0hi .icon-shape .label{text-align:center;}#mermaid-rrzifms0hi .node.clickable{cursor:pointer;}#mermaid-rrzifms0hi .root .anchor path{fill:#999!important;stroke-width:0;stroke:#999;}#mermaid-rrzifms0hi .arrowheadPath{fill:#0b0b0b;}#mermaid-rrzifms0hi .edgePath .path{stroke:#999;stroke-width:2.0px;}#mermaid-rrzifms0hi .flowchart-link{stroke:#999;fill:none;}#mermaid-rrzifms0hi .edgeLabel{background-color:#ffffff;text-align:center;}#mermaid-rrzifms0hi .edgeLabel p{background-color:#ffffff;}#mermaid-rrzifms0hi .edgeLabel rect{opacity:0.5;background-color:#ffffff;fill:#ffffff;}#mermaid-rrzifms0hi .labelBkg{background-color:rgba(255, 255, 255, 0.5);}#mermaid-rrzifms0hi .cluster rect{fill:#f8f8f8;stroke:#dddddd;stroke-width:1px;}#mermaid-rrzifms0hi .cluster text{fill:#444;}#mermaid-rrzifms0hi .cluster span{color:#444;}#mermaid-rrzifms0hi div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:12px;background:#dddddd;border:1px solid hsl(0, 0%, 76.6666666667%);border-radius:2px;pointer-events:none;z-index:100;}#mermaid-rrzifms0hi .flowchartTitleText{text-anchor:middle;font-size:18px;fill:#333;}#mermaid-rrzifms0hi rect.text{fill:none;stroke-width:0;}#mermaid-rrzifms0hi .icon-shape,#mermaid-rrzifms0hi .image-shape{background-color:#ffffff;text-align:center;}#mermaid-rrzifms0hi .icon-shape p,#mermaid-rrzifms0hi .image-shape p{background-color:#ffffff;padding:2px;}#mermaid-rrzifms0hi .icon-shape rect,#mermaid-rrzifms0hi .image-shape rect{opacity:0.5;background-color:#ffffff;fill:#ffffff;}#mermaid-rrzifms0hi .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#mermaid-rrzifms0hi .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#mermaid-rrzifms0hi .nodeLabel p,#mermaid-rrzifms0hi .edgeLabel p{color:inherit;}#mermaid-rrzifms0hi :root{--mermaid-font-family:"trebuchet ms",verdana,arial,sans-serif;}SpecializedImplementation LayerDesign LayerFoundationReferencesReferencesReferencesTechnology Stack
React, TypeScript, SupabaseProject Structure
/src/components, /libCore Architecture Decisions
ADR entriesDesign Patterns
Repository, FactoryDevelopment Standards
Naming, organizationModule Architecture
Auth, API, PagesModule Testing
Isolated testingDatabase Schema
Tables, RLSSecurity Architecture
Auth flowDeployment
CI/CD pipelineState Management
Zustand, Context
```

**Reading order for AI agents:**

1. Technology Stack → Understand tools available
2. Module Architecture → Understand system decomposition
3. Development Standards → Apply coding conventions
4. Specific sections (DB, Security) as needed for current task

Sources: [init\_eng/ARCHITECTURE.md25-789](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L25-L789)

---

## Module Architecture Philosophy

The **Module Architecture** section ([init\_eng/ARCHITECTURE.md250-446](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L250-L446)) is the most critical for token optimization, occupying ~200 lines (25% of the template). It embodies the "LEGO block" philosophy central to the framework's value proposition.

### LEGO Block Architecture Concept

```
#mermaid-i49u0f2xlp{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;fill:#333;}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#mermaid-i49u0f2xlp .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#mermaid-i49u0f2xlp .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#mermaid-i49u0f2xlp .error-icon{fill:#dddddd;}#mermaid-i49u0f2xlp .error-text{fill:#222222;stroke:#222222;}#mermaid-i49u0f2xlp .edge-thickness-normal{stroke-width:1px;}#mermaid-i49u0f2xlp .edge-thickness-thick{stroke-width:3.5px;}#mermaid-i49u0f2xlp .edge-pattern-solid{stroke-dasharray:0;}#mermaid-i49u0f2xlp .edge-thickness-invisible{stroke-width:0;fill:none;}#mermaid-i49u0f2xlp .edge-pattern-dashed{stroke-dasharray:3;}#mermaid-i49u0f2xlp .edge-pattern-dotted{stroke-dasharray:2;}#mermaid-i49u0f2xlp .marker{fill:#999;stroke:#999;}#mermaid-i49u0f2xlp .marker.cross{stroke:#999;}#mermaid-i49u0f2xlp svg{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;}#mermaid-i49u0f2xlp p{margin:0;}#mermaid-i49u0f2xlp .label{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;color:#333;}#mermaid-i49u0f2xlp .cluster-label text{fill:#444;}#mermaid-i49u0f2xlp .cluster-label span{color:#444;}#mermaid-i49u0f2xlp .cluster-label span p{background-color:transparent;}#mermaid-i49u0f2xlp .label text,#mermaid-i49u0f2xlp span{fill:#333;color:#333;}#mermaid-i49u0f2xlp .node rect,#mermaid-i49u0f2xlp .node circle,#mermaid-i49u0f2xlp .node ellipse,#mermaid-i49u0f2xlp .node polygon,#mermaid-i49u0f2xlp .node path{fill:#ffffff;stroke:#dddddd;stroke-width:1px;}#mermaid-i49u0f2xlp .rough-node .label text,#mermaid-i49u0f2xlp .node .label text,#mermaid-i49u0f2xlp .image-shape .label,#mermaid-i49u0f2xlp .icon-shape .label{text-anchor:middle;}#mermaid-i49u0f2xlp .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#mermaid-i49u0f2xlp .rough-node .label,#mermaid-i49u0f2xlp .node .label,#mermaid-i49u0f2xlp .image-shape .label,#mermaid-i49u0f2xlp .icon-shape .label{text-align:center;}#mermaid-i49u0f2xlp .node.clickable{cursor:pointer;}#mermaid-i49u0f2xlp .root .anchor path{fill:#999!important;stroke-width:0;stroke:#999;}#mermaid-i49u0f2xlp .arrowheadPath{fill:#0b0b0b;}#mermaid-i49u0f2xlp .edgePath .path{stroke:#999;stroke-width:2.0px;}#mermaid-i49u0f2xlp .flowchart-link{stroke:#999;fill:none;}#mermaid-i49u0f2xlp .edgeLabel{background-color:#ffffff;text-align:center;}#mermaid-i49u0f2xlp .edgeLabel p{background-color:#ffffff;}#mermaid-i49u0f2xlp .edgeLabel rect{opacity:0.5;background-color:#ffffff;fill:#ffffff;}#mermaid-i49u0f2xlp .labelBkg{background-color:rgba(255, 255, 255, 0.5);}#mermaid-i49u0f2xlp .cluster rect{fill:#f8f8f8;stroke:#dddddd;stroke-width:1px;}#mermaid-i49u0f2xlp .cluster text{fill:#444;}#mermaid-i49u0f2xlp .cluster span{color:#444;}#mermaid-i49u0f2xlp div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:12px;background:#dddddd;border:1px solid hsl(0, 0%, 76.6666666667%);border-radius:2px;pointer-events:none;z-index:100;}#mermaid-i49u0f2xlp .flowchartTitleText{text-anchor:middle;font-size:18px;fill:#333;}#mermaid-i49u0f2xlp rect.text{fill:none;stroke-width:0;}#mermaid-i49u0f2xlp .icon-shape,#mermaid-i49u0f2xlp .image-shape{background-color:#ffffff;text-align:center;}#mermaid-i49u0f2xlp .icon-shape p,#mermaid-i49u0f2xlp .image-shape p{background-color:#ffffff;padding:2px;}#mermaid-i49u0f2xlp .icon-shape rect,#mermaid-i49u0f2xlp .image-shape rect{opacity:0.5;background-color:#ffffff;fill:#ffffff;}#mermaid-i49u0f2xlp .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#mermaid-i49u0f2xlp .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#mermaid-i49u0f2xlp .nodeLabel p,#mermaid-i49u0f2xlp .edgeLabel p{color:inherit;}#mermaid-i49u0f2xlp :root{--mermaid-font-family:"trebuchet ms",verdana,arial,sans-serif;}AI Agent LoadingModular Approach (Solution)Monolithic Approach (Problem)Loads ALLLoads ONE at a timeOnly when neededOnly when neededOnly when neededExpensive, slowCheap, fastEntire Project
5000 lines
~8k tokens
$0.08 per loadAuth Module
200 lines
~1k tokensAPI Module
200 lines
~1k tokensUI Module
200 lines
~1k tokensBusiness Logic
200 lines
~1k tokensAI Agent$0.08 per session$0.01 per session
87% savings
```

**Module characteristics** ([init\_eng/ARCHITECTURE.md303-308](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L303-L308)):

- Solves **one narrow task**
- Has **clear input and output**
- Works as a **"black box"** for other modules
- Can be **tested separately**

Sources: [init\_eng/ARCHITECTURE.md250-308](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L250-L308) [README.md250-282](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/README.md?plain=1#L250-L282)

### Typical Module Catalog

ARCHITECTURE.md documents 5 standard module types that projects should decompose into:

```
#mermaid-3yk3w2jfpbq{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;fill:#333;}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#mermaid-3yk3w2jfpbq .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#mermaid-3yk3w2jfpbq .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#mermaid-3yk3w2jfpbq .error-icon{fill:#dddddd;}#mermaid-3yk3w2jfpbq .error-text{fill:#222222;stroke:#222222;}#mermaid-3yk3w2jfpbq .edge-thickness-normal{stroke-width:1px;}#mermaid-3yk3w2jfpbq .edge-thickness-thick{stroke-width:3.5px;}#mermaid-3yk3w2jfpbq .edge-pattern-solid{stroke-dasharray:0;}#mermaid-3yk3w2jfpbq .edge-thickness-invisible{stroke-width:0;fill:none;}#mermaid-3yk3w2jfpbq .edge-pattern-dashed{stroke-dasharray:3;}#mermaid-3yk3w2jfpbq .edge-pattern-dotted{stroke-dasharray:2;}#mermaid-3yk3w2jfpbq .marker{fill:#999;stroke:#999;}#mermaid-3yk3w2jfpbq .marker.cross{stroke:#999;}#mermaid-3yk3w2jfpbq svg{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;}#mermaid-3yk3w2jfpbq p{margin:0;}#mermaid-3yk3w2jfpbq .label{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;color:#333;}#mermaid-3yk3w2jfpbq .cluster-label text{fill:#444;}#mermaid-3yk3w2jfpbq .cluster-label span{color:#444;}#mermaid-3yk3w2jfpbq .cluster-label span p{background-color:transparent;}#mermaid-3yk3w2jfpbq .label text,#mermaid-3yk3w2jfpbq span{fill:#333;color:#333;}#mermaid-3yk3w2jfpbq .node rect,#mermaid-3yk3w2jfpbq .node circle,#mermaid-3yk3w2jfpbq .node ellipse,#mermaid-3yk3w2jfpbq .node polygon,#mermaid-3yk3w2jfpbq .node path{fill:#ffffff;stroke:#dddddd;stroke-width:1px;}#mermaid-3yk3w2jfpbq .rough-node .label text,#mermaid-3yk3w2jfpbq .node .label text,#mermaid-3yk3w2jfpbq .image-shape .label,#mermaid-3yk3w2jfpbq .icon-shape .label{text-anchor:middle;}#mermaid-3yk3w2jfpbq .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#mermaid-3yk3w2jfpbq .rough-node .label,#mermaid-3yk3w2jfpbq .node .label,#mermaid-3yk3w2jfpbq .image-shape .label,#mermaid-3yk3w2jfpbq .icon-shape .label{text-align:center;}#mermaid-3yk3w2jfpbq .node.clickable{cursor:pointer;}#mermaid-3yk3w2jfpbq .root .anchor path{fill:#999!important;stroke-width:0;stroke:#999;}#mermaid-3yk3w2jfpbq .arrowheadPath{fill:#0b0b0b;}#mermaid-3yk3w2jfpbq .edgePath .path{stroke:#999;stroke-width:2.0px;}#mermaid-3yk3w2jfpbq .flowchart-link{stroke:#999;fill:none;}#mermaid-3yk3w2jfpbq .edgeLabel{background-color:#ffffff;text-align:center;}#mermaid-3yk3w2jfpbq .edgeLabel p{background-color:#ffffff;}#mermaid-3yk3w2jfpbq .edgeLabel rect{opacity:0.5;background-color:#ffffff;fill:#ffffff;}#mermaid-3yk3w2jfpbq .labelBkg{background-color:rgba(255, 255, 255, 0.5);}#mermaid-3yk3w2jfpbq .cluster rect{fill:#f8f8f8;stroke:#dddddd;stroke-width:1px;}#mermaid-3yk3w2jfpbq .cluster text{fill:#444;}#mermaid-3yk3w2jfpbq .cluster span{color:#444;}#mermaid-3yk3w2jfpbq div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:12px;background:#dddddd;border:1px solid hsl(0, 0%, 76.6666666667%);border-radius:2px;pointer-events:none;z-index:100;}#mermaid-3yk3w2jfpbq .flowchartTitleText{text-anchor:middle;font-size:18px;fill:#333;}#mermaid-3yk3w2jfpbq rect.text{fill:none;stroke-width:0;}#mermaid-3yk3w2jfpbq .icon-shape,#mermaid-3yk3w2jfpbq .image-shape{background-color:#ffffff;text-align:center;}#mermaid-3yk3w2jfpbq .icon-shape p,#mermaid-3yk3w2jfpbq .image-shape p{background-color:#ffffff;padding:2px;}#mermaid-3yk3w2jfpbq .icon-shape rect,#mermaid-3yk3w2jfpbq .image-shape rect{opacity:0.5;background-color:#ffffff;fill:#ffffff;}#mermaid-3yk3w2jfpbq .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#mermaid-3yk3w2jfpbq .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#mermaid-3yk3w2jfpbq .nodeLabel p,#mermaid-3yk3w2jfpbq .edgeLabel p{color:inherit;}#mermaid-3yk3w2jfpbq :root{--mermaid-font-family:"trebuchet ms",verdana,arial,sans-serif;}Business Modules (Develop Last)Page Modules (Develop Second)Independent Modules (Develop First)1. Authentication Module
src/lib/auth/
LoginForm, RegisterForm2. Database Module
src/lib/db/
CRUD operations5. Backend/API Module
src/app/api/
Routes, validation3. Screen/Page Modules
src/pages/
HomePage, DashboardPage4. Business Logic Modules
src/features/
PaymentProcessor, BookingSystem
```

**Module documentation template** ([init\_eng/ARCHITECTURE.md393-434](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L393-L434)):

```
### [Module Name - e.g. "User Authentication"]**Purpose:** [What the module does]**Location:** \`[path to module files]\`**Components:**- \`Component1.tsx\` - [description]- \`service.ts\` - [module logic]**Dependencies:** [External dependencies]**Integration with other modules:** [How it interacts]**Input/Output:**[TypeScript interfaces]**Example usage:**[Code example]**Testing:** [How the module is tested]
```

Sources: [init\_eng/ARCHITECTURE.md310-446](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L310-L446)

### Token Optimization Through Modular Testing

The **Module Testing** section ([init\_eng/ARCHITECTURE.md571-733](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L571-L733)) quantifies the economic benefits:

**Token savings calculation** ([init\_eng/ARCHITECTURE.md690-712](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L690-L712)):

| Approach | Token Cost | Calculation | Total Cost |
| --- | --- | --- | --- |
| **Monolithic testing** | 24,000 tokens | 8k tokens × 3 iterations = 24k | $0.24 |
| **Modular testing** | 15,000 tokens | 1.5k × 2 iterations × 5 modules = 15k | $0.15 |
| **Savings** | 9,000 tokens | 37.5% reduction | **$0.09 saved** |

**Module readiness criteria** ([init\_eng/ARCHITECTURE.md641-667](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L641-L667)):

- All module files created
- Code compiles without TypeScript errors
- Module tested in isolation
- Core functionality implemented
- Error handling added
- BACKLOG.md tasks marked ✅
- PROJECT\_SNAPSHOT.md updated

Sources: [init\_eng/ARCHITECTURE.md571-733](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L571-L733) [README.md192-206](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/README.md?plain=1#L192-L206)

---

## Architecture Decision Records (ADR)

ARCHITECTURE.md uses the ADR pattern for documenting significant architectural decisions in a structured format.

### ADR Structure

**Core Architecture Decisions section** ([init\_eng/ARCHITECTURE.md90-139](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L90-L139)):

### ADR-001: \[Decision Title\]

**Date:** \[DATE\] **Status:** \[Accepted/Deprecated/Superseded\] **Context:** \[Why a decision was needed\] **Decision:** \[What was decided\] **Consequences:** \[What this led to\]

**Anti-pattern warning** ([init\_eng/ARCHITECTURE.md16-18](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L16-L18)):

Sources: [init\_eng/ARCHITECTURE.md90-139](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L90-L139) [init\_eng/ARCHITECTURE.md749-758](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L749-L758) [init\_eng/ARCHITECTURE.md16-18](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L16-L18)

---

## Technology Stack Documentation

The **Technology Stack** section ([init\_eng/ARCHITECTURE.md25-58](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L25-L58)) provides a comprehensive inventory of project dependencies with justification.

### Stack Documentation Template

**Frontend stack** ([init\_eng/ARCHITECTURE.md27-37](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L27-L37)):

**Backend & Infrastructure** ([init\_eng/ARCHITECTURE.md39-47](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L39-L47)):

**Key Dependencies** ([init\_eng/ARCHITECTURE.md49-58](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L49-L58)):

```
{  "react": "^18.3.1 - UI library",  "@supabase/supabase-js": "^2.x.x - Database client",  "zustand": "^5.x.x - State management"}
```

**Purpose:** Each entry should include **version + rationale** to prevent AI agents from suggesting outdated alternatives.

Sources: [init\_eng/ARCHITECTURE.md25-58](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L25-L58)

---

## Development Standards and Patterns

The **Development Standards** section ([init\_eng/ARCHITECTURE.md219-248](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L219-L248)) enforces project-wide conventions that AI agents must follow.

### Standards Hierarchy

```
#mermaid-k4icgrrnock{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;fill:#333;}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#mermaid-k4icgrrnock .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#mermaid-k4icgrrnock .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#mermaid-k4icgrrnock .error-icon{fill:#dddddd;}#mermaid-k4icgrrnock .error-text{fill:#222222;stroke:#222222;}#mermaid-k4icgrrnock .edge-thickness-normal{stroke-width:1px;}#mermaid-k4icgrrnock .edge-thickness-thick{stroke-width:3.5px;}#mermaid-k4icgrrnock .edge-pattern-solid{stroke-dasharray:0;}#mermaid-k4icgrrnock .edge-thickness-invisible{stroke-width:0;fill:none;}#mermaid-k4icgrrnock .edge-pattern-dashed{stroke-dasharray:3;}#mermaid-k4icgrrnock .edge-pattern-dotted{stroke-dasharray:2;}#mermaid-k4icgrrnock .marker{fill:#999;stroke:#999;}#mermaid-k4icgrrnock .marker.cross{stroke:#999;}#mermaid-k4icgrrnock svg{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;}#mermaid-k4icgrrnock p{margin:0;}#mermaid-k4icgrrnock .label{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;color:#333;}#mermaid-k4icgrrnock .cluster-label text{fill:#444;}#mermaid-k4icgrrnock .cluster-label span{color:#444;}#mermaid-k4icgrrnock .cluster-label span p{background-color:transparent;}#mermaid-k4icgrrnock .label text,#mermaid-k4icgrrnock span{fill:#333;color:#333;}#mermaid-k4icgrrnock .node rect,#mermaid-k4icgrrnock .node circle,#mermaid-k4icgrrnock .node ellipse,#mermaid-k4icgrrnock .node polygon,#mermaid-k4icgrrnock .node path{fill:#ffffff;stroke:#dddddd;stroke-width:1px;}#mermaid-k4icgrrnock .rough-node .label text,#mermaid-k4icgrrnock .node .label text,#mermaid-k4icgrrnock .image-shape .label,#mermaid-k4icgrrnock .icon-shape .label{text-anchor:middle;}#mermaid-k4icgrrnock .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#mermaid-k4icgrrnock .rough-node .label,#mermaid-k4icgrrnock .node .label,#mermaid-k4icgrrnock .image-shape .label,#mermaid-k4icgrrnock .icon-shape .label{text-align:center;}#mermaid-k4icgrrnock .node.clickable{cursor:pointer;}#mermaid-k4icgrrnock .root .anchor path{fill:#999!important;stroke-width:0;stroke:#999;}#mermaid-k4icgrrnock .arrowheadPath{fill:#0b0b0b;}#mermaid-k4icgrrnock .edgePath .path{stroke:#999;stroke-width:2.0px;}#mermaid-k4icgrrnock .flowchart-link{stroke:#999;fill:none;}#mermaid-k4icgrrnock .edgeLabel{background-color:#ffffff;text-align:center;}#mermaid-k4icgrrnock .edgeLabel p{background-color:#ffffff;}#mermaid-k4icgrrnock .edgeLabel rect{opacity:0.5;background-color:#ffffff;fill:#ffffff;}#mermaid-k4icgrrnock .labelBkg{background-color:rgba(255, 255, 255, 0.5);}#mermaid-k4icgrrnock .cluster rect{fill:#f8f8f8;stroke:#dddddd;stroke-width:1px;}#mermaid-k4icgrrnock .cluster text{fill:#444;}#mermaid-k4icgrrnock .cluster span{color:#444;}#mermaid-k4icgrrnock div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:12px;background:#dddddd;border:1px solid hsl(0, 0%, 76.6666666667%);border-radius:2px;pointer-events:none;z-index:100;}#mermaid-k4icgrrnock .flowchartTitleText{text-anchor:middle;font-size:18px;fill:#333;}#mermaid-k4icgrrnock rect.text{fill:none;stroke-width:0;}#mermaid-k4icgrrnock .icon-shape,#mermaid-k4icgrrnock .image-shape{background-color:#ffffff;text-align:center;}#mermaid-k4icgrrnock .icon-shape p,#mermaid-k4icgrrnock .image-shape p{background-color:#ffffff;padding:2px;}#mermaid-k4icgrrnock .icon-shape rect,#mermaid-k4icgrrnock .image-shape rect{opacity:0.5;background-color:#ffffff;fill:#ffffff;}#mermaid-k4icgrrnock .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#mermaid-k4icgrrnock .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#mermaid-k4icgrrnock .nodeLabel p,#mermaid-k4icgrrnock .edgeLabel p{color:inherit;}#mermaid-k4icgrrnock :root{--mermaid-font-family:"trebuchet ms",verdana,arial,sans-serif;}Performance OptimizationsError HandlingDatabase PatternsCode Organization Standards1 component = 1 fileServices in lib/ for reusabilityTypeScript strict mode - no anyNaming conventionsPrimary Keys: UUID/Auto-incrementRelationships: FK structureMigrations: Version controlSecurity: RLS policiesTry/catch in async functionsUser-friendly error messagesConsole logging for debuggingFallback states in UIProject-specific optimizationsLazy loading strategiesCaching policiesARCHITECTURE.md
```

**Enforcement mechanism:** AI agents must consult ARCHITECTURE.md before code generation ([init\_eng/ARCHITECTURE.md219-248](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L219-L248)), creating a "design contract" that prevents inconsistent implementations.

Sources: [init\_eng/ARCHITECTURE.md219-248](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L219-L248)

---

## Relationship with Other Meta-Files

ARCHITECTURE.md has explicit cross-references to other documentation files, creating a cohesive knowledge graph.

### Documentation Cross-Reference Map

```
#mermaid-rwkijrjkssg{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;fill:#333;}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#mermaid-rwkijrjkssg .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#mermaid-rwkijrjkssg .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#mermaid-rwkijrjkssg .error-icon{fill:#dddddd;}#mermaid-rwkijrjkssg .error-text{fill:#222222;stroke:#222222;}#mermaid-rwkijrjkssg .edge-thickness-normal{stroke-width:1px;}#mermaid-rwkijrjkssg .edge-thickness-thick{stroke-width:3.5px;}#mermaid-rwkijrjkssg .edge-pattern-solid{stroke-dasharray:0;}#mermaid-rwkijrjkssg .edge-thickness-invisible{stroke-width:0;fill:none;}#mermaid-rwkijrjkssg .edge-pattern-dashed{stroke-dasharray:3;}#mermaid-rwkijrjkssg .edge-pattern-dotted{stroke-dasharray:2;}#mermaid-rwkijrjkssg .marker{fill:#999;stroke:#999;}#mermaid-rwkijrjkssg .marker.cross{stroke:#999;}#mermaid-rwkijrjkssg svg{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;}#mermaid-rwkijrjkssg p{margin:0;}#mermaid-rwkijrjkssg .label{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;color:#333;}#mermaid-rwkijrjkssg .cluster-label text{fill:#444;}#mermaid-rwkijrjkssg .cluster-label span{color:#444;}#mermaid-rwkijrjkssg .cluster-label span p{background-color:transparent;}#mermaid-rwkijrjkssg .label text,#mermaid-rwkijrjkssg span{fill:#333;color:#333;}#mermaid-rwkijrjkssg .node rect,#mermaid-rwkijrjkssg .node circle,#mermaid-rwkijrjkssg .node ellipse,#mermaid-rwkijrjkssg .node polygon,#mermaid-rwkijrjkssg .node path{fill:#ffffff;stroke:#dddddd;stroke-width:1px;}#mermaid-rwkijrjkssg .rough-node .label text,#mermaid-rwkijrjkssg .node .label text,#mermaid-rwkijrjkssg .image-shape .label,#mermaid-rwkijrjkssg .icon-shape .label{text-anchor:middle;}#mermaid-rwkijrjkssg .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#mermaid-rwkijrjkssg .rough-node .label,#mermaid-rwkijrjkssg .node .label,#mermaid-rwkijrjkssg .image-shape .label,#mermaid-rwkijrjkssg .icon-shape .label{text-align:center;}#mermaid-rwkijrjkssg .node.clickable{cursor:pointer;}#mermaid-rwkijrjkssg .root .anchor path{fill:#999!important;stroke-width:0;stroke:#999;}#mermaid-rwkijrjkssg .arrowheadPath{fill:#0b0b0b;}#mermaid-rwkijrjkssg .edgePath .path{stroke:#999;stroke-width:2.0px;}#mermaid-rwkijrjkssg .flowchart-link{stroke:#999;fill:none;}#mermaid-rwkijrjkssg .edgeLabel{background-color:#ffffff;text-align:center;}#mermaid-rwkijrjkssg .edgeLabel p{background-color:#ffffff;}#mermaid-rwkijrjkssg .edgeLabel rect{opacity:0.5;background-color:#ffffff;fill:#ffffff;}#mermaid-rwkijrjkssg .labelBkg{background-color:rgba(255, 255, 255, 0.5);}#mermaid-rwkijrjkssg .cluster rect{fill:#f8f8f8;stroke:#dddddd;stroke-width:1px;}#mermaid-rwkijrjkssg .cluster text{fill:#444;}#mermaid-rwkijrjkssg .cluster span{color:#444;}#mermaid-rwkijrjkssg div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:12px;background:#dddddd;border:1px solid hsl(0, 0%, 76.6666666667%);border-radius:2px;pointer-events:none;z-index:100;}#mermaid-rwkijrjkssg .flowchartTitleText{text-anchor:middle;font-size:18px;fill:#333;}#mermaid-rwkijrjkssg rect.text{fill:none;stroke-width:0;}#mermaid-rwkijrjkssg .icon-shape,#mermaid-rwkijrjkssg .image-shape{background-color:#ffffff;text-align:center;}#mermaid-rwkijrjkssg .icon-shape p,#mermaid-rwkijrjkssg .image-shape p{background-color:#ffffff;padding:2px;}#mermaid-rwkijrjkssg .icon-shape rect,#mermaid-rwkijrjkssg .image-shape rect{opacity:0.5;background-color:#ffffff;fill:#ffffff;}#mermaid-rwkijrjkssg .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#mermaid-rwkijrjkssg .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#mermaid-rwkijrjkssg .nodeLabel p,#mermaid-rwkijrjkssg .edgeLabel p{color:inherit;}#mermaid-rwkijrjkssg :root{--mermaid-font-family:"trebuchet ms",verdana,arial,sans-serif;}Links to WHYReferences modulesMethodology forFollows patterns fromUpdated perDocumented inReferences processesARCHITECTURE.md
(WHY design decisions)BACKLOG.md
(WHAT implementation status)PROJECT_SNAPSHOT.md
(WHERE current state)PROCESS.md
(WHEN to update docs)DEVELOPMENT_PLAN_TEMPLATE.md
(HOW TO planning methodology)AGENTS.md
(WHO AI instructions)WORKFLOW.md
(HOW development processes)README.md
(PUBLIC user-facing info)
```

**Related Documentation section** ([init\_eng/ARCHITECTURE.md737-746](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L737-L746)):

```
- **BACKLOG.md** - Current implementation status and roadmap- **PROJECT_SNAPSHOT.md** - Current project state snapshot- **PROCESS.md** - Documentation update process after each phase- **DEVELOPMENT_PLAN_TEMPLATE.md** - Planning methodology- **AGENTS.md** - AI assistant working instructions- **WORKFLOW.md** - Development processes and sprint workflow- **README.md** - User-facing project information
```

Sources: [init\_eng/ARCHITECTURE.md737-746](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L737-L746)

---

## Update Triggers and Maintenance

ARCHITECTURE.md requires updates during specific development events to maintain accuracy.

### Update Event Flowchart

```
#mermaid-2zbe37h9uay{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;fill:#333;}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#mermaid-2zbe37h9uay .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#mermaid-2zbe37h9uay .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#mermaid-2zbe37h9uay .error-icon{fill:#dddddd;}#mermaid-2zbe37h9uay .error-text{fill:#222222;stroke:#222222;}#mermaid-2zbe37h9uay .edge-thickness-normal{stroke-width:1px;}#mermaid-2zbe37h9uay .edge-thickness-thick{stroke-width:3.5px;}#mermaid-2zbe37h9uay .edge-pattern-solid{stroke-dasharray:0;}#mermaid-2zbe37h9uay .edge-thickness-invisible{stroke-width:0;fill:none;}#mermaid-2zbe37h9uay .edge-pattern-dashed{stroke-dasharray:3;}#mermaid-2zbe37h9uay .edge-pattern-dotted{stroke-dasharray:2;}#mermaid-2zbe37h9uay .marker{fill:#999;stroke:#999;}#mermaid-2zbe37h9uay .marker.cross{stroke:#999;}#mermaid-2zbe37h9uay svg{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;}#mermaid-2zbe37h9uay p{margin:0;}#mermaid-2zbe37h9uay .label{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;color:#333;}#mermaid-2zbe37h9uay .cluster-label text{fill:#444;}#mermaid-2zbe37h9uay .cluster-label span{color:#444;}#mermaid-2zbe37h9uay .cluster-label span p{background-color:transparent;}#mermaid-2zbe37h9uay .label text,#mermaid-2zbe37h9uay span{fill:#333;color:#333;}#mermaid-2zbe37h9uay .node rect,#mermaid-2zbe37h9uay .node circle,#mermaid-2zbe37h9uay .node ellipse,#mermaid-2zbe37h9uay .node polygon,#mermaid-2zbe37h9uay .node path{fill:#ffffff;stroke:#dddddd;stroke-width:1px;}#mermaid-2zbe37h9uay .rough-node .label text,#mermaid-2zbe37h9uay .node .label text,#mermaid-2zbe37h9uay .image-shape .label,#mermaid-2zbe37h9uay .icon-shape .label{text-anchor:middle;}#mermaid-2zbe37h9uay .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#mermaid-2zbe37h9uay .rough-node .label,#mermaid-2zbe37h9uay .node .label,#mermaid-2zbe37h9uay .image-shape .label,#mermaid-2zbe37h9uay .icon-shape .label{text-align:center;}#mermaid-2zbe37h9uay .node.clickable{cursor:pointer;}#mermaid-2zbe37h9uay .root .anchor path{fill:#999!important;stroke-width:0;stroke:#999;}#mermaid-2zbe37h9uay .arrowheadPath{fill:#0b0b0b;}#mermaid-2zbe37h9uay .edgePath .path{stroke:#999;stroke-width:2.0px;}#mermaid-2zbe37h9uay .flowchart-link{stroke:#999;fill:none;}#mermaid-2zbe37h9uay .edgeLabel{background-color:#ffffff;text-align:center;}#mermaid-2zbe37h9uay .edgeLabel p{background-color:#ffffff;}#mermaid-2zbe37h9uay .edgeLabel rect{opacity:0.5;background-color:#ffffff;fill:#ffffff;}#mermaid-2zbe37h9uay .labelBkg{background-color:rgba(255, 255, 255, 0.5);}#mermaid-2zbe37h9uay .cluster rect{fill:#f8f8f8;stroke:#dddddd;stroke-width:1px;}#mermaid-2zbe37h9uay .cluster text{fill:#444;}#mermaid-2zbe37h9uay .cluster span{color:#444;}#mermaid-2zbe37h9uay div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:12px;background:#dddddd;border:1px solid hsl(0, 0%, 76.6666666667%);border-radius:2px;pointer-events:none;z-index:100;}#mermaid-2zbe37h9uay .flowchartTitleText{text-anchor:middle;font-size:18px;fill:#333;}#mermaid-2zbe37h9uay rect.text{fill:none;stroke-width:0;}#mermaid-2zbe37h9uay .icon-shape,#mermaid-2zbe37h9uay .image-shape{background-color:#ffffff;text-align:center;}#mermaid-2zbe37h9uay .icon-shape p,#mermaid-2zbe37h9uay .image-shape p{background-color:#ffffff;padding:2px;}#mermaid-2zbe37h9uay .icon-shape rect,#mermaid-2zbe37h9uay .image-shape rect{opacity:0.5;background-color:#ffffff;fill:#ffffff;}#mermaid-2zbe37h9uay .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#mermaid-2zbe37h9uay .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#mermaid-2zbe37h9uay .nodeLabel p,#mermaid-2zbe37h9uay .edgeLabel p{color:inherit;}#mermaid-2zbe37h9uay :root{--mermaid-font-family:"trebuchet ms",verdana,arial,sans-serif;}YesNoYesNoYesNoYesNoYesNoYesNoYesNoDevelopment Event OccursNew technology adopted?Architectural decision made?New module created?Design pattern applied?Database schema changed?Security model changed?Deployment architecture changed?Update Technology Stack sectionAdd ADR entry in Core Architecture DecisionsDocument module in Module ArchitectureAdd to Design Patterns sectionUpdate Database Schema sectionUpdate Security Architecture sectionUpdate Deployment Architecture sectionGit commit with docs: prefix
```

**Evolution & Migration Strategy** ([init\_eng/ARCHITECTURE.md550-568](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L550-L568)):

**Version History tracking** ([init\_eng/ARCHITECTURE.md565-568](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L565-L568)):

```
### Version History- **[VERSION]** - [DATE] - [Changes summary]
```

Sources: [init\_eng/ARCHITECTURE.md550-568](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L550-L568)

---

## AI Agent Usage Patterns

AI agents interact with ARCHITECTURE.md through specific consultation patterns defined in CLAUDE.md and AGENTS.md.

### Agent Consultation Sequence

```
CodebaseSECURITY.mdARCHITECTURE.mdBACKLOG.mdAI AgentUserCodebaseSECURITY.mdARCHITECTURE.mdBACKLOG.mdAI AgentUser#mermaid-09lpiaqqxyxc{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;fill:#333;}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#mermaid-09lpiaqqxyxc .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#mermaid-09lpiaqqxyxc .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#mermaid-09lpiaqqxyxc .error-icon{fill:#dddddd;}#mermaid-09lpiaqqxyxc .error-text{fill:#222222;stroke:#222222;}#mermaid-09lpiaqqxyxc .edge-thickness-normal{stroke-width:1px;}#mermaid-09lpiaqqxyxc .edge-thickness-thick{stroke-width:3.5px;}#mermaid-09lpiaqqxyxc .edge-pattern-solid{stroke-dasharray:0;}#mermaid-09lpiaqqxyxc .edge-thickness-invisible{stroke-width:0;fill:none;}#mermaid-09lpiaqqxyxc .edge-pattern-dashed{stroke-dasharray:3;}#mermaid-09lpiaqqxyxc .edge-pattern-dotted{stroke-dasharray:2;}#mermaid-09lpiaqqxyxc .marker{fill:#999;stroke:#999;}#mermaid-09lpiaqqxyxc .marker.cross{stroke:#999;}#mermaid-09lpiaqqxyxc svg{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;}#mermaid-09lpiaqqxyxc p{margin:0;}#mermaid-09lpiaqqxyxc .actor{stroke:#cccccc;fill:#ffffff;}#mermaid-09lpiaqqxyxc text.actor>tspan{fill:#333;stroke:none;}#mermaid-09lpiaqqxyxc .actor-line{stroke:#cccccc;}#mermaid-09lpiaqqxyxc .messageLine0{stroke-width:1.5;stroke-dasharray:none;stroke:#999999;}#mermaid-09lpiaqqxyxc .messageLine1{stroke-width:1.5;stroke-dasharray:2,2;stroke:#999999;}#mermaid-09lpiaqqxyxc #arrowhead path{fill:#999999;stroke:#999999;}#mermaid-09lpiaqqxyxc .sequenceNumber{fill:#666666;}#mermaid-09lpiaqqxyxc #sequencenumber{fill:#999999;}#mermaid-09lpiaqqxyxc #crosshead path{fill:#999999;stroke:#999999;}#mermaid-09lpiaqqxyxc .messageText{fill:#333333;stroke:none;}#mermaid-09lpiaqqxyxc .labelBox{stroke:#dddddd;fill:#ffffff;}#mermaid-09lpiaqqxyxc .labelText,#mermaid-09lpiaqqxyxc .labelText>tspan{fill:#333;stroke:none;}#mermaid-09lpiaqqxyxc .loopText,#mermaid-09lpiaqqxyxc .loopText>tspan{fill:#333;stroke:none;}#mermaid-09lpiaqqxyxc .loopLine{stroke-width:2px;stroke-dasharray:2,2;stroke:#dddddd;fill:#dddddd;}#mermaid-09lpiaqqxyxc .note{stroke:#e6d280;fill:#fff5ad;}#mermaid-09lpiaqqxyxc .noteText,#mermaid-09lpiaqqxyxc .noteText>tspan{fill:#333;stroke:none;}#mermaid-09lpiaqqxyxc .activation0{fill:hsl(-120, 0%, 91.7647058824%);stroke:hsl(-120, 0%, 81.7647058824%);}#mermaid-09lpiaqqxyxc .activation1{fill:hsl(-120, 0%, 91.7647058824%);stroke:hsl(-120, 0%, 81.7647058824%);}#mermaid-09lpiaqqxyxc .activation2{fill:hsl(-120, 0%, 91.7647058824%);stroke:hsl(-120, 0%, 81.7647058824%);}#mermaid-09lpiaqqxyxc .actorPopupMenu{position:absolute;}#mermaid-09lpiaqqxyxc .actorPopupMenuPanel{position:absolute;fill:#ffffff;box-shadow:0px 8px 16px 0px rgba(0,0,0,0.2);filter:drop-shadow(3px 5px 2px rgb(0 0 0 / 0.4));}#mermaid-09lpiaqqxyxc .actor-man line{stroke:#cccccc;fill:#ffffff;}#mermaid-09lpiaqqxyxc .actor-man circle,#mermaid-09lpiaqqxyxc line{stroke:#cccccc;fill:#ffffff;stroke-width:2px;}#mermaid-09lpiaqqxyxc .nodeLabel p,#mermaid-09lpiaqqxyxc .edgeLabel p{color:inherit;}#mermaid-09lpiaqqxyxc :root{--mermaid-font-family:"trebuchet ms",verdana,arial,sans-serif;}"Implement Auth module"Read: What tasks in Auth module?Task: Create LoginForm, RegisterFormRead: Module Architecture sectionAuth Module: src/lib/auth/, components listRead: Development Standards1 component = 1 file, TypeScript strictRead: Security practicesValidate all inputs, use bcryptGenerate LoginForm.tsxGenerate RegisterForm.tsxFiles created following architecture
```

**Mandatory reading sequence** from CLAUDE.md:

1. BACKLOG.md - "What am I implementing?"
2. ARCHITECTURE.md - "What design patterns apply?"
3. SECURITY.md - "What security rules must I follow?"
4. Code generation begins

**Consultation triggers:**

- Before implementing new module
- Before making architectural changes
- When choosing between design alternatives
- When encountering design decision conflicts

Sources: [README.md285-330](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/README.md?plain=1#L285-L330)

---

## Template Customization Guidelines

The template includes extensive placeholders and customization instructions.

### Customization Checklist

**Notes for Customization section** ([init\_eng/ARCHITECTURE.md774-784](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L774-L784)):

```
1. Replace all [FILL IN] with actual information2. Remove sections that don't apply to your project3. Add new sections specific to your project4. Update document with each architectural change5. Use diagrams where needed (Mermaid/ASCII)6. Delete this section after initial setup
```

### Section Relevance Matrix

| Section | Required | Conditional | Optional |
| --- | --- | --- | --- |
| Technology Stack | ✅ Always | \- | \- |
| Project Structure | ✅ Always | \- | \- |
| Core Architecture Decisions | ✅ Always | \- | \- |
| Module Architecture | ✅ Always | \- | \- |
| Key Services & Components | ✅ Always | \- | \- |
| Development Standards | ✅ Always | \- | \- |
| Database Schema | \- | If using database | \- |
| Security Architecture | \- | If auth/data protection | \- |
| Deployment Architecture | \- | If deployed | \- |
| State Management | \- | If complex state | \- |
| Module Testing | ✅ Always | \- | \- |
| ADR | \- | \- | ✅ For formal decisions |
| Design Patterns | \- | \- | ✅ If applicable |

**Language variants:**

- [Init/ARCHITECTURE.md1-789](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/Init/ARCHITECTURE.md?plain=1#L1-L789) - Russian template with Cyrillic text
- [init\_eng/ARCHITECTURE.md1-789](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L1-L789) - English template

Both versions have identical structure, differing only in placeholder language ([Init/ARCHITECTURE.md28](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/Init/ARCHITECTURE.md?plain=1#L28-L28) "ЗАПОЛНИТЬ" vs [init\_eng/ARCHITECTURE.md28](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L28-L28) "FILL IN").

Sources: [init\_eng/ARCHITECTURE.md774-784](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L774-L784) [Init/ARCHITECTURE.md1-789](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/Init/ARCHITECTURE.md?plain=1#L1-L789) [init\_eng/ARCHITECTURE.md1-789](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L1-L789)

---

## Common Anti-Patterns and Warnings

ARCHITECTURE.md explicitly warns against documentation anti-patterns that create conflicts.

### Anti-Pattern: Task Lists in Architecture

**Warning block** ([init\_eng/ARCHITECTURE.md15-21](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L15-L21)):

**Problem scenario:**

**Solution:**

### Anti-Pattern: Duplicating Security Rules

**From DOCS\_MAP.md principle:**

- Universal security rules → SECURITY.md
- Project-specific patterns → AGENTS.md
- Database security → ARCHITECTURE.md "Security Architecture" references SECURITY.md

**Correct cross-referencing:**

```
## 🔐 Security Architecture **Authentication:** See [SECURITY.md] for universal auth practices**Authorization:** Project uses RBAC with [specific implementation]**Data Protection:** Follows [SECURITY.md] encryption standards
```

Sources: [init\_eng/ARCHITECTURE.md15-21](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L15-L21) [init\_eng/ARCHITECTURE.md475-499](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L475-L499)

---

## Integration with Cold Start Protocol

ARCHITECTURE.md participates in the Cold Start Protocol through selective loading based on PROJECT\_SNAPSHOT.md state.

### Cold Start Loading Decision Tree

```
#mermaid-te5idl9pm3h{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;fill:#333;}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#mermaid-te5idl9pm3h .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#mermaid-te5idl9pm3h .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#mermaid-te5idl9pm3h .error-icon{fill:#dddddd;}#mermaid-te5idl9pm3h .error-text{fill:#222222;stroke:#222222;}#mermaid-te5idl9pm3h .edge-thickness-normal{stroke-width:1px;}#mermaid-te5idl9pm3h .edge-thickness-thick{stroke-width:3.5px;}#mermaid-te5idl9pm3h .edge-pattern-solid{stroke-dasharray:0;}#mermaid-te5idl9pm3h .edge-thickness-invisible{stroke-width:0;fill:none;}#mermaid-te5idl9pm3h .edge-pattern-dashed{stroke-dasharray:3;}#mermaid-te5idl9pm3h .edge-pattern-dotted{stroke-dasharray:2;}#mermaid-te5idl9pm3h .marker{fill:#999;stroke:#999;}#mermaid-te5idl9pm3h .marker.cross{stroke:#999;}#mermaid-te5idl9pm3h svg{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:16px;}#mermaid-te5idl9pm3h p{margin:0;}#mermaid-te5idl9pm3h .label{font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;color:#333;}#mermaid-te5idl9pm3h .cluster-label text{fill:#444;}#mermaid-te5idl9pm3h .cluster-label span{color:#444;}#mermaid-te5idl9pm3h .cluster-label span p{background-color:transparent;}#mermaid-te5idl9pm3h .label text,#mermaid-te5idl9pm3h span{fill:#333;color:#333;}#mermaid-te5idl9pm3h .node rect,#mermaid-te5idl9pm3h .node circle,#mermaid-te5idl9pm3h .node ellipse,#mermaid-te5idl9pm3h .node polygon,#mermaid-te5idl9pm3h .node path{fill:#ffffff;stroke:#dddddd;stroke-width:1px;}#mermaid-te5idl9pm3h .rough-node .label text,#mermaid-te5idl9pm3h .node .label text,#mermaid-te5idl9pm3h .image-shape .label,#mermaid-te5idl9pm3h .icon-shape .label{text-anchor:middle;}#mermaid-te5idl9pm3h .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#mermaid-te5idl9pm3h .rough-node .label,#mermaid-te5idl9pm3h .node .label,#mermaid-te5idl9pm3h .image-shape .label,#mermaid-te5idl9pm3h .icon-shape .label{text-align:center;}#mermaid-te5idl9pm3h .node.clickable{cursor:pointer;}#mermaid-te5idl9pm3h .root .anchor path{fill:#999!important;stroke-width:0;stroke:#999;}#mermaid-te5idl9pm3h .arrowheadPath{fill:#0b0b0b;}#mermaid-te5idl9pm3h .edgePath .path{stroke:#999;stroke-width:2.0px;}#mermaid-te5idl9pm3h .flowchart-link{stroke:#999;fill:none;}#mermaid-te5idl9pm3h .edgeLabel{background-color:#ffffff;text-align:center;}#mermaid-te5idl9pm3h .edgeLabel p{background-color:#ffffff;}#mermaid-te5idl9pm3h .edgeLabel rect{opacity:0.5;background-color:#ffffff;fill:#ffffff;}#mermaid-te5idl9pm3h .labelBkg{background-color:rgba(255, 255, 255, 0.5);}#mermaid-te5idl9pm3h .cluster rect{fill:#f8f8f8;stroke:#dddddd;stroke-width:1px;}#mermaid-te5idl9pm3h .cluster text{fill:#444;}#mermaid-te5idl9pm3h .cluster span{color:#444;}#mermaid-te5idl9pm3h div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica;font-size:12px;background:#dddddd;border:1px solid hsl(0, 0%, 76.6666666667%);border-radius:2px;pointer-events:none;z-index:100;}#mermaid-te5idl9pm3h .flowchartTitleText{text-anchor:middle;font-size:18px;fill:#333;}#mermaid-te5idl9pm3h rect.text{fill:none;stroke-width:0;}#mermaid-te5idl9pm3h .icon-shape,#mermaid-te5idl9pm3h .image-shape{background-color:#ffffff;text-align:center;}#mermaid-te5idl9pm3h .icon-shape p,#mermaid-te5idl9pm3h .image-shape p{background-color:#ffffff;padding:2px;}#mermaid-te5idl9pm3h .icon-shape rect,#mermaid-te5idl9pm3h .image-shape rect{opacity:0.5;background-color:#ffffff;fill:#ffffff;}#mermaid-te5idl9pm3h .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#mermaid-te5idl9pm3h .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#mermaid-te5idl9pm3h .nodeLabel p,#mermaid-te5idl9pm3h .edgeLabel p{color:inherit;}#mermaid-te5idl9pm3h :root{--mermaid-font-family:"trebuchet ms",verdana,arial,sans-serif;}YesNoYesNoAI Session RestartPROJECT_SNAPSHOT.md exists?Has current module?Read PROJECT_SNAPSHOT.md
~500 tokensRead ARCH module section
~1k tokensRead ARCH full file
~6k tokensDevelopment begins
2-3k tokens total
```

**Example scenario:**

**PROJECT\_SNAPSHOT.md:**

```
Current Phase: Phase 3 - Auth Module (45%)Active Module: Authentication (src/lib/auth/)Last Updated: 2024-01-15
```

**AI agent behavior:**

1. Reads PROJECT\_SNAPSHOT.md → Sees "Auth Module"
2. Opens ARCHITECTURE.md → Searches for "Authentication Module"
3. Reads only [init\_eng/ARCHITECTURE.md314-326](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L314-L326) (~200 lines)
4. Skips other 550+ lines of ARCHITECTURE.md
5. **Result:** 1k tokens instead of 6k tokens = 83% savings

**Stage 3: Never Unless Asked** ([README.md232-238](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/README.md?plain=1#L232-L238)):

ARCHITECTURE.md is **conditionally loaded** - full file only read when:

- PROJECT\_SNAPSHOT.md doesn't exist yet
- User explicitly requests architectural overview
- Making cross-module architectural decisions

Sources: [README.md209-248](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/README.md?plain=1#L209-L248)

---

## File Location and Access

**Template locations:**

- English: [init\_eng/ARCHITECTURE.md1-789](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L1-L789)
- Russian: [Init/ARCHITECTURE.md1-789](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/Init/ARCHITECTURE.md?plain=1#L1-L789)

**Deployed location:** after execution

**Access permissions:** Defined in - Claude Code has read/write access to enable AI-driven updates

**File size:** 789 lines (~50KB) in template form, grows to 1000-2000 lines in production projects

**Git tracking:** Version controlled, updated via prefixed commits per WORKFLOW.md standards

Sources: [README.md107-125](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/README.md?plain=1#L107-L125) [init\_eng/ARCHITECTURE.md1-789](https://github.com/alexeykrol/claude-code-starter/blob/907352ea/init_eng/ARCHITECTURE.md?plain=1#L1-L789)

Refresh this wiki

### On this page

- [ARCHITECTURE.md](#architecturemd)
- [Purpose and Scope](#purpose-and-scope)
- [Role in the Meta-Documentation Framework](#role-in-the-meta-documentation-framework)
- [Architectural Decision Authority Diagram](#architectural-decision-authority-diagram)
- [File Structure and Sections](#file-structure-and-sections)
- [Section Hierarchy Table](#section-hierarchy-table)
- [Information Flow Between Sections](#information-flow-between-sections)
- [Module Architecture Philosophy](#module-architecture-philosophy)
- [LEGO Block Architecture Concept](#lego-block-architecture-concept)
- [Typical Module Catalog](#typical-module-catalog)
- [Token Optimization Through Modular Testing](#token-optimization-through-modular-testing)
- [Architecture Decision Records (ADR)](#architecture-decision-records-adr)
- [ADR Structure](#adr-structure)
- [ADR-001: \[Decision Title\]](#adr-001-decision-title)
- [Technology Stack Documentation](#technology-stack-documentation)
- [Stack Documentation Template](#stack-documentation-template)
- [Development Standards and Patterns](#development-standards-and-patterns)
- [Standards Hierarchy](#standards-hierarchy)
- [Relationship with Other Meta-Files](#relationship-with-other-meta-files)
- [Documentation Cross-Reference Map](#documentation-cross-reference-map)
- [Update Triggers and Maintenance](#update-triggers-and-maintenance)
- [Update Event Flowchart](#update-event-flowchart)
- [AI Agent Usage Patterns](#ai-agent-usage-patterns)
- [Agent Consultation Sequence](#agent-consultation-sequence)
- [Template Customization Guidelines](#template-customization-guidelines)
- [Customization Checklist](#customization-checklist)
- [Section Relevance Matrix](#section-relevance-matrix)
- [Common Anti-Patterns and Warnings](#common-anti-patterns-and-warnings)
- [Anti-Pattern: Task Lists in Architecture](#anti-pattern-task-lists-in-architecture)
- [Anti-Pattern: Duplicating Security Rules](#anti-pattern-duplicating-security-rules)
- [Integration with Cold Start Protocol](#integration-with-cold-start-protocol)
- [Cold Start Loading Decision Tree](#cold-start-loading-decision-tree)
- [File Location and Access](#file-location-and-access)