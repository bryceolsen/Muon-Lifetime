# Muon Lifetime Analysis

Python analysis for estimating the muon lifetime from DiRPi detector ROOT data.

This project analyzes delayed pulses in DiRPi33 ROOT trees to identify candidate stopped-muon decay events and fit the decay-time distribution to extract an estimate of the muon lifetime.

## Current Analysis Workflow

1. Read the DiRPi33 ROOT tree using `uproot`.

2. Compute the direct pulse separation:

   ```python
   dt = t11 - t10
   ```

3. Apply timing, pulse-height, and coincidence cuts.

4. Select strict stopped-muon candidate events.

5. Build a candidate-only `dt` histogram.

6. Fit the candidate histogram with an exponential plus constant background:

   ```math
   N(t) = A e^{-(t - t_{\min})/\tau} + B
   ```

7. Combine fitted lifetimes across usable runs with a weighted mean.

8. Estimate systematic uncertainty from reasonable variations in cuts and binning.

## Important Analysis Choice

The variable `tBetweenEvents` is **not used** in the current analysis.

Direct

```python
dt = t11 - t10
```

is used instead because `tBetweenEvents` was found not to match the desired pulse separation reliably for this analysis.

## Candidate Event Logic

The current strict candidate sample is:

```python
coinc10 == 0 and coinc11 == 0
```

This selects events where neither the first nor second slab-2 pulse was coincident with slab 3.

Current main candidate cuts:

```python
250 <= t10 <= 260
dt_min <= dt <= dt_max
V10_min <= V10 <= 999
V11_min <= V11 <= 999
coinc10 == 0
coinc11 == 0
```

The primary cut setting used for the current final estimate is:

```python
{"dt_min": 75, "dt_max": 500, "V10_min": 30, "V11_min": 40, "bins": 20}
```

This setting was chosen because it removes the early non-exponential region, keeps a moderate prompt-pulse threshold, tightens the delayed-pulse threshold, and gives stable fits across nearby reasonable settings.

## Current Result

Current preliminary estimate:

```text
tau_mu = 2.04 ± 0.06_stat ± 0.13_sys microseconds
```

Combining statistical and systematic uncertainties in quadrature:

```text
tau_mu = 2.04 ± 0.14 microseconds
```

Accepted free muon lifetime:

```text
tau_mu, accepted ≈ 2.197 microseconds
```

The measured value is slightly low but reasonably consistent given detector effects, cut dependence, material effects, and limited statistics.

## Scripts

Main candidate-only fit scripts:

```bash
python3 fit_muon_lifetime2.py
```
```bash
python3 fit_muon_lifetime_simple.py
```

Comparison-table / cut-scan script:

```bash
python3 fit_muon_lifetime_compare_table.py
```

The comparison script scans different values of:

* `dt_min`
* `dt_max`
* `V10_min`
* `V11_min`
* number of histogram bins

and records the fitted lifetime, statistical uncertainty, candidate count, and reduced chi-square.

## Dependencies

Install required Python packages with:

```bash
python3 -m pip install numpy matplotlib scipy uproot
```

Main packages used:

* `numpy`
* `matplotlib`
* `scipy`
* `uproot`

## Data

Raw ROOT data files are **not included** in this repository.

The code expects local ROOT files from the DiRPi detector setup. File paths should be edited inside the Python scripts to match the local machine.

## Notes

This repository contains analysis code and selected output summaries only. Large ROOT files, generated plots, and intermediate result folders should generally be excluded from GitHub using `.gitignore`.

Recommended `.gitignore` entries include:

```gitignore
*.root
__pycache__/
*.pyc
.DS_Store
results/
results*/
```
