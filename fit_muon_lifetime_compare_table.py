import os
import re
import csv
import numpy as np
import uproot
from scipy.optimize import curve_fit

# Comparison script: runs the candidate-only fit on multiple ROOT files and
# writes a CSV table with run label, bins, dt_min, V10_min, V11_min, tau (μs),
# tau_err (μs), chi2 and reduced_chi2. Does not save any plots.

# ---------------------- User-editable settings ----------------------
# List the ROOT files to compare here (edit as needed).
filenames = [
    "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi29Run4325_DiRPi33Run43_DiRPi34Run33.root",
    "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi29Run4326_DiRPi33Run44_DiRPi34Run34.root",
    "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi29Run4327_DiRPi33Run45_DiRPi34Run35.root",
    "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi35Run36_DiRPi29Run4351_DiRPi33Run64.root",
    "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi35Run37_DiRPi29Run4352_DiRPi33Run65.root",
    "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi35Run39_DiRPi29Run4353_DiRPi33Run66.root"
]

# Tree name inside the files
tree_name = "dirpi33"


# Histogram / fit settings (edit these to change the comparison)
xmin = 0
xmax = 500

# Quality cuts (these are the variables you will tweak between runs)
t10_min = 250
t10_max = 260
# (We use explicit combos via `combo_list` below.)

# upper limits (kept constant)
V10_max = 999
V11_max = 999

# Explicit parameter combinations to run. If this list is non-empty the script
# will iterate these combos instead of performing a Cartesian product of the
# individual parameter lists above. Edit this list manually to run specific
# combos.
combo_list = []

def add(dt_min, dt_max, V10_min, V11_min, bins):
    combo_list.append({
        "dt_min": dt_min,
        "dt_max": dt_max,
        "V10_min": V10_min,
        "V11_min": V11_min,
        "bins": bins,
    })


# ============================================================
# MAIN COUPLED THRESHOLD SCAN
# V10_min = V11_min
# Tests clean threshold choices with bin widths that divide 500.
# ============================================================

for Vmin in [30, 40, 50]:

    # bins = 20 gives 25 ticks/bin.
    # Use dt_min values that land on 25-tick bin edges.
    for dt_min in [50, 75, 100]:
        add(dt_min=dt_min, dt_max=500, V10_min=Vmin, V11_min=Vmin, bins=20)

    # bins = 25 gives 20 ticks/bin.
    # Use dt_min values that land on 20-tick bin edges.
    for dt_min in [60, 80, 100]:
        add(dt_min=dt_min, dt_max=500, V10_min=Vmin, V11_min=Vmin, bins=25)

    # bins = 50 gives 10 ticks/bin.
    # This allows the usual 50, 60, 70, 80, 90, 100 scan cleanly.
    for dt_min in [50, 60, 70, 80, 90, 100]:
        add(dt_min=dt_min, dt_max=500, V10_min=Vmin, V11_min=Vmin, bins=50)

    # bins = 100 gives 5 ticks/bin.
    # This is a finer-bin sanity check, not the main setting.
    for dt_min in [60, 80, 100]:
        add(dt_min=dt_min, dt_max=500, V10_min=Vmin, V11_min=Vmin, bins=100)


# ============================================================
# DECOUPLED V10/V11 THRESHOLD SCAN
# Tests whether the first-pulse and second-pulse thresholds should differ.
# Use fewer combinations here to keep the table manageable.
# ============================================================

decoupled_pairs = [
    (50, 30),
    (50, 40),
    (40, 30),
    (40, 50),
    (30, 40),
    (30, 50),
]

for V10_min, V11_min in decoupled_pairs:

    # Coarse but stable binning near the promising region.
    add(dt_min=75, dt_max=500, V10_min=V10_min, V11_min=V11_min, bins=20)

    # Medium binning.
    add(dt_min=80, dt_max=500, V10_min=V10_min, V11_min=V11_min, bins=25)

    # More detailed binning around the likely-good fit-start region.
    for dt_min in [70, 80, 90]:
        add(dt_min=dt_min, dt_max=500, V10_min=V10_min, V11_min=V11_min, bins=50)


# ============================================================
# LATE-TAIL / dt_max SENSITIVITY
# Tests whether the far tail is pulling the fit.
# Use the settings that look physically clean and promising.
# ============================================================

for bins in [20, 25, 50]:
    for dt_max in [350, 400, 450, 500]:
        # Match dt_min to the nearest clean bin edge for each bin choice.
        if bins == 20:
            add(dt_min=75, dt_max=dt_max, V10_min=50, V11_min=50, bins=bins)
        elif bins == 25:
            add(dt_min=80, dt_max=dt_max, V10_min=50, V11_min=50, bins=bins)
        elif bins == 50:
            add(dt_min=80, dt_max=dt_max, V10_min=50, V11_min=50, bins=bins)


# ============================================================
# BINNING EXTREME SANITY CHECKS
# These are not main-analysis settings. They test over-smoothing/fine-binning.
# ============================================================

add(dt_min=100, dt_max=500, V10_min=50, V11_min=50, bins=10)    # 50 ticks/bin, very coarse
add(dt_min=80,  dt_max=500, V10_min=50, V11_min=50, bins=125)   # 4 ticks/bin, very fine

# Fit range (in ticks)
fit_min = 40
fit_max = 500

# Conversion: 1 tick = 25 ns = 0.025 microseconds
tick_us = 0.025

# Output CSV
out_dir = os.path.join(os.path.dirname(__file__), "results4")
os.makedirs(out_dir, exist_ok=True)


def _sanitize(s: str) -> str:
    # make a filesystem-safe short token
    return re.sub(r"[^A-Za-z0-9_.-]", "", str(s))


def make_out_csv_name():
    # fixed output filename; all results are saved in a single table
    fname = "dirpi33 lifetime comparison table.csv"
    return os.path.join(out_dir, fname)


# deterministic output path based on current cut values
out_csv = make_out_csv_name()


def infer_run_label(path: str) -> str:
    base = path.rsplit("/", 1)[-1]
    m = re.search(r"([A-Za-z0-9_]+Run[0-9]+)", base)
    if m:
        tag = m.group(1)
        tag = re.sub(r"Run", " Run", tag)
        tag = tag.replace("_", " ")
        return tag
    return base.rsplit('.', 1)[0]


def exp_plus_const_shifted(x, A, tau, B):
    return A * np.exp(-(x - fit_min) / tau) + B


def analyze_file(filename: str, dt_min_in: int, dt_max_in: int, V10_min_in: int, V11_min_in: int, bins_in: int):
    # open file and extract arrays
    f = uproot.open(filename)
    # allow keys with cycle suffixes like 'dirpi33;1'
    available = list(f.keys())
    matching = [k for k in available if str(k).startswith(tree_name)]
    if not matching:
        print(f"Tree starting with '{tree_name}' not found in {filename}; available: {available}")
        # return a row with NaNs but include the parameter values we were asked to use
        return {
            "run_label": infer_run_label(filename),
            "bins": bins_in,
            "dt_min": dt_min_in,
            "dt_max": dt_max_in,
            "V10_min": V10_min_in,
            "V11_min": V11_min_in,
            "n_candidate": 0,
            "bin_width_ticks": float('nan'),
            "bin_width_us": float('nan'),
            "n_fit_bins": 0,
            "ndf": float('nan'),
            "tau_us": float('nan'),
            "tau_us_err": float('nan'),
            "chi2": float('nan'),
            "reduced_chi2": float('nan'),
        }
    tree = f[matching[0]]

    t10 = tree["t10"].array(library="np")
    t11 = tree["t11"].array(library="np")
    V10 = tree["V10"].array(library="np")
    V11 = tree["V11"].array(library="np")
    coinc10 = tree["coinc10"].array(library="np")
    coinc11 = tree["coinc11"].array(library="np")

    dt = t11 - t10

    valid = (
        np.isfinite(t10)
        & np.isfinite(t11)
        & np.isfinite(V10)
        & np.isfinite(V11)
        & np.isfinite(coinc10)
        & np.isfinite(coinc11)
        & np.isfinite(dt)
        & (t10 > 0)
        & (t11 > 0)
        & (dt > 0)
    )

    base_cuts = (
        valid
        & (t10 >= t10_min)
        & (t10 <= t10_max)
        & (dt >= dt_min_in)
        & (dt <= dt_max_in)
        & (V10 >= V10_min_in)
        & (V10 <= V10_max)
        & (V11 >= V11_min_in)
        & (V11 <= V11_max)
    )

    candidate_mask = base_cuts & (coinc10 == 0) & (coinc11 == 0)
    dt_candidate = np.asarray(dt[candidate_mask], dtype=float)

    # histogram
    counts_candidate, edges = np.histogram(dt_candidate, bins=bins_in, range=(xmin, xmax))
    centers = 0.5 * (edges[:-1] + edges[1:])

    bin_width = edges[1] - edges[0]
    bin_width_us = bin_width * tick_us

    # fit mask
    fit_mask = (
        (centers >= fit_min)
        & (centers <= fit_max)
        & (counts_candidate > 0)
    )

    xfit = centers[fit_mask]
    yfit = counts_candidate[fit_mask]
    sigma_fit = np.sqrt(counts_candidate[fit_mask])

    result = {
        "run_label": infer_run_label(filename),
        "bins": bins_in,
        "dt_min": dt_min_in,
        "dt_max": dt_max_in,
        "V10_min": V10_min_in,
        "V11_min": V11_min_in,
        "n_candidate": int(len(dt_candidate)),
        "tau_us": float('nan'),
        "tau_us_err": float('nan'),
        "chi2": float('nan'),
        "reduced_chi2": float('nan'),
    }

    # include bin width and fit-bin info even if we skip fitting
    result.update({
        "bin_width_ticks": float(bin_width),
        "bin_width_us": float(bin_width_us),
        "n_fit_bins": int(len(xfit)),
    })

    if len(xfit) < 5:
        return result

    # initial guesses
    A_guess = np.max(yfit)
    tau_guess = 88.0
    B_guess = max(np.min(yfit), 0.0)

    p0 = [A_guess, tau_guess, B_guess]
    bounds = ([0, 1, 0], [np.inf, np.inf, np.inf])

    try:
        popt, pcov = curve_fit(
            exp_plus_const_shifted,
            xfit,
            yfit,
            p0=p0,
            sigma=sigma_fit,
            absolute_sigma=True,
            bounds=bounds,
            maxfev=20000,
        )
    except Exception:
        return result

    A_fit, tau_fit, B_fit = popt
    A_err, tau_err, B_err = np.sqrt(np.diag(pcov))

    y_model = exp_plus_const_shifted(xfit, *popt)

    tau_us = tau_fit * tick_us
    tau_us_err = tau_err * tick_us

    chi2 = np.sum(((yfit - y_model) / sigma_fit) ** 2)
    ndf = len(yfit) - len(popt)
    reduced_chi2 = chi2 / ndf if ndf > 0 else float('nan')

    result.update({
        "ndf": int(ndf) if ndf >= 0 else float('nan'),
        "tau_us": float(tau_us),
        "tau_us_err": float(tau_us_err),
        "chi2": float(chi2),
        "reduced_chi2": float(reduced_chi2),
    })

    return result


def main():
    rows = []
    if not ('combo_list' in globals() and combo_list):
        print("No combos defined in combo_list — add combinations at the top of the script and rerun.")
        return

    for combo in combo_list:
        dt_min = combo['dt_min']
        dt_max = combo['dt_max']
        bins = combo['bins']
        V10_min = combo['V10_min']
        V11_min = combo['V11_min']
        for fn in filenames:
            if not os.path.exists(fn):
                print(f"File not found, skipping: {fn}")
                continue
            print(f"Processing: {fn}  dt=({dt_min},{dt_max}) bins={bins} V10min={V10_min} V11min={V11_min}")
            res = analyze_file(fn, dt_min_in=dt_min, dt_max_in=dt_max, V10_min_in=V10_min, V11_min_in=V11_min, bins_in=bins)
            rows.append(res)

    # write CSV
    fieldnames = [
        "run_label",
        "bins",
        "bin_width_ticks",
        "bin_width_us",
        "dt_min",
        "dt_max",
        "V10_min",
        "V11_min",
        "n_candidate",
        "n_fit_bins",
        "ndf",
        "tau_us",
        "tau_us_err",
        "chi2",
        "reduced_chi2",
    ]

    with open(out_csv, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, '') for k in fieldnames})

    # print CSV to console for quick inspection
    print('\nComparison results:')
    with open(out_csv, 'r') as f:
        print(f.read())

    print(f"Saved CSV: {out_csv}")


if __name__ == '__main__':
    main()
