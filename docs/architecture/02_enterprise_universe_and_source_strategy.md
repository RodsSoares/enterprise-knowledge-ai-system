Enterprise Knowledge AI System
Enterprise Universe and Source Strategy
Status: Initial Architecture
Version: 0.1
Architecture: Source-Agnostic Enterprise Knowledge Intelligence
1. Purpose
This document defines the relationship between the Enterprise Knowledge
AI System, the synthetic enterprise universe, and external data and
knowledge sources.
The central architectural principle is:
Build independently. Connect generically. Use the AI Supply Chain
Copilot as the initial structured enterprise data source.

The Enterprise Knowledge AI System must remain independent from the AI
Supply Chain Copilot.
The Copilot is an initial source of structured enterprise data, not a
dependency, internal module, or architectural prerequisite.
2. Core Product Thesis
The Enterprise Knowledge AI System provides an intelligence layer over
heterogeneous corporate knowledge, independently of the original source.
The system is designed to work with enterprise information originating
from different technologies, repositories, formats, and business
domains.
Potential sources include:
- local files;
- document repositories;
- relational databases;
- enterprise applications;
- APIs;
- data warehouses;
- cloud storage;
- knowledge platforms.
The architecture must therefore model sources generically rather than
around a specific application.
3. Independence from the AI Supply Chain Copilot
The Enterprise Knowledge AI System:
- does not import Copilot application code;
- does not depend on Copilot internal architecture;
- does not embed Copilot business logic;
- does not require the Copilot to operate;
- does not use Copilot-specific concepts inside its core architecture.
Instead, interaction occurs through generic source interfaces.
Conceptually:
Enterprise Knowledge AI System
              │
              ▼
        Source Interfaces
              │
     ┌────────┼────────┐
     ▼        ▼        ▼
   Files   Databases   APIs
              │
              ▼
     AI Supply Chain Copilot
       [initial data source]
If the AI Supply Chain Copilot were replaced by another structured
enterprise system, the core Enterprise Knowledge AI System should remain
valid.
4. Synthetic Enterprise Universe
The portfolio projects may share one coherent synthetic enterprise
universe without becoming technically coupled.
                  SYNTHETIC ENTERPRISE UNIVERSE
                              │
              ┌───────────────┴───────────────┐
              │                               │
     STRUCTURED REALITY              ENTERPRISE KNOWLEDGE
              │                               │
     Operational systems             Policies / SOPs /
     Databases / APIs                Contracts / Reports /
              │                      Minutes / Guidelines
              │                               │
              └───────────────┬───────────────┘
                              │
                              ▼
                 ENTERPRISE INTELLIGENCE
The purpose of sharing the same synthetic universe is consistency.
A route, product, warehouse, carrier, incident, date, or operational
event should not acquire contradictory identities merely because it
appears in different portfolio projects.
Shared business reality does not imply shared application code.
5. Existing Structured Source: AI Supply Chain Copilot
The current AI Supply Chain Copilot contains structured operational
information in two primary domains:
Inventory
The existing model includes structured information related to:
- products;
- warehouses;
- inventory parameters;
- inventory movements;
- inventory metrics;
- inventory scoring;
- recommended actions.
Transportation
The existing model includes structured information related to:
- routes;
- vehicle types;
- route-vehicle options;
- route-vehicle rates;
- raw forecast;
- demand forecast;
- planned trips;
- transportation planning;
- cost analysis;
- capacity;
- utilization;
- weekly evolution;
- cost rankings;
- recent trends;
- operational changes.
These assets form the first structured enterprise dataset available to
the Enterprise Knowledge AI System.
They do not define the system's architecture.
6. Structured Data vs Enterprise Knowledge
A central modeling rule is the separation between operational facts and
enterprise knowledge.
Structured Data
Information belongs naturally to the structured layer when it represents
explicit operational facts that are naturally tabular, measurable,
filterable, or aggregatable.
Examples:
- route;
- SKU;
- warehouse;
- vehicle;
- forecast;
- volume;
- cost;
- capacity;
- utilization;
- inventory balance;
- operational performance;
- delivery event;
- incident occurrence.
Typical access mechanisms:
- SQL;
- database queries;
- APIs;
- analytics services.
Enterprise Knowledge
Information belongs naturally to the knowledge layer when its meaning
depends on interpretation of organizational content.
Examples:
- corporate policies;
- contractual clauses;
- procedures;
- governance rules;
- escalation requirements;
- definitions;
- document authority;
- regulatory guidance;
- committee decisions;
- security requirements.
Typical access mechanisms:
- document parsing;
- chunking;
- indexing;
- retrieval;
- RAG.
Combined Intelligence
Some questions require both.
Example:
A carrier has remained below its applicable SLA for three consecutive
periods. What action does the organization require?

The performance history is structured operational evidence.
The required action is enterprise knowledge.
The answer therefore requires synthesis across sources.
7. Information Classification Model
Enterprise questions may be classified into four primary categories.
STRUCTURED
The answer can be derived from structured operational data.
Example:
What was the forecast volume for route R001 last week?

KNOWLEDGE
The answer depends on enterprise documents or other unstructured
knowledge.
Example:
What procedure applies after repeated SLA violations?

COMBINED
The answer requires both structured facts and enterprise knowledge.
Example:
Based on the current operational performance, which escalation rule
applies?

ABSTENTION
The available enterprise sources do not contain sufficient evidence.
Example:
What is the company's policy for transporting radioactive materials?

If no such policy exists in the available enterprise corpus, the correct
behavior is to report insufficient evidence rather than generate a
plausible policy from model knowledge.
8. Source-Agnostic Architecture
The Enterprise Knowledge AI System should model connectivity through
generic source categories.
Target conceptual structure:
app/
└── sources/
    ├── files/
    ├── databases/
    └── apis/
Potential future implementations may include:
FILES
├── PDF
├── DOCX
├── XLSX
├── PPTX
├── Markdown
└── TXT

DATABASES
├── SQLite
├── PostgreSQL
├── SQL Server
└── other relational sources

APIs
├── REST
├── ERP interfaces
├── CRM interfaces
└── enterprise services
Future connectors may extend this model without changing the core
retrieval architecture.
Potential examples include:
- SharePoint;
- Google Drive;
- object storage;
- enterprise knowledge platforms;
- data warehouses.
These are architectural possibilities, not current implementation
commitments.
9. Connector Boundary
Source-specific logic should remain at the system boundary.
Conceptually:
SOURCE
   ↓
CONNECTOR / ADAPTER
   ↓
NORMALIZED INTERNAL REPRESENTATION
   ↓
KNOWLEDGE / DATA PROCESSING
   ↓
RETRIEVAL
   ↓
SYNTHESIS
The objective is to prevent source-specific implementation details from
propagating through the core system.
For example, whether structured information originates from SQLite,
PostgreSQL, or an API should not fundamentally change the downstream
enterprise intelligence model.
10. Initial Source Strategy
The initial development environment will use the AI Supply Chain Copilot
as the first structured enterprise source because it already provides a
controlled synthetic operational universe.
This provides several advantages:
- known data quality;
- known business semantics;
- reproducible scenarios;
- existing SQL and analytics;
- controlled synthetic information;
- consistency across portfolio projects.
However, the implementation must treat this source through generic
database or API boundaries.
No architectural component should be named or designed as a dedicated
copilot_connector unless it exists purely as an external adapter
implementation.
The core system should understand source types and capabilities, not
portfolio project identities.
11. Independent Product Evolution
The AI Supply Chain Copilot and Enterprise Knowledge AI System should
evolve independently.
A feature should not be added to the Copilot merely because the
Enterprise Knowledge AI System needs convenient test data.
Likewise, the Enterprise Knowledge AI System should not be designed
around existing Copilot limitations.
If future enterprise scenarios reveal missing structured information,
the decision to extend the Copilot should be based on whether that
information represents a legitimate extension of the Copilot's own
Supply Chain domain.
This preserves architectural integrity on both sides.
12. Future Structured Domain Extensions
One possible future extension of the synthetic enterprise universe is
Carrier Management.
Potential entities may include:
carriers
carrier_route_assignments
carrier_service_levels
carrier_performance
transportation_incidents
These entities are not part of the current Enterprise Knowledge AI
System implementation commitment.
They should be introduced only if they represent legitimate structured
operational concepts for the Supply Chain universe.
Contractual obligations, policy rules, escalation procedures, and
document authority should remain in the enterprise knowledge layer
rather than being duplicated unnecessarily as operational database
fields.
13. Evaluation Strategy: Two Golden Sets
The evaluation architecture should distinguish pure enterprise knowledge
retrieval from future cross-source intelligence.
Golden Set A --- Enterprise Knowledge
Primary objective:
Evaluate the Enterprise RAG architecture independently from the AI
Supply Chain Copilot.

The initial set contains approximately 36 controlled questions covering:
- direct retrieval;
- procedures;
- multi-document synthesis;
- contract comparison;
- historical information;
- document versioning;
- authority conflicts;
- contextual AI disambiguation;
- insufficient evidence;
- abstention.
This set primarily evaluates:
Documents
    ↓
Retrieval
    ↓
Reranking
    ↓
Evidence
    ↓
Grounded Generation
Golden Set B --- Cross-Source Intelligence
Future objective:
Evaluate questions that require structured operational facts and
enterprise knowledge simultaneously.

Conceptually:
                  USER QUESTION
                        │
                        ▼
              INFORMATION NEED
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
       STRUCTURED DATA       ENTERPRISE KNOWLEDGE
       Database / API              RAG
             │                     │
             └──────────┬──────────┘
                        ▼
                    SYNTHESIS
                        ▼
               GROUNDED ANSWER
Golden Set B should be created only after the structured and knowledge
requirements are explicitly mapped.
14. Relationship Between the Two Portfolio Systems
The systems demonstrate complementary architectural capabilities.
AI Supply Chain Copilot
Primary role:
Transform structured Supply Chain data into operational facts,
analytics, scenarios, and decision support.

Enterprise Knowledge AI System
Primary role:
Transform heterogeneous corporate knowledge into a trustworthy,
searchable, and evidence-backed intelligence layer.

Their relationship can be summarized as:
Data       → Facts
Analytics  → Scenarios
RAG        → Enterprise Knowledge
AI / LLM   → Synthesis & Recommendation
Human      → Decision
This relationship is conceptual.
Neither system should require the other to function independently.
15. Long-Term Product Direction
The architecture should preserve the possibility of evolving beyond a
portfolio-specific RAG implementation.
A future organization might connect:
Company A
SharePoint + SQL Server + internal APIs

Company B
Google Drive + PostgreSQL + ERP

Company C
Object Storage + Data Warehouse + REST APIs
The enterprise sources differ.
The central problem remains the same:
Transform heterogeneous and fragmented corporate knowledge into a
trustworthy and searchable enterprise intelligence layer.

Therefore, source independence is not an implementation detail.
It is part of the product thesis.
16. Architectural Decisions Frozen by This Document
The following decisions are established at this stage:
1. The Enterprise Knowledge AI System is an independent application.
2. The architecture is source-agnostic.
3. The AI Supply Chain Copilot is the initial structured enterprise
   data source.
4. The Enterprise Knowledge AI System must not depend on Copilot
   application code.
5. Connectivity should occur through generic source interfaces.
6. Structured operational facts and enterprise knowledge remain
   conceptually distinct.
7. Cross-source synthesis is a future capability, not a reason to
   couple the systems.
8. The existing 36-question knowledge evaluation remains independent
   from the Copilot.
9. A separate cross-source Golden Set may be introduced later.
10. Extensions to the Copilot must be justified by the Copilot's own
    business domain.
11. Shared synthetic business reality does not imply shared technical
    architecture.
17. Next Design Step
The next step is to formalize the controlled enterprise ground truth.
This includes:
canonical_facts.yaml
document_registry.yaml
golden_questions.yaml
Before generating the synthetic document corpus, these artifacts will
define:
- authoritative enterprise facts;
- document identities and relationships;
- expected evidence;
- distractors;
- version history;
- expected retrieval behavior;
- abstention cases.
This creates a reproducible evaluation environment while preserving the
independence of the Enterprise Knowledge AI System from any specific
source.