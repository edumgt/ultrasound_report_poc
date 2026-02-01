from __future__ import annotations
from typing import Dict, List, Optional

class Structurer:
    def __init__(self, categories: Dict[str, List[str]], key_to_canonical: Optional[Dict[str, str]] = None):
        self.categories = categories
        self.key_to_canonical = key_to_canonical or {}

    def extract(self, corrected_text: str) -> Dict:
        out = {"location": None, "lesion": None, "feature": None, "notes": ""}
        for key in self.categories.get("location", []):
            canon = self.key_to_canonical.get(key, key)
            if canon in corrected_text:
                out["location"] = canon
        for key in self.categories.get("lesion", []):
            canon = self.key_to_canonical.get(key, key)
            if canon in corrected_text:
                out["lesion"] = canon
        for key in self.categories.get("feature", []):
            canon = self.key_to_canonical.get(key, key)
            if canon in corrected_text:
                out["feature"] = canon
        out["notes"] = "Auto-extracted (PoC)"
        return out
