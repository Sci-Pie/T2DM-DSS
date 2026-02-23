import json

# Single-file MVP: no external imports besides stdlib json.

GUIDELINES_BY_COUNTRY = {
  "US": {"prefer_glp1_before_insulin": True, "allow_dual": True},
  "EU": {"prefer_glp1_before_insulin": True, "allow_dual": True},
  "RU": {"prefer_glp1_before_insulin": True, "allow_dual": True},
  "TR": {"prefer_glp1_before_insulin": True, "allow_dual": True},
  "JO": {"prefer_glp1_before_insulin": True, "allow_dual": False},
  "IQ": {"prefer_glp1_before_insulin": True, "allow_dual": False},
  "LB": {"prefer_glp1_before_insulin": True, "allow_dual": False},
  "OTHER": {"prefer_glp1_before_insulin": True, "allow_dual": True},
}

def recommend(x: dict) -> dict:
    country = x.get("country", "OTHER")
    p = GUIDELINES_BY_COUNTRY.get(country, GUIDELINES_BY_COUNTRY["OTHER"])

    if x.get("symptoms_catabolic"):
        return {
            "profile_used": country,
            "therapy": "Start basal insulin (urgent / rapid control scenario)",
            "why": ["Symptomatic hyperglycaemia / catabolic features -> insulin favored for rapid control"],
            "next_steps": [
                "Titrate basal insulin per local guideline",
                "If still above target: intensify (basal-plus / premix / basal-bolus) per country profile"
            ],
        }

    if x.get("on_basal_insulin"):
        if x.get("glp1_available") and not x.get("gi_contra_glp1"):
            return {
                "profile_used": country,
                "therapy": "Intensify: add GLP-1 RA to basal insulin",
                "why": [
                    "On basal insulin but still above target -> add-on GLP-1 RA is a common next step",
                    "Often improves HbA1c with weight benefit and typically lower hypoglycaemia risk vs adding prandial insulin"
                ],
                "next_steps": [
                    "Consider fixed-ratio basal+GLP-1 option if available (simplification)",
                    "Reassess HbA1c after titration period (per local guideline)"
                ],
            }

        return {
            "profile_used": country,
            "therapy": "Intensify insulin regimen per local guideline (basal-plus / premix / basal-bolus)",
            "why": [
                "GLP-1 RA not available or contraindicated",
                "HbA1c above target on basal insulin"
            ],
            "next_steps": [
                "Choose intensification pathway aligned with country profile",
                "Ensure titration and SMBG plan"
            ],
        }

    if p.get("prefer_glp1_before_insulin") and x.get("glp1_available") and not x.get("gi_contra_glp1"):
        bmi = x.get("bmi")
        if p.get("allow_dual") and x.get("tirzepatide_available") and (bmi is not None and bmi >= 30):
            return {
                "profile_used": country,
                "therapy": "Start dual GIP/GLP-1 RA (if available) as first injectable",
                "why": [
                    "Urgent insulin not required",
                    "High BMI + availability -> consider higher weight/glycaemic efficacy option"
                ],
                "next_steps": [
                    "Educate on dose escalation and GI tolerability",
                    "Reassess HbA1c/weight and adjust therapy per local guideline"
                ],
            }

        return {
            "profile_used": country,
            "therapy": "Start GLP-1 RA as first injectable",
            "why": [
                "Urgent insulin not required",
                "Preferred before insulin in many modern algorithms when available and tolerated"
            ],
            "next_steps": [
                "Educate on titration and GI adverse effects",
                "Reassess HbA1c/weight and intensify if needed"
            ],
        }

    return {
        "profile_used": country,
        "therapy": "Start basal insulin (first injectable fallback)",
        "why": ["GLP-1 RA not available / contraindicated / not selected"],
        "next_steps": [
            "Start and titrate basal insulin per local guideline",
            "If still above target: consider add-on GLP-1 RA (if later available) or intensify insulin regimen"
        ],
    }

def recommend_json(js_inputs_json: str) -> str:
    """Accept JSON string, return JSON string (Pyodide-safe)."""
    x = json.loads(js_inputs_json)
    out = recommend(x)
    return json.dumps(out, ensure_ascii=False)