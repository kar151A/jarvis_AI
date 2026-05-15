# jarvis_AI

An AI assistant for Karthik with a Jarvis-style frontend, camera preview, voice wake phrase, spoken replies, app launching, and optional OpenAI-powered answers.

## Features

- Say "Hey Jarvis" to wake the assistant in Chrome or Edge. The page tries to start listening automatically; use the button if the browser asks for a manual click.
- Ask questions and hear spoken replies.
- Open Windows apps by voice, for example "Hey Jarvis open notepad".
- Camera preview in the Jarvis HUD, with a button fallback if browser permission blocks auto-start.
- Use `OPENAI_API_KEY` for real AI answers. Without it, the app still runs and explains how to enable AI.

## Run

```powershell
cd C:\Users\karthik\jarvis_AI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in Chrome or Edge.

## Optional AI setup

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
python app.py
```

## Voice examples

- "Hey Jarvis open chrome"
- "Hey Jarvis open calculator"
- "Hey Jarvis what is artificial intelligence?"
