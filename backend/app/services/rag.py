import os
import re
import json
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.app.core.guardrails import EpistemicLabel

class HybridRAGService:

    def __init__(self, kb_dir: Optional[str] = None):
        self.kb_dir = kb_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "kb")
        )
        self.chunks: List[Dict[str, Any]] = []
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 3), stop_words="english", lowercase=True)
        self.matrix = None
        self._load_and_index_documents()

    def _load_and_index_documents(self):
        self.chunks.clear()

        if os.path.exists(self.kb_dir):
            for fname in os.listdir(self.kb_dir):
                if fname.endswith(".md"):
                    fpath = os.path.join(self.kb_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            text = f.read()
                        self._chunk_and_add(text, source_file=fname)
                    except Exception:
                        pass

        base_dir = os.path.dirname(self.kb_dir)
        ncr_json = os.path.join(base_dir, "historical_ncrs.json")
        if os.path.exists(ncr_json):
            try:
                with open(ncr_json, "r", encoding="utf-8") as f:
                    ncrs = json.load(f)
                for ncr in ncrs:
                    full_text = (
                        f"Nonconformance Record {ncr['id']}: {ncr['title']}. "
                        f"Part: {ncr.get('part_number', '')}, Machine: {ncr.get('machine', '')}. "
                        f"Defect: {ncr.get('defect_type', '')}. "
                        f"Description: {ncr.get('description', '')}. "
                        f"Confirmed Root Cause: {ncr.get('confirmed_root_cause', '')}. "
                        f"Resolution: {ncr.get('resolution', '')}."
                    )
                    self.chunks.append({
                        "id": ncr["id"],
                        "title": ncr["title"],
                        "source_file": "historical_ncrs.json",
                        "doc_type": "ncr",
                        "part_number": ncr.get("part_number", ""),
                        "machine": ncr.get("machine", ""),
                        "defect_type": ncr.get("defect_type", ""),
                        "confirmed_root_cause": ncr.get("confirmed_root_cause", ""),
                        "text": full_text
                    })
            except Exception:
                pass

        if self.chunks:
            corpus = [c["text"] for c in self.chunks]
            self.matrix = self.vectorizer.fit_transform(corpus)

    def _chunk_and_add(self, text: str, source_file: str):
        doc_type = "sop" if "SOP" in source_file else ("spec" if "SPEC" in source_file else ("manual" if "MANUAL" in source_file else "ncr"))

        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else source_file

        paragraphs = text.split("\n\n")
        chunk_buf = []
        current_len = 0

        for p in paragraphs:
            p_strip = p.strip()
            if not p_strip:
                continue
            words = p_strip.split()
            if current_len + len(words) > 350 and chunk_buf:
                chunk_text = "\n\n".join(chunk_buf)
                self.chunks.append({
                    "id": f"{source_file}#{len(self.chunks)+1}",
                    "title": title,
                    "source_file": source_file,
                    "doc_type": doc_type,
                    "part_number": "PS-2026-101" if "PS-101" in source_file else "",
                    "machine": "CNC-04" if "Okuma" in source_file or "CNC-04" in source_file else "",
                    "defect_type": "",
                    "confirmed_root_cause": "",
                    "text": chunk_text
                })
                chunk_buf = [p_strip]
                current_len = len(words)
            else:
                chunk_buf.append(p_strip)
                current_len += len(words)

        if chunk_buf:
            chunk_text = "\n\n".join(chunk_buf)
            self.chunks.append({
                "id": f"{source_file}#{len(self.chunks)+1}",
                "title": title,
                "source_file": source_file,
                "doc_type": doc_type,
                "part_number": "PS-2026-101" if "PS-101" in source_file else "",
                "machine": "CNC-04" if "Okuma" in source_file or "CNC-04" in source_file else "",
                "defect_type": "",
                "confirmed_root_cause": "",
                "text": chunk_text
            })

    def search(
        self,
        query: str,
        top_k: int = 3,
        metadata_filters: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        if not self.chunks:
            return []

        from backend.app.core.llm import universal_llm
        hosted_scores = None
        if hasattr(self, "_chunk_embeddings") and self._chunk_embeddings:
            q_emb = universal_llm.embed_text(query)
            if q_emb:
                q_arr = np.array(q_emb)
                hosted_scores = np.dot(self._chunk_embeddings, q_arr) / (
                    np.linalg.norm(self._chunk_embeddings, axis=1) * np.linalg.norm(q_arr) + 1e-9
                )

        if hosted_scores is not None:
            scores = hosted_scores
        elif self.matrix is not None:
            query_vec = self.vectorizer.transform([query])
            scores = cosine_similarity(query_vec, self.matrix).flatten()
        else:
            return []

        ranked_indices = np.argsort(scores)[::-1]
        results = []

        for idx in ranked_indices:
            score = float(scores[idx])
            chunk = self.chunks[idx]

            if metadata_filters:
                match = True
                for k, v in metadata_filters.items():
                    if k in chunk and chunk[k] and chunk[k].lower() != v.lower():
                        match = False
                        break
                if not match:
                    continue

            snippet = chunk["text"][:300] + ("..." if len(chunk["text"]) > 300 else "")

            results.append({
                "id": chunk["id"],
                "title": chunk["title"],
                "source_document": chunk["source_file"],
                "doc_type": chunk.get("doc_type", "kb"),
                "similarity_score": round(score, 3),
                "confirmed_root_cause": chunk.get("confirmed_root_cause", ""),
                "snippet": snippet,
                "context_notice": (
                    f"Historical context only (Cosine Similarity: {score:.3f}). "
                    f"Does NOT prove or establish causation for current production batch."
                ),
                "label": EpistemicLabel.STATISTICAL_FINDING.value
            })

            if len(results) >= top_k:
                break

        return results

rag_service = HybridRAGService()
