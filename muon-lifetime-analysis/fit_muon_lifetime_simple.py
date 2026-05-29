import numpy as np
import matplotlib.pyplot as plt
import uproot
from scipy.optimize import curve_fit
import re

# Simple candidate-only lifetime fit:
#   1. Use dt = t11 - t10 for time between pulses.
#   2. Apply quality cuts to select candidate events.
#   3. Candidate events require coinc10 == 0 AND coinc11 == 0.
#   4. Build a single dt histogram from the candidate sample.
#   5. Fit that histogram with an exponential plus constant.


# CUTS/SETTINGS:

# filename = "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi29Run4324_DiRPi33Run42_DiRPi34Run32.root"
# filename = "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi29Run4325_DiRPi33Run43_DiRPi34Run33.root"
# filename = "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi29Run4326_DiRPi33Run44_DiRPi34Run34.root"
# filename = "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi29Run4327_DiRPi33Run45_DiRPi34Run35.root"
# filename = "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi29Run4328_DiRPi33Run46_DiRPi34Run36.root" #no dirpi33 key, doesn't work
filename = "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi35Run36_DiRPi29Run4351_DiRPi33Run64.root"
# filename = "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi35Run37_DiRPi29Run4352_DiRPi33Run65.root"
# filename = "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi35Run39_DiRPi29Run4353_DiRPi33Run66.root"
tree_name = "dirpi33"

run_label = "DiRPi33 Run64" # optional descriptive label for titles and filenames; if None, will try to infer from filename

# dt histogram range
xmin = 0
xmax = 500
bins = 20
# integer number of ticks per bin to avoid aliasing; choose range and width accordingly

# Quality cuts
t10_min = 250
t10_max = 260
# first pulse in slab 2 has the correct raw time

dt_min = 75
dt_max = 500

V10_min = 30
V10_max = 999
#first pulse large enough to be a cosmic ray muon
V11_min = 40
V11_max = 999
#second pulse large enough to be a decay electron

# Background normalization region; This should be a late-time region where the real exponential is small and both samples are mostly background.
tail_norm_min = 350
tail_norm_max = 500

# Fit range for the background-subtracted histogram.
fit_min = 40
fit_max = 500

# Conversion: 1 tick = 25 ns = 0.025 microseconds
tick_us = 0.025

# RUN LABEL / IDENTIFIER
# Set "run_label" to a descriptive string for titles and filenames. 
# If left as None, the script will try to infer a label from the input filename.

def infer_run_label(path: str) -> str:
    """Try to extract a run tag from the full filepath.

    Looks for tokens like 'DiRPi33Run44' and converts them to 'DiRPi33 Run44'.
    If nothing matches, falls back to the filename without extension.
    """
    base = path.rsplit("/", 1)[-1]
    # look for tokens that include 'Run' followed by digits
    m = re.search(r"([A-Za-z0-9_]+Run[0-9]+)", base)
    if m:
        tag = m.group(1)
        # insert space before 'Run' and replace underscores with spaces
        tag = re.sub(r"Run", " Run", tag)
        tag = tag.replace("_", " ")
        return tag
    # fallback: filename without extension
    return base.rsplit(".", 1)[0].replace("_", " ")

# determine the run label to use in titles and filenames
run_label = run_label or infer_run_label(filename)
safe_label = run_label.replace(" ", "_")

# filenames for outputs use the safe label so they change automatically
# change the directory as desired; currently matches previous hardcoded path
output_plot = f"/Users/bryceolsen/Desktop/Stuart Lab/Muon Lifetime/3script/results3/{safe_label}_dt_candidate_fit_20bins.png"
log_output = f"/Users/bryceolsen/Desktop/Stuart Lab/Muon Lifetime/3script/results3/{safe_label}_dt_candidate_log_20bins.png"



# MODEL FUNCTIONS:

def exp_plus_const_shifted(x, A, tau, B):
    """
    Exponential decay plus constant background.

    Shifted form:
        N(x) = A * exp(-(x - fit_min)/tau) + B

    tau is in ticks.
    """
    return A * np.exp(-(x - fit_min) / tau) + B


def exp_only_shifted(x, A, tau):
    """
    Pure exponential.

    Use this if the background subtraction is good enough that the
    residual constant background should be near zero.
    """
    return A * np.exp(-(x - fit_min) / tau)

fit_model = "exp_const"
#fit_model = "exp_only"
# "exp_const" = exponential + constant background
# "exp_only"  = pure exponential after subtraction



# OPEN/READ ROOT FILE:

print("\nOpening ROOT file:")
print(filename)

#open chosen root file using uproot
f = uproot.open(filename)
tree = f[tree_name]

print("Using tree:", tree_name)
print("Number of entries:", tree.num_entries) #diagnostic

#varibles pulled from trees
t10 = tree["t10"].array(library="np") #channel 1, slab 2, pulse 1, raw time
t11 = tree["t11"].array(library="np") #channel 1, slab 2, pulse 2, raw time

V10 = tree["V10"].array(library="np")
V11 = tree["V11"].array(library="np")

coinc10 = tree["coinc10"].array(library="np")
coinc11 = tree["coinc11"].array(library="np")

# lifetime variable; time between first and second pulse in slab 2
dt = t11 - t10



# DEFINE AND MAKE CUTS:

# np.isfinite(x) means x is not NaN and not infinity.
# t10 and t11 exist; dt is positive
# simply filters usable events
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

#cut according to settings at the top of the script
base_cuts = (
    valid

    #requires first pulse to happened within the expected trigger window
    & (t10 >= t10_min) 
    & (t10 <= t10_max)

    #requires dt to be in set window
    & (dt >= dt_min)
    & (dt <= dt_max)

    #removes tiny and huge/saturated pulses from first pulse
    & (V10 >= V10_min)
    & (V10 <= V10_max)

    #removes tiny and huge/saturated pulses from second pulse
    & (V11 >= V11_min)
    & (V11 <= V11_max)
)

# Candidate/sample of interest; we think this sample has the true stopped-muon decay events
# require that neither pulse had a coincidence in slab 3 (no activity in channel 2)
# select events where coinc10 == 0 AND coinc11 == 0
candidate_mask = base_cuts & (coinc10 == 0) & (coinc11 == 0)

# keeps only events meeting base cuts and candidate selection
dt_candidate = np.asarray(dt[candidate_mask], dtype=float)

#Cutflow:
print("\nCutflow")
print("-------")
print("Total tree entries:                 ", len(t10))
print("Valid t10/t11/dt:                   ", np.sum(valid))
print("After base quality cuts:            ", np.sum(base_cuts))
print("Candidate, coinc10 == 0 AND coinc11 == 0:", np.sum(candidate_mask))

if len(dt_candidate) == 0:
    raise RuntimeError("No candidate events survived.")

print("\nCandidate dt stats")
print("------------------")
print("min: ", np.min(dt_candidate))
print("max: ", np.max(dt_candidate))
print("mean:", np.mean(dt_candidate))


# HISTOGRAMS AND FITTING:

# Build a histogram of dt for the candidate sample only.
# - dt_candidate contains the time differences for candidate events
#   that pass the quality cuts and the coincidence selection.
# - np.histogram returns the counts in each bin and the bin edge values.
counts_candidate, edges = np.histogram(dt_candidate, bins=bins, range=(xmin, xmax))

# Compute the bin centers from the returned edges. These centers are used for
# plotting the step histogram and for fitting later on.
centers = 0.5 * (edges[:-1] + edges[1:])
# also create microsecond-scaled centers for plotting (1 tick = tick_us μs)
centers_us = centers * tick_us

# The width of each histogram bin is the difference between consecutive edges.
# It is useful for diagnostic output or if the analysis needs to convert counts
# to a rate per tick or per unit time.
bin_width = edges[1] - edges[0]

# Choose the bins to include in the fit.
# - Must lie inside the chosen fit window [fit_min, fit_max].
# - Must have positive counts, because the fit model is defined for positive rates.
# - Must have nonzero uncertainty so that weighted least squares behaves well.
fit_mask = (
    (centers >= fit_min)
    & (centers <= fit_max)
    & (counts_candidate > 0)
)

xfit = centers[fit_mask]
yfit = counts_candidate[fit_mask]
sigma_fit = np.sqrt(counts_candidate[fit_mask])

did_fit = False

if len(xfit) < 5:
    print("\nNot enough positive bins to fit the subtracted histogram.")
    print("Try changing fit_min/fit_max, bins, or the background normalization region.")
    print("Positive bins in fit range:", len(xfit))
else:
    # Use the maximum selected bin count and a lifetime guess as starting parameters for the fit.
    A_guess = np.max(yfit)
    tau_guess = 88.0 # 88 ticks initial guess

    if fit_model == "exp_only":
        # Fit a pure exponential if the residual background should be small.
        p0 = [A_guess, tau_guess]
        bounds = ([0, 1], [np.inf, np.inf])

        popt, pcov = curve_fit(
            exp_only_shifted,
            xfit,
            yfit,
            p0=p0,
            sigma=sigma_fit,
            absolute_sigma=True,
            bounds=bounds,
            maxfev=20000,
        )

        A_fit, tau_fit = popt
        A_err, tau_err = np.sqrt(np.diag(pcov))
        B_fit = 0.0
        B_err = 0.0

        y_model = exp_only_shifted(xfit, *popt)

    else:
        # Fit exponential plus constant background if the subtracted spectrum still retains a constant offset.
        B_guess = max(np.min(yfit), 0)
        p0 = [A_guess, tau_guess, B_guess]
        bounds = ([0, 1, 0], [np.inf, np.inf, np.inf])

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

        A_fit, tau_fit, B_fit = popt
        A_err, tau_err, B_err = np.sqrt(np.diag(pcov))

        y_model = exp_plus_const_shifted(xfit, *popt)

    # Convert the fitted lifetime from ticks to microseconds. 
    # Uncomment this and recomment the next block if you want to report the lifetime in microseconds instead of ticks.
    # tau_us = tau_fit * tick_us
    # tau_us_err = tau_err * tick_us

    # Convert the fitted lifetime from ticks to microseconds and compute slope in μs^-1.
    tau_us = tau_fit * tick_us
    tau_us_err = tau_err * tick_us

    # The slope of the exponential is the negative inverse lifetime (per microsecond).
    slope_us = -1 / tau_us
    slope_us_err = tau_us_err / (tau_us ** 2)

    # Compute chi-squared to evaluate fit quality.
    chi2 = np.sum(((yfit - y_model) / sigma_fit) ** 2)
    ndf = len(yfit) - len(popt)
    reduced_chi2 = chi2 / ndf if ndf > 0 else np.nan

    did_fit = True

    print("\nFit results")
    print("-----------")
    print(f"Fit model:    {fit_model}")
    fit_min_us = fit_min * tick_us
    fit_max_us = fit_max * tick_us
    bin_width_us = bin_width * tick_us
    print(f"Fit range:    {fit_min_us:.4g} to {fit_max_us:.4g} μs")
    print(f"Bin width:    {bin_width_us:.4g} μs")
    print(f"A:            {A_fit:.4g} ± {A_err:.4g}")
    print(f"tau:          {tau_us:.4g} ± {tau_us_err:.4g} microseconds")
    print(f"slope:        {slope_us:.4g} ± {slope_us_err:.4g} per microsecond")
    print(f"B:            {B_fit:.4g} ± {B_err:.4g}")
    print(f"chi2 / ndf:   {chi2:.4g} / {ndf}")
    print(f"reduced chi2: {reduced_chi2:.4g}")


# PLOT FIT RESULTS:

# Draw the candidate histogram and the fitted exponential model.
plt.figure(figsize=(10, 6))
plt.grid(True, which='both', axis='both', linestyle=':', linewidth=0.5, color='#666666', alpha=0.6)

plt.step(
    centers_us,
    counts_candidate,
    where='mid',
    linewidth=1.5,
    label='Candidate: coinc10 = 0 & coinc11 = 0',
)

plt.errorbar(
    centers_us,
    counts_candidate,
    yerr=np.sqrt(counts_candidate),
    fmt='.',
    markersize=4,
    capsize=2,
    label='Candidate counts',
)

if did_fit:
    x_smooth = np.linspace(fit_min, fit_max, 1000)
    x_smooth_us = x_smooth * tick_us

    if fit_model == 'exp_only':
        y_smooth = exp_only_shifted(x_smooth, *popt)
    else:
        y_smooth = exp_plus_const_shifted(x_smooth, *popt)

    plt.plot(
        x_smooth_us,
        y_smooth,
        linewidth=2,
        label='Fit to candidate histogram',
    )

    plt.axvline(fit_min_us, linestyle='--', linewidth=1, label='Fit range')
    plt.axvline(fit_max_us, linestyle='--', linewidth=1)

    fit_text = (
        f'tau = {tau_us:.3g} ± {tau_us_err:.2g} μs\n'
        f'slope = {slope_us:.3g} ± {slope_us_err:.2g} μs⁻¹\n'
        f'χ²/ndf = {chi2:.3g}/{ndf}\n'
        f'reduced χ² = {reduced_chi2:.3g}'
    )

    plt.text(
        0.97,
        0.95,
        fit_text,
        transform=plt.gca().transAxes,
        ha='right',
        va='top',
        fontsize=9,
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.85),
    )

plt.xlabel('dt = t11 - t10 [μs]')
plt.ylabel('Counts')
plt.title(f'{run_label}: candidate-only dt histogram fit')
plt.legend()
plt.tight_layout()
plt.savefig(output_plot, dpi=200)
plt.show()

print('\nSaved plot:', output_plot)

# Create a log-scale version of the candidate histogram to inspect the tail and
# low-count regions. On a log axis we only display values that correspond to
# one or more counts, because fractional values below 1 are not physically
# interpretable as integer counts.
plt.figure(figsize=(10, 6))
plt.grid(True, which="both", axis="both", linestyle=":", linewidth=0.5, color="#666666", alpha=0.6)

candidate_log = np.where(counts_candidate >= 1, counts_candidate, np.nan)
positive_candidate = counts_candidate >= 1

plt.step(
    centers_us,
    candidate_log,
    where="mid",
    linewidth=1.5,
    label="Candidate: coinc10 = 0 & coinc11 = 0",
)

plt.errorbar(
    centers_us[positive_candidate],
    candidate_log[positive_candidate],
    yerr=np.sqrt(candidate_log[positive_candidate]),
    fmt=".",
    markersize=4,
    capsize=2,
    label="Candidate counts (>=1)",
)

if did_fit:
    plt.plot(
        x_smooth_us,
        y_smooth,
        linestyle="--",
        linewidth=2,
        label="Same fit model as linear plot",
    )
    plt.text(
        0.97,
        0.95,
        fit_text,
        transform=plt.gca().transAxes,
        ha="right",
        va="top",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
    )

plt.yscale("log")
ax = plt.gca()
ax.set_ylim(0.9, ax.get_ylim()[1])
plt.xlabel("dt = t11 - t10 [μs]")
plt.ylabel("Counts")
plt.title(f"{run_label}: candidate-only histogram, log scale")
plt.legend()
plt.tight_layout()
plt.savefig(log_output, dpi=200)
plt.show()

print(f"Saved plot: {log_output}")
