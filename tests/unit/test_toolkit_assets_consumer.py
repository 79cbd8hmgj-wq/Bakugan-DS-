import nds_disassembly_toolkit.assets as toolkit_assets

import bakugan_ds.assets as bakugan_assets


def test_asset_models_and_detector_are_toolkit_owned() -> None:
    assert bakugan_assets.AssetRecord is toolkit_assets.AssetRecord
    assert bakugan_assets.AssetInventory is toolkit_assets.AssetInventory
    assert bakugan_assets.detect_asset is toolkit_assets.detect_asset


def test_bakugan_inventory_keeps_profiled_boundary() -> None:
    assert bakugan_assets.inventory_assets is not toolkit_assets.inventory_assets
