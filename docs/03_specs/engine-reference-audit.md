# Engine comparison with Glycomass/Server

Compared on 2026-09-14 against the separate repository's `master` (`6c0ccee`),
`Stable`, `Dev`, and `interactive-spectrums` (`f72e2b5`) branches. Source inspection
only; the reference checkout was not executed or merged.

## Port coverage

- The 2020 deamidation correction (H −1, N −1, O +1) is already in
  `core/constants.py`. Older Stable/Dev use the opposite sign.
- The subsequent 2-AA correction (`88bc42e`, C7 H7 N1 O1) is already present.
- Carbamidomethylation, disulfide subtraction, glycan derivatization tables,
  charge handling, isotope counts and resolution settings are represented in
  the rewrite. The retained legacy also repairs NumPy multiplication of modifier
  lists; the rewrite uses elemental-composition arithmetic.
- The reference identifier source matches our retained legacy source after
  whitespace normalization. Its task wrapper adds no missing calculation logic.
- The 2025 commit changes plotting transport from PNG to sampled JSON/Plotly;
  it does not alter mass formulas or the Gaussian computation.

## Spectrum regression repaired

The rewrite returned only discrete isotope centers and joined them with a line.
The reference plots the sampled Gaussian profile. Results now additionally expose
`profile`, normalized to 100 and reduced to at most 12,000 samples by retaining
bin minima/maxima and endpoints. Scalar masses still use the full original grid.
The default display uses the Gaussian profile; Peaks draws independent zero-to-intensity sticks.
HTML profiles round display coordinates to six decimals and relative intensities
to four decimals, and responses use gzip to avoid excessive transfer time. Protein resolution therefore affects the displayed profile again.

Validation: 146 default tests, 795 legacy scalar comparisons, three JavaScript
regressions, and Chromium checks for all calculators, both display modes, repeated
submission, and mobile resizing. These establish legacy parity, not independent
scientific validation of the inherited model.

## Scientific and validation follow-ups

These are existing behaviors, not fixes available in the separate repository:

1. **Sodium adducts:** `SODIUM_MASS = 22.989770`, `PROTON_MASS = 1.0` yield
   a replacement shift of `21.989770 / charge`. Review ion/electron/proton mass
   conventions against independent reference values before changing results.
2. **Gaussian width:** the exponent divides by `2 * sigma`, while normalization
   divides by `sqrt(2*pi) * sigma` and the grid step is `sigma`. The parameter
   mixes variance and standard-deviation conventions. Define intended width or
   resolving power before changing it; this can change most-abundant m/z.
3. **Input validation:** peptide/protein forms and APIs now reject unsupported or
   empty sequences using a shared validator, accepting whitespace and lowercase.
   Direct legacy-compatible core calls still discard unknown characters;
   unknown glycan modifications fall back to native; numeric request fields
   mostly accept unrestricted integers. Define supported residues, counts,
   deamidation bounds and charge/neutral-mass semantics, with explicit errors.
4. **Scale and isotope coverage:** fixed 10/200 isotope peaks and O(P × G)
   Gaussian evaluation need independent coverage/convergence checks for very
   large compositions and resource limits. Existing slow-operation logs measure
   these phases, but do not establish scientific adequacy or a hard work bound.

Keep scientific corrections separate from display repair, with independently
validated fixtures and a documented result/version migration for saved inputs.
