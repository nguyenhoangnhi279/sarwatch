# SARWatch

**Using NISAR observations to prioritize flood verification in Hue, Vietnam.**

Developed for NASA Space Apps 2026, *Dancing with the SARs*. SARWatch combines radar change analysis, optical reference imagery and population/infrastructure intersections in an interactive website.

## Run the application

On Windows, double-click **start.bat** to open the self-contained HTML version. This mode requires no Python or local server.

To use the Python server and its APIs, install Python 3.11+ and run:

```bash
python run.py --open
```

Alternatively, run `start.bat --server` on Windows. Select another port with `python run.py --port 8001 --open`.

## Repository structure

| Directory | Contents |
|---|---|
| `app/` | Website, bundled fonts, standalone HTML and Python server |
| `data/` | Original inputs, trained model, analysis products and checksum manifest |
| `pipeline/` | Scientific processing, shared algorithms and analysis notebook |
| `dev/` | Build tools, tests, data collectors and development configuration |
| `docs/` | Methods, evaluation, limitations and data attribution |

## Commands

| Command | Purpose |
|---|---|
| `python run.py --open` | Start the server and open the website |
| `python run.py check` | Verify required files and checksums |
| `python run.py build` | Rebuild `app/standalone/index.html` |
| `python run.py reproduce` | Rerun the scientific analysis |
| `python run.py test` | Run repository checks and Python tests |
| `python run.py package` | Package the project for another computer |

## Scientific environment

Use Python 3.11 and install the dependencies before reproducing the analysis:

```bash
python -m venv dev/.venv
# Windows
dev/.venv/Scripts/python -m pip install -r requirements.txt
dev/.venv/Scripts/python run.py reproduce
# macOS/Linux: use dev/.venv/bin/python instead
```

For interface tests, use Node.js 24:

```bash
npm --prefix dev ci
npm --prefix dev run test:ui
```

## Data and findings

The published NISAR case uses observations from 15 and 27 October 2026. It contains 1,646 screened candidate regions covering 9.3045 km². Estimated population exposure is approximately 1,681 people on valid population cells, which cover only 60.5% of candidate area. Mapped road intersections total approximately 18.689 km. These are conditional exposure estimates, not confirmed flood impacts.

A Random Forest achieves F1 0.8825 against automated Sentinel-2 water labels, compared with 0.8560 for Otsu, using a spatially held-out test set. This measures optical-water label agreement, not flood-warning accuracy. The separate local rerun produces 9.3809 km² of screened candidates and retains its own processing records.

The historical case includes its radar, optical, population and infrastructure inputs. New weather forecasts and optional online basemap imagery require internet access. Forecast archiving and Python APIs require the server.

## Documentation and licence

See [Methods and evaluation](docs/METHODOLOGY.md) for the processing protocol, results, limitations and sources.

Original source code is licensed under Apache 2.0; see [LICENSE](LICENSE). Third-party data and fonts retain their respective licences; see [NOTICE](NOTICE). SARWatch is a research prototype, not an operational emergency warning system.
