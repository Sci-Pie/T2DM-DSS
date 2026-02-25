import json

# ======================
# Country configuration
# ======================

COUNTRIES = {
    "RU": {"frc": True, "label": "Russia"},
    "TR": {"frc": True, "label": "Turkey", "tr_bmi_threshold": 35},
    "LB": {"frc": True, "label": "Lebanon"},
    "IQ": {"frc": True, "label": "Iraq"},
    "JO": {"frc": False, "label": "Jordan"},  # FRC not available
    "EU": {"frc": True, "label": "EU"},
    "US": {"frc": True, "label": "USA"},
    "OTHER": {"frc": True, "label": "Other"},
}

def boolv(x):
    return bool(x)

def num(x):
    try:
        return float(x)
    except:
        return None

def recommend(inputs):

    country = inputs.get("country", "OTHER")
    profile = COUNTRIES.get(country, COUNTRIES["OTHER"])

    hba1c = num(inputs.get("hba1c"))
    bmi = num(inputs.get("bmi"))

    severe = boolv(inputs.get("symptoms_catabolic")) or (hba1c and hba1c >= 10)

    glp1 = boolv(inputs.get("glp1_available"))
    frc = boolv(inputs.get("frc_available")) and profile["frc"]

    on_basal = boolv(inputs.get("on_basal_insulin"))
    on_premix = boolv(inputs.get("on_premix"))
    on_bb = boolv(inputs.get("on_basal_bolus"))
    on_frc = boolv(inputs.get("on_frc"))
    hypogly = boolv(inputs.get("recurrent_hypoglycemia"))
    complexity = boolv(inputs.get("regimen_complexity"))

    ascvd = boolv(inputs.get("ascvd"))
    hf = boolv(inputs.get("hf"))
    ckd = boolv(inputs.get("ckd"))

    why = []
    comments = []
    next_steps = []

    # 1. Severe hyperglycaemia
    if severe:
        return {
            "therapy": "Start / intensify insulin (severe hyperglycaemia)",
            "why": ["Catabolic symptoms or HbA1c ≥10% require rapid insulin-based control."],
            "next_steps": ["Initiate or intensify insulin with close monitoring."],
            "comments": comments
        }

    # 2. Simplification
    if (on_bb or on_premix) and (hypogly or complexity):
        if frc:
            therapy = "Switch to FRC (iGlarLixi) for simplification"
            if country == "TR" and bmi and bmi < profile.get("tr_bmi_threshold", 35):
                comments.append("Turkey: reimbursement for iGlarLixi usually requires BMI ≥35. Below threshold may be out-of-pocket.")
        else:
            therapy = "Simplify insulin regimen internally"
        return {
            "therapy": therapy,
            "why": ["Hypoglycaemia or complexity supports treatment simplification."],
            "next_steps": ["Reassess glucose patterns after regimen adjustment."],
            "comments": comments
        }

    # 3. Intensification on basal
    if on_basal:
        if glp1:
            return {
                "therapy": "Add GLP-1 RA to basal insulin",
                "why": ["HbA1c above target on basal; GLP-1 preferred before prandial insulin."],
                "next_steps": ["Start GLP-1 titration and reassess control."],
                "comments": comments
            }
        elif frc:
            therapy = "Switch basal insulin to FRC (iGlarLixi)"
            if country == "TR" and bmi and bmi < profile.get("tr_bmi_threshold", 35):
                comments.append("Turkey: reimbursement for iGlarLixi usually requires BMI ≥35.")
            return {
                "therapy": therapy,
                "why": ["FRC can improve postprandial and fasting control in one injection."],
                "next_steps": ["Initiate FRC titration."],
                "comments": comments
            }
        else:
            return {
                "therapy": "Add prandial insulin (basal-plus strategy)",
                "why": ["GLP-1 and FRC not feasible."],
                "next_steps": ["Introduce mealtime insulin stepwise."],
                "comments": comments
            }

    # 4. First injectable

    if ascvd or hf or ckd:
        if glp1:
            return {
                "therapy": "Start GLP-1 RA (cardiorenal priority)",
                "why": ["Cardiorenal disease favors GLP-1 when available."],
                "next_steps": ["Initiate GLP-1 titration."],
                "comments": comments
            }
        else:
            return {
                "therapy": "Start basal insulin",
                "why": ["GLP-1 unavailable; insulin required."],
                "next_steps": ["Start basal insulin titration."],
                "comments": comments
            }

    if bmi and bmi >= 30 and glp1:
        return {
            "therapy": "Start GLP-1 RA (weight-centric choice)",
            "why": ["BMI ≥30; GLP-1 offers weight benefit."],
            "next_steps": ["Start GLP-1 titration."],
            "comments": comments
        }

    if hba1c and hba1c > 9 and frc:
        therapy = "Start FRC (iGlarLixi)"
        if country == "TR" and bmi and bmi < profile.get("tr_bmi_threshold", 35):
            comments.append("Turkey: reimbursement may require BMI ≥35.")
        return {
            "therapy": therapy,
            "why": ["Higher HbA1c without severe catabolism; FRC provides dual control."],
            "next_steps": ["Initiate FRC titration."],
            "comments": comments
        }

    if glp1:
        return {
            "therapy": "Start GLP-1 RA",
            "why": ["Preferred first injectable when available."],
            "next_steps": ["Start GLP-1 titration."],
            "comments": comments
        }

    return {
        "therapy": "Start basal insulin",
        "why": ["GLP-1 not available."],
        "next_steps": ["Start basal insulin titration."],
        "comments": comments
    }


def recommend_json(js_inputs_json: str):
    inputs = json.loads(js_inputs_json)
    return json.dumps(recommend(inputs), ensure_ascii=False)
