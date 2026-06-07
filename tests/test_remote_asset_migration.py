from backend.remote_asset_migration import copy_unique_assets, run_migration


def test_copy_remote_assets_deduplicates_by_sha256(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "A.vrm").write_bytes(b"same")
    (source / "B.vrm").write_bytes(b"same")
    target = tmp_path / "target"

    report = copy_unique_assets(source, target, (".vrm",))

    assert report["copied_count"] == 1
    assert report["duplicate_count"] == 1
    assert len(list(target.rglob("*.vrm"))) == 1


def test_run_migration_writes_json_report(tmp_path):
    avatars_source = tmp_path / "avatars-src"
    dances_source = tmp_path / "dances-src"
    avatars_source.mkdir()
    dances_source.mkdir()
    (avatars_source / "Alpha.vrm").write_bytes(b"avatar-a")
    (dances_source / "Dance One.unity3d").write_bytes(b"dance-a")
    report_path = tmp_path / "report.json"

    report = run_migration(
        avatar_source_dir=avatars_source,
        dance_source_dir=dances_source,
        backend_static_assets_dir=tmp_path / "static_assets",
        report_path=report_path,
    )

    assert report_path.exists()
    assert report["avatars"]["copied_count"] == 1
    assert report["dances"]["copied_count"] == 1
