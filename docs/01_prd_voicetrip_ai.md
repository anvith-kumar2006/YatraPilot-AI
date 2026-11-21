# Product Requirements Document (PRD)
## VoiceTrip AI (YatraPilot AI) — Intelligent Voice-Powered Travel Concierge

**Document ID:** PRD-VOICETRIP-001  
**Version:** 1.0  
**Hackathon:** Build with Agora  
**Track:** AI Agents That Get Things Done  
**Problem Statement:** PS51 – AI Travel Concierge  
**Tagline:** *Your Journey. Our Intelligence.*  
**Target Build Window:** ~8 Hours (Hackathon MVP)  

---

## 1. Document Overview

This Product Requirements Document (PRD) defines the product vision, user needs, scope, core capabilities, user journeys, and hackathon acceptance criteria for **VoiceTrip AI** (also branded as **YatraPilot AI**), a real-time conversational AI travel concierge built for the **Build with Agora** hackathon under Track **AI Agents That Get Things Done (PS51)**.

This document establishes **what** the product does and **why** it matters, serving as the single source of product truth for the accompanying Technical Requirements Document (`02_TRD_VoiceTrip_AI.md`), Software Requirements Specification (`03_SRD_VoiceTrip_AI.md`), and Functional Requirements Document (`04_FRD_VoiceTrip_AI.md`).

---

## 2. Product Vision

VoiceTrip AI transforms trip planning from a fragmented, multi-tab browser chore into a natural, hands-free voice conversation with an intelligent agent that listens, reasons, checks live destination data, builds structured itineraries, adapts to changing preferences, and executes multi-step travel tasks with explicit human-in-the-loop approval.

Instead of acting as a passive text chatbot that merely lists generic suggestions, VoiceTrip AI operates as an **agentic travel concierge**: it gathers trip constraints through real-time voice dialogue, invokes external weather and attraction APIs, calculates realistic budget breakdowns, persists itineraries, and requests explicit user confirmation before committing critical actions.

---

## 3. Problem Statement

Develop an intelligent AI travel concierge that interacts with users through real-time voice conversations, understands travel preferences, researches live destination options, compares itineraries, coordinates external services, manages travel changes, and provides follow-up assistance. The agent must go beyond answering questions—it must reason, call external tools and APIs, execute meaningful multi-step tasks, handle unavailable options or API failures gracefully, and obtain human approval before critical actions.

---

## 4. Problem Background

Planning even a short 2–5 day trip typically requires a traveler to juggle 6 to 10 disconnected tools: weather forecasts, attraction directories, budget spreadsheets, note-taking apps, and itinerary docs. Existing travel chatbots suffer from three major limitations:

1. **Text-Only Friction:** Typing complex, evolving constraints (*"Actually, make it 3 days instead of 4, keep it under ₹25,000, and skip outdoor spots if it's going to rain"*) is slow and unnatural compared to speaking.
2. **No Real-Time Grounding:** Standard LLMs hallucinate weather conditions, invent closed or non-existent attractions, and cannot persist or update a user's trip state across turns.
3. **Lack of Agency & Safety Guardrails:** Chatbots either do nothing beyond generating text or, in poorly designed prototypes, claim to have "booked" or "saved" trips without calling real APIs or asking the user for confirmation.

---

## 5. Proposed Solution

VoiceTrip AI combines **Agora Conversational AI**, **Murf AI Falcon TTS**, and **Google Gemini** inside a lightweight **Python Flask + SQLite** web application:

- **Real-Time Voice Layer (Agora Conversational AI + Agora RTC Web SDK):** Streams bidirectional low-latency voice audio between the user's browser and the AI agent runtime, handling turn-taking, voice activity detection (VAD), and barge-in interruptions.
- **Ultra-Fast Voice Output (Murf AI Falcon TTS):** Synthesizes natural, expressive spoken responses via Murf's Falcon streaming WebSocket integration inside Agora Conversational AI Engine.
- **Agentic Reasoning & Tool Execution (Gemini API + Python Tool Calling):** Interprets natural-language travel requests, breaks them into tool calls (`get_weather`, `search_attractions`, `estimate_trip_budget`, `generate_itinerary`, `save_trip`, `update_itinerary`), handles API errors/fallbacks, and enforces human-in-the-loop (HITL) approval before saving or modifying critical trip records.
- **Live Visual Companion UI (HTML5 / CSS3 / JavaScript):** Displays real-time conversation transcripts, live tool-execution status, weather & attraction cards, day-wise itinerary tables, cost breakdowns, and interactive approval prompts alongside the voice call.

---

## 6. Product Objectives

| Objective ID | Objective | Priority | Measurable Outcome |
| :--- | :--- | :--- | :--- |
| **OBJ-01** | Deliver real-time, low-latency voice interaction for travel planning | MVP – Must Have | User can start/end a voice session in < 3 seconds and converse naturally via Agora + Murf Falcon TTS |
| **OBJ-02** | Execute coordinated multi-step agentic tool calls | MVP – Must Have | Agent executes at least 2 coordinated external/backend tool calls (e.g., Weather + Attractions + Budget) in a single planning workflow |
| **OBJ-03** | Enforce human-in-the-loop (HITL) approval for critical actions | MVP – Must Have | Agent explicitly asks for and receives user confirmation before saving/committing an itinerary or simulated booking action |
| **OBJ-04** | Support dynamic itinerary updates & follow-up retrieval | MVP – Must Have | User can modify an itinerary via voice (e.g., change dates, budget, or preferences) and retrieve saved trips |
| **OBJ-05** | Handle failures, unavailable data, and changing constraints gracefully | MVP – Must Have | Agent never fabricates API results; communicates limitations/errors clearly and offers alternatives |
| **OBJ-06** | Complete full hackathon MVP within ~8 hours | MVP – Must Have | Single-repo Flask + SQLite + HTML/JS architecture with zero unnecessary microservices |

---

## 7. Target Users and Personas

### Persona 1: Aarav — The Busy Weekend Traveler (Primary)
- **Profile:** 27-year-old software engineer in Bengaluru planning a 3-day weekend getaway to Coorg or Goa.
- **Goal:** Wants a quick, weather-aware itinerary and budget estimate by speaking for 2 minutes instead of spending an hour searching blogs.
- **Behavior:** Changes mind mid-conversation (*"Wait, what if it rains on Saturday? Swap the trek for a coffee estate or indoor museum"*).

### Persona 2: Priya — The Group Trip Coordinator (Secondary)
- **Profile:** 31-year-old product designer organizing a 4-person trip to Jaipur with a strict per-person budget.
- **Goal:** Needs cost breakdowns scaled by number of travelers, saved trip plans she can revisit, and clear confirmation before locking in the final itinerary.

### Persona 3: Hackathon Judge / Evaluator (Demo Persona)
- **Profile:** Technical judge evaluating Build with Agora PS51 submissions.
- **Goal:** Needs to observe the complete 5-stage agentic journey (**Initiate → Understand/Plan → Execute → Confirm → Follow-up**) with visible tool calls, real Agora + Murf voice output, error handling, and zero fake booking claims.

---

## 8. User Pain Points

1. **Fragmented Planning:** Switching between weather apps, Google Maps/places lists, and calculators breaks flow.
2. **Rigid Forms:** Traditional travel sites force users to fill 10+ dropdowns before showing anything useful.
3. **Weather Surprises:** Static itineraries recommend outdoor hikes during heavy rain forecasts.
4. **Unsafe AI Automation:** Users distrust AI agents that silently overwrite plans or claim to complete bookings without asking.

---

## 9. Core Value Proposition

> **"Speak your trip into existence—grounded in live weather and real places, tailored to your budget, and never committed without your say-so."**

VoiceTrip AI bridges natural human speech with deterministic backend tools so users get **conversational speed** without sacrificing **factual grounding** or **user control**.

---

## 10. Product Scope

Requirements are strictly partitioned into three tiers to guarantee an achievable **8-hour hackathon MVP**:

- **MVP – Must Have:** Essential for the Build with Agora demonstration and PS51 evaluation.
- **Secondary – Should Have:** Valuable polish if time remains in the 8-hour window.
- **Future Scope – Could Have:** Post-hackathon production capabilities.

---

## 11. In-Scope Features

### 11.1 MVP – Must Have

| Feature ID | Feature Name | Description |
| :--- | :--- | :--- |
| **PRD-F01** | Real-Time Voice Session Control | Join and leave an Agora RTC voice channel from the browser with microphone capture and Murf Falcon TTS audio playback. |
| **PRD-F02** | Conversational Preference Extraction | Understand natural-language requests for destination, travel dates/duration, budget, number of travelers, and interests; ask follow-up questions for missing inputs. |
| **PRD-F03** | Live Weather Intelligence (`get_weather`) | Fetch real-time weather forecasts via Open-Meteo API and adapt recommendations (e.g., indoor vs. outdoor) based on conditions. |
| **PRD-F04** | Attraction Discovery (`search_attractions`) | Search real points of interest via Geoapify Places API filtered by destination and user preferences. |
| **PRD-F05** | Trip Budget Estimation (`estimate_trip_budget`) | Compute structured cost estimates (accommodation, food, local transport, activities) scaled by duration and traveler count. |
| **PRD-F06** | Day-Wise Itinerary Generation (`generate_itinerary`) | Synthesize weather, attractions, and budget into a structured day-by-day schedule displayed in both voice summary and UI cards. |
| **PRD-F07** | Human-in-the-Loop (HITL) Approval | Pause before executing critical state-changing actions (saving/finalizing a trip or simulated reservation hold) and require explicit verbal or UI confirmation. |
| **PRD-F08** | Trip Persistence & Retrieval (`save_trip`, `get_saved_trips`) | Save approved trips to SQLite and retrieve previously saved trips by ID or destination. |
| **PRD-F09** | Conversational Itinerary Modification (`update_itinerary`) | Update an existing or active itinerary when the user changes dates, budget, traveler count, or preferences mid-session or in follow-up. |
| **PRD-F10** | Graceful Error & Limitation Handling | Detect API timeouts, out-of-range forecast dates (>16 days), or empty attraction results; inform the user honestly without fabricating data. |
| **PRD-F11** | Live Transcript & Action Feed UI | Display real-time user/agent transcripts, active tool-call badges, itinerary cards, and an approval confirmation banner. |

### 11.2 Secondary – Should Have
- **PRD-F12:** Voice selection toggle (switch between Murf Falcon voice profiles/locales in UI).
- **PRD-F13:** Export saved itinerary as a downloadable JSON or Markdown summary.
- **PRD-F14:** Multi-option comparison mode (e.g., "Budget vs. Comfort" itinerary variants).

---

## 12. Out-of-Scope Features (Future Scope – Could Have)

- Real flight, hotel, or payment gateway integrations (Stripe/Razorpay/Amadeus production bookings).
- User authentication, OAuth, or multi-tenant account management.
- Microservices architecture, Kubernetes, or multi-agent swarm orchestration.
- Real-time collaborative multi-user voice rooms.
- Native iOS/Android mobile apps (Web browser HTML5/JS only for MVP).

---

## 13. User Journeys

### Mandatory 5-Stage Hackathon Demonstration Journey

1. **Initiate:** User clicks **"Start Voice Session"** in the browser, joins the Agora channel, and speaks: *"Hi, I want to plan a 3-day trip to Coorg for 2 people starting this Friday, with a budget of ₹20,000. We love waterfalls and coffee."*
2. **Understand / Plan:** Gemini extracts `destination="Coorg"`, `duration=3`, `travellers=2`, `budget=20000`, `preferences=["waterfalls", "coffee"]` and determines it needs live weather, attraction options, and a budget check before building the plan.
3. **Execute:** Agent invokes `get_weather("Coorg", "2026-11-20")` and `search_attractions("Coorg", ["waterfalls", "coffee"])` plus `estimate_trip_budget("Coorg", 3, 2)`. The UI shows live tool-execution indicators while Murf Falcon plays a natural waiting cue if needed.
4. **Confirm:** Agent speaks the synthesized 3-day itinerary and weather warning (*"Light rain is expected Saturday afternoon, so I scheduled Abbey Falls for Friday morning and a covered coffee plantation tour on Saturday"*). Agent asks: *"Would you like me to save this itinerary as Trip #1 and lock in your plan?"* User confirms via voice (*"Yes, save it"*) or clicks **Approve & Save** in the UI.
5. **Follow-up:** Agent calls `save_trip(...)`, confirms the saved Trip ID, and supports follow-up changes (*"Actually, add one more day and include a heritage fort"* → calls `update_itinerary(...)` → confirms update and provides a final summary).

### Example Conversation 2: Handling Changing Preferences & API Limitations
> **User:** "Plan a 4-day trip to Manali next month on December 28th."  
> **Agent (Voice via Murf Falcon):** "I'd love to help plan Manali for December 28th! Just a heads-up: live weather forecasts are only available up to 16 days ahead, so I can't pull exact December 28th forecasts yet. Would you like me to plan using typical winter indoor and scenic spots for now, and you can refresh the forecast closer to your trip?"  
> **User:** "Yes, go ahead, and keep it budget-friendly for 3 friends."  
> **Agent:** *(Calls `search_attractions` and `estimate_trip_budget`, then `generate_itinerary`)* "I've put together a 4-day budget itinerary for 3 travelers in Manali around ₹24,000 total... Shall I save this trip to your planner?"

---

## 14. Functional Capabilities Overview

- **Voice Conversation:** Start/stop Agora session, continuous VAD, barge-in support, live transcript display.
- **Agentic Tool Calling:** 6 Python tools orchestrated by Gemini function calling with structured JSON schemas.
- **Itinerary Management:** Day-wise breakdown, estimated cost per category, destination weather summary, persistent storage in SQLite.
- **Human-in-the-Loop Safety:** Explicit confirmation gate before `save_trip` or `update_itinerary` persistence, plus strict prohibition on claiming real bookings occurred.

---

## 15. Non-Functional Expectations

- **Latency:** Voice turn-around (end-of-speech to first audio byte from Murf Falcon) target < 2.0 seconds for non-tool turns; < 4.5 seconds for multi-tool turns with interim filler/status feedback.
- **Reliability:** Tool failures (HTTP 4xx/5xx/timeout) must not crash the Flask server or Agora voice session; agent must recover and explain the issue verbally.
- **Simplicity:** Achievable by 1–2 developers in ~8 hours using Python Flask, SQLite, HTML/CSS/JS, and official Agora/Murf/Gemini SDKs/APIs.

---

## 16. Success Metrics and KPIs

| Metric | Target | Measurement Method |
| :--- | :--- | :--- |
| End-to-End Voice Demo Completion | 100% of 5 stages | Live demo walkthrough |
| Coordinated Tool Calls per Planning Flow | ≥ 2 external/backend tools | Backend structured logs |
| Hallucinated Booking Claims | 0 occurrences | Transcript & prompt audit |
| Tool Failure Recovery Rate | 100% graceful fallback | Simulated API failure test |
| Setup & Cold Start Time | < 5 minutes | Local runbook verification |

---

## 17. Hackathon MVP Acceptance Criteria

1. User can initiate and terminate a live Agora voice session from the web browser and hear responses in a Murf AI Falcon TTS voice.
2. Agent successfully executes at least two coordinated tool calls (e.g., `get_weather` + `search_attractions` + `estimate_trip_budget`) in a single user workflow using real external APIs.
3. Agent generates a day-wise itinerary with estimated costs and displays it in the UI while summarizing it via voice.
4. Agent explicitly asks for human approval before saving/committing the trip and does not claim to have booked real flights/hotels.
5. User can request a mid-session or follow-up modification (`update_itinerary`) and retrieve the saved trip from SQLite.
6. When an external API fails or a date exceeds the 16-day forecast limit, the agent handles it gracefully and informs the user.

---

## 18. Assumptions

- Developers have valid API credentials for **Agora** (App ID, App Certificate, Customer ID, Customer Secret with Conversational AI Engine enabled), **Murf AI** (API Key with Falcon TTS access), **Google Gemini** (AI Studio API Key), and **Geoapify** (free-tier API Key).
- Open-Meteo API remains accessible without an API key for non-commercial hackathon use.
- If running Flask locally during the hackathon, an HTTPS tunnel (e.g., `ngrok` or `cloudflared`) is used so Agora's cloud Conversational AI Engine can reach the Flask Custom LLM endpoint.

---

## 19. Risks and Mitigations

| Risk | Impact | Mitigation |
| :--- | :--- | :--- |
| Agora cloud cannot reach `localhost` Flask endpoint | High | Use `ngrok` / `cloudflared` HTTPS tunnel or deploy to Render/Railway; verify with `/health` endpoint |
| External API rate limit or timeout during live demo | High | Set 5-second HTTP timeouts, cache recent city lookups in SQLite, and implement graceful fallback messages |
| LLM claims a real booking was made | High | Enforce strict system prompt guardrails and explicit `is_simulated: true` / `approval_required` flags in tool responses |
| Latency spikes during multi-tool execution | Medium | Send Agora `custom_metadata` filler phrase (*"Checking live weather and attractions..."*) before executing tools |

---

## 20. Future Enhancements

- Integration with live flight/hotel GDS sandboxes (e.g., Amadeus Self-Service APIs) with OAuth and real reservation holds.
- Multilingual voice switching using Murf Falcon's multilingual capabilities (e.g., English, Hindi, Kannada).
- Calendar export (`.ics`) and shareable trip links.
- Proactive weather-alert notifications for upcoming saved trips.
