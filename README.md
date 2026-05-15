# jarvis_AI

An AI assistant for Karthik with a Jarvis-style frontend, voice wake phrase, spoken replies, app launching, and optional Gemini-powered answers.

## Features

- Click "Enable Voice", allow microphone access, then say "Hey Jarvis" to wake the assistant in Chrome or Edge.
- Ask questions and hear spoken replies.
- Open Windows apps by voice, for example "Hey Jarvis open notepad".
- Use `GEMINI_API_KEY` for real AI answers. Without it, the app still runs and explains how to enable AI.

## Run

```powershell
cd C:\Users\karthik\jarvis_AI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in Chrome or Edge.

## Optional Gemini setup

Create `C:\Users\karthik\jarvis_AI\.env` and add:

```env
GEMINI_API_KEY=your_api_key_here
JARVIS_MODEL=gemini-flash-latest
JARVIS_SEARCH_MODEL=gemini-2.5-flash
```

Then run:

```powershell
python app.py
```

## Voice examples

- "Hey Jarvis open chrome"
- "Hey Jarvis open calculator"
- "Hey Jarvis what is artificial intelligence?"

## Model upgrade

Jarvis uses `gemini-flash-latest` by default for quick voice replies. For current facts, it uses Google Search grounding through `JARVIS_SEARCH_MODEL=gemini-2.5-flash`.

Good options:

- `gemini-3.1-pro-preview` for best reasoning if your quota/billing allows it.
- `gemini-flash-latest` for fastest voice replies.
- `gemini-3-flash-preview` for newer, faster replies.
- `gemini-pro-latest` to follow Google's current Pro alias.

Use `JARVIS_SEARCH_MODEL=gemini-2.5-flash` for current/news questions because Google's Search grounding currently supports the stable Gemini 2.5 models.
