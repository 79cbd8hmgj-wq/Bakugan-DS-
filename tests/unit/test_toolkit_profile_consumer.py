from nds_disassembly_toolkit import profile as toolkit_profile

from bakugan_ds import profile as bakugan_profile


def test_rom_profile_api_is_owned_by_toolkit() -> None:
    assert bakugan_profile.LayoutExpectations is toolkit_profile.LayoutExpectations
    assert bakugan_profile.RomProfile is toolkit_profile.RomProfile
    assert bakugan_profile.RomIdentity is toolkit_profile.RomIdentity
    assert bakugan_profile.load_profile is toolkit_profile.load_profile
    assert bakugan_profile.read_rom_identity is toolkit_profile.read_rom_identity
    assert bakugan_profile.sha256_file is toolkit_profile.sha256_file
    assert bakugan_profile.validate_rom is toolkit_profile.validate_rom
