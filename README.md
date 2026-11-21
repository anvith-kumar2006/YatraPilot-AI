# VoiceTrip AI (YatraPilot AI) — Documentation Suite

**Hackathon:** Build with Agora  
**Track:** AI Agents That Get Things Done  
**Problem Statement:** PS51 – AI Travel Concierge  
**Tagline:** *Your Journey. Our Intelligence.*  

---

## Document Overview

This repository contains the complete, consistent requirements and architecture baseline for **VoiceTrip AI (YatraPilot AI)**, designed to be built as a working hackathon MVP in **~8 hours**.

| File | Document | Purpose |
| :--- | :--- | :--- |
| `01_PRD_VoiceTrip_AI.md` | **Product Requirements Document (PRD)** | Defines **what** we are building and **why**: vision, personas, MVP vs. secondary/future scope, 5-stage hackathon journey, and risks. |
| `02_TRD_VoiceTrip_AI.md` | **Technical Requirements Document (TRD)** | Defines **how** it is built: verified Agora + Murf Falcon TTS + Gemini Custom LLM SSE architecture, SQLite schema, REST/SSE contracts, and 8-hour build plan. |
| `03_SRD_VoiceTrip_AI.md` | **Software Requirements Specification (SRD/SRS)** | Formal IEEE-style testable requirements (`SYS-FR-*`, `SYS-NFR-*`, `SYS-SEC-*`, `SYS-API-*`, `SYS-ERR-*`) and end-to-end traceability matrix. |
| `04_FRD_VoiceTrip_AI.md` | **Functional Requirements Document (FRD)** | Implementation-ready feature specs (`FRD-FEAT-001`..`011`), Mermaid sequence diagrams, UI layout, edge cases, and acceptance tests (`TC-001`..`014`). |

---

## Recommended Implementation Order (8-Hour Hackathon)

1. **Setup & Database (Hour 1):** Create `.env` from `02_TRD_VoiceTrip_AI.md` Section 18, initialize `voicetrip.db` using the SQLite schema in Section 15, and verify Flask `/health`.
2. **Python Tools & External APIs (Hours 1–2.5):** Implement and unit-test the 6 tools in `tools/travel_tools.py` (`get_weather` via Open-Meteo, `search_attractions` via Geoapify, `estimate_trip_budget`, `generate_itinerary`, `save_trip`, `update_itinerary`) with HITL `user_confirmed` enforcement.
3. **Gemini Custom LLM SSE Bridge (Hours 2.5–4.5):** Implement `/api/llm/chat/completions` (`02_TRD_VoiceTrip_AI.md` Section 17) using `google-genai`, expose via `ngrok` HTTPS tunnel, and test with `curl`.
4. **Agora + Murf Falcon Voice Session (Hours 4.5–6):** Implement `/api/session/start` and `/api/session/stop` calling Agora `/join` with `tts.vendor = "murf"` (`model = "FALCON"`) and wire the HTML5/JS Agora RTC Web SDK client.
5. **Companion UI & Demo Rehearsal (Hours 6–8):** Add live polling (`/api/session/state`), itinerary cards, HITL Approval banner (`/api/approve`), and rehearse the 5-stage demo + error-handling cases (`TC-001`..`TC-014`).
