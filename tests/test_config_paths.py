from app.config import CONFIG_FILE, DATA_DIR, DB_PATH


def test_data_paths_point_to_repo_data_dir():
    assert DATA_DIR.name == "data"
    assert CONFIG_FILE.name == "config.json"
    assert DB_PATH.name == "companion.db"
