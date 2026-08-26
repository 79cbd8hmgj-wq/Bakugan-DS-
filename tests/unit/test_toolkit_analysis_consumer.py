import nds_disassembly_toolkit.analysis.arm as toolkit_arm
import nds_disassembly_toolkit.analysis.model as toolkit_model
import nds_disassembly_toolkit.analysis.numeric as toolkit_numeric
import nds_disassembly_toolkit.analysis.report as toolkit_report
import nds_disassembly_toolkit.analysis.strings as toolkit_strings

import bakugan_ds.analysis.arm as bakugan_arm
import bakugan_ds.analysis.model as bakugan_model
import bakugan_ds.analysis.numeric as bakugan_numeric
import bakugan_ds.analysis.report as bakugan_report
import bakugan_ds.analysis.strings as bakugan_strings


def test_analysis_models_are_toolkit_owned() -> None:
    for name in (
        "Component",
        "StringRecord",
        "PointerReference",
        "NumericMatch",
        "SymbolCandidate",
    ):
        assert getattr(bakugan_model, name) is getattr(toolkit_model, name)


def test_analysis_primitives_are_toolkit_owned() -> None:
    module_pairs = (
        (bakugan_arm, toolkit_arm),
        (bakugan_numeric, toolkit_numeric),
        (bakugan_strings, toolkit_strings),
    )
    names_by_module = (
        ("arm_function_starts", "nearest_function_start", "function_address_for_reference"),
        ("scan_scaled_byte_rows", "cluster_numeric_matches"),
        ("extract_ascii_strings", "filter_strings", "find_pointer_references"),
    )

    for (bakugan_module, toolkit_module), names in zip(module_pairs, names_by_module, strict=True):
        for name in names:
            assert getattr(bakugan_module, name) is getattr(toolkit_module, name)


def test_generic_report_writer_is_toolkit_owned() -> None:
    assert bakugan_report.write_report is toolkit_report.write_report
    assert bakugan_report.analyze_components is not toolkit_report.analyze_components
