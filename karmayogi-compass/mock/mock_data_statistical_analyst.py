"""Extra REQUIRED_LEVELS_BY_DESIGNATION entries for the Statistical Analyst
persona, merged into app/adapters/mock_data.py at import time by
mock_dataset_loader.load_designation_overrides(). Keys here that already
exist in the app's built-in dict (e.g. 'Junior Statistical Officer') simply
overwrite those values; new keys (e.g. 'Statistical Analyst') are added.
"""

REQUIRED_LEVELS_BY_DESIGNATION = {
    "Junior Statistical Officer": {
        "statistical_score": 70, "technical_score": 55, "digital_gov_score": 50, "managerial_score": 40,
    },
    "Statistical Officer": {
        "statistical_score": 80, "technical_score": 65, "digital_gov_score": 60, "managerial_score": 55,
    },
    "Statistical Analyst": {
        "statistical_score": 80, "technical_score": 65, "digital_gov_score": 60, "managerial_score": 55,
    },
}
