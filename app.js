let pyodide = null;

const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");

function numOrNull(id) {
  const v = document.getElementById(id).value;
  if (v === "" || v === null) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function boolVal(id) {
  const el = document.getElementById(id);
  return el ? el.checked : false;
}

function getRegimen() {
  const el = document.querySelector('input[name="regimen"]:checked');
  return el ? el.value : "none";
}

function getInputs() {
  const regimen = getRegimen();

  return {
    country: document.getElementById("country").value,
    hba1c: numOrNull("hba1c"),
    bmi: numOrNull("bmi"),
    egfr: numOrNull("egfr"),

    symptoms_catabolic: boolVal("symptoms_catabolic"),
    ascvd: boolVal("ascvd"),
    hf: boolVal("hf"),
    ckd: boolVal("ckd"),

    glp1_available: boolVal("glp1_available"),
    gi_contra_glp1: boolVal("gi_contra_glp1"),
    frc_available: boolVal("frc_available"),

    // regimen flags expected by engine.py (radio mapped to booleans)
    on_basal_insulin: regimen === "basal",
    on_glp1: regimen === "glp1",
    on_frc: regimen === "frc",
    on_premix: regimen === "premix",
    on_basal_bolus: regimen === "bb",

    recurrent_hypoglycemia: boolVal("recurrent_hypoglycemia"),
    regimen_complexity: boolVal("regimen_complexity"),

    // Optional: allow overriding A1c target later (engine defaults to 7.0 if used)
    // a1c_target: numOrNull("a1c_target"),
  };
}

function fillList(ulId, items) {
  const ul = document.getElementById(ulId);
  ul.innerHTML = "";
  (items || []).forEach((x) => {
    const li = document.createElement("li");
    li.textContent = String(x);
    ul.appendChild(li);
  });
}

function fillChips(containerId, items) {
  const box = document.getElementById(containerId);
  box.innerHTML = "";
  (items || []).forEach((t) => {
    const span = document.createElement("span");
    span.className = "chip";
    span.textContent = String(t);
    box.appendChild(span);
  });
}

function render(rec) {
  document.getElementById("therapy").textContent = rec.therapy || "";
  document.getElementById("profile").textContent = rec.profile_used || "";

  fillList("why", rec.why || []);
  fillList("next", rec.next_steps || []);

  const commentsBlock = document.getElementById("comments_block");
  const basisBlock = document.getElementById("basis_block");

  const comments = rec.comments || [];
  const basis = rec.basis || [];

  if (comments.length) {
    commentsBlock.hidden = false;
    fillList("comments", comments);
  } else {
    commentsBlock.hidden = true;
  }

  if (basis.length) {
    basisBlock.hidden = false;
    fillChips("basis", basis);
  } else {
    basisBlock.hidden = true;
  }

  resultEl.hidden = false;
}

function applyCountryUIRules() {
  const country = document.getElementById("country").value;
  const frcEl = document.getElementById("frc_available");
  const hint = document.getElementById("country_hint");

  if (country === "JO") {
    frcEl.checked = false;
    frcEl.disabled = true;
    hint.textContent = "Jordan: FRC (iGlarLixi) is treated as not available.";
  } else {
    frcEl.disabled = false;
    hint.textContent = "";
  }
}

async function init() {
  try {
    statusEl.textContent = "Loading Pyodide…";

    pyodide = await loadPyodide({
      indexURL: "https://cdn.jsdelivr.net/pyodide/v0.25.1/full/",
    });

    statusEl.textContent = "Loading clinical engine…";

    // Cache-busting to avoid stale engine.py
    const engineUrl = `py/engine.py?v=${Date.now()}`;
    const engineCode = await (await fetch(engineUrl)).text();
    pyodide.runPython(engineCode);

    // Sanity check for JSON bridge
    pyodide.runPython("assert 'recommend_json' in globals()");

    statusEl.textContent = "Ready.";
  } catch (e) {
    console.error(e);
    statusEl.textContent = "Init failed — open Console (F12) for details.";
  }
}

document.getElementById("country").addEventListener("change", applyCountryUIRules);

document.getElementById("run").addEventListener("click", () => {
  if (!pyodide) {
    statusEl.textContent = "Pyodide is still loading…";
    return;
  }

  try {
    const inputs = getInputs();
    const inputsJson = JSON.stringify(inputs);

    pyodide.globals.set("JS_INPUTS_JSON", inputsJson);
    const outJson = pyodide.runPython("recommend_json(JS_INPUTS_JSON)");

    const rec = JSON.parse(outJson);
    render(rec);
  } catch (e) {
    console.error(e);
    statusEl.textContent = "Run failed — open Console (F12) for details.";
  }
});

applyCountryUIRules();
init();
