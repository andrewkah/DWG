# DWG Technical Specification: Workflow DSL v1.0 & Formal State Machine Engine

This specification freezes the **Workflow DSL v1.0 contract** and defines the **deterministic execution behavior of the Workflow Engine**. It serves as the single source of truth for the Authoring API, Workflow Engine, REST/USSD Adapters, and the automated test suite.

---

# PART 1: Workflow DSL v1.0 Specification

```text
+---------------------+        Validates Schema        +------------------------+
|    Authoring API    | -----------------------------> | JSON Schema (Draft-07) |
+----------+----------+                                +------------------------+
           |
           v (Produces Validated Immutable JSON)
+-------------------------------------------------------------------------------+
|                             WORKFLOW DEFINITION                               |
+-------------------------------------------------------------------------------+
           |
           v (Executes Graph Deterministically)
+---------------------+
|   Workflow Engine   |
+----------+----------+
           |
     +-----+-----+
     |           |
     v           v
+---------+ +---------+
|  REST   | |  USSD   |
| Adapter | | Adapter |
+---------+ +---------+
```

---

## 1. Concrete Evaluation Rules & Edge Cases

Before looking at the JSON Schema, we must define how inputs, validations, and transitions are evaluated.

### 1.1 Case 1: Type Mismatch (`"age": "hello"`)

* **Field Definition:** `{"name": "applicant_age", "type": "integer", "validation": {"min": 18, "max": 99}}`
* **Raw Input Received:** `"hello"`
* **Evaluation Pipeline:**
  1. **Coercion Attempt:** Engine attempts to parse `"hello"` as a base-10 64-bit integer.
  2. **Result:** Parsing fails (`ValueError`).
  3. **Engine Action:** Field validation halts immediately before evaluating numerical constraints (`min`/`max`).
  4. **State Mutation:** `current_state` does **not** advance. `collected_data` is **not** updated.
  5. **Error Code:** `TYPE_MISMATCH` (`expected: integer`, `provided: string`).
  6. **Adapter Responses:**
     * **REST:** Returns `HTTP 422 Unprocessable Entity` with a structured validation error array.
     * **USSD:** Returns `CON Invalid number. Please enter a valid whole number:\nEnter your age:`

---

### 1.2 Case 2: Constraint Violation (`age = 17` when `min = 18`)

* **Field Definition:** `{"name": "applicant_age", "type": "integer", "validation": {"min": 18, "max": 99}}`
* **Raw Input Received:** `"17"`
* **Evaluation Pipeline:**
  1. **Coercion Attempt:** Successfully parsed to integer `17`.
  2. **Constraint Check:** Evaluates `17 >= 18`. Result: `FALSE`.
  3. **State Mutation:** `current_state` does **not** advance. `collected_data` is **not** updated.
  4. **Error Code:** `CONSTRAINT_VIOLATION` (`rule: min`, `expected: 18`, `provided: 17`).
  5. **Adapter Responses:**
     * **REST:** Returns `HTTP 422 Unprocessable Entity` with error details: `{"rule": "min", "limit": 18}`.
     * **USSD:** Returns `CON Value too low. Must be at least 18:\nEnter your age:`

---

### 1.3 Case 3: Conditional Transition Structure

Transitions are evaluated **in declaration order**. The first transition whose predicate evaluates to `true` is selected. If a transition has no `condition` block, it is treated as an **unconditional transition** (always `true`).

```json
"transitions": [
  {
    "condition": {
      "field": "employed",
      "operator": "equals",
      "value": true
    },
    "next": "employer_name"
  },
  {
    "condition": {
      "field": "employed",
      "operator": "equals",
      "value": false
    },
    "next": "primary_crop"
  }
]
```

#### Supported Predicate Operators (DSL v1.0)

| Operator | Supported Data Types | Evaluation Logic | Example |
| --- | --- | --- | --- |
| `equals` | `string`, `integer`, `decimal`, `boolean` | `collected_data[field] == value` | `{"field": "employed", "operator": "equals", "value": true}` |
| `not_equals` | `string`, `integer`, `decimal`, `boolean` | `collected_data[field] != value` | `{"field": "role", "operator": "not_equals", "value": "ADMIN"}` |
| `gt` | `integer`, `decimal` | `collected_data[field] > value` | `{"field": "age", "operator": "gt", "value": 65}` |
| `gte` | `integer`, `decimal` | `collected_data[field] >= value` | `{"field": "age", "operator": "gte", "value": 18}` |
| `lt` | `integer`, `decimal` | `collected_data[field] < value` | `{"field": "salary", "operator": "lt", "value": 50000}` |
| `lte` | `integer`, `decimal` | `collected_data[field] <= value` | `{"field": "score", "operator": "lte", "value": 100}` |
| `in` | `string`, `integer` | `collected_data[field] in list` | `{"field": "district", "operator": "in", "value": ["Gulu", "Arua"]}` |
| `not_in` | `string`, `integer` | `collected_data[field] not in list` | `{"field": "category", "operator": "not_in", "value": ["BLOCKED"]}` |
| `exists` | Any | `field in collected_data` | `{"field": "email", "operator": "exists", "value": true}` |

---

## 2. Machine-Validatable JSON Schema (`workflow-dsl-v1.schema.json`)

This JSON Schema (Draft-07 standard) must be used by the Authoring API to validate all incoming workflow drafts before they can be published.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://dwg.io/schemas/v1/workflow.json",
  "title": "DWG Workflow Definition DSL v1.0",
  "type": "object",
  "required": [
    "dsl_schema_version",
    "workflow_id",
    "name",
    "start_state",
    "states"
  ],
  "additionalProperties": false,
  "properties": {
    "dsl_schema_version": {
      "type": "string",
      "enum": ["1.0"]
    },
    "workflow_id": {
      "type": "string",
      "pattern": "^[a-z0-9_-]{3,64}$"
    },
    "name": {
      "type": "string",
      "minLength": 3,
      "maxLength": 128
    },
    "description": {
      "type": "string",
      "maxLength": 512
    },
    "start_state": {
      "type": "string",
      "pattern": "^[a-z0-9_]{1,64}$"
    },
    "states": {
      "type": "array",
      "minItems": 1,
      "items": {
        "$ref": "#/definitions/state"
      }
    }
  },
  "definitions": {
    "state": {
      "type": "object",
      "required": ["id", "kind", "prompt"],
      "additionalProperties": false,
      "properties": {
        "id": {
          "type": "string",
          "pattern": "^[a-z0-9_]{1,64}$"
        },
        "kind": {
          "type": "string",
          "enum": ["input", "confirm", "terminal"]
        },
        "field": {
          "$ref": "#/definitions/field"
        },
        "prompt": {
          "$ref": "#/definitions/prompt"
        },
        "transitions": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/transition"
          }
        },
        "terminal_status": {
          "type": "string",
          "enum": ["COMPLETED", "CANCELLED"]
        }
      },
      "allOf": [
        {
          "if": { "properties": { "kind": { "const": "input" } } },
          "then": { "required": ["field", "transitions"] }
        },
        {
          "if": { "properties": { "kind": { "const": "confirm" } } },
          "then": { "required": ["transitions"] }
        },
        {
          "if": { "properties": { "kind": { "const": "terminal" } } },
          "then": { "required": ["terminal_status"] }
        }
      ]
    },
    "field": {
      "type": "object",
      "required": ["name", "type", "required"],
      "additionalProperties": false,
      "properties": {
        "name": {
          "type": "string",
          "pattern": "^[a-z0-9_]{1,64}$"
        },
        "type": {
          "type": "string",
          "enum": ["text", "integer", "decimal", "boolean", "choice"]
        },
        "required": {
          "type": "boolean"
        },
        "sensitive": {
          "type": "boolean",
          "default": false
        },
        "options": {
          "type": "array",
          "minItems": 1,
          "items": {
            "$ref": "#/definitions/choice_option"
          }
        },
        "validation": {
          "$ref": "#/definitions/field_validation"
        }
      },
      "allOf": [
        {
          "if": { "properties": { "type": { "const": "choice" } } },
          "then": { "required": ["options"] }
        }
      ]
    },
    "choice_option": {
      "type": "object",
      "required": ["label", "value"],
      "additionalProperties": false,
      "properties": {
        "label": { "type": "string", "minLength": 1, "maxLength": 64 },
        "value": { "type": ["string", "number", "boolean"] }
      }
    },
    "field_validation": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "min_length": { "type": "integer", "minimum": 0 },
        "max_length": { "type": "integer", "minimum": 1 },
        "min": { "type": "number" },
        "max": { "type": "number" },
        "pattern": { "type": "string" }
      }
    },
    "prompt": {
      "type": "object",
      "required": ["default"],
      "additionalProperties": false,
      "properties": {
        "default": { "type": "string", "minLength": 1, "maxLength": 320 }
      }
    },
    "transition": {
      "type": "object",
      "required": ["next"],
      "additionalProperties": false,
      "properties": {
        "next": { "type": "string", "pattern": "^[a-z0-9_]{1,64}$" },
        "condition": { "$ref": "#/definitions/condition" }
      }
    },
    "condition": {
      "type": "object",
      "required": ["field", "operator", "value"],
      "additionalProperties": false,
      "properties": {
        "field": { "type": "string", "pattern": "^[a-z0-9_]{1,64}$" },
        "operator": {
          "type": "string",
          "enum": ["equals", "not_equals", "gt", "gte", "lt", "lte", "in", "not_in", "exists"]
        },
        "value": {
          "type": ["string", "number", "boolean", "array"]
        }
      }
    }
  }
}
```

---

# PART 2: Formal State Machine Engine Specification

## 1. Reference Workflow Definition

The reference workflow for our state machine behavior specification:

```text
                  [ START ]
                      |
                      v
             (State: full_name)
                      |
                      v
             (State: applicant_age)
                      |
                      v
             (State: is_employed)
                     / \
   (employed == true)   (employed == false)
                   /     \
                  v       v
      (State: employer)   (State: income_source)
                  \       /
                   v     v
             (State: confirm)
                    / \
     (confirm == 1)     (confirm == 2)
                  /     \
                 v       v
         [ complete ]   [ cancel ]
```

---

## 2. Formal Execution Model

Let the Engine Session state be a tuple:
$$S = \langle \text{id}, \text{org\_id}, \text{ver\_id}, \text{curr\_state}, \text{data}, \text{status}, \text{ver}, \text{trans\_count}, \text{expires\_at} \rangle$$

Given an inbound command $C = \langle \text{session\_id}, \text{raw\_input}, \text{metadata} \rangle$, the Engine computes:
$$T(S, C) \rightarrow \langle S', \text{Result} \rangle$$

---

## 3. Exhaustive Execution Behavior Matrix (The 11 Engine Scenarios)

```text
+-------------------------------------------------------------------------------------------------------------------------------------------------------+
| #  | SCENARIO                    | ENGINE ACTION & STATE MUTATION    | DB / REDIS MUTATIONS            | REST HTTP RESPONSE   | USSD TELCO RESPONSE   |
+----+-----------------------------+-----------------------------------+---------------------------------+----------------------+-----------------------+
| 1  | Valid Input                 | Coerces value; appends to `data`; | Redis: Update state & data;     | HTTP 200 OK          | CON <Next Prompt>     |
|    |                             | advances `curr_state` -> `next`.  | Incr `row_version`. Expire=180s.| (Next state details) |                       |
+----+-----------------------------+-----------------------------------+---------------------------------+----------------------+-----------------------+
| 2  | Invalid Input               | Parsing fails; `curr_state` stays;| Redis: No state advance;        | HTTP 422             | CON Invalid number... |
|    | (Type Mismatch)             | `data` remains untouched.         | Expire reset to 180s.           | TYPE_MISMATCH        | <Current Prompt>      |
+----+-----------------------------+-----------------------------------+---------------------------------+----------------------+-----------------------+
| 3  | Invalid Input               | Type passes; rule bounds fail;    | Redis: No state advance;        | HTTP 422             | CON Value too low...  |
|    | (Constraint Violation)      | `curr_state` stays; no data added.| Expire reset to 180s.           | CONSTRAINT_VIOLATION | <Current Prompt>      |
+----+-----------------------------+-----------------------------------+---------------------------------+----------------------+-----------------------+
| 4  | No Matching Transition      | Validation passes; no predicate   | Redis: Set status='FAILED';     | HTTP 500             | END An unexpected     |
|    | (Dead End / Fallthrough)    | is true; halts execution.         | Log SEVERE graph breach.        | NO_TRANSITION_MATCH  | error occurred.       |
+----+-----------------------------+-----------------------------------+---------------------------------+----------------------+-----------------------+
| 5  | Expired Session             | Session key missing in Redis;     | Redis: None.                    | HTTP 410 Gone        | END Session expired.  |
|    | (TTL Elapsed)               | Reject immediately.               | DB: None.                       | SESSION_EXPIRED      | Please dial again.    |
+----+-----------------------------+-----------------------------------+---------------------------------+----------------------+-----------------------+
| 6  | Cancelled Session           | User selected 'Cancel' on confirm;| Redis: Status='CANCELLED';      | HTTP 200 OK          | END Application       |
|    |                             | Terminal state reached.           | DB: NO submission created.      | Status: CANCELLED    | cancelled.            |
+----+-----------------------------+-----------------------------------+---------------------------------+----------------------+-----------------------+
| 7  | Completed Session           | User confirms terminal state;     | DB: Insert `submissions` row;   | HTTP 200 OK          | END Thank you!        |
|    |                             | Session status -> `COMPLETED`.    | Redis: Status='COMPLETED'.      | Submission ID returned| Submission complete.  |
+----+-----------------------------+-----------------------------------+---------------------------------+----------------------+-----------------------+
| 8  | Duplicate Request           | Inbound hash matches existing     | None (Engine bypassed entirely; | HTTP 200 OK          | (Exact identical      |
|    | (Aggregator Retry / Replay) | key in `idem:{hash}`.             | return from cache).             | (Cached JSON payload)| cached string)        |
+----+-----------------------------+-----------------------------------+---------------------------------+----------------------+-----------------------+
| 9  | Concurrent Request          | Two workers process same session; | Winner: Commits normally.       | Winner: HTTP 200     | Winner: CON/END       |
|    | (Race Condition)            | `row_version` mismatch on write.  | Loser: Redis CAS write fails.   | Loser: HTTP 409      | Loser: Retry Turn     |
+----+-----------------------------+-----------------------------------+---------------------------------+----------------------+-----------------------+
| 10 | Unknown State               | Session pointer corrupted; state  | Redis: Set status='FAILED'.     | HTTP 500             | END System error.     |
|    | (Invalid State Pointer)     | ID missing in workflow JSON.      | Log alert to CloudWatch.        | UNKNOWN_STATE_ID     | Please contact support|
+----+-----------------------------+-----------------------------------+---------------------------------+----------------------+-----------------------+
| 11 | Execution Loop Breaker      | Session transition count exceeds  | Redis: Set status='FAILED'.     | HTTP 508             | END Session limit     |
|    | (Infinite Cycle Guard)      | `max_transitions` (50).           | Alert: Graph cycle detected.    | LOOP_LIMIT_EXCEEDED  | exceeded.             |
+-------------------------------------------------------------------------------------------------------------------------------------------------------+
```

---

## 4. Deep-Dive Specification by Scenario

---

### Scenario 1: Valid Input (Normal State Progression)

* **Pre-condition:** Session is `ACTIVE` at state `full_name`. User submits `"Sarah Nabukeera"`.
* **Engine Processing:**
  1. Validates string length ($15 \ge 3$ and $\le 60$). Passes.
  2. Mutates `collected_data["applicant_name"] = "Sarah Nabukeera"`.
  3. Evaluates outgoing transition: Unconditional `next: "applicant_age"`.
  4. Sets `current_state = "applicant_age"`.
  5. Increments `transition_count` from `0` to `1`.
  6. Increments `row_version` from `1` to `2`.
* **Redis Write:** Atomic update to `sess:{id}` with refreshed 180s TTL.
* **REST Response (HTTP 200 OK):**

  ```json
  {
    "session_id": "8f3b2e7d-94c1-4b3e-8c7a-123456789abc",
    "status": "ACTIVE",
    "current_state": {
      "id": "applicant_age",
      "prompt": "Enter your age in years:",
      "field": {
        "name": "applicant_age",
        "type": "integer",
        "required": true
      }
    }
  }
  ```

* **USSD Response:** `CON Enter your age in years:`

---

### Scenario 2: Invalid Input — Type Mismatch

* **Pre-condition:** Session is `ACTIVE` at state `applicant_age`. User submits `"twenty"`.
* **Engine Processing:**
  1. Attempts integer coercion: fails.
  2. Sets error context: `{"code": "TYPE_MISMATCH", "expected": "integer"}`.
  3. `current_state` remains `"applicant_age"`.
  4. `collected_data` remains unchanged.
* **Redis Write:** Extends session TTL (180s); session state data is **not** mutated.
* **REST Response (HTTP 422 Unprocessable Entity):**

  ```json
  {
    "error": {
      "code": "TYPE_MISMATCH",
      "message": "Invalid data type for field 'applicant_age'. Expected integer.",
      "field": "applicant_age",
      "expected_type": "integer"
    }
  }
  ```

* **USSD Response:** `CON Invalid number. Please enter a valid whole number:\nEnter your age in years:`

---

### Scenario 3: Invalid Input — Constraint Violation

* **Pre-condition:** Session is `ACTIVE` at state `applicant_age`. User submits `"14"`.
* **Engine Processing:**
  1. Integer coercion succeeds (`14`).
  2. Constraint validation check fails: `14 < min (18)`.
  3. Sets error context: `{"code": "CONSTRAINT_VIOLATION", "rule": "min", "limit": 18}`.
  4. `current_state` remains `"applicant_age"`.
* **REST Response (HTTP 422 Unprocessable Entity):**

  ```json
  {
    "error": {
      "code": "CONSTRAINT_VIOLATION",
      "message": "Value 14 is below minimum allowed value of 18.",
      "field": "applicant_age",
      "rule": "min",
      "limit": 18
    }
  }
  ```

* **USSD Response:** `CON Value too low. Must be at least 18:\nEnter your age in years:`

---

### Scenario 4: No Matching Transition (Graph Dead End)

* **Pre-condition:** Session is `ACTIVE` at state `is_employed`. `collected_data["employed"] = "UNKNOWN"`.
* **Engine Processing:**
  1. Evaluates Transition 1 (`employed == true`): `FALSE`.
  2. Evaluates Transition 2 (`employed == false`): `FALSE`.
  3. No unconditional fallback transition exists.
  4. Graph execution enters a deadlock. Engine halts and marks session `status = "FAILED"`.
* **Observability:** Emits `ERROR` log with alert `ENGINE_GRAPH_DEADLOCK`.
* **REST Response (HTTP 500 Internal Server Error):**

  ```json
  {
    "error": {
      "code": "NO_MATCHING_TRANSITION",
      "message": "Workflow definition error: No valid transition predicate satisfied from state 'is_employed'."
    }
  }
  ```

* **USSD Response:** `END An unexpected system error occurred. Please contact support.`

---

### Scenario 5: Expired Session (TTL Elapsed)

* **Pre-condition:** User dials turn 2 after 10 minutes. Key `sess:{id}` has been evicted by Redis.
* **Engine Processing:**
  1. Adapter queries `sess:{id}` in Redis $\rightarrow$ Returns `NULL`.
  2. Adapter intercepts `NULL` before invoking Engine.
* **REST Response (HTTP 410 Gone):**

  ```json
  {
    "error": {
      "code": "SESSION_EXPIRED",
      "message": "The workflow session has expired due to inactivity. Please initiate a new session."
    }
  }
  ```

* **USSD Response:** `END Your session has expired. Please dial again.`

---

### Scenario 6: Cancelled Session

* **Pre-condition:** Session is `ACTIVE` at state `confirm`. User selects option `2` ("Cancel").
* **Engine Processing:**
  1. Input validates as choice `2` (`_confirm = false`).
  2. Condition `_confirm == false` routes to state `cancel_state`.
  3. State `cancel_state` is `kind: terminal` with `terminal_status: "CANCELLED"`.
  4. Engine marks session `status = "CANCELLED"`.
  5. **Durable Database Action:** Zero database writes to `submissions`.
* **REST Response (HTTP 200 OK):**

  ```json
  {
    "session_id": "8f3b2e7d-94c1-4b3e-8c7a-123456789abc",
    "status": "CANCELLED",
    "message": "Application cancelled. No data was saved."
  }
  ```

* **USSD Response:** `END Application cancelled. No data was saved.`

---

### Scenario 7: Completed Session (Terminal Success)

* **Pre-condition:** Session is `ACTIVE` at state `confirm`. User selects option `1` ("Confirm").
* **Engine Processing:**
  1. Input validates as choice `1` (`_confirm = true`).
  2. Routes to state `complete_state` (`kind: terminal`, `terminal_status: "COMPLETED"`).
  3. Engine triggers **Durable Submission Pipeline**:
     * Inserts row into PostgreSQL `submissions`:

       ```sql
       INSERT INTO submissions (organization_id, workflow_version_id, session_id, channel, subscriber_hash, data)
       VALUES ('b1a2...', 'c5d6...', '8f3b...', 'ussd', 'hash(phone)', '{"applicant_name": "Sarah", ...}'::jsonb);
       ```

     * Sets Redis session `status = "COMPLETED"`.
* **REST Response (HTTP 200 OK):**

  ```json
  {
    "session_id": "8f3b2e7d-94c1-4b3e-8c7a-123456789abc",
    "status": "COMPLETED",
    "submission_id": "99e8d7c6-b5a4-3210-fedc-ba9876543210",
    "message": "Thank you! Your application has been submitted successfully."
  }
  ```

* **USSD Response:** `END Thank you! Your application has been submitted successfully.`

---

### Scenario 8: Duplicate Request (Aggregator Retry / Replay)

* **Pre-condition:** Network lag causes telco aggregator to resend HTTP POST for turn 1 with identical payload (`sessionId=AT123`, `text=Sarah`).
* **Engine Processing:**
  1. USSD Adapter computes request signature hash: `MD5(africas_talking:AT123:Sarah)`.
  2. Adapter checks Redis key `idem:{hash}`.
  3. **Cache Hit:** Finds cached response `"CON Enter your age in years:"`.
  4. Engine execution is **completely bypassed**.
* **REST / USSD Response:** Returns cached response string immediately in $< 2\text{ms}$.

---

### Scenario 9: Concurrent Request Race Condition

* **Pre-condition:** Two HTTP requests ($R_1$ and $R_2$) for `session_id = 8f3b...` hit Worker 1 and Worker 2 simultaneously when `row_version = 3`.
* **Worker Execution:**
  1. Both workers load `sess:{id}` with `row_version = 3`.
  2. Both workers validate input and prepare updated payload with `row_version = 4`.
  3. Worker 1 executes Redis update first using Compare-And-Swap (CAS) / Lua script:
     $$\text{SET if } \text{row\_version} == 3 \rightarrow \text{SUCCESS. (Version becomes 4)}$$
  4. Worker 2 attempts update with expected version $3$:
     $$\text{SET if } \text{row\_version} == 3 \rightarrow \text{FAILS. (Current version is 4)}$$
* **Worker 2 Action:** Aborts transaction, rolls back local state, and rejects request.
* **REST Response to Loser (HTTP 409 Conflict):**

  ```json
  {
    "error": {
      "code": "CONCURRENT_MODIFICATION_CONFLICT",
      "message": "A concurrent request has modified this session. Please retry."
    }
  }
  ```

---

### Scenario 10: Unknown / Corrupted State ID

* **Pre-condition:** A session in Redis points to `current_state_id = "deleted_step"`, which does not exist in the pinned `WorkflowVersion` definition.
* **Engine Processing:**
  1. Engine loads workflow JSON and searches `states` for `id == "deleted_step"`.
  2. Lookup returns `None`.
  3. Engine halts execution; transitions session `status = "FAILED"`.
  4. Emits `CRITICAL` log: `STATE_POINTER_CORRUPTION`.
* **REST Response (HTTP 500 Internal Server Error):**

  ```json
  {
    "error": {
      "code": "CORRUPTED_STATE_POINTER",
      "message": "State machine integrity fault: State 'deleted_step' does not exist in workflow version."
    }
  }
  ```

* **USSD Response:** `END A system integrity error occurred. Please dial again.`

---

### Scenario 11: Execution Loop Breaker

* **Pre-condition:** A poorly authored workflow contains a logical cycle (State A $\rightarrow$ State B $\rightarrow$ State A).
* **Engine Processing:**
  1. On each transition, `transition_count` increments by 1.
  2. When `transition_count > max_transitions` (50):
     * Engine halts execution immediately.
     * Sets session `status = "FAILED"`.
     * Emits `CRITICAL` log: `MAX_TRANSITION_LIMIT_EXCEEDED`.
* **REST Response (HTTP 508 Loop Detected):**

  ```json
  {
    "error": {
      "code": "MAX_TRANSITIONS_EXCEEDED",
      "message": "Execution halted: Workflow exceeded maximum transition threshold of 50 steps."
    }
  }
  ```

* **USSD Response:** `END Session terminated: Maximum step limit reached.`

---

# PART 3: Mapping Behavior to Test Suites (Milestone 1 Testing Foundation)

This specification forms the basis for Milestone 1 unit and integration test assertions:

```text
+------------------------------------+---------------------------------------------------+
| TEST CATEGORY                      | TARGET TEST SCENARIOS COVERED                     |
+------------------------------------+---------------------------------------------------+
| 1. DSL Schema Validation Tests     | - Valid Schema ingestion                          |
|                                    | - Missing required start_state / empty states     |
|                                    | - Invalid field types or unrecognized operators   |
+------------------------------------+---------------------------------------------------+
| 2. Engine Pure Unit Tests          | - Scenario 1: Valid linear progression            |
|                                    | - Scenario 2 & 3: Type and constraint failures   |
|                                    | - Scenario 4: Unhandled transition deadlocks      |
|                                    | - Scenario 11: Loop limit guard trip at 50 steps  |
+------------------------------------+---------------------------------------------------+
| 3. Concurrency & Idempotency Tests | - Scenario 8: Duplicate replay returns cache      |
|                                    | - Scenario 9: Concurrent CAS version collision    |
+------------------------------------+---------------------------------------------------+
| 4. End-to-End Integration Tests   | - Scenario 6: Cancellation leaves zero submissions|
|                                    | - Scenario 7: Completed session writes Postgres DB|
|                                    | - Scenario 5: Expired Redis key returns HTTP 410  |
+------------------------------------+---------------------------------------------------+
```

# PART 4: Production FastAPI Project Structure

The project follows a **Clean Architecture / Ports & Adapters (Hexagonal)** layout implemented within a Python Modular monolith.

```text
dwg-backend/
├── pyproject.toml                 # Poetry/Hatch/Pip dependencies & tool config
├── Dockerfile                     # Multi-stage production container build
├── docker-compose.yml             # Local Postgres & Redis development infrastructure
├── README.md
│
├── alembic/                       # Database migrations
│   ├── env.py
│   └── versions/
│       └── 0001_initial_schema.py
│
├── src/
│   └── dwg/
│       ├── __init__.py
│       ├── main.py                # FastAPI application entrypoint & middleware assembly
│       ├── config.py              # Pydantic-Settings environment configuration
│       │
│       ├── domain/                # Pure domain models (zero framework dependencies)
│       │   ├── __init__.py
│       │   ├── entities.py        # Organization, Workflow, Version, Session entities
│       │   ├── dsl.py             # Pydantic models for the JSON Schema DSL
│       │   └── errors.py          # Domain exceptions (ValidationError, StateMismatchError)
│       │
│       ├── engine/                # Core Workflow State Machine (Pure Python)
│       │   ├── __init__.py
│       │   ├── state_machine.py   # State transition & condition evaluation engine
│       │   ├── validator.py       # Input validation logic (type coercion, min/max rules)
│       │   └── types.py           # Engine command & result interfaces
│       │
│       ├── adapters/              # Channel & Provider Protocol Adapters
│       │   ├── __init__.py
│       │   ├── ussd/
│       │   │   ├── base.py        # UssdProviderAdapter (Abstract SPI)
│       │   │   ├── africas_talking.py # Africa's Talking webhook adapter
│       │   │   ├── mock.py        # Mock adapter for local CLI & CI testing
│       │   │   └── renderer.py    # Plaintext CON/END formatting & length validation
│       │   └── rest/
│       │       └── serializer.py  # Canonical engine to REST JSON view models
│       │
│       ├── storage/               # Persistence Layer (PostgreSQL & Redis)
│       │   ├── __init__.py
│       │   ├── redis_session.py   # Redis session repository (TTL, CAS optimistic lock)
│       │   ├── redis_idempotency.py # Idempotency cache client
│       │   ├── db.py              # SQLAlchemy 2.0 AsyncEngine session factory
│       │   └── repositories/      # SQL repositories (Org, Workflow, Version, Submission)
│       │       ├── org_repo.py
│       │       ├── workflow_repo.py
│       │       └── submission_repo.py
│       │
│       ├── api/                   # HTTP Routers & Middleware (FastAPI layer)
│       │   ├── __init__.py
│       │   ├── dependencies.py    # FastAPI Dependency Injection (get_db, get_session_repo)
│       │   ├── middleware/
│       │   │   ├── auth.py        # API key verification middleware
│       │   │   ├── logging.py     # Request-ID injection & structured JSON logging
│       │   │   └── idempotency.py # Idempotency header enforcement middleware
│       │   └── v1/
│       │       ├── router.py      # V1 API Router aggregator
│       │       ├── workflows.py   # Authoring endpoints (/v1/workflows)
│       │       ├── sessions.py    # REST session execution (/v1/sessions)
│       │       └── ussd.py        # USSD webhook endpoints (/v1/ussd/*)
│       │
│       └── cli/                   # Developer Tooling & Utilities
│           ├── __init__.py
│           └── simulator.py       # Interactive terminal USSD CLI simulator
│
└── tests/
    ├── conftest.py                # Pytest fixtures & Testcontainers setup
    ├── unit/
    │   ├── test_dsl_parser.py     # Schema validation tests
    │   ├── test_engine.py         # Pure state-machine evaluation tests
    │   └── test_ussd_renderer.py  # CON/END string formatting tests
    ├── integration/
    │   ├── test_redis_session.py  # Redis TTL & optimistic locking tests
    │   ├── test_workflow_repo.py  # Postgres CRUD & unique constraint tests
    │   └── test_rest_api.py       # FastAPI HTTP client endpoint tests
    ├── contract/
    │   └── test_africas_talking.py# Africa's Talking payload contract fixtures
    └── e2e/
        └── test_full_ussd_flow.py # End-to-end simulated USSD sessions
```
