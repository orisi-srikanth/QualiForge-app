"""
High-Performance Semantic Vector Store and RAG Retrieval System for QualityMind
Indexes all technical KB documents and historical NCRs with unified MVTec AD metadata.
Metadata filters: doc_type, part_number, machine, defect_type, defect_family, proxy_category, provenance.
Strictly frames matches as historical context, never as proven causation.
"""
import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class ManufacturingVectorStore:
    def __init__(self, storage_path: Optional[str] = None):
        self.kb_dir = Path(__file__).resolve().parent.parent.parent / "data" / "kb"
        self.ncrs_json = Path(__file__).resolve().parent.parent.parent / "data" / "historical_ncrs.json"
        self.storage_path = storage_path or str(Path(__file__).resolve().parent.parent.parent / "data" / "vector_kb.json")
        self.documents: List[Dict[str, Any]] = []
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 3), stop_words="english", lowercase=True)
        self.matrix = None
        self.rebuild_index()

    def rebuild_index(self):
        """Loads and indexes all documents from kb/ and historical_ncrs.json with rich metadata."""
        self.documents.clear()

        # 1. Ingest Markdown documents from data/kb
        if self.kb_dir.exists():
            for fname in sorted(os.listdir(self.kb_dir)):
                if fname.endswith(".md"):
                    fpath = self.kb_dir / fname
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            text = f.read()
                        doc = self._parse_markdown_doc(text, fname)
                        if doc:
                            self.documents.append(doc)
                    except Exception as e:
                        print(f"[VectorStore] Error parsing {fname}: {e}")

        # 2. Ingest structured Historical NCRs
        if self.ncrs_json.exists():
            try:
                with open(self.ncrs_json, "r", encoding="utf-8") as f:
                    ncrs = json.load(f)
                existing_ids = {d["id"] for d in self.documents}
                for ncr in ncrs:
                    rec_id = ncr.get("id")
                    if rec_id and rec_id not in existing_ids:
                        self.documents.append({
                            "id": rec_id,
                            "type": "Historical NCR",
                            "doc_type": "ncr",
                            "title": ncr.get("title", f"Nonconformance {rec_id}"),
                            "defect_type": ncr.get("defect_type", ""),
                            "defect_family": ncr.get("defect_family", ""),
                            "proxy_category": ncr.get("proxy_category", "none"),
                            "part_number": ncr.get("part_number", ""),
                            "machine": ncr.get("machine", ""),
                            "material": ncr.get("material", "Carbon Steel"),
                            "description": ncr.get("description", ""),
                            "confirmed_root_cause": ncr.get("confirmed_root_cause", ""),
                            "action_taken": ncr.get("resolution", ncr.get("corrective_action", "")),
                            "verification_method": "Quality engineering sign-off",
                            "provenance": ncr.get("data_provenance", "synthetic_illustrative"),
                            "source_file": "historical_ncrs.json"
                        })
            except Exception as e:
                print(f"[VectorStore] Error loading historical_ncrs.json: {e}")

        self._save()
        self._build_matrix()

    def _parse_markdown_doc(self, text: str, fname: str) -> Optional[Dict[str, Any]]:
        # Extract title
        title_m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = title_m.group(1).strip() if title_m else fname

        # Extract fields
        rec_id = fname.replace(".md", "")
        if "NCR-" in fname:
            rec_id_m = re.search(r"NCR-\d+", fname)
            if rec_id_m: rec_id = rec_id_m.group(0)

        doc_type = "sop" if "SOP" in fname else ("spec" if "SPEC" in fname else ("manual" if "MANUAL" in fname else ("reference" if "REF" in fname else "ncr")))
        type_label = "Historical NCR" if doc_type == "ncr" else ("Standard Operating Procedure" if doc_type == "sop" else ("Specification" if doc_type == "spec" else "Reference Standard"))

        def get_meta(pattern: str, default: str = "") -> str:
            m = re.search(pattern, text, re.IGNORECASE)
            return m.group(1).strip() if m else default

        part_no = get_meta(r"-\s+\*\*Part Number:\*\*\s*(.+)")
        machine = get_meta(r"-\s+\*\*Machine:\*\*\s*(.+)")
        defect_type = get_meta(r"-\s+\*\*Defect Classification:\*\*\s*(.+)")
        defect_family = get_meta(r"-\s+\*\*Defect Family:\*\*\s*(.+)")
        proxy_cat = get_meta(r"-\s+\*\*Proxy Category:\*\*\s*(.+)", "none")
        provenance = get_meta(r"-\s+\*\*Data Provenance:\*\*\s*(.+)", "public_reference" if doc_type == "reference" else "synthetic_illustrative")
        desc = get_meta(r"-\s+\*\*Incident Description:\*\*\s*(.+)")
        root_cause = get_meta(r"-\s+\*\*Confirmed Root Cause:\*\*\s*(.+)")
        resolution = get_meta(r"-\s+\*\*Corrective Resolution:\*\*\s*(.+)")

        if not desc:
            desc = text[:400].replace("\n", " ")

        return {
            "id": rec_id,
            "type": type_label,
            "doc_type": doc_type,
            "title": title,
            "defect_type": defect_type,
            "defect_family": defect_family,
            "proxy_category": proxy_cat,
            "part_number": part_no,
            "machine": machine,
            "material": "Carbon Steel" if "PS-" in part_no else "Standard Spec",
            "description": desc,
            "confirmed_root_cause": root_cause,
            "action_taken": resolution,
            "verification_method": "Engineering inspection protocol",
            "provenance": provenance,
            "source_file": fname
        }

    def _save(self):
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, indent=2)
        except Exception:
            pass

    def _build_matrix(self):
        corpus = [
            f"{d['title']} {d.get('defect_type', '')} {d.get('defect_family', '')} {d.get('proxy_category', '')} {d.get('description', '')} {d.get('confirmed_root_cause', '')} {d.get('machine', '')} {d.get('part_number', '')}"
            for d in self.documents
        ]
        if corpus:
            self.matrix = self.vectorizer.fit_transform(corpus)

    def search(
        self,
        query: str,
        top_k: int = 3,
        defect_type: Optional[str] = None,
        proxy_category: Optional[str] = None,
        doc_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic RAG retrieval with defect_type boosting and context-only framing.
        """
        if not self.documents or self.matrix is None:
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.matrix)[0]

        # Apply boosting for matching defect_type or proxy_category
        boosted_scores = []
        for idx, doc in enumerate(self.documents):
            score = float(similarities[idx])
            if defect_type and doc.get("defect_type"):
                dt_clean = defect_type.lower().replace("_", " ")
                doc_dt_clean = doc.get("defect_type", "").lower().replace("_", " ")
                if dt_clean in doc_dt_clean or doc_dt_clean in dt_clean:
                    score *= 1.60

            if proxy_category and doc.get("proxy_category"):
                if proxy_category.lower() == doc.get("proxy_category", "").lower():
                    score *= 1.30

            if doc_type and doc.get("doc_type") != doc_type:
                score *= 0.50

            boosted_scores.append((score, idx))

        boosted_scores.sort(key=lambda x: x[0], reverse=True)
        results = []

        for score, idx in boosted_scores:
            doc = self.documents[idx]
            if score > 0.05:
                doc_copy = dict(doc)
                doc_copy["incident_id"] = doc.get("id")
                doc_copy["similarity_score"] = round(min(0.99, score), 3)
                doc_copy["context_notice"] = "Historical context only. Historical similarity does not establish the same root cause."
                doc_copy["data_provenance"] = doc.get("provenance", "synthetic_illustrative")
                results.append(doc_copy)
            if len(results) >= top_k:
                break

        return results

    def add_document(self, doc: Dict[str, Any]):
        self.documents.append(doc)
        self._save()
        self._build_matrix()

# Global singleton
vector_store = ManufacturingVectorStore()
