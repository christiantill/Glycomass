# Performance timings

Expensive algorithm phases emit structured `operation_timing` logs. Operations
lasting at least `GLYCOMASS_SLOW_OPERATION_MS` (default **1000 ms**) emit WARNING;
faster operations emit DEBUG. Set `GLYCOMASS_LOG_LEVEL=DEBUG` to inspect every
phase. A threshold of zero temporarily logs all instrumented phases at WARNING.
Keep INFO/WARNING enabled to receive slow-operation warnings.

Events include `operation`, wall-clock `elapsed_ms`, `outcome`, and workload
counts. They do not include sequences, compositions, file contents, or filenames.
The parent identifier computation also includes its job ID. Durations include
scheduling/I/O waits; they are not CPU-time measurements or memory measurements.

| Operation | Workload fields | Cost to investigate |
| --- | --- | --- |
| `isotopes.variants` | requested peaks | Isotope distribution generation |
| `isotopes.gaussian` | peaks, sigma, grid points, peak-grid evaluations | O(P × G) time and O(P + G) memory for P isotope peaks and G grid points |
| `identifier.read` | spectra, total peaks, largest spectrum | Whole-file parsing; O(T) retained peak data for T peaks |
| `identifier.select` | spectra | Oxonium selection over all peaks |
| `identifier.match_and_filter` | selected spectra and total peaks | O(N log N) time and O(N) memory per spectrum; no quadratic pair matrix |
| `identifier.write` | identified spectra | Result serialization and disk I/O |
| `identifier.job` | job ID | Child startup plus complete MGF computation; excludes DB commits |

Both web and worker startup configure logging. Child-process timings use stderr,
leaving stdout exclusively for the JSON result protocol. The parent relays child
stderr when computation completes; these phase logs are not live progress reports.
No per-peak or per-spectrum events are emitted. Docker captures the logs; inspect
`docker logs --since 15m <web-or-worker-container>` on the server.

## Initial measurements and remaining work

A local development-machine check on 2026-09-14 (Python 3.14, three repetitions,
median wall time) measured the following synthetic workloads. These are local
baselines, not production latency guarantees:

- Protein `ACDEFGHIKLMNPQRSTVWY` repeated ten times, charge 1: low resolution
  1.91 ms, medium 16.48 ms, super high 48.15 ms.
- Fragment matching on sorted peaks spaced 0.1 m/z apart, using m/z as intensity:
  1,000 peaks 0.29 ms; 10,000 peaks 2.40 ms; 100,000 peaks 49.18 ms.

These samples do not show second-long execution, but they do not exercise large
real uploads or concurrent web calculations. Higher-resolution Gaussian grids
remain the main nested numerical loop. Narrow-window evaluation/caching could
reduce its cost, but must preserve the existing most-abundant-m/z grid behavior
and pass numerical parity checks. MGF parsing and output construction still retain
the whole file and selected results; streaming is the next memory improvement to
investigate with representative large datasets. Timing logs alone cannot detect
high memory consumption.
