# Glycomass

Calculate theoretical masses and isotope spectra for glycans, glycopeptides, and
glycoproteins, and identify glycopeptide spectra in MGF files.

**[Open Glycomass](https://glycomass.com)** ·
[API documentation](https://glycomass.com/docs) ·
[Report a problem](https://github.com/christiantill/Glycomass/issues)

## Calculators

| Tool | Inputs |
| --- | --- |
| [Glycan](https://glycomass.com/glycan) | Monosaccharide composition, modifications, and charge |
| [Glycopeptide](https://glycomass.com/peptide) | Peptide sequence, glycan composition, and charge |
| [Glycoprotein](https://glycomass.com/protein) | Protein sequence, glycan composition, modifications, and resolution |

View monoisotopic and most-abundant m/z, explore the isotope profile or individual
peaks, and copy or download the peak table. Saved calculation links let you share
your inputs. The [glycopeptide identifier](https://glycomass.com/identifier)
processes uploaded MGF files and provides a downloadable result.

## Research use

Glycomass is research software. Calculator outputs are regression-tested against the original implementation, but this does not constitute independent scientific validation. Please verify results for your intended application.

See the [engine notes](docs/engine.md) for model assumptions, validation scope,
and known limitations.

## Cite Glycomass

If you use Glycomass in a paper, preprint, thesis, or other research output,
please cite the software and state the version or commit used. For the hosted
service, also record your access date.

> Bärenfänger, Melissa, and Till, Christian. *Glycomass* [Computer software].
> https://github.com/christiantill/Glycomass

Citation metadata is available in [CITATION.cff](CITATION.cff) and through GitHub's
**Cite this repository** button.
Melissa Bärenfänger: [ORCID 0000-0002-2855-924X](https://orcid.org/0000-0002-2855-924X).

## Development and self-hosting

See [CONTRIBUTING.md](CONTRIBUTING.md) for local setup, tests, and contribution
guidance, or the [deployment guide](deploy/README.md) to run your own instance.

## License

Licensed under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for
attributions and the [vendored-library notices](src/glycomass/web/static/vendor/README.md)
for third-party licenses.
