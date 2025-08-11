"""
chunk_gaap_taxonomy.py
----------------------
Reads a GAAP taxonomy Excel (e.g., "GAAP Taxonomy 2024.xlsx") and produces
concept-centric chunks (Core + Relations) as JSONL files for later indexing.

Now with progress bars and live stats.

Output layout (by default under ./gaap_chunks):
- gaap_chunks/
  - meta.json             # metadata of the run
  - chunks_core.jsonl     # one JSON per line; concept core chunks
  - chunks_relations.jsonl# one JSON per line; concept relation chunks

Usage:
  python chunk_gaap_taxonomy.py \
      --excel "/path/to/GAAP Taxonomy 2024.xlsx" \
      --out_dir "./gaap_chunks" \
      [--quiet] [--every 200]

Dependencies:
  pip install pandas openpyxl tqdm
"""
import argparse
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple

import pandas as pd
from tqdm.auto import tqdm

def norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r"\s+", "", str(c).lower()) for c in df.columns]
    return df

def load_excel(excel_path: Path) -> Dict[str, pd.DataFrame]:
    sheets = pd.read_excel(excel_path, sheet_name=None, dtype=str)
    cleaned = {}
    for name, df in sheets.items():
        df = df.fillna("")
        df = norm_cols(df)
        cleaned[name.lower()] = df
    return cleaned

def find_sheet(sheets: Dict[str, pd.DataFrame], candidates: List[str]) -> List[Tuple[str, pd.DataFrame]]:
    out = []
    for nm, df in sheets.items():
        for c in candidates:
            if c in nm:
                out.append((nm, df))
                break
    return out

def concept_id(prefix: str, name: str) -> str:
    prefix = (prefix or "").strip()
    name = (name or "").strip()
    return f"{prefix}:{name}" if prefix and name else name

def coalesce(*vals, default=""):
    for v in vals:
        if v is not None and str(v).strip() != "":
            return str(v)
    return default

def row_idx_for_debug(i: int) -> int:
    return i + 2

def build_core_text(c: Dict[str, Any]) -> str:
    lines = [
        "[Concept Core]",
        f"ID: {c['concept_id']}",
        f"Label: {c.get('label','')}",
        f"Type: {c.get('type','')} | Balance: {c.get('balance','')} | PeriodType: {c.get('periodtype','')} | Abstract: {c.get('abstract','')}",
        f"Status: {c.get('status','')} | DeprecatedLabel: {c.get('deprecatedlabel','')} | DeprecatedDate: {c.get('deprecateddate','')}",
        "Documentation:",
        c.get("documentation","").strip() or "(none)",
        "",
        f"Provenance: file={c.get('file_name','')} | sheet=Concepts | row={c.get('row', '?')}",
    ]
    return "\n".join(lines)

def build_relations_text(concept: str,
                         presentation: List[Dict[str, Any]],
                         calculation: List[Dict[str, Any]],
                         definition: List[Dict[str, Any]],
                         references: List[Dict[str, Any]],
                         enums: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
    chunks: List[Tuple[str, str]] = []

    if presentation:
        body = [ "[Concept Relations]", f"ID: {concept}", "", "Presentation:" ]
        for r in presentation[:2000]:
            role = r.get("role","")
            path = r.get("path","")
            pref = r.get("preferredlabel","")
            body.append(f"- Role: {role}\n  Path: {path}\n  PreferredLabel: {pref}")
        body.append("Provenance: sheets include Presentation-like sheets")
        chunks.append(("relations:pres", "\n".join(body)))

    if calculation:
        body = [ "[Concept Relations]", f"ID: {concept}", "", "Calculation:" ]
        parents = [r for r in calculation if r.get("direction") == "as_child"]
        children = [r for r in calculation if r.get("direction") == "as_parent"]
        if children:
            body.append("- As Parent:")
            for r in children[:2000]:
                body.append(f"  child={r.get('to','')} | weight={r.get('weight','')} | role={r.get('role','')}")
        if parents:
            body.append("- As Child:")
            for r in parents[:2000]:
                body.append(f"  parent={r.get('from','')} | weight={r.get('weight','')} | role={r.get('role','')}")
        body.append("Provenance: sheets include Calculation-like sheets")
        chunks.append(("relations:calc", "\n".join(body)))

    if definition:
        body = [ "[Concept Relations]", f"ID: {concept}", "", "Definition (Dimensions/Domain/Hypercube):" ]
        for r in definition[:2000]:
            arcrole = r.get("arcrole","")
            frm = r.get("from","")
            to = r.get("to","")
            role = r.get("role","")
            body.append(f"- {arcrole}: from={frm} -> to={to} (role={role})")
        body.append("Provenance: sheets include Definition-like sheets")
        chunks.append(("relations:def", "\n".join(body)))

    if references:
        body = [ "[Concept Relations]", f"ID: {concept}", "", "References:" ]
        for r in references[:2000]:
            source = r.get("source","")
            section = r.get("section","")
            note = r.get("note","")
            body.append(f"- {source} | {section} | {note}")
        body.append("Provenance: sheets include Reference-like sheets")
        chunks.append(("relations:ref", "\n".join(body)))

    if enums:
        body = [ "[Concept Relations]", f"ID: {concept}", "", "Extensible Enumerations:" ]
        for r in enums[:2000]:
            domain = r.get("domain","")
            members = ", ".join(r.get("members", []))
            lr = r.get("linkrole","")
            body.append(f"- Domain: {domain} | Members: [{members}] | linkrole={lr}")
        body.append("Provenance: sheets include Enumeration-like sheets")
        chunks.append(("relations:enum", "\n".join(body)))

    return chunks

def extract_presentation_rows(dfs: List[Tuple[str, pd.DataFrame]], cid: str, label_lookup: Dict[str, str]) -> List[Dict[str, Any]]:
    out = []
    for name, df in dfs:
        for _, r in df.iterrows():
            role = coalesce(r.get("role"), r.get("linkrole"))
            preferred = coalesce(r.get("preferredlabel"))
            from_id = concept_id(coalesce(r.get("fromprefix"), r.get("fromnamespace")), coalesce(r.get("fromname"), r.get("from")))
            to_id = concept_id(coalesce(r.get("toprefix"), r.get("tonamespace")), coalesce(r.get("toname"), r.get("to")))
            if from_id == cid or to_id == cid:
                parent = from_id if to_id == cid else (from_id if from_id and to_id else "")
                child  = to_id if to_id == cid else (to_id if from_id and to_id else "")
                if parent and child:
                    path = f"{label_lookup.get(parent, parent)} > {label_lookup.get(child, child)}"
                else:
                    path = label_lookup.get(cid, cid)
                out.append({"role": role, "preferredlabel": preferred, "path": path})
    return out

def extract_calculation_rows(dfs: List[Tuple[str, pd.DataFrame]], cid: str) -> List[Dict[str, Any]]:
    out = []
    for name, df in dfs:
        for _, r in df.iterrows():
            role = coalesce(r.get("role"), r.get("linkrole"))
            weight = coalesce(r.get("weight"))
            from_id = concept_id(coalesce(r.get("fromprefix"), r.get("fromnamespace")), coalesce(r.get("fromname"), r.get("from")))
            to_id = concept_id(coalesce(r.get("toprefix"), r.get("tonamespace")), coalesce(r.get("toname"), r.get("to")))
            if from_id == cid:
                out.append({"direction":"as_parent","from":from_id,"to":to_id,"weight":weight,"role":role})
            elif to_id == cid:
                out.append({"direction":"as_child","from":from_id,"to":to_id,"weight":weight,"role":role})
    return out

def extract_definition_rows(dfs: List[Tuple[str, pd.DataFrame]], cid: str) -> List[Dict[str, Any]]:
    out = []
    for name, df in dfs:
        for _, r in df.iterrows():
            role = coalesce(r.get("role"), r.get("linkrole"))
            arcrole = coalesce(r.get("arcrole"), r.get("arcroleuri"))
            from_id = concept_id(coalesce(r.get("fromprefix"), r.get("fromnamespace")), coalesce(r.get("fromname"), r.get("from")))
            to_id = concept_id(coalesce(r.get("toprefix"), r.get("tonamespace")), coalesce(r.get("toname"), r.get("to")))
            if from_id == cid or to_id == cid:
                out.append({"arcrole":arcrole,"from":from_id,"to":to_id,"role":role})
    return out

def extract_reference_rows(dfs: List[Tuple[str, pd.DataFrame]], cid: str) -> List[Dict[str, Any]]:
    out = []
    for name, df in dfs:
        for _, r in df.iterrows():
            target = coalesce(r.get("concept"), concept_id(coalesce(r.get("prefix")), coalesce(r.get("name"))))
            if target != cid:
                continue
            source = coalesce(r.get("source"), r.get("authority"), r.get("publisher"))
            section = coalesce(r.get("section"), r.get("chapter"), r.get("paragraph"), r.get("subsection"))
            note = coalesce(r.get("note"), r.get("text"), r.get("description"))
            out.append({"source":source,"section":section,"note":note})
    return out

def extract_enum_rows(dfs: List[Tuple[str, pd.DataFrame]], cid: str) -> List[Dict[str, Any]]:
    out = []
    for name, df in dfs:
        for _, r in df.iterrows():
            domain = coalesce(r.get("domain"), r.get("domaingroup"), r.get("enumdomain"), r.get("domainname"))
            linkrole = coalesce(r.get("role"), r.get("linkrole"))
            concept = concept_id(coalesce(r.get("prefix")), coalesce(r.get("name")))
            member = coalesce(r.get("member"), r.get("membername"), r.get("enumvalue"))
            if concept == cid or domain == cid:
                out.append({"domain":domain or concept, "members":[m.strip() for m in [member] if m], "linkrole":linkrole})
    # aggregate
    agg: Dict[str, Dict[str, Any]] = {}
    for r in out:
        key = (r.get("domain",""), r.get("linkrole",""))
        k = "|".join(key)
        if k not in agg:
            agg[k] = {"domain":r.get("domain",""), "members":[], "linkrole":r.get("linkrole","")}
        agg[k]["members"].extend(r.get("members",[]))
    return list(agg.values())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--excel", required=True, help="Path to GAAP taxonomy Excel")
    ap.add_argument("--out_dir", default="./gaap_chunks", help="Output directory for JSONL chunks")
    ap.add_argument("--quiet", action="store_true", help="Reduce console output")
    ap.add_argument("--every", type=int, default=200, help="Print a brief log every N concepts")
    args = ap.parse_args()

    t0 = time.time()
    excel_path = Path(args.excel)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.quiet:
        print(f"Loading workbook: {excel_path} ...")

    sheets = load_excel(excel_path)

    # concept sheet
    concept_candidates = [k for k in sheets.keys() if "concept" in k]
    if not concept_candidates:
        raise RuntimeError("No sheet with 'concept' in name was found.")
    concepts_df = sheets[concept_candidates[0]]

    # relation sheets
    pres_dfs = find_sheet(sheets, ["presentation"])
    calc_dfs = find_sheet(sheets, ["calculation"])
    def_dfs  = find_sheet(sheets, ["definition"])
    ref_dfs  = find_sheet(sheets, ["reference", "ref "])
    enum_dfs = find_sheet(sheets, ["enumeration", "enum"])

    # build concept records
    concepts = []
    label_lookup = {}
    for i, r in concepts_df.iterrows():
        prefix = coalesce(r.get("prefix"), r.get("namespaceprefix"), r.get("ns"))
        name = coalesce(r.get("name"), r.get("localname"), r.get("elementname"))
        if not name:
            continue
        cid = concept_id(prefix, name)
        c = {
            "concept_id": cid,
            "prefix": prefix,
            "name": name,
            "label": coalesce(r.get("label"), r.get("standardlabel"), r.get("preferredlabel")),
            "type": coalesce(r.get("type"), r.get("basetype"), r.get("datatype")),
            "balance": coalesce(r.get("balance")),
            "periodtype": coalesce(r.get("periodtype"), r.get("period")),
            "abstract": str(coalesce(r.get("abstract"), "false")).lower() in ["true","1","yes","y"],
            "documentation": coalesce(r.get("documentation"), r.get("definition"), r.get("description")),
            "status": coalesce(r.get("status")),
            "deprecatedlabel": coalesce(r.get("deprecatedlabel")),
            "deprecateddate": coalesce(r.get("deprecateddate")),
            "row": row_idx_for_debug(i),
            "file_name": excel_path.name
        }
        label_lookup[cid] = c.get("label") or c["concept_id"]
        concepts.append(c)

    if not args.quiet:
        print(f"Concepts detected: {len(concepts)}")
        print("Writing chunks ...")

    core_path = out_dir / "chunks_core.jsonl"
    rel_path  = out_dir / "chunks_relations.jsonl"

    n_core = n_rel = 0
    stats_rel = {"pres":0,"calc":0,"def":0,"ref":0,"enum":0}

    with core_path.open("w", encoding="utf-8") as f_core, rel_path.open("w", encoding="utf-8") as f_rel:
        for idx, c in enumerate(tqdm(concepts, desc="Concepts", unit="concept")):
            cid = c["concept_id"]
            # Core
            core_text = build_core_text(c)
            core_doc = {
                "chunk_text": core_text,
                "chunk_kind": "core",
                "doc": excel_path.name,
                "sheet": "Concepts",
                "concept_id": cid,
                "label": c.get("label",""),
                "type": c.get("type",""),
                "balance": c.get("balance",""),
                "periodType": c.get("periodtype",""),
                "abstract": bool(c.get("abstract", False)),
                "roles": [],
                "arcroles": [],
                "deprecated": bool(c.get("deprecatedlabel","") or c.get("deprecateddate","")),
                "taxonomy_version": "",
                "path": label_lookup.get(cid, cid),
                "provenance_row": c.get("row", None),
                "_id": f"{cid}::core"
            }
            f_core.write(json.dumps(core_doc, ensure_ascii=False) + "\n")
            n_core += 1

            # Relations
            pres = extract_presentation_rows(pres_dfs, cid, label_lookup) if pres_dfs else []
            calc = extract_calculation_rows(calc_dfs, cid) if calc_dfs else []
            defi = extract_definition_rows(def_dfs, cid) if def_dfs else []
            refs = extract_reference_rows(ref_dfs, cid) if ref_dfs else []
            enums = extract_enum_rows(enum_dfs, cid) if enum_dfs else []

            rel_chunks = build_relations_text(cid, pres, calc, defi, refs, enums)
            for kind, text in rel_chunks:
                body = {
                    "chunk_text": text,
                    "chunk_kind": kind,
                    "doc": excel_path.name,
                    "sheet": "relations",
                    "concept_id": cid,
                    "label": c.get("label",""),
                    "type": c.get("type",""),
                    "balance": c.get("balance",""),
                    "periodType": c.get("periodtype",""),
                    "abstract": bool(c.get("abstract", False)),
                    "roles": sorted(list({r.get("role","") for r in pres+calc if r.get('role')})),
                    "arcroles": sorted(list({r.get("arcrole","") for r in defi if r.get('arcrole')})),
                    "deprecated": bool(c.get("deprecatedlabel","") or c.get("deprecateddate","")),
                    "taxonomy_version": "",
                    "path": label_lookup.get(cid, cid),
                    "provenance_row": c.get("row", None),
                    "_id": f"{cid}::{kind}"
                }
                f_rel.write(json.dumps(body, ensure_ascii=False) + "\n")
                n_rel += 1
                if kind == "relations:pres": stats_rel["pres"] += 1
                elif kind == "relations:calc": stats_rel["calc"] += 1
                elif kind == "relations:def": stats_rel["def"] += 1
                elif kind == "relations:ref": stats_rel["ref"] += 1
                elif kind == "relations:enum": stats_rel["enum"] += 1

            if not args.quiet and args.every and (idx+1) % args.every == 0:
                print(f"[{idx+1}/{len(concepts)}] core={n_core}, rel={n_rel} (pres={stats_rel['pres']}, calc={stats_rel['calc']}, def={stats_rel['def']}, ref={stats_rel['ref']}, enum={stats_rel['enum']})")

    meta = {
        "excel": excel_path.as_posix(),
        "out_dir": out_dir.as_posix(),
        "core_file": core_path.name,
        "relations_file": rel_path.name,
        "num_core": n_core,
        "num_relations": n_rel,
        "relations_breakdown": stats_rel,
        "duration_sec": round(time.time() - t0, 2)
    }
    with (out_dir / "meta.json").open("w", encoding="utf-8") as f_meta:
        json.dump(meta, f_meta, ensure_ascii=False, indent=2)

    if not args.quiet:
        print("\n== Summary ==")
        print(json.dumps(meta, ensure_ascii=False, indent=2))

    print(f"Done. Core chunks: {n_core}, Relation chunks: {n_rel}. Output dir: {out_dir}")

if __name__ == "__main__":
    main()
