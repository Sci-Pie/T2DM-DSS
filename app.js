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
  return document.getElementById(id).checked;
}

function getInputs() {
  return {
    country: document.getElementById("country").value,
    hba1c: numOrNull("hba1c"),
    bmi: numOrNull("bmi"),
    egfr: numOrNull("egfr"),
    symptoms_catabolic: boolVal("symptoms_catabolic"),
    ascvd: boolVal("ascvd"),
    hf: boolVal("hf"),
    ckd: boolVal("ckd"),
    on_basal_insulin: boolVal("on_basal_insulin"),
    glp1_available: boolVal("glp1_available"),
    tirzepatide_available: boolVal("tirzepatide_available"),
    gi_contra_glp1: boolVal("gi_contra_glp1"),
  };
}

function fillList(ulId, items) {
  const ul = document.getElementById(ulId);
  ul.innerHTML = "";
  (items || []).forEach((x) => {
    const li = document.createElement("li");
    li.textContent = x;
    ul.appendChild(li);
  });
}

function render(rec) {
  document.getElementById("therapy").textContent = rec.therapy || "";
  document.getElementById("profile").textContent = rec.profile_used || "";
  fillList("why", rec.why || []);
  fillList("next", rec.next_steps || []);
  resultEl.hidden = false;
}

async function init() {
  try {
    statusEl.textContent = "Loading Pyodide…";

    // IMPORTANT: pin indexURL to the same CDN path used in index.html
    pyodide = await loadPyodide({
      indexURL: "https://cdn.jsdelivr.net/npm/pyodide@0.25.1/",
    });

    statusEl.textContent = "Loading Python engine…";

    // Cache-busting to avoid “server uses old file” situations
    const engineUrl = `py/engine.py?v=${Date.now()}`;
    const engineCode = await (await fetch(engineUrl)).text();

    pyodide.runPython(engineCode);

    // Optional sanity check (will throw if recommend_js is missing)
    pyodide.runPython("assert 'recommend_json' in globals()");

    statusEl.textContent = "Ready.";
  } catch (e) {
    console.error(e);
    statusEl.textContent = "Init failed — open Console (F12) to see details.";
  }
}

document.getElementById("run").addEventListener("click", () => {
  if (!pyodide) {
    statusEl.textContent = "Pyodide is still loading…";
    return;
  }

  try {
    const inputs = getInputs();
    const inputsJson = JSON.stringify(inputs);

    // pass as a python string variable safely
    pyodide.globals.set("JS_INPUTS_JSON", JSON.stringify(inputs));
    const outJson = pyodide.runPython("recommend_json(JS_INPUTS_JSON)");
    const rec = JSON.parse(outJson);

    render(rec);
  } catch (e) {
    console.error(e);
    statusEl.textContent = "Run failed — open Console (F12) to see details.";
  }
});

init();