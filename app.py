from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - handled at runtime for friendly setup.
    genai = None
    types = None


APP_ALIASES = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
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
    "whatsapp": "whatsapp",
    "whats app": "whatsapp",
    "whatsapp desktop": "whatsapp",
}

APP_PROTOCOLS = {
    "settings": "ms-settings:",
    "whatsapp": "whatsapp://",
    "telegram": "tg://",
    "spotify": "spotify:",
    "zoom": "zoommtg://",
    "discord": "discord://",
    "mail": "mailto:",
    "email": "mailto:",
    "camera": "microsoft.windows.camera:",
}

CURRENT_INFO_PATTERNS = [
    r"\b(current|currently|latest|today|now|right now|recent|new|news|updated)\b",
    r"\b(price|score|weather|stock|election|result|schedule|deadline)\b",
    r"\b(cm|chief minister|prime minister|president|governor|ceo|mayor)\b",
    r"\b(who is|who's|who won|when is|when did)\b",
    r"\b(2025|2026|2027)\b",
]


@dataclass(frozen=True)
class AssistantConfig:
    model: str = os.getenv("JARVIS_MODEL", "gemini-flash-latest")
    search_model: str = os.getenv("JARVIS_SEARCH_MODEL", "gemini-2.5-flash")
    system_prompt: str = (
        "You are Jarvis, Karthik's concise AI assistant. "
        "Answer clearly, helpfully, and speak like a capable desktop companion. Keep spoken answers short unless the user asks for detail. "
        "For current facts, offices, news, prices, elections, sports, laws, and anything date-sensitive, use current information and mention the date when helpful."
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
    protocol = APP_PROTOCOLS.get(label) or APP_PROTOCOLS.get(command)
    names = sorted({label, command, app_name.strip()}, key=len, reverse=True)
    result = run_windows_launcher(names, protocol)
    return {
        "ok": result["ok"],
        "label": label,
        "command": command,
        "method": result.get("method"),
        "error": result.get("error"),
    }


def run_windows_launcher(names: list[str], protocol: str | None = None) -> dict[str, Any]:
    ps_names = "@(" + ",".join(to_ps_string(name) for name in names if name.strip()) + ")"
    ps_protocol = to_ps_string(protocol) if protocol else "$null"
    script = (
        "$ErrorActionPreference = 'Stop'; "
        f"$names = {ps_names}; "
        f"$protocol = {ps_protocol}; "
        "$commonRoots = @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:LOCALAPPDATA, $env:APPDATA) | Where-Object { $_ }; "
        "function Open-Target($target, $method) { Start-Process $target; [pscustomobject]@{ ok=$true; method=$method; target=$target } | ConvertTo-Json -Compress; exit 0 }; "
        "foreach ($name in $names) { "
        "  $app = Get-StartApps | Where-Object { $_.Name -ieq $name } | Select-Object -First 1; "
        "  if (-not $app) { $app = Get-StartApps | Where-Object { $_.Name -like \"*$name*\" } | Select-Object -First 1 }; "
        "  if ($app) { Open-Target \"shell:AppsFolder\\$($app.AppID)\" 'start-menu' }; "
        "} "
        "foreach ($name in $names) { "
        "  try { $cmd = Get-Command $name -ErrorAction Stop; if ($cmd.Source) { Open-Target $cmd.Source 'path-command' } } catch {} "
        "  try { Start-Process $name -ErrorAction Stop; [pscustomobject]@{ ok=$true; method='start-process'; target=$name } | ConvertTo-Json -Compress; exit 0 } catch {} "
        "} "
        "foreach ($root in $commonRoots) { "
        "  foreach ($name in $names) { "
        "    $matches = Get-ChildItem -Path $root -Recurse -Filter '*.exe' -ErrorAction SilentlyContinue | "
        "      Where-Object { $_.BaseName -ieq $name -or $_.BaseName -like \"*$name*\" } | Select-Object -First 1; "
        "    if ($matches) { Open-Target $matches.FullName 'common-folder' } "
        "  } "
        "} "
        "if ($protocol) { try { Open-Target $protocol 'protocol' } catch {} } "
        "[pscustomobject]@{ ok=$false; error='App not found or Windows refused to launch it.' } | ConvertTo-Json -Compress; exit 2"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    output = completed.stdout.strip()
    if output:
        try:
            import json

            parsed = json.loads(output)
            return parsed if isinstance(parsed, dict) else {"ok": False, "error": output}
        except Exception:
            return {"ok": completed.returncode == 0, "error": output}
    return {"ok": False, "error": completed.stderr.strip() or "No launcher response."}


def to_ps_string(value: str | None) -> str:
    if value is None:
        return "$null"
    return "'" + value.replace("'", "''") + "'"


def answer_question(message: str, config: AssistantConfig) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return (
            "I heard you. To answer with full AI power, add your GEMINI_API_KEY "
            "to a .env or your Windows environment, then restart me. "
            f"You asked: {message}"
        )

    client = genai.Client(api_key=api_key)
    if needs_current_info(message):
        grounded = answer_with_google_search(client, message, config)
        if grounded:
            return grounded

    model_chain = [config.model, "gemini-3-flash-preview", "gemini-2.5-pro", "gemini-2.5-flash"]
    tried_models: set[str] = set()
    last_error = ""

    for model in model_chain:
        if model in tried_models:
            continue
        tried_models.add(model)
        try:
            kwargs = {
                "model": model,
                "contents": f"{config.system_prompt}\n\nUser: {message}",
            }
            if types is not None:
                kwargs["config"] = types.GenerateContentConfig(max_output_tokens=180, temperature=0.4)
            response = client.models.generate_content(**kwargs)
            return response.text or "I do not have an answer yet."
        except Exception as exc:  # pragma: no cover - depends on remote API state.
            last_error = str(exc)
            if "RESOURCE_EXHAUSTED" not in last_error and "429" not in last_error:
                break

    return (
        "Gemini is reachable, but the selected model could not answer right now. "
        "This is usually quota or billing. Try again later, or change JARVIS_MODEL in .env. "
        f"Last error: {last_error[:180]}"
    )


def needs_current_info(message: str) -> bool:
    text = normalize(message)
    return any(re.search(pattern, text) for pattern in CURRENT_INFO_PATTERNS)


def answer_with_google_search(client: Any, message: str, config: AssistantConfig) -> str | None:
    if types is None:
        return None

    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    generation_config = types.GenerateContentConfig(
        tools=[grounding_tool],
        max_output_tokens=240,
        temperature=0.3,
    )
    prompt = (
        f"{config.system_prompt}\n\n"
        "Use Google Search grounding for the answer. If the user asks for a current office holder, election result, news, or recent fact, do not rely on memory.\n\n"
        f"User: {message}"
    )

    try:
        response = client.models.generate_content(
            model=config.search_model,
            contents=prompt,
            config=generation_config,
        )
        return response.text or None
    except Exception as exc:  # pragma: no cover - depends on remote API state.
        error = str(exc)
        if "RESOURCE_EXHAUSTED" in error or "429" in error:
            return None
        return None


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    create_app().run(host="127.0.0.1", port=port, debug=debug, use_reloader=False)
