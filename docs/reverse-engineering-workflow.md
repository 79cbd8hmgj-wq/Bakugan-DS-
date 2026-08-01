# Reverse-Engineering Evidence Workflow

Every symbol, structure, and behavioral claim must include an overlay or
executable component, a runtime address, a component-relative offset, and one
of the confidence levels below.

## Confirmed

Use `confirmed` only when behavior is demonstrated by runtime observation, a
controlled reversible patch, an exact documented file format, or immutable ROM
metadata verified by tests.

## Probable

Use `probable` when static evidence is strong and multiple references agree,
but no controlled runtime demonstration has been completed.

## Candidate

Use `candidate` for search results, strings, call sites, data regions, or
hypotheses that are useful investigation leads but remain unverified.

## Address notation

ARM9 symbols record the runtime address and the relative offset from
`0x02000000`. Overlay symbols record the overlay ID, runtime address, and
component-relative offset from that overlay's declared load address. Because
all current ARM9 overlays share `0x02219440`, a runtime address alone is
ambiguous and must never be used as a unique identifier.

## Promotion rule

A candidate may become probable after static cross-reference analysis. A
probable symbol becomes confirmed only after a controlled runtime observation
or patch demonstrates its behavior. Documentation must retain the evidence
used for promotion.
