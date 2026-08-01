# G-Power Runtime Validation

Static analysis cannot identify the final G-Power calculation with sufficient
confidence. Runtime evidence is required.

1. Enter a controlled battle and record the displayed G-Power.
2. Search emulator RAM for the value as both unsigned 16-bit and 32-bit data.
3. Change exactly one input: Gate Card, level, evolution state, attribute, or an
   Ability Card effect.
4. Filter the candidate addresses using the new displayed value.
5. Set a write breakpoint on the surviving live value.
6. Repeat the action and record:
   - writing instruction address;
   - active executable component or overlay ID;
   - source registers and memory operands;
   - call stack or link-register chain;
   - before and after values.
7. Convert addresses to component-relative offsets:
   - ARM9 offset = address minus `0x02000000`;
   - overlay 7 offset = address minus `0x02219440`.
8. Repeat with isolated changes to base Bakugan, level, evolution, Gate Card,
   and attribute to identify where each contribution enters the pipeline.

The target deliverable is a verified function and input map for base G-Power,
level growth, evolution, Gate bonus, attribute modifier, and final stored value.
Only then should a guarded balance patch be designed.
