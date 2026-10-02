# Performance timings

Expensive algorithm phases emit structured `operation_timing` logs. Operations
lasting at least `GLYCOMASS_SLOW_OPERATION_MS` (default **1000 ms**) emit WARNING;
faster operations emit DEBUG. Set `GLYCOMASS_LOG_LEVEL=DEBUG` to inspect every
phase. A threshold of zero temporarily logs all instrumented phases at WARNING.
Keep INFO/WARNING enabled to receive slow-operation warnings. For Kamal, set
these variables under `env.clear` in `config/deploy.yml` and redeploy.

Events include `operation`, wall-clock `elapsed_ms`, `outcome`, and workload
counts. They do not include sequences, compositions, file contents, or filenames.
The parent identifier computation also includes its job ID. Durations include
scheduling/I/O waits; they are not CPU-time measurements or memory measurements.

| Operation | Workload fields | Cost to investigate |
| --- | --- | --- |
| `isotopes.variants` | requested peaks | Isotope distribution generation |
| `isotopes.gaussian` | peaks, sigma, grid points, peak-grid evaluations | O(P × G) time and O(P + G) memory for P isotope peaks and G grid points |
| `identifier.process` | spectra, total peaks, largest spectrum, glycopeptides, identified | Streams one spectrum at a time through parsing, oxonium selection, O(N log N) matching (no quadratic pair matrix) and writing; memory is O(N) for the largest spectrum, not the file |
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
and pass numerical parity checks. The identifier streams MGF files, so memory
follows the largest spectrum rather than the file size; see the deployment guide's
memory limits for measurements. Timing logs alone cannot detect high memory
consumption.

Staging observation after deployment: a tiny synthetic identifier job emitted
`identifier.job` at **1306.116 ms**. A separate diagnostic of the same synthetic
input measured the child phases in tens of milliseconds (reading about 41 ms,
other phases below 1 ms each). This suggests interpreter/library startup overhead
is significant for small jobs; the two runs are not an exact phase breakdown.
Investigate a reusable, bounded process pool if small-job latency matters, while
preserving cancellation and memory isolation. Do not move the computation back
onto the worker event loop.
