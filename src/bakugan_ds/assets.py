from nds_disassembly_toolkit.assets import (
    AssetInventory,
    AssetRecord,
    detect_asset,
)
from nds_disassembly_toolkit.assets import inventory_assets as _toolkit_inventory_assets

from bakugan_ds.inspection import RomInspection


def inventory_assets(
    rom_data: bytes,
    inspection: RomInspection,
    *,
    include_unknown: bool = False,
) -> AssetInventory:
    if inspection.profile_id is None or inspection.supported is None:
        raise ValueError("Bakugan asset inventory requires a profiled ROM inspection")
    return _toolkit_inventory_assets(
        rom_data,
        inspection,
        include_unknown=include_unknown,
    )


__all__ = ["AssetInventory", "AssetRecord", "detect_asset", "inventory_assets"]
