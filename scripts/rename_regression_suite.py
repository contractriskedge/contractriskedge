"""
Rename Regression Suite — standardizes all contract filenames.

Convention: {TYPE}_{NUMBER}_{Company}_{RiskLevel}.{ext}

Types: NDA, MSA, SOW, DPA, EMP, PUR, VEN, SaaS, LEASE, AMEND
RiskLevels: Gold, LowRisk, MediumRisk, HighRisk, Critical

Also copies the organized RegressionSuite to a top-level location
at SampleContracts/RegressionSuite/ for easy access.
"""

import os
import re
import shutil
import unicodedata

# ── Configuration ──────────────────────────────────────────────────────────

SOURCE_DIR = "/Volumes/ContractEdge/ContractRiskEdge/SampleContracts/Contrats E2E June 8/files/RegressionSuite"
TARGET_DIR = "/Volumes/ContractEdge/ContractRiskEdge/SampleContracts/RegressionSuite"

TYPE_MAP = {
    "NDA": "NDA",
    "MSA": "MSA",
    "SOW": "SOW",
    "DPA": "DPA",
    "EMP": "EMP",
    "PUR": "PUR",
    "VEN": "VEN",
    "Vendor": "VEN",
    "SaaS": "SaaS",
    "Lease": "LEASE",
    "Lea": "LEASE",
    "Amendment": "AMEND",
    "Amed": "AMEND",
    "Amend": "AMEND",
}

# Manual rename map for files that don't follow the pattern
MANUAL_RENAMES = {
    # NDA folder
    "EX-10.11.pdf": "NDA_001_Intuit_Gold.pdf",
    "rokit_ex102.pdf": "NDA_002_JPMorgan_HighRisk.pdf",
    "ea0214276-13da1axonic_power.htm.pdf": "NDA_003_AxonicPower_MediumRisk.pdf",
    "b317232px14a6g.pdf": "NDA_004_Generic_MediumRisk.pdf",
    "ex10-2.pdf": "NDA_005_Generic_LowRisk.pdf",
    "ex10-3.htm.pdf": "NDA_006_Generic_LowRisk.pdf",
    "ex14 (1).pdf": "NDA_007_Generic_LowRisk.pdf",
    "ex14.pdf": "NDA_008_Generic_LowRisk.pdf",
    "tm2532528-1_sctot_DIV_36-exd4 - none - 2.0735582s.pdf": "NDA_009_Generic_MediumRisk.pdf",
    "HE Code of Ethics (02099478).pdf": "NDA_010_HE_CodeOfEthics_LowRisk.pdf",
    "MSA Safety Incorporated.pdf": "NDA_011_SafetyInc_LowRisk.pdf",

    # MSA folder
    "Amherst Single Family.pdf": "MSA_001_Amherst_Gold.pdf",
    "SUNRISE AND TOWERCO.pdf": "MSA_002_SunriseTowerco_MediumRisk.pdf",

    # DPA folder
    "Form7Rcomplete.pdf": "DPA_004_Form7R_MediumRisk.pdf",
    "legalopino.pdf": "DPA_005_LegalOpinion_LowRisk.pdf",

    # Lease folder
    "dec21_audit_alkali_public5.pdf": "LEASE_005_AuditAlkali_MediumRisk.pdf",

    # Purchase folder
    "authenticitiformca.pdf": "PUR_007_Authenticiti_MediumRisk.pdf",
    "primary_doc.xml": None,  # Skip XML files

    # Employment folder
    "Sample-Regular-Employment-Contrac10-12.docx": "EMP_006_Sample_LowRisk.docx",
    "Sample-Regular-Employment-Contrac10-24.docx": "EMP_007_Sample_LowRisk.docx",
    "Sample-Regular-Employment-Contrac10-31.docx": "EMP_008_Sample_LowRisk.docx",
    "Sample-Regular-Employment-Contrac10-51.docx": "EMP_009_Sample_LowRisk.docx",
}

# ── Helpers ────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Convert to ASCII-safe, underscore-separated identifier."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "_", text)
    return text.strip("_")


def infer_risk_level(filename: str) -> str:
    """Infer risk level from filename keywords."""
    name = filename.lower()
    if "critical" in name or "high" in name:
        return "HighRisk"
    if "medium" in name:
        return "MediumRisk"
    if "low" in name or "gold" in name or "clean" in name:
        return "LowRisk"
    return "MediumRisk"  # default


def generate_new_name(folder_type: str, filename: str, index: int) -> str:
    """Generate a standardized name for a file."""
    ext = os.path.splitext(filename)[1]
    base = os.path.splitext(filename)[0]

    prefix = TYPE_MAP.get(folder_type, folder_type.upper())

    # Extract company name from existing pattern
    # Pattern: PREFIX_Company.ext or PREFIX_Company_Risk.ext
    parts = base.split("_")
    if len(parts) >= 2:
        company_part = "_".join(parts[1:])
        # Remove risk suffix if present
        company_part = re.sub(r"_(Gold|LowRisk|MediumRisk|HighRisk|Critical)$", "", company_part)
    else:
        company_part = base

    # Clean up company name
    company = slugify(company_part)
    if not company:
        company = f"Contract_{index:03d}"

    risk = infer_risk_level(filename)

    return f"{prefix}_{index:03d}_{company}_{risk}{ext}"


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(SOURCE_DIR):
        print(f"❌ Source directory not found: {SOURCE_DIR}")
        return

    # First, copy the entire RegressionSuite to the top level
    if os.path.exists(TARGET_DIR):
        print(f"⚠️  Target directory already exists: {TARGET_DIR}")
        print(f"   Removing old version...")
        shutil.rmtree(TARGET_DIR)

    print(f"📋 Copying RegressionSuite to {TARGET_DIR}...")
    shutil.copytree(SOURCE_DIR, TARGET_DIR)
    print(f"✅ Copied successfully\n")

    # Now rename files in each subdirectory
    total_renamed = 0
    total_skipped = 0

    for folder in sorted(os.listdir(TARGET_DIR)):
        folder_path = os.path.join(TARGET_DIR, folder)
        if not os.path.isdir(folder_path) or folder.startswith("."):
            continue

        print(f"\n📁 {folder}/")
        files = sorted([f for f in os.listdir(folder_path)
                       if not f.startswith(".") and os.path.isfile(os.path.join(folder_path, f))])

        for idx, filename in enumerate(files, start=1):
            old_path = os.path.join(folder_path, filename)

            # Check manual rename map
            if filename in MANUAL_RENAMES:
                new_name = MANUAL_RENAMES[filename]
                if new_name is None:
                    # Marked for deletion/skip
                    print(f"   ⏭️  Skipping: {filename}")
                    total_skipped += 1
                    continue
            else:
                new_name = generate_new_name(folder, filename, idx)

            new_path = os.path.join(folder_path, new_name)

            if old_path == new_path:
                print(f"   ✅ {filename} (already correct)")
                continue

            os.rename(old_path, new_path)
            print(f"   🔄 {filename} → {new_name}")
            total_renamed += 1

    print(f"\n{'='*60}")
    print(f"✅ Complete: {total_renamed} renamed, {total_skipped} skipped")
    print(f"📁 Location: {TARGET_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
