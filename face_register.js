/**
 * Registration Step 2: capture two classes of webcam frames ("Face" and
 * "Not Face"), train a personal Teachable Machine (MobileNet transfer
 * learning) model entirely in the browser, then export it as
 * model.json + weights.bin + metadata.json and submit them to the server
 * via a normal (non-AJAX) form POST.
 *
 * Nothing leaves the browser until training has actually finished — the
 * upload form is only populated at the very end.
 */
(() => {
  const cfg = window.FACE_ENROLL_CONFIG;
  const LABELS = [cfg.faceLabel, cfg.notFaceLabel];

  const video = document.getElementById("webcam");
  const canvas = document.getElementById("captureCanvas");
  const ring = document.getElementById("ring");
  const phaseTitle = document.getElementById("phaseTitle");
  const phaseCount = document.getElementById("phaseCount");
  const phaseHint = document.getElementById("phaseHint");
  const progressFill = document.getElementById("progressFill");
  const statusLine = document.getElementById("statusLine");
  const actionBtn = document.getElementById("actionBtn");

  const ctx = canvas.getContext("2d");
  canvas.width = 224;
  canvas.height = 224;

  // captured frames per class, as fresh <canvas> snapshots ready for addExample()
  const captured = [[], []];

  let stream = null;
  let state = "init";
  let teachableModel = null;

  const PHASES = [
    {
      classIndex: 0,
      title: `Phase 1 — ${cfg.faceLabel}`,
      hint: `Look at the camera and move your head slightly — turn, tilt, change your expression — while we capture "${cfg.faceLabel}" samples.`,
      buttonIdle: `Start capturing my face`,
    },
    {
      classIndex: 1,
      title: `Phase 2 — ${cfg.notFaceLabel}`,
      hint: `Now show the camera something that is NOT your face — point it at a wall/ceiling, hold up your hand, or step out of frame — while we capture "${cfg.notFaceLabel}" samples.`,
      buttonIdle: `Start capturing "${cfg.notFaceLabel}"`,
    },
  ];
  let phaseIdx = 0;

  function setStatus(text, cls) {
    statusLine.textContent = text;
    statusLine.className = "status-line" + (cls ? " " + cls : "");
  }

  function setRing(cls) {
    ring.className = "ring" + (cls ? " " + cls : "");
  }

  async function initCamera() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { width: 320, height: 240 }, audio: false });
      video.srcObject = stream;
      await video.play();
      setStatus("Camera ready.");
      enterPhase(0);
    } catch (err) {
      setStatus("Could not access camera: " + err.message, "bad");
      actionBtn.textContent = "Camera unavailable";
      actionBtn.disabled = true;
    }
  }

  function enterPhase(idx) {
    phaseIdx = idx;
    const p = PHASES[idx];
    phaseTitle.textContent = p.title;
    phaseHint.textContent = p.hint;
    phaseCount.textContent = `0 / ${cfg.samplesPerClass}`;
    progressFill.style.width = "0%";
    actionBtn.disabled = false;
    actionBtn.textContent = p.buttonIdle;
    state = "phase_ready";
    setStatus("Click the button below when ready.");
    setRing("");
  }

  function grabFrame() {
    // draw the current video frame into a fresh canvas snapshot (not mirrored —
    // the CSS mirror is purely a visual UX flip for the <video> preview)
    const snap = document.createElement("canvas");
    snap.width = 224;
    snap.height = 224;
    const sctx = snap.getContext("2d");
    sctx.drawImage(video, 0, 0, 224, 224);
    return snap;
  }

  function runCapturePhase() {
    const p = PHASES[phaseIdx];
    state = "capturing";
    actionBtn.disabled = true;
    actionBtn.textContent = "Capturing…";
    setRing("capturing");
    setStatus("Hold steady, capturing…");

    let count = 0;
    const total = cfg.samplesPerClass;
    const timer = setInterval(() => {
      const frame = grabFrame();
      captured[p.classIndex].push(frame);
      count++;
      phaseCount.textContent = `${count} / ${total}`;
      progressFill.style.width = `${(count / total) * 100}%`;

      if (count >= total) {
        clearInterval(timer);
        setRing("good");
        setStatus(`Captured ${total} "${LABELS[p.classIndex]}" samples.`, "good");
        onPhaseCaptureDone();
      }
    }, cfg.captureIntervalMs);
  }

  function onPhaseCaptureDone() {
    if (phaseIdx === 0) {
      actionBtn.disabled = false;
      actionBtn.textContent = "Continue to Phase 2";
      state = "advance_phase";
    } else {
      actionBtn.disabled = false;
      actionBtn.textContent = "Train my model";
      state = "ready_to_train";
      phaseTitle.textContent = "Both phases captured";
      phaseHint.textContent = "Ready to train. This runs locally in your browser and takes roughly 15-30 seconds.";
    }
  }

  async function trainModel() {
    state = "training";
    actionBtn.disabled = true;
    actionBtn.textContent = "Training…";
    setRing("capturing");
    progressFill.style.width = "0%";
    phaseCount.textContent = "";
    setStatus("Loading base MobileNet model…");

    teachableModel = await tmImage.createTeachable(
      { tfjsVersion: tf.version.tfjs, tmVersion: tmImage.version || "0.8.5" },
      {}
    );
    teachableModel.setLabels(LABELS); // also resets the internal per-class example arrays

    setStatus("Extracting features from captured frames…");
    for (let c = 0; c < LABELS.length; c++) {
      for (const frame of captured[c]) {
        await teachableModel.addExample(c, frame);
      }
    }

    const EPOCHS = 50;
    setStatus(`Training epoch 0 / ${EPOCHS}…`);

    await teachableModel.train(
      { denseUnits: 100, epochs: EPOCHS, learningRate: 0.001, batchSize: 16 },
      {
        onEpochEnd: async (epoch, logs) => {
          const pct = Math.round(((epoch + 1) / EPOCHS) * 100);
          progressFill.style.width = pct + "%";
          const acc = typeof logs.acc === "number" ? logs.acc.toFixed(2) : "…";
          setStatus(`Training epoch ${epoch + 1} / ${EPOCHS} — accuracy ${acc}`);
        },
      }
    );

    setRing("good");
    setStatus("Training complete. Preparing upload…", "good");
    await exportAndSubmit();
  }

  async function exportAndSubmit() {
    let modelJsonBlob = null;
    let weightsBlob = null;

    await teachableModel.save(
      tf.io.withSaveHandler(async (artifacts) => {
        const weightsManifest = [
          { paths: ["./weights.bin"], weights: artifacts.weightSpecs },
        ];
        const modelJson = {
          modelTopology: artifacts.modelTopology,
          format: artifacts.format,
          generatedBy: artifacts.generatedBy,
          convertedBy: artifacts.convertedBy,
          weightsManifest,
        };
        modelJsonBlob = new Blob([JSON.stringify(modelJson)], { type: "application/json" });
        weightsBlob = new Blob([artifacts.weightData], { type: "application/octet-stream" });
        return {
          modelArtifactsInfo: {
            dateSaved: new Date(),
            modelTopologyType: "JSON",
          },
        };
      })
    );

    const metadata = {
      tfjsVersion: tf.version.tfjs,
      tmVersion: tmImage.version || "0.8.5",
      packageVersion: "0.8.5",
      packageName: "@teachablemachine/image",
      timeStamp: new Date().toISOString(),
      userMetadata: {},
      labels: LABELS,
      imageSize: 224,
    };

    const modelFile = new File([modelJsonBlob], "model.json", { type: "application/json" });
    const weightsFile = new File([weightsBlob], "weights.bin", { type: "application/octet-stream" });

    const dtModel = new DataTransfer();
    dtModel.items.add(modelFile);
    document.getElementById("modelJsonInput").files = dtModel.files;

    const dtWeights = new DataTransfer();
    dtWeights.items.add(weightsFile);
    document.getElementById("weightsBinInput").files = dtWeights.files;

    document.getElementById("metadataJsonInput").value = JSON.stringify(metadata);

    setStatus("Uploading trained model…");
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
    }
    document.getElementById("uploadForm").submit();
  }

  actionBtn.addEventListener("click", () => {
    if (state === "phase_ready") {
      runCapturePhase();
    } else if (state === "advance_phase") {
      enterPhase(1);
    } else if (state === "ready_to_train") {
      trainModel();
    }
  });

  initCamera();
})();
