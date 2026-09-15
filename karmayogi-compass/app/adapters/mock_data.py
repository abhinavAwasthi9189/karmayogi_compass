"""Structured fixtures standing in for live iGOT Karmayogi + MoSPI competency data."""
from app.adapters import mock_dataset_loader as _loader

# Required competency levels (0-100 scale) by designation. Falls back to DEFAULT.
REQUIRED_LEVELS_BY_DESIGNATION = {
    "Junior Statistical Officer": {
        "statistical_score": 70, "technical_score": 55, "digital_gov_score": 50, "managerial_score": 40,
    },
    "Statistical Officer": {
        "statistical_score": 80, "technical_score": 65, "digital_gov_score": 60, "managerial_score": 55,
    },
    "Deputy Director": {
        "statistical_score": 85, "technical_score": 70, "digital_gov_score": 70, "managerial_score": 75,
    },
    "Director": {
        "statistical_score": 90, "technical_score": 70, "digital_gov_score": 75, "managerial_score": 85,
    },
    "DEFAULT": {
        "statistical_score": 75, "technical_score": 65, "digital_gov_score": 60, "managerial_score": 55,
    },
}

# Merge in any designation requirements supplied via mock/mock_data_statistical_analyst.py.
# Existing keys are overwritten with the override's values; new designations (e.g.
# "Statistical Analyst") are added. No-op if the mock/ dataset isn't present.
REQUIRED_LEVELS_BY_DESIGNATION.update(_loader.load_designation_overrides())

DOMAINS = ["statistical_score", "technical_score", "digital_gov_score", "managerial_score"]

DOMAIN_LABELS = {
    "statistical_score": "statistical",
    "technical_score": "technical",
    "digital_gov_score": "digital_gov",
    "managerial_score": "managerial",
}

# Mock iGOT course catalog, tagged by the domain (short label) they build competency in.
MOCK_COURSES = [
    {"id": "igot-stat-101", "title": "Fundamentals of Official Statistics", "domain": "statistical",
     "source": "iGOT Karmayogi", "launch_url": "https://igot.gov.in/course/igot-stat-101",
     "description": "Core concepts of NSS, sampling design and estimation for official statistics."},
    {"id": "igot-stat-204", "title": "Advanced Survey Methodology for MoSPI", "domain": "statistical",
     "source": "iGOT Karmayogi", "launch_url": "https://igot.gov.in/course/igot-stat-204",
     "description": "Stratified and multi-stage sampling techniques used in NSS rounds."},
    {"id": "igot-stat-310", "title": "National Accounts Statistics (GDP Compilation)", "domain": "statistical",
     "source": "iGOT Karmayogi", "launch_url": "https://igot.gov.in/course/igot-stat-310",
     "description": "GVA/GDP compilation methodology under the System of National Accounts."},
    {"id": "igot-tech-110", "title": "Data Analytics with Python for Statisticians", "domain": "technical",
     "source": "iGOT Karmayogi", "launch_url": "https://igot.gov.in/course/igot-tech-110",
     "description": "Pandas, visualization and statistical testing for government data."},
    {"id": "igot-tech-215", "title": "Introduction to R for Survey Data Processing", "domain": "technical",
     "source": "iGOT Karmayogi", "launch_url": "https://igot.gov.in/course/igot-tech-215",
     "description": "Cleaning, tabulation and weighting of survey microdata in R."},
    {"id": "igot-tech-330", "title": "Database Management for Statistical Systems", "domain": "technical",
     "source": "iGOT Karmayogi", "launch_url": "https://igot.gov.in/course/igot-tech-330",
     "description": "Relational data modelling for large administrative datasets."},
    {"id": "igot-dgov-120", "title": "Digital Governance & e-Office Essentials", "domain": "digital_gov",
     "source": "iGOT Karmayogi", "launch_url": "https://igot.gov.in/course/igot-dgov-120",
     "description": "e-Office, DigiLocker and interoperable digital governance workflows."},
    {"id": "igot-dgov-225", "title": "Cyber Hygiene for Government Officials", "domain": "digital_gov",
     "source": "iGOT Karmayogi", "launch_url": "https://igot.gov.in/course/igot-dgov-225",
     "description": "Data protection, secure handling of citizen data and cyber hygiene."},
    {"id": "igot-dgov-340", "title": "Open Government Data (OGD) Platform Practices", "domain": "digital_gov",
     "source": "iGOT Karmayogi", "launch_url": "https://igot.gov.in/course/igot-dgov-340",
     "description": "Publishing and consuming datasets on the OGD platform."},
    {"id": "igot-mgmt-130", "title": "People Management for Statistical Officers", "domain": "managerial",
     "source": "iGOT Karmayogi", "launch_url": "https://igot.gov.in/course/igot-mgmt-130",
     "description": "Leading field survey teams and managing enumerator performance."},
    {"id": "igot-mgmt-240", "title": "Project Management in Government Programmes", "domain": "managerial",
     "source": "iGOT Karmayogi", "launch_url": "https://igot.gov.in/course/igot-mgmt-240",
     "description": "Planning, monitoring and evaluation of statistical survey programmes."},
    {"id": "igot-mgmt-350", "title": "Ethical Leadership in Public Administration", "domain": "managerial",
     "source": "iGOT Karmayogi", "launch_url": "https://igot.gov.in/course/igot-mgmt-350",
     "description": "Integrity, accountability and decision-making for MoSPI officials."},
]

# Extend the curated catalog with courses loaded from mock/rag_learning_corpus_flat.csv,
# skipping any id collision with the curated list above. No-op if that file isn't present.
_existing_ids = {c["id"] for c in MOCK_COURSES}
for _course in _loader.load_courses_from_corpus():
    if _course["id"] not in _existing_ids:
        MOCK_COURSES.append(_course)
        _existing_ids.add(_course["id"])

# Seed users for local demo (password for all: "Karmayogi@123")
SEED_USERS = [
    {"name": "Aditi Sharma", "email": "aditi.sharma@mospi.gov.in", "role": "official",
     "department": "NSSO", "designation": "Statistical Officer",
     "scores": {"statistical_score": 62, "technical_score": 40, "digital_gov_score": 55, "managerial_score": 35}},
    {"name": "Ravi Kumar", "email": "ravi.kumar@mospi.gov.in", "role": "admin",
     "department": "CSO", "designation": "Director",
     "scores": {"statistical_score": 78, "technical_score": 58, "digital_gov_score": 66, "managerial_score": 70}},
    {"name": "Priya Iyer", "email": "priya.iyer@mospi.gov.in", "role": "official",
     "department": "FOD", "designation": "Junior Statistical Officer",
     "scores": {"statistical_score": 38, "technical_score": 30, "digital_gov_score": 42, "managerial_score": 25}},
]
