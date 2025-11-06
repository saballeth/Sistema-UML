import json
from typing import Dict, List, Optional
import uuid
import os

class DiagramCRUD:
    def __init__(self, diagram_data: Dict, storage_path: Optional[str] = None):
        self.diagram = diagram_data
        self.storage_path = storage_path
        # garantizar estructura mínima
        if "classes" not in self.diagram:
            self.diagram["classes"] = []

    def generate_id(self) -> str:
        return str(uuid.uuid4())

    def create_class(self, class_name: str, attributes: List = None) -> Dict:
        if attributes is None:
            attributes = []
        new_class = {
            "id": self.generate_id(),
            "name": class_name,
            "attributes": attributes,
            "methods": [],
            "relationships": []
        }
        self.diagram["classes"].append(new_class)
        self._persist()
        return new_class

    def find_class_by_name(self, class_name: str) -> Optional[Dict]:
        return next(
            (cls for cls in self.diagram["classes"]
             if cls["name"].lower() == class_name.lower()),
            None
        )

    def find_class_by_id(self, class_id: str) -> Optional[Dict]:
        return next((cls for cls in self.diagram["classes"] if cls.get("id") == class_id), None)

    def list_classes(self) -> List[Dict]:
        return self.diagram.get("classes", [])

    def update_class(self, class_id: str, new_data: Dict) -> Optional[Dict]:
        cls = self.find_class_by_id(class_id)
        if not cls:
            return None
        cls.update({k: v for k, v in new_data.items() if k in ["name", "attributes", "methods", "relationships"]})
        self._persist()
        return cls

    def delete_class(self, class_id: str) -> bool:
        cls = self.find_class_by_id(class_id)
        if not cls:
            return False
        self.diagram["classes"] = [c for c in self.diagram["classes"] if c.get("id") != class_id]
        self._persist()
        return True

    # attribute/method helpers
    def add_attribute(self, class_id: str, attribute: Dict) -> Optional[Dict]:
        cls = self.find_class_by_id(class_id)
        if not cls:
            return None
        cls.setdefault("attributes", []).append(attribute)
        self._persist()
        return attribute

    def remove_attribute(self, class_id: str, attr_name: str) -> bool:
        cls = self.find_class_by_id(class_id)
        if not cls:
            return False
        before = len(cls.get("attributes", []))
        cls["attributes"] = [a for a in cls.get("attributes", []) if a.get("name") != attr_name]
        self._persist()
        return len(cls.get("attributes", [])) < before

    def add_method(self, class_id: str, method: Dict) -> Optional[Dict]:
        cls = self.find_class_by_id(class_id)
        if not cls:
            return None
        cls.setdefault("methods", []).append(method)
        self._persist()
        return method

    def remove_method(self, class_id: str, method_name: str) -> bool:
        cls = self.find_class_by_id(class_id)
        if not cls:
            return False
        before = len(cls.get("methods", []))
        cls["methods"] = [m for m in cls.get("methods", []) if m.get("name") != method_name]
        self._persist()
        return len(cls.get("methods", [])) < before

    # Persistencia simple: guardar JSON en archivo si storage_path fue dado
    def _persist(self):
        if not self.storage_path:
            return
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.diagram, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @classmethod
    def load_from_file(cls, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data, storage_path=path)