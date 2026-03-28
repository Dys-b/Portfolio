import os
import re
import zipfile
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

BASE_PATH = os.getenv("BASE_PATH", "input")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
LOGO_PATH = os.getenv("LOGO_PATH", "assets/logo.jpg")
OLD_PERIOD = os.getenv("OLD_PERIOD", "OLDPRD")
NEW_PERIOD = os.getenv("NEW_PERIOD", "NEWPRD")

LOGO_NAME = os.path.basename(LOGO_PATH)
PERIOD_PATTERN = re.compile(r"_[A-Z]{3}\d{2}$")

# Replace with sanitized aliases only
WORKBOOK_TO_HYPER_MAP = {
    "CLIENT_A": "CLIENT_A",
    "CLIENT_B": "CLIENT_B",
    "CLIENT_C": "CLIENT_C",
}


def normalize_hyper_paths_xml(twb_xml: str) -> str:
    """
    Convert absolute .hyper paths inside a Tableau .twb XML
    into portable relative paths under Data/.
    """
    root = ET.fromstring(twb_xml)

    for element in root.iter():
        dbname = element.attrib.get("dbname")
        if dbname and dbname.lower().endswith(".hyper"):
            filename = os.path.basename(dbname)
            element.set("dbname", f"Data/{filename}")

    return ET.tostring(root, encoding="utf-8").decode("utf-8")


def replace_logo_paths(content: str, logo_name: str) -> str:
    """
    Replace absolute jpg/jpeg/png asset paths with Images/<logo_name>.
    """
    pattern = r"[A-Za-z]:[\\/][^\"'\n<>]*\.(jpg|jpeg|png)"
    return re.sub(
        pattern,
        f"Images/{logo_name}",
        content,
        flags=re.IGNORECASE,
    )


def find_absolute_paths(content: str) -> list[str]:
    """
    Detect leftover absolute Windows-style paths.
    """
    matches = re.findall(
        r"[A-Za-z]:[\\/][^\"'<>|\n]+",
        content,
        flags=re.IGNORECASE,
    )
    return matches


def resolve_hyper_files(base_name: str) -> tuple[str | None, str | None]:
    """
    Resolve expected Hyper files for a workbook.
    """
    hyper_base = WORKBOOK_TO_HYPER_MAP.get(base_name, base_name)

    hyper_month = os.path.join(BASE_PATH, f"{hyper_base}_MES.hyper")
    hyper_period = os.path.join(BASE_PATH, f"{hyper_base}_PERIODO.hyper")

    if not os.path.exists(hyper_month):
        alt_month = os.path.join(BASE_PATH, f"{hyper_base}_MES_ALT.hyper")
        if os.path.exists(alt_month):
            hyper_month = alt_month
        else:
            hyper_month = None

    if not os.path.exists(hyper_period):
        alt_period = os.path.join(BASE_PATH, f"{hyper_base}_PERIODO_ALT.hyper")
        if os.path.exists(alt_period):
            hyper_period = alt_period
        else:
            hyper_period = None

    return hyper_month, hyper_period


def rename_period_if_needed(file_name: str) -> tuple[str, str]:
    """
    Optionally rename workbook period token, for example OLDPRD -> NEWPRD.
    Returns (workbook_name_without_ext, workbook_path).
    """
    original_path = os.path.join(BASE_PATH, file_name)
    workbook_name = file_name[:-4]
    workbook_path = original_path

    if OLD_PERIOD in workbook_name:
        new_name = workbook_name.replace(OLD_PERIOD, NEW_PERIOD)
        new_file_name = f"{new_name}.twb"
        new_path = os.path.join(BASE_PATH, new_file_name)

        if not os.path.exists(new_path):
            os.rename(original_path, new_path)

        workbook_name = new_name
        workbook_path = new_path

    return workbook_name, workbook_path


def build_twbx_for_file(file_name: str):
    """
    Package a .twb into a .twbx with relative Hyper paths and embedded assets.
    """
    if not file_name.lower().endswith(".twb"):
        return

    workbook_name, workbook_path = rename_period_if_needed(file_name)
    base_name = PERIOD_PATTERN.sub("", workbook_name)

    hyper_month, hyper_period = resolve_hyper_files(base_name)

    if not hyper_month or not hyper_period:
        print(f"[WARN] Skipping {workbook_name}: missing Hyper files")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    twbx_path = os.path.join(OUTPUT_DIR, f"{workbook_name}.twbx")

    if os.path.exists(twbx_path):
        print(f"[INFO] Skipping {workbook_name}: TWBX already exists")
        return

    with open(workbook_path, "r", encoding="utf-8") as file:
        twb_content = file.read()

    twb_content = normalize_hyper_paths_xml(twb_content)
    twb_content = replace_logo_paths(twb_content, LOGO_NAME)

    remaining_paths = find_absolute_paths(twb_content)
    if remaining_paths:
        print(f"[WARN] Absolute paths still detected in {workbook_name}:")
        for item in remaining_paths[:5]:
            print(f"   {item}")
    else:
        print(f"[OK] No absolute paths detected in {workbook_name}")

    temp_twb_path = os.path.join(OUTPUT_DIR, f"{workbook_name}_temp.twb")
    with open(temp_twb_path, "w", encoding="utf-8") as file:
        file.write(twb_content)

    with zipfile.ZipFile(twbx_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(temp_twb_path, arcname=f"{workbook_name}.twb")
        archive.write(hyper_month, arcname=f"Data/{os.path.basename(hyper_month)}")
        archive.write(hyper_period, arcname=f"Data/{os.path.basename(hyper_period)}")

        if os.path.exists(LOGO_PATH):
            archive.write(LOGO_PATH, arcname=f"Images/{LOGO_NAME}")

    os.remove(temp_twb_path)
    print(f"[OK] Created {os.path.basename(twbx_path)}")


def main():
    if not os.path.exists(BASE_PATH):
        raise FileNotFoundError(f"BASE_PATH does not exist: {BASE_PATH}")

    files = os.listdir(BASE_PATH)
    twb_files = [file_name for file_name in files if file_name.lower().endswith(".twb")]

    print(f"[INFO] Found {len(twb_files)} TWB file(s) in {BASE_PATH}")

    for file_name in twb_files:
        try:
            build_twbx_for_file(file_name)
        except Exception as exc:
            print(f"[ERROR] {file_name}: {exc}")


if __name__ == "__main__":
    main()
