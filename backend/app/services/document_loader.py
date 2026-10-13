"""
Document Loader & Record Extraction Service
Extracts and chunks manufacturing records from CSV, PDF, Markdown, and JSON files
for RAG indexing in ChromaDB, preserving complete tabular rows as unified chunks.
"""
import os
import re
import csv
import json
from typing import List, Dict, Any, Tuple, Optional
import pymupdf


def infer_document_category(fname: str, row_dict: Optional[dict] = None) -> str:
    """Determines semantic category based on filename or contents."""
    name_lower = fname.lower()
    if "ncr" in name_lower:
        return "previous_ncr"
    elif "capa" in name_lower:
        return "capa_record"
    elif "maint" in name_lower:
        return "maintenance_record"
    elif "spec" in name_lower:
        return "specification"
    elif "inspect" in name_lower:
        return "inspection_procedure"
    elif "sop" in name_lower:
        return "manufacturing_sop"
    elif "manual" in name_lower or "guide" in name_lower:
        return "machine_manual"
    elif "standard" in name_lower or "nist" in name_lower or "handbook" in name_lower:
        return "quality_standard"

    if row_dict:
        if "defect_type" in row_dict or "root_cause" in str(row_dict):
            return "previous_ncr"
        if "nominal_mm" in row_dict or "usl" in str(row_dict):
            return "specification"
        if "technician" in row_dict or "maintenance_type" in row_dict:
            return "maintenance_record"

    return "quality_standard"


def extract_records_from_file(fpath: str, ext: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses a source file and extracts records with source metadata.
    Preserves entire CSV rows as single cohesive records.
    """
    fname = os.path.basename(fpath)
    records: List[Dict[str, Any]] = []
    warnings: List[str] = []

    if ext == ".csv":
        try:
            with open(fpath, "r", encoding="utf-8-sig", errors="replace") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    warnings.append(f"CSV file '{fname}' is empty or missing headers.")
                    return [], warnings

                for idx, row in enumerate(reader):
                    if not any(row.values()):
                        continue  # Skip blank row

                    rec_id = row.get("record_id") or row.get("id") or row.get("ncr_id") or f"ROW-{idx+1:03d}"
                    part_no = row.get("part_number") or ""
                    mach_id = row.get("machine_id") or row.get("machine") or ""
                    batch_id = row.get("batch_id") or ""
                    category = infer_document_category(fname, row)
                    doc_type = row.get("doc_type") or ("ncr" if "ncr" in fname.lower() else "csv")
                    defect_type = row.get("defect_type") or ""
                    defect_family = row.get("defect_family") or ""
                    proxy_cat = row.get("proxy_category") or "none"
                    prov = row.get("data_provenance") or row.get("provenance") or "synthetic_illustrative"

                    # Build complete self-contained narrative text for row
                    row_items = [f"{k}: {v}" for k, v in row.items() if v is not None and str(v).strip()]
                    record_text = f"[{category.upper()} RECORD {rec_id}] From file: {fname}\n" + "\n".join(row_items)

                    records.append({
                        "id": f"{fname}::{rec_id}::0",
                        "text": record_text,
                        "metadata": {
                            "source": fpath,
                            "file_name": fname,
                            "file_type": "csv",
                            "category": category,
                            "document_type": category,
                            "doc_type": doc_type,
                            "record_id": str(rec_id),
                            "batch_id": str(batch_id),
                            "machine_id": str(mach_id),
                            "machine": str(mach_id),
                            "part_number": str(part_no),
                            "defect_type": str(defect_type),
                            "defect_family": str(defect_family),
                            "proxy_category": str(proxy_cat),
                            "provenance": str(prov),
                            "record_index": idx,
                            "chunk_index": 0
                        }
                    })
        except Exception as e:
            warnings.append(f"Error reading CSV '{fname}': {str(e)}")

    elif ext == ".pdf":
        try:
            doc = pymupdf.open(fpath)
            total_text_len = 0
            pdf_pages = []

            for p_idx, page in enumerate(doc):
                text = page.get_text().strip()
                total_text_len += len(text)
                if text:
                    pdf_pages.append((p_idx + 1, text))

            doc.close()

            if total_text_len < 20:
                warnings.append(
                    f"Warning: PDF '{fname}' contains little or no extractable text ({total_text_len} chars). "
                    "OCR is required for scanned documents."
                )
                return [], warnings

            category = infer_document_category(fname)
            for page_num, ptext in pdf_pages:
                records.append({
                    "id": f"{fname}::page_{page_num}::0",
                    "text": f"[{category.upper()} - {fname}] Page {page_num}\n{ptext}",
                    "metadata": {
                        "source": fpath,
                        "file_name": fname,
                        "file_type": "pdf",
                        "category": category,
                        "document_type": category,
                        "doc_type": "pdf",
                        "record_id": f"{fname}#p{page_num}",
                        "part_number": "",
                        "machine": "",
                        "defect_type": "",
                        "defect_family": "",
                        "proxy_category": "none",
                        "provenance": "synthetic_illustrative",
                        "record_index": page_num - 1,
                        "chunk_index": 0
                    }
                })
        except Exception as e:
            warnings.append(f"Error reading PDF '{fname}': {str(e)}")

    elif ext in [".md", ".txt"]:
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
            if not content:
                warnings.append(f"File '{fname}' is empty.")
                return [], warnings

            category = infer_document_category(fname)
            paragraphs = re.split(r"\n\s*\n", content)
            current_chunks = []
            cur_text = []
            cur_len = 0

            doc_type = "sop" if "SOP" in fname else ("spec" if "SPEC" in fname else ("manual" if "MANUAL" in fname else ("reference" if "REF" in fname else "ncr")))

            def get_m(pattern: str, default: str = "") -> str:
                m = re.search(pattern, content, re.IGNORECASE)
                return m.group(1).strip() if m else default

            part_no = get_m(r"-\s+\*\*Part Number:\*\*\s*(.+)")
            mach_id = get_m(r"-\s+\*\*Machine:\*\*\s*(.+)")
            defect_type = get_m(r"-\s+\*\*Defect Classification:\*\*\s*(.+)")
            defect_family = get_m(r"-\s+\*\*Defect Family:\*\*\s*(.+)")
            proxy_cat = get_m(r"-\s+\*\*Proxy Category:\*\*\s*(.+)", "none")
            prov = get_m(r"-\s+\*\*Data Provenance:\*\*\s*(.+)", "public_reference" if doc_type == "reference" else "synthetic_illustrative")

            for para in paragraphs:
                words = para.strip().split()
                if not words:
                    continue
                if cur_len + len(words) > 350 and cur_text:
                    current_chunks.append("\n\n".join(cur_text))
                    cur_text = [para.strip()]
                    cur_len = len(words)
                else:
                    cur_text.append(para.strip())
                    cur_len += len(words)

            if cur_text:
                current_chunks.append("\n\n".join(cur_text))

            for c_idx, c_body in enumerate(current_chunks):
                records.append({
                    "id": f"{fname}::chunk_{c_idx}::{c_idx}",
                    "text": f"[{category.upper()} - {fname}] (Part {c_idx+1})\n{c_body}",
                    "metadata": {
                        "source": fpath,
                        "file_name": fname,
                        "file_type": ext.replace(".", ""),
                        "category": category,
                        "document_type": category,
                        "doc_type": doc_type,
                        "record_id": f"{fname}#c{c_idx+1}",
                        "part_number": part_no,
                        "machine_id": mach_id,
                        "machine": mach_id,
                        "defect_type": defect_type,
                        "defect_family": defect_family,
                        "proxy_category": proxy_cat,
                        "provenance": prov,
                        "record_index": 0,
                        "chunk_index": c_idx
                    }
                })
        except Exception as e:
            warnings.append(f"Error reading text/markdown '{fname}': {str(e)}")

    elif ext == ".json":
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)

            items = data if isinstance(data, list) else [data]
            category = infer_document_category(fname)

            for idx, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                rec_id = item.get("id") or item.get("record_id") or f"ITEM-{idx+1:03d}"
                part_no = item.get("part_number") or ""
                mach_id = item.get("machine") or item.get("machine_id") or ""
                batch_id = item.get("batch_id") or ""
                doc_type = item.get("doc_type") or ("ncr" if "ncr" in fname.lower() else "json")
                defect_type = item.get("defect_type") or ""
                defect_family = item.get("defect_family") or ""
                proxy_cat = item.get("proxy_category") or "none"
                prov = item.get("data_provenance") or item.get("provenance") or "synthetic_illustrative"

                item_str = [f"{k}: {v}" for k, v in item.items() if v is not None and str(v).strip()]
                record_text = f"[{category.upper()} JSON RECORD {rec_id}] From file: {fname}\n" + "\n".join(item_str)

                records.append({
                    "id": f"{fname}::{rec_id}::0",
                    "text": record_text,
                    "metadata": {
                        "source": fpath,
                        "file_name": fname,
                        "file_type": "json",
                        "category": category,
                        "document_type": category,
                        "doc_type": doc_type,
                        "record_id": str(rec_id),
                        "batch_id": str(batch_id),
                        "machine_id": str(mach_id),
                        "machine": str(mach_id),
                        "part_number": str(part_no),
                        "defect_type": str(defect_type),
                        "defect_family": str(defect_family),
                        "proxy_category": str(proxy_cat),
                        "provenance": str(prov),
                        "record_index": idx,
                        "chunk_index": 0
                    }
                })
        except Exception as e:
            warnings.append(f"Error reading JSON '{fname}': {str(e)}")

    else:
        warnings.append(f"Skipping unsupported file format '{ext}' for file '{fname}'.")

    return records, warnings
