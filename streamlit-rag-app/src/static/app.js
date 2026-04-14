const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

const scroll = $("#scroll");
const empty = $("#empty");
const thread = $("#thread");
const form = $("#form");
const input = $("#input");
const go = $("#go");
const dot = $("#dot");
const stxt = $("#stxt");
const toolsBtn = $("#toolsBtn");
const toolsMenu = $("#toolsMenu");
const guidedTool = $("#guidedTool");
const videoTool = $("#videoTool");
const autograderTool = $("#autograderTool");
const toolChip = $("#toolChip");
const toolChipX = $("#toolChipX");
const toolChipLabel = toolChip.querySelector(".tool-chip-label");

let busy = false;
let activeMode = "guided"; // 'guided' | 'video' | 'autograder' | null
let selectedCourse = "CS 2200";

const PLACEHOLDERS = {
  default: "Ask about any topic from class",
  guided: "Ask about any topic from class",
  video: "What concept do you want to generate a video for?",
  autograder: "Paste the code you want graded",
};

const CHIP_LABELS = {
  guided: "📚 Guided Learning",
  video: "🎬 Generate Video",
  autograder: "📝 Autograder",
};

const SUBTITLES = {
  default: "Guided Learning",
  guided: "Guided Learning",
  video: "Video Generation",
  autograder: "Autograder",
};

function setMode(mode) {
  // Save and detach sessions when switching away from a mode
  if (mode !== "guided" && current && current.guided) {
    saveCurrentGuided();
    current.guided = null;
  }
  if (mode !== "video" && current && current.video) {
    saveCurrentVideo();
    current.video = null;
  }
  if (mode !== "autograder" && current && current.autograder) {
    saveCurrentAutograder();
    current.autograder = null;
  }
  if (typeof renderSessionLists === "function") renderSessionLists();
  activeMode = mode;
  input.placeholder = PLACEHOLDERS[mode] || PLACEHOLDERS.default;
  if (mode && CHIP_LABELS[mode]) {
    toolChipLabel.textContent = CHIP_LABELS[mode];
    toolChip.classList.add("on");
  } else {
    toolChip.classList.remove("on");
  }
  const sub = document.getElementById("mhSubtitle");
  if (sub) sub.textContent = SUBTITLES[mode] || SUBTITLES.default;
  toolsMenu.classList.remove("open");
  updateSetupPanels();
  input.focus();
}

function updateSetupPanels() {
  const videoSetup = document.getElementById("videoSetup");
  const agSetup = document.getElementById("agSetup");
  const emptyEl = document.getElementById("empty");
  const threadEmpty = thread.children.length === 0;
  const showVideo = activeMode === "video" && threadEmpty;
  const showAg = activeMode === "autograder" && threadEmpty;
  videoSetup.classList.toggle("on", showVideo);
  agSetup.classList.toggle("on", showAg);
  if (showVideo || showAg) emptyEl.classList.add("off");
  else if (threadEmpty) emptyEl.classList.remove("off");
}

// Backwards-compat alias
function updateVideoSetup() { updateSetupPanels(); }

// Video setup dropdowns (scoped to #videoSetup only)
const videoChoices = { type: "lecture-style", length: "30 seconds" };
document.querySelectorAll("#videoSetup .vs-dd-btn").forEach(btn => {
  btn.addEventListener("click", e => {
    e.stopPropagation();
    const dd = btn.parentElement;
    const open = dd.classList.contains("open");
    document.querySelectorAll("#videoSetup .vs-dd").forEach(d => d.classList.remove("open"));
    if (!open) dd.classList.add("open");
  });
});

document.querySelectorAll("#videoSetup .vs-dd-menu").forEach(menu => {
  menu.addEventListener("click", e => e.stopPropagation());
  menu.querySelectorAll(".vs-dd-item").forEach(item => {
    item.addEventListener("click", () => {
      const dd = menu.parentElement;
      const key = dd.dataset.key;
      const value = item.dataset.value;
      videoChoices[key] = value;
      menu.querySelectorAll(".vs-dd-item").forEach(i => i.classList.toggle("active", i === item));
      const valueEl = dd.querySelector(".vs-dd-value");
      if (valueEl) valueEl.textContent = value;
      dd.classList.remove("open");
    });
  });
});

document.addEventListener("click", () => {
  document.querySelectorAll(".vs-dd").forEach(d => d.classList.remove("open"));
});

toolsBtn.addEventListener("click", e => {
  e.stopPropagation();
  toolsMenu.classList.toggle("open");
});

toolsMenu.addEventListener("click", e => e.stopPropagation());
document.addEventListener("click", () => toolsMenu.classList.remove("open"));

guidedTool.addEventListener("click", () => setMode("guided"));
videoTool.addEventListener("click", () => setMode("video"));
autograderTool.addEventListener("click", () => setMode("autograder"));
toolChipX.addEventListener("click", () => setMode("guided"));

// Course dropdown
const courseDd = $("#courseDd");
const courseValue = $("#courseValue");
courseDd.querySelector(".course-btn").addEventListener("click", e => {
  e.stopPropagation();
  courseDd.classList.toggle("open");
});
courseDd.querySelectorAll(".vs-dd-item").forEach(item => {
  item.addEventListener("click", e => {
    e.stopPropagation();
    selectedCourse = item.dataset.value;
    courseValue.textContent = selectedCourse;
    courseDd.querySelectorAll(".vs-dd-item").forEach(i => i.classList.toggle("active", i === item));
    courseDd.classList.remove("open");
  });
});

// Sidebar toggle via panel icon
$("#sidePanelBtn").addEventListener("click", () => {
  document.getElementById("app").classList.toggle("side-open");
});

// ── Autograder setup wiring ───────────
const agMain = $("#agMainUpload");
const agSubPlus = $("#agSubPlus");
const agSubFile = $("#agSubFile");
const agSubLabel = $("#agSubLabel");
const agRubricBtn = $("#agRubricBtn");
const agRubricFile = $("#agRubricFile");
const agRubricLabel = $("#agRubricLabel");
const agAssignDd = $("#agAssignDd");
const agAssignValue = $("#agAssignValue");
const agCourseDd = $("#agCourseDd");
const agCourseValue = $("#agCourseValue");

function openSubFile(e) {
  if (e.target.closest(".course-dd")) return;
  agSubFile.click();
}
agMain.addEventListener("click", openSubFile);
agSubPlus.addEventListener("click", e => { e.stopPropagation(); agSubFile.click(); });

const agGradeBtn = $("#agGradeBtn");

agSubFile.addEventListener("change", () => {
  const files = Array.from(agSubFile.files || []);
  if (!files.length) return;
  agSubLabel.textContent = files.length === 1
    ? files[0].name
    : `${files.length} files selected \u00b7 ${files.map(f => f.name).join(", ")}`;
  agSubLabel.classList.add("filled");
  agGradeBtn.disabled = false;
});

agGradeBtn.addEventListener("click", () => {
  const files = Array.from(agSubFile.files || []);
  if (!files.length) return;
  const label = files.length === 1 ? files[0].name : `${files.length} files`;
  // Create an autograder session
  const entry = {
    id: ++sessIdSeq,
    title: label,
    filename: label,
    agvThreadHtml: "",
    selectedQid: null,
  };
  sessions.autograder.push(entry);
  current.autograder = entry;
  enterAutograderGraded(label);
  renderSessionLists();
});

agRubricBtn.addEventListener("click", () => agRubricFile.click());
agRubricFile.addEventListener("change", () => {
  const f = agRubricFile.files[0];
  if (!f) return;
  agRubricLabel.textContent = f.name;
  agRubricLabel.classList.add("filled");
});

// Assignment dropdown
agAssignDd.querySelector(".ag-assign-btn").addEventListener("click", e => {
  e.stopPropagation();
  agAssignDd.classList.toggle("open");
});
agAssignDd.querySelectorAll(".vs-dd-item").forEach(item => {
  item.addEventListener("click", e => {
    e.stopPropagation();
    agAssignValue.textContent = item.dataset.value;
    agAssignValue.classList.add("filled");
    agAssignDd.querySelectorAll(".vs-dd-item").forEach(i => i.classList.toggle("active", i === item));
    agAssignDd.classList.remove("open");
  });
});

// Course dropdown inside autograder (syncs with selectedCourse)
agCourseDd.querySelector(".course-btn").addEventListener("click", e => {
  e.stopPropagation();
  agCourseDd.classList.toggle("open");
});
agCourseDd.querySelectorAll(".vs-dd-item").forEach(item => {
  item.addEventListener("click", e => {
    e.stopPropagation();
    const v = item.dataset.value;
    agCourseValue.textContent = v;
    selectedCourse = v;
    if (courseValue) courseValue.textContent = v;
    agCourseDd.querySelectorAll(".vs-dd-item").forEach(i => i.classList.toggle("active", i === item));
    document.querySelectorAll("#courseMenu .vs-dd-item").forEach(i => i.classList.toggle("active", i.dataset.value === v));
    agCourseDd.classList.remove("open");
  });
});

function resetAutograder() {
  agSubFile.value = "";
  agRubricFile.value = "";
  agSubLabel.textContent = "Upload Completed Submission (pdf)";
  agSubLabel.classList.remove("filled");
  agRubricLabel.textContent = "Upload Rubric";
  agRubricLabel.classList.remove("filled");
  agAssignValue.textContent = "Select Assignment";
  agAssignValue.classList.remove("filled");
  agAssignDd.querySelectorAll(".vs-dd-item").forEach(i => i.classList.remove("active"));
  if (typeof agGradeBtn !== "undefined" && agGradeBtn) agGradeBtn.disabled = true;
}

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 120) + "px";
  go.disabled = !input.value.trim();
});

input.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (input.value.trim() && !busy) form.dispatchEvent(new Event("submit"));
  }
});

form.addEventListener("submit", async e => {
  e.preventDefault();
  const q = input.value.trim();
  if (!q || busy) return;

  const isVideo = activeMode === "video";

  show();
  addQ(q);
  input.value = "";
  input.style.height = "auto";
  go.disabled = true;
  busy = true;
  setStatus(isVideo ? "Generating video" : "Processing", true);

  const ldr = addLoader();
  toBottom();

  if (isVideo) {
    // Simulate generation delay, then switch to video view
    await new Promise(r => setTimeout(r, 1500));
    ldr.remove();
    enterVideoView(q, "videos/Assembly.mp4");
    busy = false;
    go.disabled = !input.value.trim();
    setStatus("Ready", false);
    return;
  }

  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q }),
    });
    if (!r.ok) {
      const e = await r.json().catch(() => ({}));
      throw new Error(e.detail || `Error ${r.status}`);
    }
    const d = await r.json();
    ldr.remove();
    enterChatMode(q, d);
  } catch (err) {
    ldr.remove();
    addErr(err.message);
  } finally {
    busy = false;
    go.disabled = !input.value.trim();
    setStatus("Ready", false);
    toBottom();
  }
});

$$(".nav-item, .ea").forEach(b => {
  b.addEventListener("click", () => {
    input.value = b.dataset.q;
    input.dispatchEvent(new Event("input"));
    form.dispatchEvent(new Event("submit"));
  });
});

$("#newBtn").addEventListener("click", resetToChat);
$("#sideNewBtn").addEventListener("click", resetToChat);

function resetToChat() {
  // Save any active sessions before clearing
  saveCurrentGuided();
  saveCurrentVideo();
  saveCurrentAutograder();
  document.getElementById("app").classList.remove("video-mode");
  document.getElementById("app").classList.remove("exitable");
  document.getElementById("main").classList.remove("chat-mode");
  document.getElementById("main").classList.remove("ag-graded-mode");
  csThread.innerHTML = "";
  refPanel.innerHTML = "";
  if (agvThread) agvThread.innerHTML = "";
  thread.innerHTML = "";
  empty.classList.remove("off");
  document.getElementById("videoSetup").classList.remove("on");
  document.getElementById("agSetup").classList.remove("on");
  resetAutograder();
  const vvPlayer = document.getElementById("vvPlayer");
  try { vvPlayer.pause(); } catch (_) {}
  document.getElementById("vvSource").src = "";
  try { vvPlayer.load(); } catch (_) {}
  document.getElementById("vvThread").innerHTML = "";
  current.video = null;
  current.guided = null;
  current.autograder = null;
  setMode("guided");
  renderSessionLists();
  input.focus();
}

// ── Autograder graded view ───────────
const AG_SAMPLE = {
  filename: "submission.pdf",
  assignment: "Assignment 3",
  student: "Student Name",
  earned: 37,
  max: 50,
  selectedId: 3,
  questions: [
    { id: 1, points: 8,  prompt: "Identify all data hazards in the given 5-instruction LC-2200 sequence and indicate which can be resolved by forwarding.", answer: "Identified the RAW hazard between instructions 1\u21922 and 2\u21923. Noted that both can be resolved with EX/MEM \u2192 EX forwarding. Missed the load-use hazard between instructions 3\u21924, which requires a stall even with forwarding.", score: 6 },
    { id: 2, points: 10, prompt: "Draw the pipeline diagram for the sequence above, assuming full forwarding and one stall slot where required.", answer: "Diagram correctly shows IF/ID/EX/MEM/WB stages across all five instructions, with the load-use stall inserted in the correct cycle. Forwarding arrows drawn cleanly from MEM/WB back to EX.", score: 10 },
    { id: 3, points: 12, prompt: "A direct-mapped cache has 16 blocks of 32 bytes each. Given the address stream 0x1040, 0x1044, 0x2040, 0x1040, 0x3040, compute the hit/miss sequence and the final miss rate. Show tag/index/offset breakdown.", answer: "Offset = 5 bits, index = 4 bits correctly identified, but tag bits computed as 23 instead of the correct value for a 32-bit address. Marked all five accesses as misses; the second access (0x1044) should be a hit because it maps to the same block as 0x1040. Final miss rate reported as 100% instead of 80%.", score: 7 },
    { id: 4, points: 10, prompt: "Explain the difference between write-through and write-back caching. Give one scenario where each is preferable.", answer: "Clear definitions of both policies. Good example of write-through for multi-core coherence scenarios. Write-back example was reasonable but lacked discussion of the dirty-bit mechanism.", score: 8 },
    { id: 5, points: 10, prompt: "For a 2-way set associative cache with LRU replacement, trace the cache state after the given 8-address reference stream.", answer: "Trace is correct through the first 6 accesses. On access 7, replaced the wrong way \u2014 evicted the more recently used block instead of applying LRU correctly. This error propagated to access 8.", score: 6 },
  ],
};

const agvFilename = $("#agvFilename");
const agvQuestions = $("#agvQuestions");
const agvScoresList = $("#agvScoresList");
const agvTotal = $("#agvTotal");
const agvThread = $("#agvThread");
const agvForm = $("#agvForm");
const agvInput = $("#agvInput");
const agvGo = $("#agvGo");
const agvCourseDd = $("#agvCourseDd");
const agvCourseValue = $("#agvCourseValue");

let agSelectedQid = null;

$("#agvExit").addEventListener("click", () => {
  const app = document.getElementById("app");
  const main = document.getElementById("main");
  if (app.classList.contains("video-mode")) {
    saveCurrentVideo();
    current.video = null;
    app.classList.remove("video-mode");
    try { document.getElementById("vvPlayer").pause(); } catch (_) {}
  }
  if (main.classList.contains("chat-mode")) {
    saveCurrentGuided();
    current.guided = null;
    main.classList.remove("chat-mode");
  }
  if (main.classList.contains("ag-graded-mode")) {
    saveCurrentAutograder();
    current.autograder = null;
    main.classList.remove("ag-graded-mode");
  }
  app.classList.remove("exitable");
  thread.innerHTML = "";
  updateSetupPanels();
  renderSessionLists();
});

function markExitable() {
  document.getElementById("app").classList.add("exitable");
}

function enterAutograderGraded(filename) {
  const main = document.getElementById("main");
  main.classList.add("ag-graded-mode");
  markExitable();
  if (filename) agvFilename.textContent = filename;
  agvTotal.textContent = `${AG_SAMPLE.earned}/${AG_SAMPLE.max}`;
  renderAgQuestions();
  renderAgScores();
  agvThread.innerHTML = "";
  addAgvA(`I\u2019ve graded your submission. Final score: <strong>${AG_SAMPLE.earned}/${AG_SAMPLE.max}</strong>. Click any question on the left or in the score panel to see the detailed feedback, or ask a follow-up below.`);
  selectAgQ(AG_SAMPLE.selectedId);
}

function renderAgQuestions() {
  agvQuestions.innerHTML = "";
  AG_SAMPLE.questions.forEach(q => {
    const row = document.createElement("div");
    row.className = "agv-q";
    row.dataset.qid = q.id;
    row.innerHTML = `
      <span class="agv-q-label">Q${q.id}</span>
      <div class="agv-q-body">
        <div class="agv-q-prompt">${esc(q.prompt)}</div>
        <div class="agv-q-answer">${esc(q.answer)}</div>
      </div>
    `;
    row.addEventListener("click", () => selectAgQ(q.id));
    agvQuestions.appendChild(row);
  });
}

function renderAgScores() {
  agvScoresList.innerHTML = "";
  AG_SAMPLE.questions.forEach(q => {
    const row = document.createElement("div");
    row.className = "agv-score-row";
    row.dataset.qid = q.id;
    row.innerHTML = `
      <div class="agv-score-head-row">
        <span class="agv-score-label">Q${q.id}:</span>
        <span class="agv-score-val">${q.score}/${q.points}</span>
      </div>
      <div class="agv-score-detail">${esc(q.answer)}</div>
    `;
    row.addEventListener("click", () => selectAgQ(q.id));
    agvScoresList.appendChild(row);
  });
}

function selectAgQ(qid) {
  agSelectedQid = qid;
  agvQuestions.querySelectorAll(".agv-q").forEach(r => {
    r.classList.toggle("selected", Number(r.dataset.qid) === qid);
  });
  const scored = agvScoresList.querySelectorAll(".agv-score-row");
  scored.forEach(r => {
    const match = Number(r.dataset.qid) === qid;
    r.classList.toggle("selected", match);
    if (match) r.scrollIntoView({ block: "nearest", behavior: "smooth" });
  });
  const leftSel = agvQuestions.querySelector(`.agv-q[data-qid="${qid}"]`);
  if (leftSel) leftSel.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function addAgvQ(text) {
  const el = document.createElement("div");
  el.className = "agv-q-bubble";
  el.textContent = text;
  agvThread.appendChild(el);
}

function addAgvA(html) {
  const el = document.createElement("div");
  el.className = "agv-a-bubble";
  el.innerHTML = `<p>${html}</p>`;
  agvThread.appendChild(el);
}

function agvScrollBottom() {
  requestAnimationFrame(() => { agvThread.scrollTop = agvThread.scrollHeight; });
}

agvInput.addEventListener("input", () => {
  agvInput.style.height = "auto";
  agvInput.style.height = Math.min(agvInput.scrollHeight, 100) + "px";
  agvGo.disabled = !agvInput.value.trim();
});

agvInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (agvInput.value.trim()) agvForm.dispatchEvent(new Event("submit"));
  }
});

agvForm.addEventListener("submit", e => {
  e.preventDefault();
  const q = agvInput.value.trim();
  if (!q) return;
  addAgvQ(q);
  agvInput.value = "";
  agvInput.style.height = "auto";
  agvGo.disabled = true;
  agvScrollBottom();
  setTimeout(() => {
    const sel = AG_SAMPLE.questions.find(x => x.id === agSelectedQid);
    const refBits = sel
      ? `Regarding <strong>Q${sel.id}</strong> (${sel.score}/${sel.points}): ${esc(sel.answer)}`
      : "Select a question on the left or in the score panel to reference specific feedback.";
    addAgvA(refBits);
    agvScrollBottom();
  }, 400);
});

// Course dropdown (autograder graded view)
agvCourseDd.querySelector(".course-btn").addEventListener("click", e => {
  e.stopPropagation();
  agvCourseDd.classList.toggle("open");
});
agvCourseDd.querySelectorAll(".vs-dd-item").forEach(item => {
  item.addEventListener("click", e => {
    e.stopPropagation();
    const v = item.dataset.value;
    agvCourseValue.textContent = v;
    selectedCourse = v;
    agvCourseDd.querySelectorAll(".vs-dd-item").forEach(i => i.classList.toggle("active", i === item));
    agvCourseDd.classList.remove("open");
  });
});

// ── Chat split view (references + chat) ─────
const csForm = $("#csForm");
const csInput = $("#csInput");
const csGo = $("#csGo");
const csThread = $("#csThread");
const refPanel = $("#refPanel");
const csCourseDd = $("#csCourseDd");
const csCourseValue = $("#csCourseValue");

function enterChatMode(firstQ, firstData) {
  const main = document.getElementById("main");
  main.classList.add("chat-mode");
  markExitable();
  if (!current.guided) {
    const entry = { id: ++sessIdSeq, title: firstQ, csThreadHtml: "", refPanelHtml: "" };
    sessions.guided.push(entry);
    current.guided = entry;
    csThread.innerHTML = "";
    refPanel.innerHTML = "";
  }
  addCsQ(firstQ);
  addCsA(firstData);
  renderReferences(firstData, firstQ);
  csScrollBottom();
  csInput.focus();
  saveCurrentGuided();
  renderSessionLists();
}

function extractKeywords(q) {
  const stop = new Set(["the","a","an","and","or","but","of","to","in","on","at","for","with","is","are","was","were","be","been","being","do","does","did","have","has","had","can","could","should","would","will","what","how","why","when","where","which","who","that","this","these","those","as","by","from","about","into","than","then","so","if","it","its","i","you","we","they","he","she","explain","describe","list","show"]);
  return (q || "").toLowerCase().split(/[^a-z0-9]+/i).filter(w => w && w.length > 2 && !stop.has(w));
}

function highlightText(text, keywords) {
  let out = esc(text);
  if (!keywords.length) return out;
  const pattern = new RegExp("\\b(" + keywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") + ")\\b", "gi");
  return out.replace(pattern, "<mark>$1</mark>");
}

function renderReferences(data, query) {
  refPanel.innerHTML = "";
  const keywords = extractKeywords(query);

  if (!data.context?.length && !data.citations?.length) {
    const el = document.createElement("div");
    el.className = "cs-ref-empty";
    el.textContent = "No references for this response.";
    refPanel.appendChild(el);
    return;
  }

  if (data.citations?.length) {
    const c = data.citations[0];
    const head = document.createElement("div");
    head.className = "cs-ref-head";
    head.innerHTML = `Reference: <span class="cs-ref-src">${esc(c.source)}${c.details ? ", " + esc(c.details) : ""}</span>`;
    refPanel.appendChild(head);
  }

  (data.context || []).forEach(ch => {
    const card = document.createElement("div");
    card.className = "cs-ref-card";
    const src = ch.source || "text";
    const cls = src === "slides" ? "sl" : "bk";
    let meta = `<span class="ctx-t ${cls}">${esc(src)}</span>`;
    if (ch.slide_name) meta += `<span class="ctx-t nt">${esc(ch.slide_name)}</span>`;
    if (ch.slide_number) meta += `<span class="ctx-t nt">Slide ${ch.slide_number}</span>`;
    if (ch.data_source_type) meta += `<span class="ctx-t nt">${esc(ch.data_source_type)}</span>`;
    card.innerHTML = `
      <div class="cs-ref-meta">${meta}</div>
      <div class="cs-ref-body">${highlightText(ch.text, keywords)}</div>
    `;
    refPanel.appendChild(card);
  });
}

function addCsQ(text) {
  const el = document.createElement("div");
  el.className = "cs-q";
  el.textContent = text;
  csThread.appendChild(el);
}

function addCsA(data) {
  const el = document.createElement("div");
  el.className = "cs-a";
  const body = (data.answer || "No response")
    .split(/\n{2,}/)
    .map(p => `<p>${renderAnswerMarkdown(p.trim())}</p>`)
    .join("");
  el.innerHTML = body;
  csThread.appendChild(el);
}

function addCsLoader() {
  const el = document.createElement("div");
  el.className = "cs-ld";
  el.innerHTML = "<span></span><span></span><span></span>";
  csThread.appendChild(el);
  return el;
}

function csScrollBottom() {
  requestAnimationFrame(() => { csThread.scrollTop = csThread.scrollHeight; });
}

csInput.addEventListener("input", () => {
  csInput.style.height = "auto";
  csInput.style.height = Math.min(csInput.scrollHeight, 100) + "px";
  csGo.disabled = !csInput.value.trim();
});

csInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (csInput.value.trim()) csForm.dispatchEvent(new Event("submit"));
  }
});

csForm.addEventListener("submit", async e => {
  e.preventDefault();
  const q = csInput.value.trim();
  if (!q) return;
  addCsQ(q);
  csInput.value = "";
  csInput.style.height = "auto";
  csGo.disabled = true;
  const ldr = addCsLoader();
  csScrollBottom();

  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q }),
    });
    const d = await r.json();
    ldr.remove();
    addCsA(d);
    renderReferences(d, q);
  } catch (err) {
    ldr.remove();
    const el = document.createElement("div");
    el.className = "cs-a";
    el.textContent = "Error: " + err.message;
    csThread.appendChild(el);
  } finally {
    csScrollBottom();
  }
});

// Course dropdown (chat-split side)
csCourseDd.querySelector(".course-btn").addEventListener("click", e => {
  e.stopPropagation();
  csCourseDd.classList.toggle("open");
});
csCourseDd.querySelectorAll(".vs-dd-item").forEach(item => {
  item.addEventListener("click", e => {
    e.stopPropagation();
    const v = item.dataset.value;
    csCourseValue.textContent = v;
    selectedCourse = v;
    csCourseDd.querySelectorAll(".vs-dd-item").forEach(i => i.classList.toggle("active", i === item));
    csCourseDd.classList.remove("open");
  });
});

// ── Video view ─────────────────────────
const vvForm = $("#vvForm");
const vvInput = $("#vvInput");
const vvGo = $("#vvGo");
const vvThread = $("#vvThread");

function enterVideoView(query, videoUrl) {
  const app = document.getElementById("app");
  app.classList.add("video-mode");
  markExitable();

  const src = document.getElementById("vvSource");
  const player = document.getElementById("vvPlayer");
  src.src = videoUrl;
  try { player.load(); } catch (_) {}

  // Create a new video session
  const entry = {
    id: ++sessIdSeq,
    title: query,
    url: videoUrl,
    type: videoChoices.type,
    length: videoChoices.length,
    threadHtml: "",
  };
  sessions.video.push(entry);
  current.video = entry;

  // Clear any leftover main thread content
  thread.innerHTML = "";
  updateSetupPanels();
  renderSessionLists();
}

// ── Sessions system ─────────────────
const sessions = { guided: [], video: [], autograder: [] };
const current = { guided: null, video: null, autograder: null };
let sessIdSeq = 0;

function saveCurrentGuided() {
  if (!current.guided) return;
  current.guided.csThreadHtml = csThread.innerHTML;
  current.guided.refPanelHtml = refPanel.innerHTML;
}

function saveCurrentVideo() {
  if (!current.video) return;
  current.video.threadHtml = vvThread.innerHTML;
}

function saveCurrentAutograder() {
  if (!current.autograder) return;
  current.autograder.agvThreadHtml = agvThread.innerHTML;
  current.autograder.selectedQid = agSelectedQid;
}

function endGuidedSession() {
  saveCurrentGuided();
  current.guided = null;
  renderSessionLists();
}

function renderSessionLists() {
  renderSessionList("guided", "sessListGuided", "📚");
  renderSessionList("video", "sessListVideo", "🎬");
  renderSessionList("autograder", "sessListAutograder", "📝");
}

function renderSessionList(kind, elId, icon) {
  const list = document.getElementById(elId);
  if (!list) return;
  list.innerHTML = "";
  const items = sessions[kind];
  if (!items.length) {
    const empty = document.createElement("span");
    empty.className = "sess-empty";
    empty.textContent = "No sessions yet";
    list.appendChild(empty);
    return;
  }
  items.forEach(entry => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "sess-item";
    if (current[kind] && current[kind].id === entry.id) btn.classList.add("active");
    btn.title = entry.title;
    btn.innerHTML = `
      <span class="sess-item-icon">${icon}</span>
      <span class="sess-item-text">${esc(entry.title)}</span>
    `;
    btn.addEventListener("click", () => openSession(kind, entry.id));
    list.appendChild(btn);
  });
}

function openSession(kind, id) {
  const entry = sessions[kind].find(s => s.id === id);
  if (!entry) return;
  // Save whatever we're currently in
  saveCurrentGuided();
  saveCurrentVideo();
  saveCurrentAutograder();

  const app = document.getElementById("app");
  const main = document.getElementById("main");
  // Reset view modes
  app.classList.remove("video-mode");
  main.classList.remove("chat-mode");
  main.classList.remove("ag-graded-mode");
  try { document.getElementById("vvPlayer").pause(); } catch (_) {}

  if (kind === "guided") {
    main.classList.add("chat-mode");
    csThread.innerHTML = entry.csThreadHtml || "";
    refPanel.innerHTML = entry.refPanelHtml || "";
    current.guided = entry;
    activeMode = "guided";
    setChipForMode("guided");
    csScrollBottom();
    markExitable();
  } else if (kind === "video") {
    app.classList.add("video-mode");
    const src = document.getElementById("vvSource");
    const player = document.getElementById("vvPlayer");
    src.src = entry.url;
    try { player.load(); } catch (_) {}
    vvThread.innerHTML = entry.threadHtml || "";
    current.video = entry;
    activeMode = "video";
    setChipForMode("video");
    vvScrollBottom();
    markExitable();
  } else if (kind === "autograder") {
    main.classList.add("ag-graded-mode");
    agvFilename.textContent = entry.filename;
    agvTotal.textContent = `${AG_SAMPLE.earned}/${AG_SAMPLE.max}`;
    renderAgQuestions();
    renderAgScores();
    agvThread.innerHTML = entry.agvThreadHtml || "";
    current.autograder = entry;
    activeMode = "autograder";
    setChipForMode("autograder");
    if (entry.selectedQid) selectAgQ(entry.selectedQid);
    markExitable();
  }
  renderSessionLists();
}

function setChipForMode(mode) {
  input.placeholder = PLACEHOLDERS[mode] || PLACEHOLDERS.default;
  if (mode && CHIP_LABELS[mode]) {
    toolChipLabel.textContent = CHIP_LABELS[mode];
    toolChip.classList.add("on");
  } else {
    toolChip.classList.remove("on");
  }
  const sub = document.getElementById("mhSubtitle");
  if (sub) sub.textContent = SUBTITLES[mode] || SUBTITLES.default;
}

function addVvQ(text) {
  const el = document.createElement("div");
  el.className = "vv-q";
  el.textContent = text;
  vvThread.appendChild(el);
}

function addVvA(text) {
  const el = document.createElement("div");
  el.className = "vv-a";
  el.innerHTML = text.split(/\n{2,}/).map(p => `<p>${renderAnswerMarkdown(p.trim())}</p>`).join("");
  vvThread.appendChild(el);
}

function addVvLoader() {
  const el = document.createElement("div");
  el.className = "vv-ld";
  el.innerHTML = "<span></span><span></span><span></span>";
  vvThread.appendChild(el);
  return el;
}

function vvScrollBottom() {
  requestAnimationFrame(() => { vvThread.scrollTop = vvThread.scrollHeight; });
}

vvInput.addEventListener("input", () => {
  vvInput.style.height = "auto";
  vvInput.style.height = Math.min(vvInput.scrollHeight, 100) + "px";
  vvGo.disabled = !vvInput.value.trim();
});

vvInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (vvInput.value.trim()) vvForm.dispatchEvent(new Event("submit"));
  }
});

vvForm.addEventListener("submit", async e => {
  e.preventDefault();
  const q = vvInput.value.trim();
  if (!q) return;
  addVvQ(q);
  vvInput.value = "";
  vvInput.style.height = "auto";
  vvGo.disabled = true;
  const ldr = addVvLoader();
  vvScrollBottom();

  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q }),
    });
    const d = await r.json();
    ldr.remove();
    addVvA(d.answer || "No response");
  } catch (err) {
    ldr.remove();
    addVvA("Error: " + err.message);
  } finally {
    vvScrollBottom();
  }
});

function show() {
  empty.classList.add("off");
  document.getElementById("videoSetup").classList.remove("on");
  document.getElementById("agSetup").classList.remove("on");
}

function addQ(text) {
  const el = document.createElement("div");
  el.className = "q";
  el.textContent = text;
  thread.appendChild(el);
}

function addA(data) {
  const el = document.createElement("div");
  el.className = "a";

  const body = data.answer
    .split(/\n{2,}/)
    .map(p => `<p>${renderAnswerMarkdown(p.trim())}</p>`)
    .join("");

  let src = "";
  if (data.citations?.length) {
    src = `<div class="a-src">${data.citations.map(c =>
      `<span class="src">${esc(c.source)}${c.details ? " · " + esc(c.details) : ""}</span>`
    ).join("")}</div>`;
  }

  let ctx = "";
  if (data.context?.length) {
    const entries = data.context.map(ch => {
      const s = ch.source || "text";
      const cls = s === "slides" ? "sl" : "bk";
      let m = `<span class="ctx-t ${cls}">${esc(s)}</span>`;
      if (ch.slide_name) m += `<span class="ctx-t nt">${esc(ch.slide_name)}</span>`;
      if (ch.slide_number) m += `<span class="ctx-t nt">Slide ${ch.slide_number}</span>`;
      if (ch.data_source_type) m += `<span class="ctx-t nt">${esc(ch.data_source_type)}</span>`;
      return `<div class="ctx-c"><div class="ctx-m">${m}</div>${esc(ch.text)}</div>`;
    }).join("");

    ctx = `<div class="a-ctx">
      <button class="ctx-tog" onclick="togCtx(this)">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="6 9 12 15 18 9"/></svg>
        ${data.context.length} passages
      </button>
      <div class="ctx-box">${entries}</div>
    </div>`;
  }

  el.innerHTML = `
    <div class="a-head"><div class="a-dot"></div><span class="a-name">Backbone</span></div>
    <div class="a-text">${body}</div>
    ${src}${ctx}
  `;
  thread.appendChild(el);
}

function addLoader() {
  const el = document.createElement("div");
  el.className = "a";
  el.innerHTML = `
    <div class="a-head"><div class="a-dot"></div><span class="a-name">Backbone</span></div>
    <div class="ld"><span></span><span></span><span></span></div>
  `;
  thread.appendChild(el);
  return el;
}

function addVideo(prompt, videoUrl) {
  const el = document.createElement("div");
  el.className = "a";
  el.innerHTML = `
    <div class="a-head"><div class="a-dot"></div><span class="a-name">Backbone</span></div>
    <div class="a-text"><p>Here's a video for: <strong>${esc(prompt)}</strong></p></div>
    <div class="a-video">
      <video controls playsinline>
        <source src="${videoUrl}" type="video/mp4">
        Your browser does not support video.
      </video>
    </div>
  `;
  thread.appendChild(el);
}

function addErr(msg) {
  const el = document.createElement("div");
  el.className = "a";
  el.innerHTML = `
    <div class="a-head"><div class="a-dot"></div><span class="a-name">Backbone</span></div>
    <div class="a-err">${esc(msg)}</div>
  `;
  thread.appendChild(el);
}

function togCtx(btn) {
  btn.classList.toggle("on");
  btn.nextElementSibling.classList.toggle("on");
}

function setStatus(t, on) {
  stxt.textContent = t;
  dot.classList.toggle("on", on);
}

function toBottom() {
  requestAnimationFrame(() => { scroll.scrollTop = scroll.scrollHeight; });
}

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

// Renders inline markdown (bold, italic) in safe way: escape HTML first, then convert ** and *
function renderAnswerMarkdown(text) {
  const escaped = esc(text);
  return escaped
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/__(.+?)__/g, "<strong>$1</strong>")
    .replace(/_(.+?)_/g, "<em>$1</em>");
}

// ── Session search overlay ─────────────────
const searchOverlay = $("#searchOverlay");
const searchInput = $("#searchInput");
const searchResults = $("#searchResults");
const searchClose = $("#searchClose");

$("#sideSearchBtn").addEventListener("click", () => {
  searchOverlay.classList.add("open");
  searchInput.value = "";
  renderSearchResults("");
  setTimeout(() => searchInput.focus(), 50);
});

searchClose.addEventListener("click", closeSearch);
searchOverlay.addEventListener("click", e => {
  if (e.target === searchOverlay) closeSearch();
});

document.addEventListener("keydown", e => {
  if (e.key === "Escape" && searchOverlay.classList.contains("open")) closeSearch();
  // Cmd/Ctrl+K to open search
  if ((e.metaKey || e.ctrlKey) && e.key === "k") {
    e.preventDefault();
    searchOverlay.classList.add("open");
    searchInput.value = "";
    renderSearchResults("");
    setTimeout(() => searchInput.focus(), 50);
  }
});

function closeSearch() {
  searchOverlay.classList.remove("open");
  searchInput.value = "";
}

searchInput.addEventListener("input", () => {
  renderSearchResults(searchInput.value.trim().toLowerCase());
});

function renderSearchResults(query) {
  searchResults.innerHTML = "";

  if (!query) {
    // Show all sessions grouped, or hint
    const total = sessions.guided.length + sessions.video.length + sessions.autograder.length;
    if (!total) {
      searchResults.innerHTML = '<div class="search-hint">No sessions yet. Start a chat to create one.</div>';
      return;
    }
    // Show all grouped
    appendGroup("Guided Learning", "📚", sessions.guided, query);
    appendGroup("Video Generation", "🎬", sessions.video, query);
    appendGroup("Autograder", "📝", sessions.autograder, query);
    if (!searchResults.children.length) {
      searchResults.innerHTML = '<div class="search-hint">Start typing to search across all sessions</div>';
    }
    return;
  }

  const guidedMatches = sessions.guided.filter(s => s.title.toLowerCase().includes(query));
  const videoMatches = sessions.video.filter(s => s.title.toLowerCase().includes(query));
  const agMatches = sessions.autograder.filter(s => s.title.toLowerCase().includes(query));

  appendGroup("Guided Learning", "📚", guidedMatches, query);
  appendGroup("Video Generation", "🎬", videoMatches, query);
  appendGroup("Autograder", "📝", agMatches, query);

  if (!guidedMatches.length && !videoMatches.length && !agMatches.length) {
    searchResults.innerHTML = '<div class="search-no-results">No matching sessions</div>';
  }
}

function appendGroup(label, icon, items, query) {
  if (!items.length) return;
  const heading = document.createElement("div");
  heading.className = "search-group-label";
  heading.textContent = label;
  searchResults.appendChild(heading);

  items.forEach(entry => {
    const kind = label.includes("Guided") ? "guided" : label.includes("Video") ? "video" : "autograder";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "search-result";
    const highlighted = query ? highlightSearchMatch(entry.title, query) : esc(entry.title);
    btn.innerHTML = `
      <span class="search-result-icon">${icon}</span>
      <span class="search-result-text">${highlighted}</span>
    `;
    btn.addEventListener("click", () => {
      closeSearch();
      openSession(kind, entry.id);
    });
    searchResults.appendChild(btn);
  });
}

function highlightSearchMatch(text, query) {
  const escaped = esc(text);
  const escapedQuery = esc(query);
  const idx = escaped.toLowerCase().indexOf(escapedQuery.toLowerCase());
  if (idx === -1) return escaped;
  return escaped.slice(0, idx) + "<mark>" + escaped.slice(idx, idx + escapedQuery.length) + "</mark>" + escaped.slice(idx + escapedQuery.length);
}

// Initialize default tool (Guided Learning)
setMode("guided");
