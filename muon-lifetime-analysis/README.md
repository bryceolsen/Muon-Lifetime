# Muon Lifetime Analysis

Python analysis for estimating the muon lifetime from DiRPi detector ROOT data.

The workflow:
1. Read the DiRPi33 ROOT tree with uproot.
2. Compute direct pulse separation: dt = t11 - t10.
3. Apply timing, pulse-height, and coincidence cuts.
4. Build candidate and background/control histograms.
5. Normalize background in the late-time tail.
6. Subtract scaled background.
7. Fit the subtracted spectrum to an exponential plus constant.

Current candidate logic:
- candidate sample: coinc11 == 0
- background/control sample: coinc11 == 1
- coinc10 unrestricted
- direct dt = t11 - t10
- tBetweenEvents is not used

Dependencies:
python3 -m pip install numpy matplotlib scipy uproot

Run:
python3 fit_muon_lifetime.py

Raw ROOT data files are not included in this repository.
