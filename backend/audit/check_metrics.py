import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR) if os.path.basename(SCRIPT_DIR) == "audit" else SCRIPT_DIR

metrics_candidates = [
    os.path.join(BACKEND_DIR, "models", "metrics.json"),
    os.path.join("backend", "models", "metrics.json"),
    os.path.join("models", "metrics.json"),
]
metrics_file = next((p for p in metrics_candidates if os.path.exists(p)), metrics_candidates[0])

m = json.load(open(metrics_file))
for key in ["best_short_term", "best_long_term"]:
    name = m[key]["name"]
    if name in m["models"] and "feature_importance" in m["models"][name]:
        fi = m["models"][name]["feature_importance"]
        print(f"\n{name}:")
        for f, v in sorted(fi.items(), key=lambda x: -x[1]):
            print(f"  {f:<20} {v:>6.1f}%")
    else:
        print(f"\n{name}: no feature importance")
print(f"\nSample week entries: {len(m['sample_test_week'])}")
print(f"Test period: {m['test_period']}")
