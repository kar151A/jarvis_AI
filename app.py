from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - handled at runtime for friendly setup.
    OpenAI = None


APP_ALIASES = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "camera": "microsoft.windows.camera:",
    "settings": "ms-settings:",
    "paint": "mspaint",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "cmd": "cmd",
    "command prompt": "cmd",
    "powershell": "powershell",
    "vscode": "code",
    "visual studio code": "code",
}


@dataclass(frozen=True)
class AssistantConfig:
    model: str = os.getenv("JARVIS_MODEL", "gpt-4o-mini")
    system_prompt: str = (
        "You are Jarvis, Karthik's concise AI assistant. "
        "Answer clearly, helpfully, and speak like a capable desktop companion."
    )


def create_app() -> Flask:
    app = Flask(__name__)
    config = AssistantConfig()

    @app.get("/")
    def home() -> str:
        return render_template("index.html")

    @app.post("/api/ask")
    def ask() -> tuple[Any, int] | Any:
        payload = request.get_json(silent=True) or {}
        message = str(payload.get("message", "")).strip()
        if not message:
            return jsonify({"error": "Ask me something first."}), 400

        command = parse_open_command(message)
        if command:
            result = launch_app(command)
            reply = (
                f"Opening {result['label']}."
                if result["ok"]
                else f"I could not open {result['label']}. {result['error']}"
            )
            return jsonify({"reply": reply, "action": result})

        reply = answer_question(message, config)
        return jsonify({"reply": reply})

    @app.post("/api/open-app")
    def open_app() -> tuple[Any, int] | Any:
        payload = request.get_json(silent=True) or {}
        app_name = str(payload.get("app", "")).strip()
        if not app_name:
            return jsonify({"error": "Tell me which app to open."}), 400
        return jsonify(launch_app(app_name))

    return app


def parse_open_command(message: str) -> str | None:
    text = normalize(message)
    patterns = [
        r"^(open|launch|start)\s+(.+)$",
        r"^(can you|please)\s+(open|launch|start)\s+(.+)$",
        r"^(hey\s+)?jarvis\s+(open|launch|start)\s+(.+)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, text)
        if match:
            return match.group(match.lastindex or 1).strip()
    return None


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip(" .!?")


def resolve_app(app_name: str) -> tuple[str, str]:
    label = normalize(app_name)
    command = APP_ALIASES.get(label, app_name.strip())
    return label or app_name, command


def launch_app(app_name: str) -> dict[str, Any]:
    label, command = resolve_app(app_name)
    try:
        if command.endswith(":"):
            subprocess.Popen(["cmd", "/c", "start", "", command], shell=False)
        else:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", "Start-Process", command],
                shell=False,
            )
        return {"ok": True, "label": label, "command": command}
    except Exception as exc:  # pragma: no cover - depends on local Windows apps.
        return {"ok": False, "label": label, "command": command, "error": str(exc)}


def answer_question(message: str, config: AssistantConfig) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return (
            "I heard you. To answer with full AI power, add your OPENAI_API_KEY "
            "to a .env or your Windows environment, then restart me. "
            f"You asked: {message}"
        )

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=config.model,
        messages=[
            {"role": "system", "content": config.system_prompt},
            {"role": "user", "content": message},
        ],
        temperature=0.5,
    )
    return response.choices[0].message.content or "I do not have an answer yet."


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    create_app().run(host="127.0.0.1", port=port, debug=True)
