/**
 * Login Step 3: loads THIS user's personal Teachable Machine model, runs a
 * short burst of live webcam predictions, averages them for stability, and
 * posts the resulting per-class probabilities to the server (which applies
 * the real pass/fail threshold — the client never decides success alone).
 */
(() => {
  const cfg = window.FACE_LOGIN_CONFIG;

  const video = document.getElementById("webcam");
  const ring = document.getElementById("ring");
  const progressFill = document.getElementById("progressFill");
  const statusLine = document.getElementById("statusLine");
  const scanBtn = document.getElementById("scanBtn");

  let stream = null;
  let model = null;
  let scanning = false;

  function setStatus(text, cls) {
    statusLine.textContent = text;
    statusLine.className = "status-line" + (cls ? " " + cls : "");
  }

  function setRing(cls) {
    ring.className = "ring" + (cls ? " " + cls : "");
  }

  async function init() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { width: 320, height: 240 }, audio: false });
      video.srcObject = stream;
      await video.play();
    } catch (err) {
      setStatus("Could not access camera: " + err.message, "bad");
      return;
    }

    try {
      model = await tmImage.load(cfg.modelURL, cfg.metadataURL);
    } catch (err) {
      setStatus("Could not load your face model: " + err.message, "bad");
      return;
    }

    setStatus("Ready. Click below and hold still.");
    scanBtn.disabled = false;
    scanBtn.textContent = "Scan my face";
  }

  function grabFrame() {
    const snap = document.createElement("canvas");
    snap.width = 224;
    snap.height = 224;
    snap.getContext("2d").drawImage(video, 0, 0, 224, 224);
    return snap;
  }

  async function runScan() {
    if (scanning) return;
    scanning = true;
    scanBtn.disabled = true;
    scanBtn.textContent = "Scanning…";
    setRing("capturing");
    progressFill.style.width = "0%";

    const total = cfg.framesPerScan;
    const sums = {}; // className -> running total probability

    for (let i = 0; i < total; i++) {
      const frame = grabFrame();
      const predictions = await model.predict(frame);
      for (const p of predictions) {
        sums[p.className] = (sums[p.className] || 0) + p.probability;
      }
      progressFill.style.width = `${((i + 1) / total) * 100}%`;
      setStatus(`Analyzing… (${i + 1}/${total})`);
      await new Promise((r) => setTimeout(r, cfg.frameIntervalMs));
    }

    const averaged = Object.entries(sums).map(([className, sum]) => ({
      className,
      probability: sum / total,
    }));

    setStatus("Checking result…");
    await submit(averaged);
  }

  async function submit(predictions) {
    try {
      const res = await fetch(cfg.submitURL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ challenge: cfg.challenge, predictions }),
      });
      const data = await res.json();

      if (data.ok) {
        setRing("good");
        setStatus("Face matched! Logging you in…", "good");
        if (stream) stream.getTracks().forEach((t) => t.stop());
        window.location.href = data.redirect;
        return;
      }

      setRing("bad");
      if (data.locked) {
        setStatus("Too many failed attempts. Account locked.", "bad");
      } else {
        setStatus("No match. Redirecting for another attempt…", "bad");
      }
      if (stream) stream.getTracks().forEach((t) => t.stop());
      setTimeout(() => {
        window.location.href = data.redirect || cfg.submitURL;
      }, 1200);
    } catch (err) {
      setRing("bad");
      setStatus("Network error verifying your scan. Please try again.", "bad");
      scanning = false;
      scanBtn.disabled = false;
      scanBtn.textContent = "Scan my face";
    }
  }

  scanBtn.addEventListener("click", runScan);
  init();
})();
