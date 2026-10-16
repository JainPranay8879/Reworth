"""Unit tests for the rule-based recommendation engine (TC-01 to TC-05)."""
from conftest import GOOD


def run(app_module, **over):
    data = {**GOOD, **over}
    data["age"] = int(data["age"])
    for k in ("repair_cost", "replacement_cost"):
        data[k] = None if data[k] in ("", None) else float(data[k])
    data.setdefault("problem_description", "")
    data.setdefault("incident", "")
    data.setdefault("missing_parts", "")
    return app_module.calculate_recommendation(data)


def test_tc01_good_product_cheap_repair(app_module):
    r = run(app_module)
    assert r["decision"] in {"Repair", "Reuse"}
    assert r["reason"]


def test_tc02_blank_costs_do_not_invent_prices(app_module):
    r = run(app_module, repair_cost="", replacement_cost="")
    assert r["components"]["economics"] == 0


def test_tc03_dead_laptop_unknown_fault_needs_diagnosis(app_module):
    r = run(app_module, category="Computer / Laptop", functional_condition="Does not work",
            problem_type="Not sure", repair_cost="", replacement_cost="", condition="Poor")
    assert r["decision"] == "Diagnosis Required"
    assert r["confidence"] == "Low"


def test_tc04_repair_close_to_replacement_is_not_repair(app_module):
    r = run(app_module, repair_cost="14000", replacement_cost="15000", condition="Fair")
    assert r["decision"] != "Repair"


def test_tc05_very_old_repeatedly_repaired_scores_lower(app_module):
    young = run(app_module)
    old = run(app_module, age="12", repair_history="Repaired multiple times", condition="Poor",
              functional_condition="Barely works", cosmetic_condition="Visible wear",
              problem_type="Battery / power issue")
    assert old["score"] < young["score"]
    assert old["decision"] in {"Recycle", "Replace", "Donate"}


def test_engine_is_deterministic(app_module):
    assert run(app_module) == run(app_module)
