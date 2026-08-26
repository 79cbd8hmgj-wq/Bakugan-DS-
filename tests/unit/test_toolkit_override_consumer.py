from nds_disassembly_toolkit.workspace import overrides as toolkit_overrides

from bakugan_ds.workspace import overrides as bakugan_overrides


def test_override_primitives_are_owned_by_toolkit() -> None:
    assert bakugan_overrides.RawNitroFsOverride is toolkit_overrides.RawNitroFsOverride
    assert bakugan_overrides.OverlayLayoutOverride is toolkit_overrides.OverlayLayoutOverride
    assert issubclass(bakugan_overrides.BuildOverrides, toolkit_overrides.BuildOverrides)


def test_bakugan_override_container_keeps_profile_policy() -> None:
    valid = bakugan_overrides.BuildOverrides(1, "b6re_rev0", (), ())
    valid.validate()
