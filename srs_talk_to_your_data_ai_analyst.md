# SOFTWARE REQUIREMENTS SPECIFICATION (SRS)

## for
**Talk to Your Data – AI Analyst (Text-to-SQL System)**  
Version 1.0

---

## 1. Introduction

### 1.1 Purpose
This document specifies the functional and non-functional requirements for the **Talk to Your Data AI Analyst**, a system that allows users to query relational databases using natural language and receive accurate, safe, and explainable results.

### 1.2 Scope
The system enables non-technical users to ask business questions in plain English. The system converts these questions into validated SQL queries, executes them securely, and presents results along with human-readable explanations.

Key features include:
- Natural language to SQL conversion
- Secure query execution with guardrails
- Result explanation and visualization
- Role-based access control

---

## 2. Overall Description

### 2.1 Product Perspective
The product is a standalone web-based internal analytics tool that integrates with existing relational databases (PostgreSQL/MySQL). It does not replace BI tools but complements them by enabling ad-hoc analysis through conversational interaction.

### 2.2 Operating Environment
- Backend: Python (Flask/Django API)
- Database: PostgreSQL / MySQL
- LLM Access: API-based or private deployment
- Client: Web browser (modern browsers)
- Hosting: Cloud or on-premise
- Fallback Mode: When `DEV_FALLBACK_MODE=true`, the system runs fully without LLM calls (template SQL + result-based explanations)

### 2.3 Design and Implementation Constraints
- SQL queries must be read-only by default
- The system must prevent SQL injection and destructive queries
- Sensitive schemas/tables may be restricted per role
- LLM responses must conform to structured output formats

---

## 3. Requirement Identifying Technique
Use case–based requirement identification is used due to the interactive nature of the system.

### 3.1 Use Case Diagram
Actors:
- Business User
- Admin
- Database System

### 3.2 Use Case Description

**Use Case ID:** UC-1  
**Use Case Name:** Ask Business Question

**Primary Actor:** Business User  
**Secondary Actor:** Database System

**Description:**
User submits a natural language query to retrieve insights from the database.

**Trigger:**
User submits a question in the chat interface.

**Preconditions:**
- User is authenticated
- Database connection is configured

**Postconditions:**
- Query results are displayed
- Explanation is generated

**Normal Flow:**
1. User enters a question in natural language.
2. System analyzes intent and schema.
3. System generates SQL query.
4. SQL query is validated.
5. Query is executed on database.
6. Results are returned.
7. System generates explanation.
8. Results and explanation are displayed.

**Exceptions:**
- Invalid or unsafe SQL generated
- User lacks permission for requested data

---

## 4. Specific Requirements

### 4.1 System Feature: Natural Language Querying

**FR-1:** The system shall accept natural language questions from users.

**FR-2:** The system shall translate natural language into SQL queries.

**FR-3:** The system shall validate generated SQL before execution.

**FR-4:** The system shall execute SQL queries in read-only mode.

**FR-5:** The system shall display query results in tabular form.

**FR-6:** The system shall generate a natural language explanation of results.

### 4.2 Advanced Requirements

**FR-7:** The system shall support role-based table access control (RBAC) with at least 3 roles: analyst, finance, and admin.

**FR-8:** The system shall maintain an audit trail of all executed queries, including user ID, question, generated SQL, execution status, and timestamp.

**FR-9:** The system shall cache database schema metadata with a configurable time-to-live (TTL) to reduce introspection overhead.

**FR-10:** The system shall handle LLM failures gracefully by providing a fallback mode that uses template-based SQL generation for common query patterns.

### 4.3 User Management & Authentication

**FR-11:** The system shall provide JWT-based authentication with token generation, validation, and role assignment.

**FR-12:** The system shall support saved queries, allowing users to bookmark frequently-used questions with custom names and descriptions.

**FR-13:** The system shall provide search functionality for saved queries using keyword matching.

### 4.4 Analytics & Monitoring

**FR-14:** The system shall track query analytics including total queries executed, success rates, average latency, and slowest queries.

**FR-15:** The system shall provide an analytics dashboard accessible via API endpoint displaying aggregate statistics.

**FR-16:** The system shall maintain query history for the last N executed queries with timestamps.

### 4.5 Performance Optimization

**FR-17:** The system shall cache query results based on question hash with configurable TTL (default 5 minutes) to reduce redundant database queries.

**FR-18:** The system shall provide cache statistics including hit rate, miss rate, and cache size.

**FR-19:** The system shall implement rate limiting to prevent API abuse (default: 20 queries/minute per IP address).

### 4.6 Data Export & Visualization

**FR-20:** The system shall allow users to export query results in CSV and JSON formats.

**FR-21:** The system shall provide data visualization capabilities with automatic chart generation for numeric results.

**FR-22:** The system shall offer tabbed result views including: table view, chart view, SQL view, and explanation view.

**Export usage note:** The `/query/export` endpoint consumes the `columns` and `rows` returned from a prior `/query` call, along with a requested `format` (csv|json).

---

## 5. Quality Attributes

### 5.1 Usability
- Minimal learning curve for non-technical users
- Clear error messages and explanations

### 5.2 Performance
- 95% of queries shall execute within 5 seconds for datasets under defined limits

### 5.3 Security

**NFR-1:** The system shall prevent SQL injection through multi-layer validation:
- Forbidden keyword detection (INSERT, UPDATE, DELETE, DROP, ALTER, etc.)
- Pattern-based detection (semicolons, comments, UNION, CTEs)
- Table and column allowlisting per user role
- Auto-injection of LIMIT clause to prevent runaway queries

**NFR-2:** The system shall enforce read-only transactions on all database connections via "SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY".

**NFR-3:** The system shall enforce statement-level timeouts (default 5 seconds) to prevent resource exhaustion from long-running queries.

### 5.4 Reliability
- System shall gracefully degrade when LLM is unavailable
- System shall log all query execution details for auditability
- System shall validate user permissions before query execution
- Fallback explanations derive from returned rows/columns when LLM is unavailable, ensuring results remain usable without external API access
- Edge-case suite covers empty input, malformed JSON, long queries, cache behavior, and injection attempts to guard against regressions

### 5.5 Availability & Scalability

**NFR-4:** The system shall implement in-memory caching to handle repeated queries with sub-100ms response times.

**NFR-5:** The system shall implement rate limiting with configurable thresholds per endpoint (global: 200/hour, query endpoint: 20/minute).

**NFR-6:** The system shall provide comprehensive error messages with actionable suggestions, including available table lists when access is denied.

### 5.6 Maintainability

**NFR-7:** The system shall maintain modular architecture with clear separation of concerns across authentication, caching, analytics, and core query processing.

**NFR-8:** The system shall provide API documentation through structured endpoint listings and response schemas.

---

## 6. External Interface Requirements

### 6.1 User Interfaces
- Web-based chat-style interface
- Results table and summary panel

### 6.2 Software Interfaces
- Database connectors (PostgreSQL/MySQL)
- LLM APIs

### 6.3 Hardware Interfaces
Not applicable

### 6.4 Communication Interfaces
HTTPS-based API communication

---

## 7. Project Gantt Chart
(To be defined during implementation planning)

---

## 8. References
- Software Engineering – Roger Pressman
- UML and Use Case Modeling Standards

