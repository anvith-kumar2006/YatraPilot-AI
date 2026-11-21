# YatraPilot AI - Complete Hackathon Build

> AI-powered travel planning assistant with conversational interface

## 🎉 All Phases Complete

✅ **Phase 1:** Backend security & API endpoints  
✅ **Phase 2:** AI intelligence & voice integration  
✅ **Phase 3:** Frontend web application

---

## 🚀 Quick Start

```bash
# 1. Start the server
python app.py

# 2. Open your browser
http://localhost:5000/

# 3. Start planning your trip!
```

---

## ✨ Features

### What's Fully Functional

- ✅ **AI Travel Chat** - Real-time conversation with Gemini AI
- ✅ **Weather Forecasts** - Powered by Open-Meteo API
- ✅ **Attraction Search** - Powered by Geoapify Places
- ✅ **Budget Estimates** - AI-generated trip budgets
- ✅ **Itinerary Generation** - Day-by-day travel plans
- ✅ **Database Storage** - Neon PostgreSQL for trip data
- ✅ **Responsive Design** - Works on mobile and desktop
- ✅ **15+ API Endpoints** - Complete REST API

### Demo Limitations

- ⚠️ **Voice Integration** - Mock RTC tokens (endpoints exist, needs agora-token-builder for production)
- ℹ️ **Authentication** - Not implemented (as per requirements)

---

## 🏗️ Architecture

```
Frontend (HTML/CSS/JS)
    ↓
Flask Backend (Python)
    ├── Gemini AI (gemini-2.5-flash)
    ├── Weather API (Open-Meteo)
    ├── Places API (Geoapify)
    ├── Database (Neon PostgreSQL)
    └── Agora Voice (configured, mock tokens)
```

---

## 📁 Project Structure

```
YatraPilot-AI/
├── app.py                  # Flask backend (15+ endpoints)
├── config.py               # Configuration
├── templates/
│   └── index.html          # Frontend application
├── static/
│   ├── css/style.css       # Styling
│   └── js/app.js           # Frontend logic
├── integrations/
│   ├── gemini.py           # Gemini AI (REST API)
│   ├── agora.py            # Voice integration
│   └── travel_apis.py      # Weather & places
├── tools/
│   └── travel_tools.py     # 6 AI tools
└── database/
    └── db.py               # PostgreSQL integration
```

---

## 🔑 Environment Setup

Required in `.env`:

```env
GEMINI_API_KEY=your_key_here
GEOAPIFY_API_KEY=your_key_here
DATABASE_URL=postgresql://...
FLASK_SECRET_KEY=your_secret_here
```

Optional (for voice):
```env
AGORA_APP_ID=...
AGORA_APP_CERTIFICATE=...
AGORA_CUSTOMER_ID=...
AGORA_CUSTOMER_SECRET=...
MURF_API_KEY=...
```

---

## 🎯 API Endpoints

### Frontend
- `GET  /` - Main application

### Chat & AI
- `POST /api/chat` - AI conversation endpoint

### Travel Data
- `GET  /api/weather` - Weather forecasts
- `GET  /api/places/search` - Search attractions
- `GET  /api/places/nearby` - Nearby places

### Voice (Mock)
- `POST /api/session/start` - Start voice session
- `POST /api/session/stop` - Stop voice session

### Trips
- `GET  /api/trips` - List all trips
- `GET  /api/trips/<id>` - Get trip details

### Health
- `GET  /health` - Server health check

---

## 🧪 Testing

```bash
# Test all components
python phase2_complete.py

# Expected output:
# [OK] Gemini AI working
# [OK] Travel Tools working
# [OK] Agora Voice working
# [OK] Flask App healthy
```

---

## 📱 Usage Example

1. **Open the app:** http://localhost:5000/
2. **Ask a question:** "I want to visit Jaipur for 3 days with my family"
3. **Get AI response:** Weather, attractions, budget, itinerary
4. **Continue chatting:** Refine your plans, ask followup questions

---

## 🚀 Deployment

### Option 1: Vercel
```bash
npm i -g vercel
vercel --prod
```

### Option 2: Railway
1. Connect GitHub repo
2. Add environment variables
3. Deploy automatically

### Option 3: Render
1. Connect GitHub repo
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `python app.py`
4. Add environment variables

**Database:** Already using Neon (cloud PostgreSQL) - ready for production!

---

## 📊 What Was Built

### Phase 1: Security & Backend
- SQL injection prevention
- CORS configuration
- Input validation
- New REST endpoints

### Phase 2: AI Intelligence
- Gemini AI integration (gemini-2.5-flash)
- 6 travel tools (weather, attractions, budget, itinerary, save, update)
- Agora voice configuration
- 15+ API endpoints

### Phase 3: Frontend
- Modern web interface (HTML/CSS/JS)
- Real-time AI chat
- Responsive design
- Dynamic content display

---

## ⚠️ Important Notes

### What's Real
✅ Gemini AI conversations  
✅ Weather data from Open-Meteo  
✅ Attraction data from Geoapify  
✅ Database storage in Neon PostgreSQL  
✅ All backend processing  

### What's Mock/Demo
⚠️ Agora RTC tokens (endpoints exist, tokens are SHA256 hashes)  
⚠️ Voice interaction (needs agora-token-builder for production)  

### What's Not Included
❌ User authentication (as requested)  
❌ Login/registration (as requested)  
❌ Production deployment (local dev only)  

---

## 📖 Documentation

- **PHASE1_REMEDIATION_FINAL_REPORT.txt** - Security fixes & backend
- **PHASE2_COMPLETE.txt** - AI & voice integration
- **PHASE3_COMPLETE.txt** - Frontend & deployment guide

---

## 🎓 For Hackathon Judges

### What to Demonstrate

1. **Open the web interface** - Clean, professional design
2. **Chat with the AI** - Ask about travel destinations
3. **Show real data** - Weather forecasts, attractions
4. **Explain architecture** - Gemini + APIs + Database
5. **Note limitations** - Voice is configured but uses mock tokens

### Tech Stack

- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **Backend:** Flask (Python)
- **AI:** Google Gemini 2.5 Flash
- **Database:** Neon PostgreSQL (serverless)
- **APIs:** Open-Meteo (weather), Geoapify (places)
- **Voice:** Agora (configured, mock tokens)

---

## 🛠️ Troubleshooting

**Flask won't start:**
```bash
.\venv\Scripts\python.exe app.py
```

**Port 5000 in use:**
```bash
# Edit app.py, change port at bottom:
app.run(host="0.0.0.0", port=5001)
```

**Database connection error:**
- Check DATABASE_URL in .env
- Verify Neon database is active

**Gemini API error:**
- Check GEMINI_API_KEY in .env
- Verify API key is active

---

## 📝 License

Built for hackathon demonstration. See individual API providers for their terms.

---

## 🙏 Credits

- Google Gemini API
- Open-Meteo Weather API
- Geoapify Places API
- Neon PostgreSQL
- Agora Voice Platform
- Murf AI TTS

---

**Status:** ✅ Ready for hackathon demonstration!

**Last Updated:** Phase 3 Complete - All features implemented and tested
