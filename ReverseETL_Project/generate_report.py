
import getpass
import os
import platform
import shutil
import socket
import sys
from datetime import datetime
from importlib.util import find_spec
from pathlib import Path


# ==========================================================
# DATA ENGINEERING LAB CONFIGURATION REPORT GENERATOR
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORT_FILE = BASE_DIR / "PROJECT_REPORT.txt"


def ask(prompt, default=""):
    """Ask for a value, optionally providing a default."""
    value = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    return value if value else default


def get_library_status(module_name):
    """Check whether a Python library is installed."""
    return "PASS (Installed)" if find_spec(module_name) else "NOT INSTALLED"


def get_file_status(file_path):
    """Check whether a project file or folder exists."""
    return "PASS" if file_path.exists() else "NOT FOUND"


def main():
    print("=" * 62)
    print("       DATA ENGINEERING LAB REPORT GENERATOR")
    print("=" * 62)

    # 1. Collect project and experiment details
    print("\n--- PROJECT DETAILS ---")

    project_title = ask(
        "Project title"
    )
    experiment_no = ask("Experiment number")
    batch = ask("Batch")
    member_count = 4

    # 2. Collect all four students' details
    print("\n--- FOUR PROJECT MEMBERS ---")

    members = []

    for number in range(1, member_count + 1):
        print(f"\nMember {number}")
        name = ask("Enter student name")
        roll_no = ask("Enter roll number")

        members.append({
            "name": name if name else f"Member {number}",
            "roll_no": roll_no if roll_no else "Not provided"
        })

    # 3. Collect lab details
    print("\n--- LAB DETAILS ---")

    lab_name = ask("Lab / subject name")
    student_class = ask("Class / division")
    faculty_name = ask("Faculty name ")

    # 4. Detect system information
    username = getpass.getuser()
    hostname = socket.gethostname()
    current_dir = Path.cwd()
    operating_system = platform.platform()
    python_version = platform.python_version()
    processor = platform.processor() or "Not available"

    # 5. Check available disk space
    disk = shutil.disk_usage(BASE_DIR)
    disk_free_gb = disk.free / (1024 ** 3)
    disk_total_gb = disk.total / (1024 ** 3)

    # 6. Check project files
    workspace_items = [
        ("pipeline.py", BASE_DIR / "pipeline.py"),
        ("data folder", DATA_DIR),
        ("raw_customers.csv", DATA_DIR / "raw_customers.csv"),
        ("segmented_customers.csv", DATA_DIR / "segmented_customers.csv"),
        ("warehouse.duckdb", DATA_DIR / "warehouse.duckdb"),
        ("crm_export.csv", DATA_DIR / "crm_export.csv"),
    ]

    # 7. Check installed software / libraries
    libraries = [
        ("Python", f"PASS (Python {python_version})"),
        ("Pandas", get_library_status("pandas")),
        ("DuckDB", get_library_status("duckdb")),
    ]

    # 8. Create report content
    now = datetime.now()

    lines = [
        "=" * 62,
        f"       {lab_name.upper()} CONFIGURATION REPORT",
        "=" * 62,
        "",
        "Project Title       : " + project_title,
        "Experiment No       : " + experiment_no,
        "Batch               : " + batch,
        "Class / Division    : " + student_class,
        "Faculty Name        : " + faculty_name,
        "",
        "--------------------------------------------------------------",
        "Project Members",
        "--------------------------------------------------------------",
        "",
    ]

    for number, member in enumerate(members, start=1):
        lines.extend([
            f"Member {number} Name    : {member['name']}",
            f"Member {number} Roll No  : {member['roll_no']}",
        ])

    lines.extend([
        "",
        "--------------------------------------------------------------",
        "System Information",
        "--------------------------------------------------------------",
        "",
        f"Username            : {username}",
        f"Hostname            : {hostname}",
        f"Operating System    : {operating_system}",
        f"Python Version      : {python_version}",
        f"Current Directory   : {current_dir}",
        f"Processor           : {processor}",
        f"Disk Available      : {disk_free_gb:.2f} GB free of {disk_total_gb:.2f} GB",
        "",
        "--------------------------------------------------------------",
        "Environment Information",
        "--------------------------------------------------------------",
        "",
        f"Virtual Environment : {os.environ.get('VIRTUAL_ENV', 'Not detected')}",
        f"Python Executable   : {sys.executable}",
        "",
        "--------------------------------------------------------------",
        "Installed Software and Libraries",
        "--------------------------------------------------------------",
        "",
    ])

    for name, status in libraries:
        lines.append(f"{name:<20}: {status}")

    lines.extend([
        "",
        "--------------------------------------------------------------",
        "Project Workspace",
        "--------------------------------------------------------------",
        "",
    ])

    for name, path in workspace_items:
        lines.append(f"{get_file_status(path):<12} {name}")

    # Check whether the most recent pipeline run created outputs.
    outputs_exist = all(
        (DATA_DIR / filename).exists()
        for filename in [
            "segmented_customers.csv",
            "warehouse.duckdb",
            "crm_export.csv",
        ]
    )

    lines.extend([
        "",
        "--------------------------------------------------------------",
        "Pipeline Configuration",
        "--------------------------------------------------------------",
        "",
        "Input Dataset       : data/raw_customers.csv",
        "Database            : data/warehouse.duckdb",
        "Database Table      : customer_segments",
        "Segmented Output    : data/segmented_customers.csv",
        "CRM Export          : data/crm_export.csv",
        "",
        "Customer Rules:",
        "  High Value: Spend >= 1000 and last purchase within 30 days",
        "  At Risk   : More than 90 days since last purchase",
        "  Regular   : All remaining customers",
        "",
        "Pipeline Output Files: "
        + ("PASS (Files exist)" if outputs_exist else
           "PENDING (Run pipeline.py first)"),
        "",
        "--------------------------------------------------------------",
        "Completion Information",
        "--------------------------------------------------------------",
        "",
        f"Report Date          : {now.strftime('%d-%b-%Y')}",
        f"Report Time          : {now.strftime('%I:%M:%S %p')}",
        "",
        "Remarks",
        "",
        "This project demonstrates a local Reverse ETL workflow.",
        "Customer records are segmented using Python and Pandas,",
        "stored in DuckDB, validated using SQL, and exported to a",
        "CRM-ready CSV file.",
        "",
        "Live CRM integration and automatic scheduling are not",
        "implemented and remain possible future enhancements.",
        "",
        "=" * 62,
    ])

    report = "\n".join(lines)

    # 9. Save and print the report
    REPORT_FILE.write_text(report, encoding="utf-8")

    print("\n\n" + report)
    print(f"\nReport saved successfully to:\n{REPORT_FILE}")


if __name__ == "__main__":
    main()
