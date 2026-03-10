import json

# ======================
# Country configuration
# ======================

COUNTRIES = {
    "TR": {"frc": True, "label": "Turkey", "tr_bmi_threshold": 35},
    "LB": {"frc": True, "label": "Lebanon"},
    "IQ": {"frc": True, "label": "Iraq"},
}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def boolv(x):
    if isinstance(x, bool):
        return x
    if x is None:
        return False
    if isinstance(x, (int, float)):
        return x != 0
    if isinstance(x, str):
        s = x.strip().lower()
        if s in {"true", "1", "yes", "y", "on"}:
            return True
        if s in {"false", "0", "no", "n", "off", "", "none", "null"}:
            return False
    return bool(x)


def num(x):
    try:
        return float(x)
    except Exception:
        return None


def add_tr_frc_reimbursement_note(country, profile, bmi, comments):
    if country == "TR" and bmi is not None and bmi < profile.get("tr_bmi_threshold", 35):
        comments.append(
            "Turkey: reimbursement for FRC may be limited when BMI < 35; "
            "treatment may be out-of-pocket depending on local access conditions."
        )


# ──────────────────────────────────────────────
# Main router
# ──────────────────────────────────────────────

def recommend(inputs):
    country = inputs.get("country")
    if country not in COUNTRIES:
        return {
            "therapy": "Unsupported country",
            "why": [
                "This engine currently supports only Turkey, Lebanon, and Iraq."
            ],
            "next_steps": [
                "Provide one of: TR, LB, IQ."
            ],
            "comments": []
        }

    profile = COUNTRIES[country]

    # Numeric inputs
    hba1c = num(inputs.get("hba1c"))
    hba1c_target = num(inputs.get("hba1c_target"))
    bmi = num(inputs.get("bmi"))

    # Current regimen
    on_basal = boolv(inputs.get("on_basal_insulin"))
    on_bb = boolv(inputs.get("on_basal_bolus"))
    on_premix = boolv(inputs.get("on_premix"))
    on_frc = boolv(inputs.get("on_frc"))
    on_rapid_added = boolv(inputs.get("on_rapid_added"))

    # Clinical flags
    symptoms_catabolic = boolv(inputs.get("symptoms_catabolic"))
    recurrent_hypoglycemia = boolv(inputs.get("recurrent_hypoglycemia"))
    ppg_uncontrolled = boolv(inputs.get("ppg_uncontrolled"))

    # HbA1c target logic:
    # if target not provided but HbA1c exists, use default target = 7.0
    effective_hba1c_target = hba1c_target
    if effective_hba1c_target is None and hba1c is not None:
        effective_hba1c_target = 7.0

    # Auto-calculate target_unmet and gap
    if hba1c is not None and effective_hba1c_target is not None:
        target_unmet = hba1c > effective_hba1c_target
        gap = hba1c - effective_hba1c_target
    else:
        target_unmet = False
        gap = None

    # Country FRC availability (fixed by country)
    frc = profile["frc"]

    comments = []

    if hba1c is not None and hba1c_target is None:
        comments.append(
            "HbA1c target was not provided; default target of 7.0% was used."
        )

    # 1. Severe hyperglycaemia override
    severe = symptoms_catabolic or (hba1c is not None and hba1c >= 10)
    if severe:
        return {
            "therapy": "Start / intensify insulin (severe hyperglycaemia)",
            "why": [
                "Catabolic symptoms or HbA1c ≥ 10% require rapid insulin-based control."
            ],
            "next_steps": [
                "Initiate or intensify insulin with close monitoring.",
                "Reassess regimen after initial stabilisation."
            ],
            "comments": comments
        }

    # 2. On FRC + rapid insulin + target still unmet
    if on_frc and on_rapid_added and target_unmet:
        return {
            "therapy": "Intensify to basal-bolus regimen OR premixed insulin",
            "why": [
                "Glycaemic target remains unmet despite FRC plus rapid-acting insulin.",
                "Further intensification is warranted."
            ],
            "next_steps": [
                "Basal-bolus: continue basal insulin + add rapid-acting insulin before additional meals.",
                "Premixed insulin: consider when a simpler multidose insulin regimen is preferable.",
                "Reassess HbA1c in 3 months.",
                "Ensure SMBG or CGM where available."
            ],
            "comments": comments
        }

    # 3. On FRC + target still unmet
    if on_frc and target_unmet:
        comments.append(
            "Adding rapid-acting insulin to FRC may be off-label depending on local label and market."
        )
        return {
            "therapy": "Add rapid-acting insulin to FRC",
            "why": [
                "Glycaemic target remains unmet on FRC.",
                "Prandial coverage may be needed as the next intensification step."
            ],
            "next_steps": [
                "Start with 1 prandial injection at the largest meal.",
                "If needed, intensify stepwise to additional meals.",
                "Reassess HbA1c in 3 months.",
                "Review local label / internal policy because this approach may be off-label."
            ],
            "comments": comments
        }

    # 4. On basal-bolus or premix + recurrent hypoglycaemia
    if (on_bb or on_premix) and recurrent_hypoglycemia:
        if frc:
            add_tr_frc_reimbursement_note(country, profile, bmi, comments)
            return {
                "therapy": "Consider switch to FRC for simplification",
                "why": [
                    "Recurrent hypoglycaemia on basal-bolus or premixed insulin supports simplification."
                ],
                "next_steps": [
                    "Review current insulin doses and switching approach.",
                    "Initiate FRC and titrate according to local label.",
                    "Reassess glucose patterns after switch."
                ],
                "comments": comments
            }

    # 5. On basal insulin + target unmet or PPG uncontrolled
    if on_basal and (target_unmet or ppg_uncontrolled):
        if frc:
            add_tr_frc_reimbursement_note(country, profile, bmi, comments)

            why = []
            if target_unmet:
                why.append("HbA1c remains above target on basal insulin.")
            if ppg_uncontrolled:
                why.append("Postprandial glucose remains uncontrolled on basal insulin.")
            why.append("FRC can address both fasting and postprandial glucose in one injectable strategy.")

            return {
                "therapy": "Switch basal insulin to FRC",
                "why": why,
                "next_steps": [
                    "Stop basal-only strategy and initiate FRC.",
                    "Titrate according to local label and glucose response.",
                    "Reassess HbA1c and postprandial control in 3 months."
                ],
                "comments": comments
            }

    # 6. First injectable / early injectable logic
    # 6A. Gap-based logic if gap is available
    if gap is not None:
        # gap < 2%
        if gap < 2.0:
            if bmi is not None and bmi <= 30:
                return {
                    "therapy": "Start basal insulin",
                    "why": [
                        f"HbA1c gap {gap:.1f}% is < 2% above target.",
                        "BMI ≤ 30 kg/m²: basal insulin is the preferred initial injectable choice."
                    ],
                    "next_steps": [
                        "Initiate basal insulin and titrate to fasting glucose target.",
                        "Reassess HbA1c in 3 months."
                    ],
                    "comments": comments
                }

            if bmi is not None and bmi > 30:
                add_tr_frc_reimbursement_note(country, profile, bmi, comments)
                comments.append(
                    "Optional non-reimbursed consideration: standalone GLP-1 RA may be discussed if feasible out-of-pocket."
                )
                return {
                    "therapy": "Start FRC",
                    "why": [
                        f"HbA1c gap {gap:.1f}% is < 2% above target.",
                        "BMI > 30 kg/m²: FRC is preferred as the reimbursed incretin-containing path."
                    ],
                    "next_steps": [
                        "Initiate FRC and titrate according to local label.",
                        "Reassess HbA1c in 3 months."
                    ],
                    "comments": comments
                }

            # BMI unknown
            comments.append(
                "BMI not provided; recommendation made conservatively. If BMI > 30, FRC may be preferred."
            )
            return {
                "therapy": "Start basal insulin",
                "why": [
                    f"HbA1c gap {gap:.1f}% is < 2% above target.",
                    "BMI is unavailable, so a conservative basal-insulin-first choice is used."
                ],
                "next_steps": [
                    "Confirm BMI if possible.",
                    "Initiate basal insulin and titrate to fasting glucose target.",
                    "Reassess HbA1c in 3 months."
                ],
                "comments": comments
            }

        # gap >= 2%
        add_tr_frc_reimbursement_note(country, profile, bmi, comments)
        comments.append(
            "Optional non-reimbursed consideration: GLP-1 RA-based strategy may be discussed if feasible out-of-pocket."
        )
        return {
            "therapy": "Start FRC",
            "why": [
                f"HbA1c gap {gap:.1f}% is ≥ 2% above target.",
                "FRC is preferred as the reimbursed combination path from initiation."
            ],
            "next_steps": [
                "Initiate FRC and titrate according to local label.",
                "Reassess HbA1c in 3 months."
            ],
            "comments": comments
        }

    # 6B. Fallback if HbA1c gap cannot be calculated
    # (e.g. current HbA1c itself is missing)
    if bmi is not None and bmi > 30:
        add_tr_frc_reimbursement_note(country, profile, bmi, comments)
        comments.append(
            "Optional non-reimbursed consideration: standalone GLP-1 RA may be discussed if feasible out-of-pocket."
        )
        return {
            "therapy": "Start FRC",
            "why": [
                "HbA1c gap cannot be calculated because current HbA1c is not available.",
                "BMI > 30 kg/m²: FRC is preferred."
            ],
            "next_steps": [
                "Initiate FRC and titrate according to local label.",
                "Define individualised HbA1c target for follow-up."
            ],
            "comments": comments
        }

    if bmi is not None and bmi <= 30:
        return {
            "therapy": "Start basal insulin",
            "why": [
                "HbA1c gap cannot be calculated because current HbA1c is not available.",
                "BMI ≤ 30 kg/m²: basal insulin is the preferred conservative choice."
            ],
            "next_steps": [
                "Initiate basal insulin and titrate to fasting glucose target.",
                "Define individualised HbA1c target for follow-up."
            ],
            "comments": comments
        }

    comments.append(
        "Recommendation made conservatively because current HbA1c and BMI were not fully available. If BMI > 30, FRC may be preferred."
    )
    return {
        "therapy": "Start basal insulin",
        "why": [
            "Current HbA1c and BMI are not sufficiently available for more specific routing, so a conservative basal-insulin-first approach is used."
        ],
        "next_steps": [
            "Confirm BMI and current HbA1c if possible.",
            "Initiate basal insulin and titrate to fasting glucose target."
        ],
        "comments": comments
    }


def recommend_json(js_inputs_json: str) -> str:
    inputs = json.loads(js_inputs_json)
    return json.dumps(recommend(inputs), ensure_ascii=False)


# ──────────────────────────────────────────────
# Self-test
# ──────────────────────────────────────────────

if __name__ == "__main__":
    TEST_CASES = [
        {
            "label": "TR | severe hyperglycaemia",
            "inputs": {
                "country": "TR",
                "hba1c": 10.5,
                "bmi": 33,
                "symptoms_catabolic": False
            }
        },
        {
            "label": "LB | on FRC uncontrolled -> add rapid",
            "inputs": {
                "country": "LB",
                "hba1c": 8.4,
                "hba1c_target": 7.0,
                "bmi": 34,
                "on_frc": True
            }
        },
        {
            "label": "IQ | on FRC + rapid uncontrolled -> BB/premix",
            "inputs": {
                "country": "IQ",
                "hba1c": 9.0,
                "hba1c_target": 7.0,
                "bmi": 31,
                "on_frc": True,
                "on_rapid_added": True
            }
        },
        {
            "label": "TR | BB + recurrent hypoglycaemia -> simplify to FRC",
            "inputs": {
                "country": "TR",
                "hba1c": 7.8,
                "bmi": 32,
                "on_basal_bolus": True,
                "recurrent_hypoglycemia": True
            }
        },
        {
            "label": "LB | basal insulin + PPG uncontrolled -> FRC",
            "inputs": {
                "country": "LB",
                "hba1c": 7.1,
                "hba1c_target": 7.0,
                "bmi": 29,
                "on_basal_insulin": True,
                "ppg_uncontrolled": True
            }
        },
        {
            "label": "IQ | first injectable, gap <2, BMI <=30 -> basal",
            "inputs": {
                "country": "IQ",
                "hba1c": 7.8,
                "hba1c_target": 7.0,
                "bmi": 28
            }
        },
        {
            "label": "TR | first injectable, gap <2, BMI >30 -> FRC + reimbursement note",
            "inputs": {
                "country": "TR",
                "hba1c": 8.2,
                "hba1c_target": 7.0,
                "bmi": 32
            }
        },
        {
            "label": "LB | first injectable, gap >=2 -> FRC",
            "inputs": {
                "country": "LB",
                "hba1c": 9.4,
                "hba1c_target": 7.0,
                "bmi": 27
            }
        },
        {
            "label": "IQ | no target provided, default target 7.0, gap >=2 -> FRC",
            "inputs": {
                "country": "IQ",
                "hba1c": 9.1,
                "bmi": 33
            }
        },
        {
            "label": "TR | no target, BMI unknown, default target 7.0 -> FRC because gap >=2",
            "inputs": {
                "country": "TR",
                "hba1c": 8.1
            }
        },
        {
            "label": "TR | no HbA1c, BMI unknown -> basal fallback",
            "inputs": {
                "country": "TR"
            }
        },
    ]

    sep = "─" * 72
    for tc in TEST_CASES:
        result = recommend(tc["inputs"])
        print(sep)
        print(f"TEST        : {tc['label']}")
        print(f"Therapy     : {result['therapy']}")
        print(f"Why         : {result['why']}")
        print(f"Next steps  : {result['next_steps']}")
        if result.get("comments"):
            print(f"Comments    : {result['comments']}")
    print(sep)
