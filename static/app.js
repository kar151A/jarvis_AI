const statusEl = document.querySelector("#status");
const transcriptEl = document.querySelector("#transcript");
const listenButton = document.querySelector("#listenButton");
const muteButton = document.querySelector("#muteButton");
const signalEl = document.querySelector("#signal");
const modeEl = document.querySelector("#mode");
const wakeEl = document.querySelector("#wake");
const interruptEl = document.querySelector("#interrupt");
const radarEl = document.querySelector(".radar");

const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;

let recognition;
let awake = false;
let listening = false;
let shouldListen = false;
let starting = false;
let voiceEnabled = true;
let micPermissionGranted = false;
let restartTimer;
let restartDelay = 900;
let isSpeaking = false;
let currentRequestController;
let micStream;

function setStatus(value) {
  statusEl.textContent = value;
}

function setTelemetry({ signal, mode, wake, interrupt } = {}) {
  if (signal) signalEl.textContent = signal;
  if (mode) modeEl.textContent = mode;
  if (wake) wakeEl.textContent = wake;
  if (interrupt) interruptEl.textContent = interrupt;
}

function flashInterrupt() {
  radarEl.classList.remove("interrupt-flash");
  void radarEl.offsetWidth;
  radarEl.classList.add("interrupt-flash");
}

function cancelActiveOutput(reason = "Interrupted") {
  let interrupted = false;
  if (window.speechSynthesis && window.speechSynthesis.speaking) {
    window.speechSynthesis.cancel();
    interrupted = true;
  }
  if (currentRequestController) {
    currentRequestController.abort();
    currentRequestController = undefined;
    interrupted = true;
  }
  if (interrupted) {
    isSpeaking = false;
    setStatus(reason);
    setTelemetry({ signal: "Voice Override", mode: "Interrupt", interrupt: "Active" });
    flashInterrupt();
  }
}

function say(text) {
  transcriptEl.textContent = text;
  if (!voiceEnabled || !window.speechSynthesis) return;

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1;
  utterance.pitch = 0.92;
  utterance.onstart = () => {
    isSpeaking = true;
    setTelemetry({ mode: "Speaking", interrupt: "Listening" });
  };
  utterance.onend = () => {
    isSpeaking = false;
    setTelemetry({ mode: shouldListen ? "Listening" : "Idle", interrupt: "Armed" });
    scheduleRestart(700);
  };
  utterance.onerror = () => {
    isSpeaking = false;
    setTelemetry({ interrupt: "Armed" });
  };
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

async function requestMicrophone() {
  if (micPermissionGranted) return true;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    say("Microphone access is not available in this browser. Use Chrome or Edge.");
    return false;
  }

  try {
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    micPermissionGranted = true;
    setTelemetry({ signal: "Mic Ready" });
    return true;
  } catch (error) {
    shouldListen = false;
    starting = false;
    setStatus("Mic blocked");
    setTelemetry({ signal: "Blocked", mode: "Permission" });
    listenButton.textContent = "Enable Voice";
    say("Microphone permission is blocked. Allow microphone access in the browser, then click Enable Voice again.");
    return false;
  }
}

async function askJarvis(message) {
  if (currentRequestController) currentRequestController.abort();
  currentRequestController = new AbortController();
  setStatus("Thinking");
  setTelemetry({ mode: "Processing", interrupt: "Armed" });
  const response = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
    signal: currentRequestController.signal,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Jarvis failed to respond.");
  }
  currentRequestController = undefined;
  say(data.reply);
}

function handleSpeech(text) {
  const cleanText = text.trim();
  if (!cleanText) return;

  cancelActiveOutput("Interrupted");
  transcriptEl.textContent = cleanText;
  setTelemetry({ signal: "Voice Detected" });

  if (/hey\s+jarvis/i.test(cleanText)) {
    awake = true;
    setTelemetry({ wake: "Awake" });
    const command = cleanText.replace(/.*hey\s+jarvis[, ]*/i, "").trim();
    say(command ? "Yes sir. Working on it." : "Yes sir. I am listening.");
    if (command) {
      askJarvis(command).catch((error) => {
        if (error.name !== "AbortError") say(error.message);
      });
    }
    return;
  }

  if (awake) {
    askJarvis(cleanText).catch((error) => {
      if (error.name !== "AbortError") say(error.message);
    });
  } else {
    setStatus("Say Hey Jarvis");
    setTelemetry({ wake: "Waiting" });
  }
}

function scheduleRestart(delay = restartDelay) {
  window.clearTimeout(restartTimer);
  if (!shouldListen || listening || starting) return;
  restartTimer = window.setTimeout(() => {
    startListening();
  }, delay);
}

function buildRecognition() {
  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = "en-IN";

  recognition.onstart = () => {
    starting = false;
    listening = true;
    restartDelay = 900;
    listenButton.textContent = "Stop Voice";
    setStatus("Say Hey Jarvis");
    setTelemetry({ signal: "Listening", mode: "Listening" });
  };

  recognition.onend = () => {
    listening = false;
    starting = false;
    listenButton.textContent = shouldListen ? "Stop Voice" : "Enable Voice";
    setStatus(shouldListen ? "Listening standby" : "Idle");
    setTelemetry({ mode: shouldListen ? "Re-arming" : "Idle" });
    scheduleRestart();
  };

  recognition.onerror = (event) => {
    const hardStop = event.error === "not-allowed" || event.error === "audio-capture";
    const errorMessages = {
      "not-allowed": "Microphone blocked",
      "audio-capture": "No microphone found",
      network: "Speech service issue",
      "no-speech": "Listening standby",
      aborted: "Listening standby",
    };

    setStatus(errorMessages[event.error] || "Speech standby");
    if (hardStop) {
      shouldListen = false;
      starting = false;
      listenButton.textContent = "Enable Voice";
      setTelemetry({ signal: "Offline", mode: "Check mic" });
      return;
    }

    restartDelay = Math.min(restartDelay + 500, 3500);
    setTelemetry({ mode: "Re-arming" });
  };

  recognition.onresult = (event) => {
    const result = event.results[event.results.length - 1];
    const text = result[0].transcript;
    const cleanText = text.trim();
    if (result.isFinal && (isSpeaking || currentRequestController) && cleanText.length > 2) {
      cancelActiveOutput("Interrupted");
    }
    if (result.isFinal) {
      handleSpeech(text);
    } else {
      transcriptEl.textContent = text;
      setTelemetry({
        signal: isSpeaking ? "Override Heard" : "Hearing",
        interrupt: isSpeaking ? "Active" : "Armed",
      });
    }
  };
}

async function startListening() {
  if (listening || starting) return;
  if (!SpeechRecognition) {
    say("Speech recognition is not available in this browser. Use Chrome or Edge.");
    return;
  }
  if (!(await requestMicrophone())) return;

  shouldListen = true;
  starting = true;
  setStatus("Activating mic");
  setTelemetry({ mode: "Booting" });

  if (!recognition) buildRecognition();

  try {
    recognition.start();
  } catch (error) {
    starting = false;
    setStatus("Listening standby");
    scheduleRestart(1200);
  }
}

function stopListening() {
  shouldListen = false;
  starting = false;
  cancelActiveOutput("Idle");
  window.clearTimeout(restartTimer);
  listenButton.textContent = "Enable Voice";
  setStatus("Idle");
  setTelemetry({ signal: "Mic Ready", mode: "Idle", interrupt: "Armed" });
  if (recognition && listening) recognition.stop();
}

listenButton.addEventListener("click", () => {
  if (shouldListen || listening || starting) {
    stopListening();
  } else {
    startListening();
  }
});

muteButton.addEventListener("click", () => {
  voiceEnabled = !voiceEnabled;
  muteButton.textContent = voiceEnabled ? "Voice On" : "Voice Off";
  if (!voiceEnabled && window.speechSynthesis) window.speechSynthesis.cancel();
});

setStatus(SpeechRecognition ? "Ready" : "Use Chrome or Edge");
