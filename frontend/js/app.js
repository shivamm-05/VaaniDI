// VaaniBI — Voice-Powered Data Intelligence Frontend Script

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const badgeStt = document.getElementById("badge-stt");
  const badgeTts = document.getElementById("badge-tts");
  const activeFilenameEl = document.getElementById("active-filename");

  const uploadZone = document.getElementById("upload-zone");
  const fileInput = document.getElementById("file-input");
  const btnLoadSample = document.getElementById("btn-load-sample");

  const profileGrid = document.getElementById("profile-grid");
  const profRows = document.getElementById("prof-rows");
  const profCols = document.getElementById("prof-cols");
  const profMissing = document.getElementById("prof-missing");
  const profDupes = document.getElementById("prof-dupes");
  const profMemory = document.getElementById("prof-memory");

  const previewSection = document.getElementById("preview-section");
  const togglePreviewBtn = document.getElementById("toggle-preview-btn");
  const tableScroll = document.getElementById("table-scroll");
  const previewThead = document.getElementById("preview-thead");
  const previewTbody = document.getElementById("preview-tbody");

  const languageSelect = document.getElementById("language-select");
  const voiceSelect = document.getElementById("voice-select");

  const btnMic = document.getElementById("btn-mic");
  const micStatusText = document.getElementById("mic-status-text");
  const audioVisualizer = document.getElementById("audio-visualizer");

  const textQueryForm = document.getElementById("text-query-form");
  const queryInput = document.getElementById("query-input");
  const btnAsk = document.getElementById("btn-ask");
  const suggestionChips = document.getElementById("suggestion-chips");

  const resultsCard = document.getElementById("results-card");
  const executionMeta = document.getElementById("execution-meta");
  const intentBadge = document.getElementById("intent-badge");
  const transcriptContainer = document.getElementById("transcript-container");
  const transcriptText = document.getElementById("transcript-text");
  const answerText = document.getElementById("answer-text");
  const audioPlayerWrapper = document.getElementById("audio-player-wrapper");
  const ttsAudioElement = document.getElementById("tts-audio-element");
  const chartWrapper = document.getElementById("chart-wrapper");
  const resultsTable = document.getElementById("results-table");
  const resultsThead = document.getElementById("results-thead");
  const resultsTbody = document.getElementById("results-tbody");

  // Dynamic Suggested Questions Elements
  const suggestedQuestionsSection = document.getElementById("suggested-questions-section");
  const generatedQuestionsGrid = document.getElementById("generated-questions-grid");
  const langToggleBtns = document.querySelectorAll(".lang-toggle-btn");

  let currentSuggestedQuestions = [];
  let activeLangFilter = "both";

  // Audio recording state
  let isRecording = false;
  let audioContext = null;
  let mediaStream = null;
  let audioInput = null;
  let scriptProcessor = null;
  let audioChunks = [];
  let animFrameId = null;

  // Initialize
  checkHealth();
  loadInitialDataset();

  // Event Listeners
  languageSelect.addEventListener("change", updateVoicesForLanguage);

  // Suggested Questions Language Filter
  langToggleBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      langToggleBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeLangFilter = btn.dataset.langFilter;
      renderSuggestedQuestions();
    });
  });

  // File Upload
  uploadZone.addEventListener("click", () => fileInput.click());
  uploadZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadZone.classList.add("dragover");
  });
  uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
  uploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });
  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileUpload(e.target.files[0]);
    }
  });

  btnLoadSample.addEventListener("click", loadSampleDataset);

  // Preview toggle
  togglePreviewBtn.addEventListener("click", () => {
    const isHidden = tableScroll.style.display === "none";
    tableScroll.style.display = isHidden ? "block" : "none";
    togglePreviewBtn.textContent = isHidden ? "Hide Table" : "Show Table";
  });

  // Suggestion chips
  suggestionChips.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    const query = chip.dataset.q;
    const lang = chip.dataset.lang;
    if (lang) {
      languageSelect.value = lang;
      updateVoicesForLanguage();
    }
    queryInput.value = query;
    submitQuery(query);
  });

  // Text query form
  textQueryForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (!query) return;
    submitQuery(query);
  });

  // Microphone toggle
  btnMic.addEventListener("click", () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  });

  // --- API Functions ---

  async function checkHealth() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      if (data.gnani_configured) {
        badgeStt.innerHTML = `<span class="status-dot online"></span><span class="badge-label">Prisma STT Ready</span>`;
        badgeTts.innerHTML = `<span class="status-dot online"></span><span class="badge-label">Timbre TTS Ready</span>`;
      } else {
        badgeStt.innerHTML = `<span class="status-dot" style="background:#eab308"></span><span class="badge-label">Prisma (Demo/Mock)</span>`;
        badgeTts.innerHTML = `<span class="status-dot" style="background:#eab308"></span><span class="badge-label">Timbre (Demo/Mock)</span>`;
      }
    } catch (e) {
      console.warn("Health check error:", e);
    }
  }

  async function loadInitialDataset() {
    try {
      const res = await fetch("/api/dataset");
      if (res.ok) {
        const profile = await res.json();
        renderProfile(profile);
      }
    } catch (e) {
      console.log("No default dataset yet.");
    }
  }

  async function loadSampleDataset() {
    btnLoadSample.disabled = true;
    btnLoadSample.textContent = "Loading...";
    try {
      const res = await fetch("/api/dataset");
      if (res.ok) {
        const profile = await res.json();
        renderProfile(profile);
      }
    } catch (e) {
      alert("Failed to load sample dataset: " + e.message);
    } finally {
      btnLoadSample.disabled = false;
      btnLoadSample.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg> Load Sample Dataset`;
    }
  }

  async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append("file", file);

    uploadZone.style.opacity = "0.5";
    micStatusText.textContent = `Uploading ${file.name}...`;

    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to upload file");
      }

      renderProfile(data.profile);
      micStatusText.textContent = `Dataset loaded! Ask a question by voice or text.`;
    } catch (err) {
      alert("Upload error: " + err.message);
    } finally {
      uploadZone.style.opacity = "1";
    }
  }

  function renderProfile(profile) {
    activeFilenameEl.textContent = `${profile.filename} (${profile.total_rows.toLocaleString()} rows)`;
    profRows.textContent = profile.total_rows.toLocaleString();
    profCols.textContent = profile.total_columns.toLocaleString();
    profMissing.textContent = `${profile.missing_count} (${profile.missing_pct}%)`;
    profDupes.textContent = profile.duplicate_rows.toLocaleString();
    profMemory.textContent = `${profile.memory_kb} KB`;

    profileGrid.style.display = "grid";
    previewSection.style.display = "flex";

    // Populate preview table
    if (profile.sample_data && profile.sample_data.length > 0) {
      const cols = profile.columns;
      previewThead.innerHTML = `<tr>${cols.map((c) => `<th>${c}</th>`).join("")}</tr>`;
      previewTbody.innerHTML = profile.sample_data
        .map((row) => `<tr>${cols.map((c) => `<td>${row[c] !== undefined ? row[c] : "—"}</td>`).join("")}</tr>`)
        .join("");
    }

    // Auto-Generated Questions for Uploaded File
    currentSuggestedQuestions = profile.suggested_questions || [];
    renderSuggestedQuestions();
    updateSuggestionChips();
  }

  function renderSuggestedQuestions() {
    if (!suggestedQuestionsSection || !generatedQuestionsGrid) return;
    if (!currentSuggestedQuestions || currentSuggestedQuestions.length === 0) {
      suggestedQuestionsSection.style.display = "none";
      return;
    }

    suggestedQuestionsSection.style.display = "flex";
    generatedQuestionsGrid.innerHTML = "";

    currentSuggestedQuestions.forEach((q) => {
      const card = document.createElement("div");
      card.className = "gen-question-card";

      let primaryText = q.question_en;
      let secondaryText = q.question_hi;
      let queryLang = "en-IN";

      if (activeLangFilter === "hi") {
        primaryText = q.question_hi;
        secondaryText = "";
        queryLang = "hi-IN";
      } else if (activeLangFilter === "en") {
        primaryText = q.question_en;
        secondaryText = "";
        queryLang = "en-IN";
      }

      card.innerHTML = `
        <div class="gen-card-top">
          <span class="gen-badge">${q.badge}</span>
          <span class="gen-tag">${q.category}</span>
        </div>
        <div>
          <p class="gen-question-text">${primaryText}</p>
          ${secondaryText ? `<p class="gen-question-sub">${secondaryText}</p>` : ""}
        </div>
        <div class="gen-action-hint">
          <span>Click to ask</span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </div>
      `;

      card.addEventListener("click", () => {
        const textToAsk = activeLangFilter === "hi" ? q.question_hi : q.question_en;
        languageSelect.value = queryLang;
        updateVoicesForLanguage();
        queryInput.value = textToAsk;
        submitQuery(textToAsk);
      });

      generatedQuestionsGrid.appendChild(card);
    });
  }

  function updateSuggestionChips() {
    if (!suggestionChips || !currentSuggestedQuestions || currentSuggestedQuestions.length === 0) return;
    suggestionChips.innerHTML = "";

    currentSuggestedQuestions.slice(0, 6).forEach((q) => {
      const chipEn = document.createElement("button");
      chipEn.className = "chip";
      chipEn.dataset.q = q.question_en;
      chipEn.dataset.lang = "en-IN";
      chipEn.textContent = q.question_en;
      suggestionChips.appendChild(chipEn);

      if (q.question_hi && (q.id === "q_highest" || q.id === "q_compare")) {
        const chipHi = document.createElement("button");
        chipHi.className = "chip";
        chipHi.dataset.q = q.question_hi;
        chipHi.dataset.lang = "hi-IN";
        chipHi.textContent = q.question_hi;
        suggestionChips.appendChild(chipHi);
      }
    });
  }

  async function updateVoicesForLanguage() {
    const lang = languageSelect.value;
    try {
      const res = await fetch(`/api/voices?language=${lang}`);
      const data = await res.json();
      if (data.voices && data.voices.length > 0) {
        voiceSelect.innerHTML = data.voices
          .map((v) => `<option value="${v}">${v}</option>`)
          .join("");
      }
    } catch (e) {
      console.warn("Error fetching voices:", e);
    }
  }

  // --- Query Submission ---

  async function submitQuery(query) {
    setLoadingState(true, `Analyzing question with Pandas...`);
    transcriptContainer.style.display = "none";

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query,
          language: languageSelect.value,
          voice: voiceSelect.value,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Query failed");
      }

      renderResults(data);
    } catch (err) {
      alert("Query Error: " + err.message);
    } finally {
      setLoadingState(false);
    }
  }

  async function submitVoiceBlob(wavBlob) {
    setLoadingState(true, `Transcribing audio via Gnani Prisma STT...`);

    const formData = new FormData();
    formData.append("audio", wavBlob, "query_audio.wav");
    formData.append("language", languageSelect.value);
    formData.append("voice", voiceSelect.value);

    try {
      const res = await fetch("/api/voice-query", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Voice query failed");
      }

      renderResults(data, true);
    } catch (err) {
      alert("Voice Query Error: " + err.message);
    } finally {
      setLoadingState(false);
    }
  }

  function setLoadingState(isLoading, message = "") {
    btnAsk.disabled = isLoading;
    btnMic.disabled = isLoading;
    if (isLoading) {
      micStatusText.textContent = message;
      btnAsk.innerHTML = `Running...`;
    } else {
      btnAsk.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="22" y1="2" x2="11" y2="13"></line>
          <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
        </svg> Ask`;
      micStatusText.textContent = "Click microphone and ask a question";
    }
  }

  function renderResults(data, fromVoice = false) {
    resultsCard.style.display = "flex";
    executionMeta.textContent = `Completed in ${data.execution_time_ms} ms via deterministic Pandas execution`;
    intentBadge.textContent = data.intent || "INSIGHT";

    // Prisma Transcript
    if (fromVoice && data.transcript) {
      transcriptContainer.style.display = "flex";
      transcriptText.textContent = `"${data.transcript}"`;
    } else {
      transcriptContainer.style.display = "none";
    }

    // Answer Text
    answerText.textContent = data.answer;

    // Timbre Audio Player
    if (data.audio_url) {
      audioPlayerWrapper.style.display = "flex";
      ttsAudioElement.src = data.audio_url + "?t=" + Date.now();
      ttsAudioElement.play().catch((err) => console.log("Audio autoplay prevented:", err));
    } else {
      audioPlayerWrapper.style.display = "none";
    }

    // Plotly Chart
    if (data.chart_json) {
      chartWrapper.style.display = "block";
      try {
        const chartObj = JSON.parse(data.chart_json);
        Plotly.newPlot("plotly-chart", chartObj.data, chartObj.layout, {
          responsive: true,
          displayModeBar: true,
          displaylogo: false,
        });
      } catch (e) {
        console.error("Plotly render error:", e);
      }
    } else {
      chartWrapper.style.display = "none";
    }

    // Results Table
    if (data.data && data.data.length > 0) {
      resultsTable.style.display = "table";
      const keys = Object.keys(data.data[0]);
      resultsThead.innerHTML = `<tr>${keys.map((k) => `<th>${k}</th>`).join("")}</tr>`;
      resultsTbody.innerHTML = data.data
        .map((row) => `<tr>${keys.map((k) => `<td>${row[k] !== undefined ? row[k] : "—"}</td>`).join("")}</tr>`)
        .join("");
    } else {
      resultsTable.style.display = "none";
    }

    // Scroll to results
    resultsCard.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // --- In-Browser 16 kHz Mono PCM WAV Recorder ---
  // Encodes raw 16 kHz mono 16-bit PCM WAV directly in JS!
  // This bypasses any need for server-side FFmpeg conversion when speaking from modern browsers.

  async function startRecording() {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      audioContext = new AudioCtx({ sampleRate: 16000 });
      audioInput = audioContext.createMediaStreamSource(mediaStream);

      // Buffer size 4096, 1 input channel, 1 output channel
      scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
      audioChunks = [];

      scriptProcessor.onaudioprocess = (e) => {
        if (!isRecording) return;
        const channelData = e.inputBuffer.getChannelData(0);
        // Copy audio samples
        audioChunks.push(new Float32Array(channelData));
      };

      audioInput.connect(scriptProcessor);
      scriptProcessor.connect(audioContext.destination);

      isRecording = true;
      btnMic.classList.add("recording");
      micStatusText.textContent = "Listening... Click mic again to stop and analyze";
      audioVisualizer.style.display = "block";
      drawVisualizer();
    } catch (err) {
      console.error("Microphone access error:", err);
      alert("Microphone access denied or not supported: " + err.message);
    }
  }

  function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    btnMic.classList.remove("recording");
    audioVisualizer.style.display = "none";
    if (animFrameId) cancelAnimationFrame(animFrameId);

    // Stop streams & disconnect
    if (scriptProcessor) scriptProcessor.disconnect();
    if (audioInput) audioInput.disconnect();
    if (mediaStream) mediaStream.getTracks().forEach((track) => track.stop());

    // Encode audio chunks into 16 kHz 16-bit mono WAV Blob
    const wavBlob = encodeWAV(audioChunks, 16000);
    audioChunks = [];

    submitVoiceBlob(wavBlob);
  }

  function encodeWAV(chunks, sampleRate) {
    let totalLength = 0;
    for (const chunk of chunks) totalLength += chunk.length;

    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    const buffer = new ArrayBuffer(44 + merged.length * 2);
    const view = new DataView(buffer);

    // Write RIFF header
    writeString(view, 0, "RIFF");
    view.setUint32(4, 36 + merged.length * 2, true);
    writeString(view, 8, "WAVE");
    writeString(view, 12, "fmt ");
    view.setUint32(16, 16, true);          // Subchunk1Size (16 for PCM)
    view.setUint16(20, 1, true);           // AudioFormat (1 = PCM)
    view.setUint16(22, 1, true);           // NumChannels (1 = Mono)
    view.setUint32(24, sampleRate, true);  // SampleRate (16000)
    view.setUint32(28, sampleRate * 2, true); // ByteRate (SampleRate * 1 * 2)
    view.setUint16(32, 2, true);           // BlockAlign (1 * 2)
    view.setUint16(34, 16, true);          // BitsPerSample (16)
    writeString(view, 36, "data");
    view.setUint32(40, merged.length * 2, true);

    // Convert Float32 to 16-bit PCM
    let byteOffset = 44;
    for (let i = 0; i < merged.length; i++) {
      const s = Math.max(-1, Math.min(1, merged[i]));
      const pcm16 = s < 0 ? s * 0x8000 : s * 0x7fff;
      view.setInt16(byteOffset, pcm16, true);
      byteOffset += 2;
    }

    return new Blob([view], { type: "audio/wav" });
  }

  function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  }

  function drawVisualizer() {
    const canvas = audioVisualizer;
    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;

    function renderFrame() {
      if (!isRecording) return;
      ctx.clearRect(0, 0, width, height);

      const latestChunk = audioChunks.length > 0 ? audioChunks[audioChunks.length - 1] : null;
      ctx.lineWidth = 2;
      ctx.strokeStyle = "#38bdf8";
      ctx.beginPath();

      if (latestChunk && latestChunk.length > 0) {
        const step = Math.ceil(latestChunk.length / width);
        let x = 0;
        for (let i = 0; i < latestChunk.length; i += step) {
          const v = latestChunk[i] * 1.5;
          const y = (height / 2) + (v * (height / 2));
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
          x++;
        }
      } else {
        ctx.moveTo(0, height / 2);
        ctx.lineTo(width, height / 2);
      }

      ctx.stroke();
      animFrameId = requestAnimationFrame(renderFrame);
    }
    renderFrame();
  }
});
