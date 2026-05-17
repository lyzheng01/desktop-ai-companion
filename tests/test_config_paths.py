from pathlib import Path

import app.config as config_module


def test_default_data_paths_have_expected_filenames():
    config_module.set_data_dir(config_module.APP_DIR / "data")
    assert config_module.DATA_DIR.name == "data"
    assert config_module.CONFIG_FILE.name == "config.json"
    assert config_module.DB_PATH.name == "companion.db"


def test_set_data_dir_updates_runtime_paths(tmp_path):
    chosen = tmp_path / "user-data"
    config_module.set_data_dir(chosen)

    assert config_module.get_data_dir() == chosen.resolve()
    assert config_module.get_config_file() == chosen.resolve() / "config.json"
    assert config_module.get_db_path() == chosen.resolve() / "companion.db"
    assert config_module.get_imported_models_dir() == chosen.resolve() / "live2d" / "imported"
    assert config_module.get_imported_preview_dir() == chosen.resolve() / "model-previews" / "imported"

    config_module.set_data_dir(config_module.APP_DIR / "data")
