import numpy as np
import matplotlib.pyplot as plt
import uproot
from scipy.optimize import curve_fit
import re

# Histogram subtraction process:
#   1. Use dt = t11 - t10 for time between pulses; tBetweenEvents does not work.
#   2. Apply the same quality cuts to both samples.
#   3. Candidate/sample of interest: coinc11 == 0; second pulse is NOT coincident with another slab
#   4. Background/control sample: coinc11 == 1; second pulse WAS coincident with another slab
#   5. Normalize the background sample to the late-time tail.
#   6. Subtract scaled background from candidate. 
#   7. Fit the subtracted spectrum.


# CUTS/SETTINGS:

# filename = "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi29Run4324_DiRPi33Run42_DiRPi34Run32.root"
# filename = "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi29Run4325_DiRPi33Run43_DiRPi34Run33.root"
filename = "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi29Run4326_DiRPi33Run44_DiRPi34Run34.root"
# filename = "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi29Run4327_DiRPi33Run45_DiRPi34Run35.root"
# filename = "/Users/bryceolsen/Desktop/Stuart Lab/Root Files/DiRPi29Run4328_DiRPi33Run46_DiRPi34Run36.root" #no dirpi33 key, doesn't work
tree_name = "dirpi33"

run_label = "DiRPi33 Run44" # optional descriptive label for titles and filenames; if None, will try to infer from filename

# dt histogram range
xmin = 0
xmax = 500
bins = 100
# integer number of ticks per bin to avoid aliasing; choose range and width accordingly

# Quality cuts
t10_min = 250
t10_max = 260
# first pulse in slab 2 has the correct raw time

dt_min = 50
dt_max = 500

V10_min = 30
V10_max = 999
#first pulse large enough to be a cosmic ray muon
V11_min = 30
V11_max = 999
#second pulse large enough to be a decay electron

# Background normalization region; This should be a late-time region where the real exponential is small and both samples are mostly background.
tail_norm_min = 350
tail_norm_max = 500

# Fit range for the background-subtracted histogram.
fit_min = 60
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
output_plot = f"/Users/bryceolsen/Desktop/Stuart Lab/Muon Lifetime/3script/results1/{safe_label}_dt_background_subtraction_fit.png"
log_output = f"/Users/bryceolsen/Desktop/Stuart Lab/Muon Lifetime/3script/results1/{safe_label}_dt_background_subtraction_log.png"
subtracted_plot = f"/Users/bryceolsen/Desktop/Stuart Lab/Muon Lifetime/3script/results1/{safe_label}_dt_background_subtraction_only.png"



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
# second pulse is NOT coincident with another slab
# coinc10 can be either 0 or 1
candidate_mask = base_cuts & (coinc11 == 0)

# Background/control sample:
# second pulse WAS coincident with another slab
# makes it less like a local decay pulse and more like background
background_mask = base_cuts & (coinc11 == 1)

#keeps only events meeting base cuts and coinc == 0 is true
dt_candidate = np.asarray(dt[candidate_mask], dtype=float)
#keeps only events meeting base cuts and coinc == 1 is true
dt_background = np.asarray(dt[background_mask], dtype=float)

#Cutflow:
print("\nCutflow")
print("-------")
print("Total tree entries:                 ", len(t10))
print("Valid t10/t11/dt:                   ", np.sum(valid))
print("After base quality cuts:            ", np.sum(base_cuts))
print("Candidate, coinc11 == 0:            ", np.sum(candidate_mask))
print("Background/control, coinc11 == 1:   ", np.sum(background_mask))

if len(dt_candidate) == 0:
    raise RuntimeError("No candidate events survived.")
if len(dt_background) == 0:
    raise RuntimeError("No background/control events survived.")

print("\nCandidate dt stats")
print("------------------")
print("min: ", np.min(dt_candidate))
print("max: ", np.max(dt_candidate))
print("mean:", np.mean(dt_candidate))

print("\nBackground dt stats")
print("-------------------")
print("min: ", np.min(dt_background))
print("max: ", np.max(dt_background))
print("mean:", np.mean(dt_background))



# HISTOGRAMS AND BACKGROUND SUBTRACTION:

# Build histograms of dt for the selected candidate and background samples.
# - dt_candidate and dt_background contain the time differences for events
#   that pass the quality cuts and the coinc11 selection.
# - np.histogram returns the counts in each bin and the bin edge values.
# - The histogram range is fixed from xmin to xmax to ensure both histograms
#   share the same binning and are directly comparable.
counts_candidate, edges = np.histogram(dt_candidate, bins=bins, range=(xmin, xmax))
counts_background, _ = np.histogram(dt_background, bins=bins, range=(xmin, xmax))

# Compute the bin centers from the returned edges. These centers are used for
# plotting the step histograms and for fitting later on.
centers = 0.5 * (edges[:-1] + edges[1:])

# The width of each histogram bin is the difference between consecutive edges.
# It is useful for diagnostic output or if the analysis needs to convert counts
# to a rate per tick or per unit time.
bin_width = edges[1] - edges[0]

# Select the late-time tail region where both the candidate and background samples are dominated by random or accidental coincidences.
tail_mask = (centers >= tail_norm_min) & (centers <= tail_norm_max)

# Sum the counts in the tail region for each sample. 
# Used to determine relative normalization needed to make the background shape match the candidate shape in late-time tail.
# This gives us the scale factor to apply to the background histogram before subtraction.
candidate_tail = np.sum(counts_candidate[tail_mask])
background_tail = np.sum(counts_background[tail_mask])

if background_tail > 0:
    bg_scale = candidate_tail / background_tail
else:
    bg_scale = 1.0
    print("\nWARNING: background tail has zero counts. Using bg_scale = 1.")

print("\nBackground normalization")
print("------------------------")
print(f"Tail normalization region: {tail_norm_min} to {tail_norm_max} ticks")
print(f"Candidate tail counts:     {candidate_tail}")
print(f"Background tail counts:    {background_tail}")
print(f"Background scale factor:   {bg_scale:.6g}")

# Scale the background histogram so its late-time tail matches the candidate.
# Then subtract to hopefully isolate real stopped-muon decays in the candidate sample.
counts_background_scaled = bg_scale * counts_background
counts_subtracted = counts_candidate - counts_background_scaled

# Propagate Poisson uncertainties through the subtraction.
# For S = C - alpha * B, the uncertainty is sqrt(C + alpha^2 B).
# This neglects uncertainty in alpha from the tail normalization itself,
# but it is a reasonable first approximation for counting errors.
sigma_subtracted = np.sqrt(counts_candidate + (bg_scale ** 2) * counts_background)


# Choose the bins to include in the fit.
# - Must lie inside the chosen fit window [fit_min, fit_max].
# - Must have positive subtracted counts, because the fit model is defined for positive rates.
# - Must have nonzero uncertainty so that weighted least squares behaves well.
fit_mask = (
    (centers >= fit_min)
    & (centers <= fit_max)
    & (counts_subtracted > 0)
    & (sigma_subtracted > 0)
)

xfit = centers[fit_mask]
yfit = counts_subtracted[fit_mask]
sigma_fit = sigma_subtracted[fit_mask]

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

    # Leaves the fitted lifetime in ticks. Variable names still use "us" to indicate this is the lifetime estimate 
    # we will report as the final result, even though it is still in ticks. 
    # This makes it easy to change the conversion later if we want to report in microseconds instead of ticks, 
    # without having to change all the variable names and print statements.
    tau_us = tau_fit
    tau_us_err = tau_err

    # The slope of the exponential is the negative inverse lifetime.
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
    print(f"Fit range:    {fit_min} to {fit_max} ticks")
    print(f"Bin width:    {bin_width:.4g} ticks")
    print(f"A:            {A_fit:.4g} ± {A_err:.4g}")
    print(f"tau:          {tau_fit:.4g} ± {tau_err:.4g} ticks")
    # print(f"tau:          {tau_us:.4g} ± {tau_us_err:.4g} microseconds") #uncomment when reporting in microseconds
    print(f"slope:        {slope_us:.4g} ± {slope_us_err:.4g} per tick")
    # print(f"slope:        {slope_us:.4g} ± {slope_us_err:.4g} per tick") #uncomment when reporting slope in microseconds⁻¹
    print(f"B:            {B_fit:.4g} ± {B_err:.4g}")
    print(f"chi2 / ndf:   {chi2:.4g} / {ndf}")
    print(f"reduced chi2: {reduced_chi2:.4g}")


# PLOT FIT AND SUBTRACTION RESULTS:

# Draw the candidate and scaled background histograms, plus the background-subtracted result. 
# The step plots show raw bin counts, while the errorbar markers show the subtracted spectrum with propagated uncertainties.
plt.figure(figsize=(10, 6))
plt.grid(True, which='both', axis='both', linestyle=':', linewidth=0.5, color='#666666', alpha=0.6)

plt.step(
    centers,
    counts_candidate,
    where="mid",
    linewidth=1.5,
    label="Candidate: coinc11 = 0",
)

plt.step(
    centers,
    counts_background_scaled,
    where="mid",
    linewidth=1.5,
    label=f"Scaled background: coinc11 = 1, scale={bg_scale:.3g}",
)

plt.errorbar(
    centers,
    counts_subtracted,
    yerr=sigma_subtracted,
    fmt=".",
    markersize=4,
    capsize=2,
    label="Candidate - scaled background",
)

if did_fit:
    # Plot the fitted model over a smooth x grid so the curve appears continuous.
    x_smooth = np.linspace(fit_min, fit_max, 1000)

    if fit_model == "exp_only":
        y_smooth = exp_only_shifted(x_smooth, *popt)
    elif fit_model == "exp_const":
        y_smooth = exp_plus_const_shifted(x_smooth, *popt)

    plt.plot(
        x_smooth,
        y_smooth,
        linewidth=2,
        label="Fit to subtracted spectrum",
    )

    # Mark the fit range on the plot so it is easy to see which bins were used.
    plt.axvline(fit_min, linestyle="--", linewidth=1, label="Fit range")
    plt.axvline(fit_max, linestyle="--", linewidth=1)

    fit_text = (
        f"tau = {tau_fit:.3g} ± {tau_err:.2g} ticks\n"
        # f"tau = {tau_us:.3g} ± {tau_us_err:.2g} μs\n" #uncomment when reporting in microseconds
        f"slope = {slope_us:.3g} ± {slope_us_err:.2g} ticks⁻¹\n" 
        # f"slope = {slope_us:.3g} ± {slope_us_err:.2g} μs⁻¹\n" #uncomment when reporting slope in microseconds⁻¹
        f"bg scale = {bg_scale:.3g}\n"
        f"χ²/ndf = {chi2:.3g}/{ndf}\n"
        f"reduced χ² = {reduced_chi2:.3g}"
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

plt.xlabel("dt = t11 - t10 [ticks]")
plt.ylabel("Counts")
plt.title(f"{run_label}: histogram subtraction using direct dt")
plt.legend()
plt.tight_layout()
plt.savefig(output_plot, dpi=200)
plt.show()

print("\nSaved plot:", output_plot)


# Create a focused plot showing only the background-subtracted spectrum.
# This keeps the same fit overlay and styling, but removes the candidate and
# scaled background histograms so the subtracted result is the only dataset.
plt.figure(figsize=(10, 6))
plt.grid(True, which='both', axis='both', linestyle=':', linewidth=0.5, color='#666666', alpha=0.6)

plt.errorbar(
    centers,
    counts_subtracted,
    yerr=sigma_subtracted,
    fmt='.',
    markersize=4,
    capsize=2,
    label='Candidate - scaled background',
)

if did_fit:
    plt.plot(
        x_smooth,
        y_smooth,
        linewidth=2,
        label='Fit to subtracted spectrum',
    )
    plt.axvline(fit_min, linestyle='--', linewidth=1, label='Fit range')
    plt.axvline(fit_max, linestyle='--', linewidth=1)
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

plt.xlabel("dt = t11 - t10 [ticks]")
plt.ylabel("Counts")
plt.title(f"{run_label}: background-subtracted spectrum only")
plt.legend()
plt.tight_layout()
plt.savefig(subtracted_plot, dpi=200)
plt.show()

print(f"\nSaved plot: {subtracted_plot}")


# Create a log-scale version of the subtraction plot to inspect the tail and
# low-count regions. On a log axis we only display values that correspond to
# one or more effective counts, because fractional values below 1 are not
# physically interpretable as integer counts.
plt.figure(figsize=(10, 6))
plt.grid(True, which='both', axis='both', linestyle=':', linewidth=0.5, color='#666666', alpha=0.6)

candidate_log = np.where(counts_candidate >= 1, counts_candidate, np.nan)
background_log = np.where(counts_background_scaled >= 1, counts_background_scaled, np.nan)
subtracted_log = np.where(counts_subtracted >= 1, counts_subtracted, np.nan)
positive_sub = counts_subtracted >= 1

plt.step(
    centers,
    candidate_log,
    where="mid",
    linewidth=1.5,
    label="Candidate: coinc11 = 0",
)

plt.step(
    centers,
    background_log,
    where="mid",
    linewidth=1.5,
    label=f"Scaled background: coinc11 = 1, scale={bg_scale:.3g}",
)

lower_err = np.minimum(
    sigma_subtracted[positive_sub],
    subtracted_log[positive_sub] - 1,
)
upper_err = sigma_subtracted[positive_sub]

plt.errorbar(
    centers[positive_sub],
    subtracted_log[positive_sub],
    yerr=np.vstack((lower_err, upper_err)),
    fmt=".",
    markersize=4,
    capsize=2,
    label="Candidate - scaled background (>=1 count)",
)

if did_fit:
    # Plot the same fitted exponential model on the log-scale plot. On a log
    # y-axis, an exponential curve appears as a straight line, and this uses
    # exactly the same fit parameters as the linear plot above.
    plt.plot(
        x_smooth,
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
plt.xlabel("dt = t11 - t10 [ticks]")
plt.ylabel("Counts")
plt.title(f"{run_label}: histogram subtraction, log scale")
plt.legend()
plt.tight_layout()
plt.savefig(log_output, dpi=200)
plt.show()

print(f"Saved plot: {log_output}")