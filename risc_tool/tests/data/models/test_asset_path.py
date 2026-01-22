from pathlib import Path

from risc_tool.data.models.asset_path import MODULE_NAME, AssetPath


def test_asset_path_structure():
    # Verify that paths are correctly constructed as Path objects starting with module name
    assert isinstance(AssetPath.APP_ICON, Path)
    assert (
        str(AssetPath.APP_ICON).replace("\\", "/")
        == f"{MODULE_NAME}/assets/rt-icon.svg"
    )

    assert isinstance(AssetPath.FILTER_QUERY_REFERENCE, Path)
    assert (
        str(AssetPath.FILTER_QUERY_REFERENCE).replace("\\", "/")
        == f"{MODULE_NAME}/assets/filter_query_reference.md"
    )


def test_all_attributes_are_paths():
    # Iterate over all upper-case attributes and check they are Paths
    for attr in dir(AssetPath):
        if attr.isupper() and not attr.startswith("_"):
            val = getattr(AssetPath, attr)
            assert isinstance(val, Path)


def test_asset_paths_exist():
    # Verify that all defined asset paths actually exist on disk
    base_dir = Path(__file__).resolve().parents[4]
    for attr in dir(AssetPath):
        if attr.isupper() and not attr.startswith("_"):
            path = getattr(AssetPath, attr)
            assert (base_dir / path).exists(), f"Asset path does not exist: {path}"
