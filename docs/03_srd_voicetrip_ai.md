# Software Requirements Specification (SRS / SRD)
## VoiceTrip AI (YatraPilot AI) — Formal Software Requirements

**Document ID:** SRD-VOICETRIP-001  
**Version:** 1.0  
**Standard Reference:** IEEE Std 830 / ISO/IEC/IEEE 29148 Style  
**Related Documents:** `01_PRD_VoiceTrip_AI.md`, `02_TRD_VoiceTrip_AI.md`, `04_FRD_VoiceTrip_AI.md`  

---

## 1. Introduction

This Software Requirements Specification (SRD/SRS) defines the verifiable, unambiguous software requirements for **VoiceTrip AI (YatraPilot AI)**, a real-time voice-powered AI travel concierge built on Agora Conversational AI, Murf AI Falcon TTS, Google Gemini, Python Flask, and SQLite.

---

## 2. Purpose

The purpose of this document is to establish a formal engineering contract specifying what the software must satisfy across functional behavior, external interfaces, data persistence, security, reliability, and error handling so developers and testers can implement and validate the 8-hour hackathon MVP without ambiguity.

---

## 3. Scope

This specification covers the **VoiceTrip AI** web application:
- Browser-based HTML5/CSS3/JS client using Agora RTC Web SDK.
- Python Flask backend exposing session lifecycle, Custom LLM SSE, approval, and trip CRUD endpoints.
- Integration with Agora Conversational AI Engine (ASR + session runtime + Murf Falcon TTS WebSocket streaming).
- Google Gemini API orchestration with 6 Python tool functions.
- External Open-Meteo and Geoapify Places API integrations.
- Local SQLite persistence (`voicetrip.db`).

---

## 4. Definitions and Abbreviations

| Term | Definition |
| :--- | :--- |
| **ASR** | Automatic Speech Recognition (speech-to-text) |
| **HITL** | Human-in-the-Loop (explicit user confirmation before critical mutations) |
| **MVP** | Minimum Viable Product (achievable in ~8 hours) |
| **POI** | Point of Interest |
| **RTC** | Real-Time Communication (Agora WebRTC transport) |
| **SDRTN®** | Agora Software-Defined Real-Time Network |
| **SSE** | Server-Sent Events (`text/event-stream`) |
| **TTS** | Text-to-Speech (Murf AI Falcon) |
| **VAD** | Voice Activity Detection |

---

## 5. Overall System Description

VoiceTrip AI operates as a single-server, four-layer conversational agent system:
1. Browser client captures user voice and renders live state.
2. Agora Conversational AI Engine manages the RTC channel, ASR, turn-taking, and Murf Falcon TTS streaming.
3. Flask `/api/llm/chat/completions` acts as Agora's Custom LLM endpoint, invoking Google Gemini with Python tool calling.
4. Python tool functions query Open-Meteo, Geoapify Places, and SQLite, returning grounded results to Gemini.

---

## 6. Product Perspective

VoiceTrip AI is a standalone hackathon web application. It is not a microservice mesh and does not depend on external databases or authentication providers. It relies on external cloud APIs (Agora, Murf, Gemini, Open-Meteo, Geoapify) over HTTPS/WSS.

---

## 7. User Classes

| User Class | Description | Access Level |
| :--- | :--- | :--- |
| **Traveler (End User)** | Interacts via browser microphone and UI to plan, modify, approve, and retrieve trips. | Full MVP UI & voice session |
| **Developer / Judge** | Inspects logs, SQLite records, and demo behavior. | Localhost/HTTPS + `/health` + `tool_logs` |

---

## 8. Operating Environment

- **Client:** Modern desktop/laptop browser (Chrome 110+, Edge 110+, Firefox 110+, Safari 16+) with WebRTC and microphone permissions.
- **Server:** Python 3.11+ on Linux/macOS/Windows; SQLite 3; `ngrok` or `cloudflared` HTTPS tunnel (if hosted locally).

---

## 9. System Constraints

- **SYS-CON-001:** Total MVP implementation time is constrained to ~8 hours.
- **SYS-CON-002:** Backend must use Python Flask and SQLite without microservices, Celery/Redis, or complex ORMs.
- **SYS-CON-003:** Real payment gateways and production booking APIs are prohibited in the MVP.
- **SYS-CON-004:** Open-Meteo Forecast API provides forecasts up to 16 days in the future only.
- **SYS-CON-005:** Agora Custom LLM endpoints must be reachable over public HTTPS and emit OpenAI-compatible SSE streams.

---

## 10. Assumptions and Dependencies

- Valid API credentials exist in `.env` for Agora, Murf AI, Google Gemini, and Geoapify.
- Agora Conversational AI Engine is enabled on the target Agora App ID.
- Outbound HTTPS and WebSocket connections from Agora Cloud and the Flask server are permitted.

---

## 11. External Interface Requirements

### 11.1 Hardware Interface Requirements
- **SYS-HW-001:** Client device must have a working microphone and audio output (speakers/headphones) accessible via browser `navigator.mediaDevices.getUserMedia`.

### 11.2 Software Interface Requirements
- **SYS-API-001 (Agora Conversational AI):** The backend shall start and stop voice agents via `POST /api/conversational-ai-agent/v2/projects/{appid}/join` and `POST .../agents/{agentId}/leave` using HTTP Basic Auth.
- **SYS-API-002 (Murf Falcon TTS):** The backend shall configure `tts.vendor = "murf"`, `model = "FALCON"`, and `base_url = "wss://global.api.murf.ai/v1/speech/stream-input"` inside the Agora `/join` payload.
- **SYS-API-003 (Agora Custom LLM SSE):** The backend shall expose `POST /api/llm/chat/completions` accepting OpenAI Chat Completions JSON and returning `text/event-stream` SSE chunks terminated by `data: [DONE]`.
- **SYS-API-004 (Google Gemini):** The backend shall invoke the Gemini API (`google-genai`) with function declarations for all 6 travel tools.
- **SYS-API-005 (Open-Meteo):** The backend shall query `geocoding-api.open-meteo.com` and `api.open-meteo.com/v1/forecast` via HTTPS GET with a 5-second timeout.
- **SYS-API-006 (Geoapify Places):** The backend shall query `api.geoapify.com/v2/places` via HTTPS GET with a 5-second timeout and `apiKey`.

### 11.3 Communication Interface Requirements
- **SYS-COM-001:** Browser-to-Agora audio transport shall use WebRTC over Agora SDRTN®.
- **SYS-COM-002:** Browser-to-Flask control and state sync shall use JSON over HTTPS/HTTP REST.

---

## 12. Functional Requirements

| Req ID | Priority | Requirement Statement |
| :--- | :--- | :--- |
| **SYS-FR-001** | MVP | The system shall allow a user to start a voice session from the browser, generating an Agora RTC token and starting an Agora Conversational AI agent configured with Murf Falcon TTS. |
| **SYS-FR-002** | MVP | The system shall allow a user to stop an active voice session, disconnecting the Agora RTC client and calling Agora `/leave` to terminate the agent. |
| **SYS-FR-003** | MVP | The system shall extract destination, travel dates/duration, budget, traveler count, and preferences from natural-language voice transcripts and prompt the user for any missing required fields. |
| **SYS-FR-004** | MVP | The system shall execute `get_weather(destination, date)` via Open-Meteo and return temperature min/max, precipitation probability, and weather condition summary. |
| **SYS-FR-005** | MVP | If the requested travel date exceeds Open-Meteo's 16-day forecast window, `get_weather` shall return an explicit `out_of_range` status rather than fabricating forecast data. |
| **SYS-FR-006** | MVP | The system shall execute `search_attractions(destination, preferences)` via Geoapify Places API and return up to 10 relevant POIs with name, category, and address. |
| **SYS-FR-007** | MVP | The system shall execute `estimate_trip_budget(destination, duration, travellers)` and return itemized cost estimates (accommodation, food, transport, activities, total) in the target currency. |
| **SYS-FR-008** | MVP | The system shall execute `generate_itinerary(destination, dates, budget, preferences)` combining weather, attractions, and budget into a structured day-by-day plan. |
| **SYS-FR-009** | MVP | The system shall execute at least two coordinated tool calls within a single user planning turn when destination, dates, and preferences are provided. |
| **SYS-FR-010** | MVP | The system shall enforce a Human-in-the-Loop (HITL) approval gate before executing `save_trip` or `update_itinerary` persistence in SQLite. |
| **SYS-FR-011** | MVP | The system shall never state or imply that a real-world flight, hotel, or ticket booking has been completed. |
| **SYS-FR-012** | MVP | Upon explicit user confirmation (via voice or UI `POST /api/approve`), the system shall persist the trip in the SQLite `trips` table and return a unique `trip_id`. |
| **SYS-FR-013** | MVP | The system shall support retrieving previously saved trips via `GET /api/trips` and `GET /api/trips/<id>` and via conversational voice queries. |
| **SYS-FR-014** | MVP | The system shall support modifying an active or saved itinerary via `update_itinerary(trip_id, changes)` based on conversational instructions and confirming the update. |
| **SYS-FR-015** | MVP | The browser UI shall poll `GET /api/session/state` and display live tool-execution badges, active itinerary cards, and pending approval prompts. |
| **SYS-FR-016** | Secondary | The UI shall allow selecting among supported Murf Falcon voice IDs prior to starting a session. |
| **SYS-FR-017** | Secondary | The UI shall allow exporting a saved trip as a downloadable JSON or Markdown file. |

---

## 13. Non-Functional Requirements

| Req ID | Category | Requirement Statement |
| :--- | :--- | :--- |
| **SYS-NFR-001** | Latency | Non-tool conversational turns shall begin streaming Murf Falcon TTS audio within 2.5 seconds of end-of-speech under normal network conditions. |
| **SYS-NFR-002** | Latency | Multi-tool planning turns shall complete tool execution and begin TTS playback within 6.0 seconds, or emit an interim status/filler phrase. |
| **SYS-NFR-003** | Usability | Voice responses generated by Gemini shall be concise (<= 4 sentences per turn) and free of raw markdown syntax (`**`, `|`, `#`). |
| **SYS-NFR-004** | Maintainability | Backend code shall be organized into modular files (`app.py`, `services/`, `tools/`, `db/`) with < 800 lines of Python total for MVP. |
| **SYS-NFR-005** | Portability | Application configuration shall be driven entirely by `.env` variables loaded via `python-dotenv`. |

---

## 14. Data Requirements

- **SYS-DAT-001:** All saved trips shall be stored in SQLite (`voicetrip.db`) with `id`, `destination`, `start_date`, `duration_days`, `travellers`, `budget_amount`, `itinerary_json`, `status`, and timestamps.
- **SYS-DAT-002:** Every tool invocation shall be logged to `tool_logs` with `tool_name`, `arguments_json`, `status`, and `latency_ms`.
- **SYS-DAT-003:** Active session state (`active_itinerary_json`, `pending_approval_json`) shall be persisted in `session_state` keyed by `channel_name`.

---

## 15. Security Requirements

- **SYS-SEC-001:** API keys (`AGORA_CUSTOMER_SECRET`, `MURF_API_KEY`, `GEMINI_API_KEY`, `GEOAPIFY_API_KEY`) shall never be sent to or stored in browser JavaScript.
- **SYS-SEC-002:** `POST /api/llm/chat/completions` shall validate the `Authorization: Bearer <CUSTOM_LLM_SECRET>` header and reject unauthorized callers with HTTP `401`.
- **SYS-SEC-003:** All SQLite queries shall use parameterized bindings to prevent SQL injection.
- **SYS-SEC-004:** `save_trip` and `update_itinerary` shall reject database writes if `user_confirmed` is not explicitly `True`.

---

## 16. Reliability Requirements

- **SYS-REL-001:** An external API failure (Open-Meteo or Geoapify HTTP error/timeout) shall not terminate the Flask process or the Agora RTC session.
- **SYS-REL-002:** Agora agent sessions shall configure `idle_timeout: 180` seconds to prevent orphaned cloud agent instances.

---

## 17. Error Handling Requirements

- **SYS-ERR-001:** All external HTTP requests shall enforce a maximum timeout of 5 seconds.
- **SYS-ERR-002:** When `get_weather` or `search_attractions` fails, the tool shall return a structured JSON error object (`{"status": "ERROR", "reason": "..."}`) so Gemini informs the user and offers a fallback.
- **SYS-ERR-003:** If Gemini fails or times out, `/api/llm/chat/completions` shall stream a graceful spoken apology SSE chunk followed by `data: [DONE]`.
- **SYS-ERR-004:** If `update_itinerary` is called with a non-existent `trip_id`, it shall return `{"status": "NOT_FOUND"}` and ask the user to verify the trip.

---

## 18. Acceptance Criteria

The software satisfies this SRD when:
1. All `MVP` requirements (`SYS-FR-001` through `SYS-FR-015`, `SYS-SEC-001` through `SYS-SEC-004`, `SYS-ERR-001` through `SYS-ERR-004`) pass their corresponding functional test cases (`TC-001` through `TC-014` in `04_FRD_VoiceTrip_AI.md`).
2. `tool_logs` proves ≥ 2 coordinated tool calls in a single planning workflow.
3. No unapproved writes occur in `trips` and no fake booking claims appear in agent responses.

---

## 19. Traceability Matrix (PRD → SRD → FRD → TRD → Test Case)

| PRD Feature | SRD Requirement(s) | FRD Feature | TRD Component | Test Case(s) |
| :--- | :--- | :--- | :--- | :--- |
| PRD-F01 Voice Session | SYS-FR-001, SYS-FR-002, SYS-API-001, SYS-API-002 | FRD-FEAT-001 | `agora_service.py`, `app.js` | TC-001, TC-002 |
| PRD-F02 Preference Extraction | SYS-FR-003 | FRD-FEAT-002 | `agent_service.py` | TC-003 |
| PRD-F03 Weather Intelligence | SYS-FR-004, SYS-FR-005, SYS-API-005 | FRD-FEAT-003 | `travel_tools.py` (`get_weather`) | TC-004, TC-005 |
| PRD-F04 Attraction Search | SYS-FR-006, SYS-API-006 | FRD-FEAT-004 | `travel_tools.py` (`search_attractions`) | TC-006 |
| PRD-F05 Budget Estimation | SYS-FR-007 | FRD-FEAT-005 | `travel_tools.py` (`estimate_trip_budget`) | TC-007 |
| PRD-F06 Itinerary Generation | SYS-FR-008, SYS-FR-009 | FRD-FEAT-006 | `travel_tools.py` (`generate_itinerary`) | TC-008 |
| PRD-F07 HITL Approval | SYS-FR-010, SYS-FR-011, SYS-SEC-004 | FRD-FEAT-007 | `travel_tools.py`, `/api/approve` | TC-009, TC-010 |
| PRD-F08 Trip Persistence | SYS-FR-012, SYS-FR-013, SYS-DAT-001 | FRD-FEAT-008 | `database.py`, `/api/trips` | TC-011 |
| PRD-F09 Itinerary Update | SYS-FR-014, SYS-ERR-004 | FRD-FEAT-009 | `travel_tools.py` (`update_itinerary`) | TC-012 |
| PRD-F10 Error Handling | SYS-REL-001, SYS-ERR-001..003 | FRD-FEAT-010 | `travel_tools.py`, `agent_service.py` | TC-013 |
| PRD-F11 Live Transcript & UI | SYS-FR-015 | FRD-FEAT-011 | `index.html`, `app.js`, `/api/session/state` | TC-014 |
