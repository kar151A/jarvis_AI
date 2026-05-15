const statusEl = document.querySelector("#status");
const transcriptEl = document.querySelector("#transcript");
const listenButton = document.querySelector("#listenButton");
const cameraButton = document.querySelector("#cameraButton");
const muteButton = document.querySelector("#muteButton");
const cameraEl = document.querySelector("#camera");

const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;

let recognition;
let awake = false;
let listening = false;
let shouldListen = false;
let voiceEnabled = true;

function setStatus(value) {
  statusEl.textContent = value;
}

function say(text) {
  transcriptEl.textContent = text;
  if (!voiceEnabled || !window.speechSynthesis) return;

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1;
  utterance.pitch = 0.92;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

async function askJarvis(message) {
  setStatus("Thinking");
  const response = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Jarvis failed to respond.");
  }
  say(data.reply);
  setStatus("Listening");
}

function handleSpeech(text) {
  const cleanText = text.trim();
  transcriptEl.textContent = cleanText;

  if (/hey\s+jarvis/i.test(cleanText)) {
    awake = true;
    const command = cleanText.replace(/.*hey\s+jarvis[, ]*/i, "").trim();
    say(command ? "Yes sir. Working on it." : "Yes sir.");
    if (command) askJarvis(command).catch((error) => say(error.message));
    return;
  }

  if (awake && cleanText) {
    askJarvis(cleanText).catch((error) => say(error.message));
  }
}

function startListening() {
  if (!SpeechRecognition) {
    say("Speech recognition is not available in this browser. Use Chrome or Edge.");
    return;
  }

  if (!recognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      listening = true;
      listenButton.textContent = "Listening";
      setStatus("Say Hey Jarvis");
    };

    recognition.onend = () => {
      listening = false;
      listenButton.textContent = "Start Listening";
      setStatus(shouldListen ? "Reconnecting" : "Idle");
      if (shouldListen) {
        window.setTimeout(startListening, 700);
      }
    };

    recognition.onerror = (event) => {
      setStatus(event.error || "Speech error");
    };

    recognition.onresult = (event) => {
      const result = event.results[event.results.length - 1];
      if (result.isFinal) handleSpeech(result[0].transcript);
    };
  }

  shouldListen = true;
  try {
    recognition.start();
  } catch (error) {
    setStatus("Listening already active");
  }
}

async function enableCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: false,
    });
    cameraEl.srcObject = stream;
    cameraButton.textContent = "Camera On";
  } catch (error) {
    say("I could not access the camera. Check browser permission.");
  }
}

listenButton.addEventListener("click", () => {
  if (listening && recognition) {
    shouldListen = false;
    recognition.stop();
  } else {
    startListening();
  }
});

cameraButton.addEventListener("click", enableCamera);

muteButton.addEventListener("click", () => {
  voiceEnabled = !voiceEnabled;
  muteButton.textContent = voiceEnabled ? "Voice On" : "Voice Off";
  if (!voiceEnabled && window.speechSynthesis) window.speechSynthesis.cancel();
});

setStatus(SpeechRecognition ? "Ready" : "Use Chrome or Edge");

window.addEventListener("load", () => {
  window.setTimeout(() => {
    startListening();
    enableCamera();
  }, 800);
});
