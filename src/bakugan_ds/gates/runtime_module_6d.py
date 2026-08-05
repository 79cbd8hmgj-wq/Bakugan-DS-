from __future__ import annotations

import hashlib
import struct

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.arm32 import (
    Condition,
    DataOpcode,
    Register,
    ShiftType,
    encode_bx,
    encode_data_processing_immediate,
    encode_data_processing_register,
    encode_halfword_transfer,
    encode_load_store,
    encode_mul,
    encode_pop,
    encode_push,
)
from bakugan_ds.gates.history import WEIGHTED_SELECTOR_ADDRESS
from bakugan_ds.gates.loader import CACHE_ADDRESS, SYSTEM2_MODULE_SIZE
from bakugan_ds.gates.record import (
    GATE_RECORD_BATTLE_WEIGHTS_OFFSET,
    GateConditionId,
    GateEffectId,
    GateTargetMode,
)
from bakugan_ds.gates.system2 import (
    CORE_G_COMPRESSION_BASE,
    CORE_G_COMPRESSION_THRESHOLD,
)
from bakugan_ds.gates.runtime_module import (
    MODULE_BASE,
    RuntimeModule,
    RuntimeSymbol,
    _RoutineAssembler,
    _RoutineDefinition,
    _RoutineImage,
    _add_register,
    _branch,
    _build_clear_cache,
    _build_crc32_update,
    _build_load_selected_record,
    _build_validate_cache,
    _build_validate_selected_record,
    _compare_immediate,
    _compare_register,
    _emit_participant_pointer,
    _hook_replacements,
    _mov_register,
    _shift_register,
    _static_routine,
    _with_condition,
)

_MILESTONE_6D_OFFSETS = {
    "g2_clear_cache": 0x000,
    "g2_validate_cache": 0x040,
    "g2_crc32_update": 0x0A0,
    "g2_load_selected_record": 0x100,
    "g2_validate_selected_record": 0x500,
    "g2_legacy_gate_bonus": 0x700,
    "g2_calculate_gate_bonus": 0x740,
    "g2_gate_bonus_hook": 0xB40,
    "g2_context_store_hook": 0xB80,
    "g2_select_battle_type": 0xC00,
    "g2_selector_hook": 0xC80,
    "g2_loader_trampoline": 0xCC0,
    "g2_clear_hook": 0xD00,
    "g2_evaluate_condition": 0xE00,
    "g2_matches_target": 0xF00,
    "g2_apply_effect": 0xF80,
}


def _address_6d(name: str) -> int:
    return MODULE_BASE + _MILESTONE_6D_OFFSETS[name]


def _build_evaluate_condition_6d() -> _RoutineImage:
    """Return r0=result and r1=valid for a deterministic condition."""
    asm = _RoutineAssembler(_address_6d("g2_evaluate_condition"))
    asm.emit(_mov_register(Register.R12, Register.R0))
    asm.emit(_mov_register(Register.R0, Register.R1))

    for condition, label in (
        (GateConditionId.NONE, "condition_none"),
        (GateConditionId.OWNER_BEHIND, "condition_owner_behind"),
        (GateConditionId.OWNER_AHEAD, "condition_owner_ahead"),
        (GateConditionId.SCORE_TIED, "condition_score_tied"),
        (GateConditionId.OWNER_SCORE_ZERO, "condition_owner_zero"),
        (GateConditionId.OWNER_AT_MATCH_POINT, "condition_owner_match_point"),
        (GateConditionId.OPPONENT_AT_MATCH_POINT, "condition_opponent_match_point"),
        (GateConditionId.LANDING_GATE_CARD_WON, "condition_landing_won"),
    ):
        asm.emit(_compare_immediate(Register.R12, int(condition)))
        asm.branch(label, condition=Condition.EQ)
    asm.branch("invalid")

    asm.label("condition_none")
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=1))
    asm.branch("valid")

    asm.label("condition_owner_behind")
    asm.emit(_compare_register(Register.R0, Register.R2))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.MOV,
            rd=Register.R0,
            immediate=1,
            condition=Condition.LO,
        )
    )
    asm.branch("valid")

    asm.label("condition_owner_ahead")
    asm.emit(_compare_register(Register.R0, Register.R2))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.MOV,
            rd=Register.R0,
            immediate=1,
            condition=Condition.HI,
        )
    )
    asm.branch("valid")

    asm.label("condition_score_tied")
    asm.emit(_compare_register(Register.R0, Register.R2))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.MOV,
            rd=Register.R0,
            immediate=1,
            condition=Condition.EQ,
        )
    )
    asm.branch("valid")

    asm.label("condition_owner_zero")
    asm.emit(_compare_immediate(Register.R0, 0))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.MOV,
            rd=Register.R0,
            immediate=1,
            condition=Condition.EQ,
        )
    )
    asm.branch("valid")

    asm.label("condition_owner_match_point")
    asm.emit(_compare_immediate(Register.R0, 2))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.MOV,
            rd=Register.R0,
            immediate=1,
            condition=Condition.EQ,
        )
    )
    asm.branch("valid")

    asm.label("condition_opponent_match_point")
    asm.emit(_compare_immediate(Register.R2, 2))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.MOV,
            rd=Register.R0,
            immediate=1,
            condition=Condition.EQ,
        )
    )
    asm.branch("valid")

    asm.label("condition_landing_won")
    asm.load_constant(Register.R1, "landing_unavailable", 0xFFFFFFFF)
    asm.emit(_compare_register(Register.R3, Register.R1))
    asm.branch("invalid", condition=Condition.EQ)
    asm.emit(_compare_immediate(Register.R3, 1))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.MOV,
            rd=Register.R0,
            immediate=1,
            condition=Condition.EQ,
        )
    )
    asm.branch("valid")

    asm.label("invalid")
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R1, immediate=0))
    asm.emit(encode_bx(Register.LR))
    asm.label("valid")
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R1, immediate=1))
    asm.emit(encode_bx(Register.LR))
    return asm.finish()


def _build_matches_target_6d() -> _RoutineImage:
    """Return r0=result and r1=valid for a current-combatant target predicate."""
    asm = _RoutineAssembler(_address_6d("g2_matches_target"))
    asm.emit(_mov_register(Register.R12, Register.R0))
    asm.emit(_mov_register(Register.R0, Register.R1))
    asm.emit(_compare_immediate(Register.R12, int(GateTargetMode.CURRENT_COMBATANT)))
    asm.branch("always", condition=Condition.EQ)
    asm.emit(_compare_immediate(Register.R12, int(GateTargetMode.GATE_OWNER)))
    asm.branch("owner", condition=Condition.EQ)
    asm.emit(_compare_immediate(Register.R12, int(GateTargetMode.GATE_NON_OWNER)))
    asm.branch("non_owner", condition=Condition.EQ)
    asm.branch("invalid")

    asm.label("always")
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=1))
    asm.branch("valid")
    asm.label("owner")
    asm.emit(_compare_register(Register.R0, Register.R2))
   ²È="25}}‰Õ¥±‘}±•…É}¡½½­|Ù ¤€´ø}I½ÕÑ¥¹•%µ…”è(€€€…Í´€ô}I½ÕÑ¥¹•ÍÍ•µ‰±•È¡}…‘‘É•ÍÍ|Ù ‰œÉ}±•…É}¡½½¬ˆ¤¤(€€€Í…Ù•€ô€ (€€€€€€€I•¥ÍÑ•È¹HÄ°(€€€€€€€I•¥ÍÑ•È¹HÈ°(€€€€€€€I•¥ÍÑ•È¹HÌ°(€€€€€€€I•¥ÍÑ•È¹HÐ°(€€€€€€€I•¥ÍÑ•È¹HÄÈ°(€€€€€€€I•¥ÍÑ•È¹1H°(€€€€¤(€€€…Í´¹•µ¥Ð¡•¹½‘•}ÁÕÍ ¡Í…Ù•¤¤(€€€…Í´¹‰É…¹ ¡}…‘‘É•ÍÍ|Ù ‰œÉ}±•…É}…¡”ˆ¤°±¥¹¬õQÉÕ”¤(€€€…Í´¹±½…‘}½¹ÍÑ…¹Ð¡I•¥ÍÑ•È¹HÄÈ°€‰±•…å}±½…‘}…‘‘É•ÍÌˆ°€ÁàÀÈÈÐÅÁ¤(€€€…Í´¹•µ¥Ð¡•¹½‘•}±½…‘}ÍÑ½É”¡I•¥ÍÑ•È¹HÀ°I•¥ÍÑ•È¹HÄÈ°½™™Í•ÐôÀ°±½…õQÉÕ”¤¤(€€€…Í´¹•µ¥Ð (€€€€€€€•¹½‘•}Á½À (€€€€€€€€€€€€ (€€€€€€€€€€€€€€€I•¥ÍÑ•È¹HÄ°(€€€€€€€€€€€€€€€I•¥ÍÑ•È¹HÈ°(€€€€€€€€€€€€€€€I•¥ÍÑ•È¹HÌ°(€€€€€€€€€€€€€€€I•¥ÍÑ•È¹HÐ°(€€€€€€€€€€€€€€€I•¥ÍÑ•È¹HÄÈ°(€€€€€€€€€€€€€€€I•¥ÍÑ•È¹A°(€€€€€€€€€€€€¤(€€€€€€€€¤(€€€€¤(€€€É•ÑÕÉ¸…Í´¹™¥¹¥Í  ¤(()‘•˜}µ¥±•ÍÑ½¹•|Ù‘}É½ÕÑ¥¹•}‘•™¥¹¥Ñ¥½¹Ì ¤€´øÑÕÁ±•m}I½ÕÑ¥¹••™¥¹¥Ñ¥½¸°€¸¸¹tè(€€€±•…ä€ô}…‘‘É•ÍÍ|Ù ‰œÉ}±•…å}…Ñ•}‰½¹ÕÌˆ¤(€€€É•ÑÕÉ¸€ (€€€€€€€}I½ÕÑ¥¹••™¥¹¥Ñ¥½¸ (€€€€€€€€€€€€‰œÉ}±•…É}…¡”ˆ°(€€€€€€€€€€€}5%1MQ=9|Ù}=MQMl‰œÉ}±•…É}…¡”‰t°(€€€€€€€€€€€}‰Õ¥±‘}±•…É}…¡” ¤°(€€€€€€€€€€€€‰±•…È•á…Ñ±äÍ¥áÑ••¸…¡”Ý½É‘Ì…¹É•ÑÕÉ¸¸ˆ°(€€€€€€€€¤°(€€€€€€€}I½ÕÑ¥¹••™¥¹¥Ñ¥½¸ (€€€€€€€€€€€€‰œÉ}Ù…±¥‘…Ñ•}…¡”ˆ°(€€€€€€€€€€€}5%1MQ=9|Ù}=MQMl‰œÉ}Ù…±¥‘…Ñ•}…¡”‰t°(€€€€€€€€€€€}‰Õ¥±‘}Ù…±¥‘…Ñ•}…¡” ¤°(€€€€€€€€€€€€‰Y…±¥‘…Ñ”…¡”™±…œ°Ù•ÉÍ¥½¸°µ•Ñ…‘…Ñ„%°…¹É•½É%¸ˆ°(€€€€€€€€¤°(€€€€€€€}I½ÕÑ¥¹••™¥¹¥Ñ¥½¸ (€€€€€€€€€€€€‰œÉ}ÉŒÌÉ}ÕÁ‘…Ñ”ˆ°(€€€€€€€€€€€}5%1MQ=9|Ù}=MQMl‰œÉ}ÉŒÌÉ}ÕÁ‘…Ñ”‰t°(€€€€€€€€€€€}‰Õ¥±‘}ÉŒÌÉ}ÕÁ‘…Ñ” ¤°(€€€€€€€€€€€€‰UÁ‘…Ñ”„É•™±•Ñ•%IÌÈ½Ù•È„‰½Õ¹‘•‰åÑ”‰Õ™™•È¸ˆ°(€€€€€€€€¤°(€€€€€€€}I½ÕÑ¥¹••™¥¹¥Ñ¥½¸ (€€€€€€€€€€€€‰œÉ}±½…‘}Í•±•Ñ•‘}É•½Éˆ°(€€€€€€€€€€€}5%1MQ=9|Ù}=MQMl‰œÉ}±½…‘}Í•±•Ñ•‘}É•½É‰t°(€€€€€€€€€€€}‰Õ¥±‘}±½…‘}Í•±•Ñ•‘}É•½É ¤°(€€€€€€€€€€€€ (€€€€€€€€€€€€€€€€‰I•……±°€ÄÀÌ½É‘•É•É•½É‘Ì°É•½µÁÕÑ”Á…å±½…IÌÈ°…¹ÍÑ…”€ˆ(€€€€€€€€€€€€€€€€‰Ñ¡”Í•±•Ñ•É•½ÉÑ¡É½Õ ½¹™¥Éµ•9¥ÑÉ½L…±±Ì¸ˆ(€€€€€€€€€€€€¤°(€€€€€€€€¤°(€€€€€€€}I½ÕÑ¥¹••™¥¹¥Ñ¥½¸ (€€€€€€€€€€€€‰œÉ}Ù…±¥‘…Ñ•}Í•±•Ñ•‘}É•½Éˆ°(€€€€€€€€€€€}5%1MQ=9|Ù}=MQMl‰œÉ}Ù…±¥‘…Ñ•}Í•±•Ñ•‘}É•½É‰t°(€€€€€€€€€€€}‰Õ¥±‘}Ù…±¥‘…Ñ•}Í•±•Ñ•‘}É•½É ¤°(€€€€€€€€€€€€‰Y…±¥‘…Ñ”…¹½¹¥…°Á…ÍÍÑ¡É½Õ ‰åÑ•Ì½ÈÑ¡”•á…Ð…ÁÁÉ½Ù•…Ñ”€ÄäÉ•½É¸ˆ°(€€€€€€€€¤°(€€€€€€€}I½ÕÑ¥¹••™¥¹¥Ñ¥½¸ (€€€€€€€€€€€€‰œÉ}±•…å}…Ñ•}‰½¹ÕÌˆ°(€€€€€€€€€€€}5%1MQ=9|Ù}=MQMl‰œÉ}±•…å}…Ñ•}‰½¹ÕÌ‰t°(€€€€€€€€€€€}ÍÑ…Ñ¥}É½ÕÑ¥¹” (€€€€€€€€€€€€€€€±•…ä°(€€€€€€€€€€€€€€€€ (€€€€€€€€€€€€€€€€€€€€ÁáÑLÄÀÄä°(€€€€€€€€€€€€€€€€€€€€ÁáÅØÀÁÐ°(€€€€€€€€€€€€€€€€€€€€ÁáÅÀÅÀÄ°(€€€€€€€€€€€€€€€€€€€€ÁáÅÀÅÈÄ°(€€€€€€€€€€€€€€€€€€€}‰É…¹ ¡±•…ä€¬€ÄØ°€ÁàÀÈÀØÕ	Ð°±¥¹¬õQÉÕ”¤°(€€€€€€€€€€€€€€€€€€€€ÁáÍÀÄÀÁ°(€€€€€€€€€€€€€€€€€€€€ÁáÀÀÄÀÄäÀ°(€€€€€€€€€€€€€€€€€€€€ÁáÅÔÄÅÈ°(€€€€€€€€€€€€€€€€€€€€ÁáÍÀÌÀÀÀ°(€€€€€€€€€€€€€€€€€€€}‰É…¹ ¡±•…ä€¬€ÌØ°€ÁàÀÈÈÍÈÜà¤°(€€€€€€€€€€€€€€€€¤°(€€€€€€€€€€€€€€€€ Ð°€ä¤°(€€€€€€€€€€€€¤°(€€€€€€€€€€€€‰I•±½…Ñ••á…Ð½É¥¥¹…°…Ñ”±½½­ÕÀ°Í…±”°…¹ÍÑ½É”‰±½¬¸ˆ°(€€€€€€€€¤°(€€€€€€€}I½ÕÑ¥¹••™¥¹¥Ñ¥½¸ (€€€€€€€€€€€€‰œÉ}…±Õ±…Ñ•}…Ñ•}‰½¹ÕÌˆ°(€€€€€€€€€€€}5%1MQ=9|Ù}=MQMl‰œÉ}…±Õ±…Ñ•}…Ñ•}‰½¹ÕÌ‰t°(€€€€€€€€€€€}‰Õ¥±‘}…±Õ±…Ñ•}…Ñ•}‰½¹ÕÍ|Ù ¤°(€€€€€€€€€€€€‰Ù…±Õ…Ñ”Ñ¡”Í•±•Ñ•Ù•ÉÍ¥½¸´Ä…Ñ”É•½ÉÑ¡É½Õ •¹•É¥Œ‘•Ñ•Éµ¥¹¥ÍÑ¥Œ‘¥ÍÁ…Ñ ¸ˆ°(€€€€€€€€¤°(€€€€€€€}I½ÕÑ¥¹••™¥¹¥Ñ¥½¸ (€€€€€€€€€€€€‰œÉ}…Ñ•}‰½¹ÕÍ}¡½½¬ˆ°(€€€€€€€€€€€}5%1MQ=9|Ù}=MQMl‰œÉ}…Ñ•}‰½¹ÕÍ}¡½½¬‰t°(€€€€€€€€€€€}ÍÑ…Ñ¥}É½ÕÑ¥¹” (€€€€€€€€€€€€€€€}…‘‘É•ÍÍ|Ù ‰œÉ}…Ñ•}‰½¹ÕÍ}¡½½¬ˆ¤°(€€€€€€€€€€€€€€€€ (€€€€€€€€€€€€€€€€€€€}‰É…¹  (€€€€€€€€€€€€€€€€€€€€€€€}…‘‘É•ÍÍ|Ù ‰œÉ}…Ñ•}‰½¹ÕÍ}¡½½¬ˆ¤°(€€€€€€€€€€€€€€€€€€€€€€€}…‘‘É•ÍÍ|Ù ‰œÉ}…±Õ±…Ñ•}…Ñ•}‰½¹ÕÌˆ¤°(€€€€€€€€€€€€€€€€€€€€¤°(€€€€€€€€€€€€€€€€¤°(€€€€€€€€€€€€€€€€ À°¤°(€€€€€€€€€€€€¤°(€€€€€€€€€€€€‰MÑ…‰±”…Ñ”¡½½¬•¹ÑÉäÉ½ÕÑ•Ñ¡É½Õ Ñ¡”5¥±•ÍÑ½¹”€Ù‘¥ÍÁ…Ñ¡•È¸ˆ°(€€€€€€€€¤°(€€€€€€€}I½ÕÑ¥¹••™¥¹¥Ñ¥½¸ (€€€€€€€€€€€€‰œÉ}½¹Ñ•áÑ}ÍÑ½É•}¡½½¬ˆ°(€€€€€€€€€€€}5%1MQ=9|Ù}=MQMl‰œÉ}½¹Ñ•áÑ}ÍÑ½É•}¡½½¬‰t°(€€€€€€€€€€€}‰Õ¥±‘}½¹Ñ•áÑ}ÍÑ½É•}¡½½­|Ù ¤°(€€€€€€€€€€€€‰±…µÀÍ¥¹•MåÍÑ•´€È¸ÀÑ½Ñ…±Ì…¹É•Á±…äÑ¡”•á…Ð±•…ä…‘½ÍÑ½É”Á…Ñ ¸ˆ°(€€€€€€€€¤°(€€€€€€€}I½ÕÑ¥¹••™¥¹¥Ñ¥½¸ (€€€€€€€€€€€€‰œÉ}Í•±•Ñ}‰…ÑÑ±•}ÑåÁ”ˆ°(€€€€€€€€€€€}5%1MQ=9|Ù}=MQMl‰œÉ}Í•±•Ñ}‰…ÑÑ±•}ÑåÁ”‰t°(€€€€€€€€€€€}‰Õ¥±‘}Í•±•Ñ}‰…ÑÑ±•}ÑåÁ•|Ù ¤°(€€€€€€€€€€€€‰UÍ”‰½Õ¹‘•…¡•Ý•¥¡ÑÌ™½È¹½¹±•…äÉ•½É‘Ì…¹±•…äµ•Ñ…‘…Ñ„½Ñ¡•ÉÝ¥Íe.",
        ),
        _RoutineDefinition(
            "g2_selector_hook",
            _MILESTONE_6D_OFFSETS["g2_selector_hook"],
            _static_routine(
                _address_6d("g2_selector_hook"),
                (
                    _branch(
                        _address_6d("g2_selector_hook"),
                        _address_6d("g2_select_battle_type"),
                    ),
                ),
                (0,),
            ),
            "Stable selector entry routed through bounded Milestone 6D weights.",
        ),
        _RoutineDefinition(
            "g2_loader_trampoline",
            _MILESTONE_6D_OFFSETS["g2_loader_trampoline"],
            _build_loader_trampoline_6d(),
            "Validate selected cache identity, reload on mismatch, then continue selector.",
        ),
        _RoutineDefinition(
            "g2_clear_hook",
            _MILESTONE_6D_OFFSETS["g2_clear_hook"],
            _build_clear_hook_6d(),
            "Clear cache, replay displaced result-path load, and return.",
        ),
        _RoutineDefinition(
            "g2_evaluate_condition",
            _MILESTONE_6D_OFFSETS["g2_evaluate_condition"],
            _build_evaluate_condition_6d(),
            "Evaluate one deterministic Gate condition and return result plus validity.",
        ),
        _RoutineDefinition(
            "g2_matches_target",
            _MILESTONE_6D_OFFSETS["g2_matches_target"],
            _build_matches_target_6d(),
            "Evaluate the current-combatant Gate target predicate.",
        ),
        _RoutineDefinition(
            "g2_apply_effect",
            _MILESTONE_6D_OFFSETS["g2_apply_effect"],
            _build_apply_effect_6d(),
            "Apply one checked signed Gate G effect and return validity.",
        ),
    )


def build_milestone_6d_module() -> RuntimeModule:
    image = bytearray(SYSTEM2_MODULE_SIZE)
    symbols: dict[str, RuntimeSymbol] = {}
    for definition in _milestone_6d_routine_definitions():
        address = MODULE_BASE + definition.offset
        data = struct.pack(f"<{len(definition.image.words)}I", *definition.image.words)
        end = definition.offset + len(data)
        if end > SYSTEM2_MODULE_SIZE:
            raise WorkspaceError(f"runtime routine {definition.name} exceeds module")
        if any(image[definition.offset:end]):
            raise WorkspaceError(f"runtime routine {definition.name} overlaps another")
        image[definition.offset:end] = data
        symbol = RuntimeSymbol(
            name=definition.name,
            address=address,
            size=len(data),
            code_size=definition.image.instruction_word_count * 4,
            branch_targets=definition.image.branch_targets,
            purpose=definition.purpose,
        )
        symbol.validate()
        symbols[definition.name] = symbol
    ordered_symbols = dict(sorted(symbols.items(), key=lambda item: item[1].address))
    module = RuntimeModule(
        image=bytes(image),
        symbols=ordered_symbols,
        hook_replacements=_hook_replacements(ordered_symbols),
        sha256=hashlib.sha256(image).hexdigest(),
    )
    module.validate()
    return module
