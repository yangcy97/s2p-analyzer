# -*- coding: utf-8 -*-
"""
s2p_calc.py
Free-space S-parameter (S33/S43/S34/S44 format) -> full EM property extraction
- Reflection/Transmission/Absorption, Return/Insertion Loss, VSWR, Group Delay
- Shielding Effectiveness (SE_Total, SE_R, SE_A)
- Complex permittivity/permeability (eps', eps'', mu', mu'') via NRW method
- Complex refractive index (n, kappa), wave impedance, loss tangents,
  propagation constant (alpha, beta), penetration depth
- Passivity check flag
"""

import numpy as np
import pandas as pd

C0 = 299792458.0  # speed of light, m/s


def db_ang_to_complex(db, ang_deg):
    """Convert dB magnitude + angle(deg) to complex number."""
    mag = 10.0 ** (np.asarray(db) / 20.0)
    ang_rad = np.deg2rad(np.asarray(ang_deg))
    return mag * (np.cos(ang_rad) + 1j * np.sin(ang_rad))


def parse_s2p_free_space(filepath):
    """
    Parse a 4-port-derived free-space s2p-style file with columns:
    FREQ  S33_DB S33_ANG  S43_DB S43_ANG  S34_DB S34_ANG  S44_DB S44_ANG
    (# Hz S DB R 50 header assumed)
    Returns a DataFrame with columns: freq, S33, S43, S34, S44 (complex)
    """
    freqs = []
    rows = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("!"):
                continue
            if line.startswith("#"):
                # option line, e.g. "# Hz S DB R 50.00" -- assume this format
                continue
            parts = line.split()
            if len(parts) < 9:
                continue
            try:
                vals = [float(x) for x in parts[:9]]
            except ValueError:
                continue
            freqs.append(vals[0])
            rows.append(vals[1:9])

    if not freqs:
        raise ValueError("No numeric data rows found in the file. Check the file format.")

    rows = np.array(rows)
    freq = np.array(freqs)

    S33 = db_ang_to_complex(rows[:, 0], rows[:, 1])
    S43 = db_ang_to_complex(rows[:, 2], rows[:, 3])
    S34 = db_ang_to_complex(rows[:, 4], rows[:, 5])
    S44 = db_ang_to_complex(rows[:, 6], rows[:, 7])

    df = pd.DataFrame({
        "freq": freq,
        "S33": S33, "S43": S43, "S34": S34, "S44": S44,
        "S33_dB": rows[:, 0], "S33_ang": rows[:, 1],
        "S43_dB": rows[:, 2], "S43_ang": rows[:, 3],
        "S34_dB": rows[:, 4], "S34_ang": rows[:, 5],
        "S44_dB": rows[:, 6], "S44_ang": rows[:, 7],
    })
    df = df.sort_values("freq").reset_index(drop=True)
    return df


def nrw_extract(S11, S21, freq, thickness_m):
    """
    Nicolson-Ross-Weir extraction for free-space (TEM) normal-incidence data.
    S11, S21: complex arrays (already averaged/symmetrized as needed)
    freq: array, Hz
    thickness_m: sample thickness in meters (scalar)
    Returns dict of arrays: Gamma, T, n, kappa, Z, eps_r, eps_i, mu_r, mu_i,
                             tan_d_e, tan_d_m, alpha, beta, penetration_depth
    """
    d = thickness_m
    k0 = 2.0 * np.pi * freq / C0

    # Reflection coefficient via NRW
    X = (S11 ** 2 - S21 ** 2 + 1.0) / (2.0 * S11 + 1e-30)
    sqrt_term = np.sqrt(X ** 2 - 1.0 + 0j)
    Gamma_plus = X + sqrt_term
    Gamma_minus = X - sqrt_term
    Gamma = np.where(np.abs(Gamma_plus) <= 1.0, Gamma_plus, Gamma_minus)

    # Transmission coefficient
    T = (S11 + S21 - Gamma) / (1.0 - (S11 + S21) * Gamma + 1e-30)

    # Unwrap phase of T across the frequency sweep to reduce branch (2*pi*m) ambiguity
    phase_T = np.unwrap(np.angle(T))
    ln_mag_T = np.log(np.clip(np.abs(T), 1e-12, None))

    # Complex refractive index N = n - j*kappa  (time convention e^{+jwt}, T = exp(-j k0 N d))
    n_real = -phase_T / (k0 * d + 1e-30)
    kappa = -ln_mag_T / (k0 * d + 1e-30)

    # Normalized wave impedance from Gamma, Re(Z) forced >= 0
    Z = np.sqrt(((1.0 + Gamma) ** 2) / ((1.0 - Gamma) ** 2 + 1e-30) + 0j)
    Z = np.where(Z.real < 0, -Z, Z)

    N = n_real - 1j * kappa  # complex refractive index

    eps_r_complex = N / Z
    mu_r_complex = N * Z

    eps_real = eps_r_complex.real
    eps_imag = -eps_r_complex.imag  # report as positive-loss convention (eps'')
    mu_real = mu_r_complex.real
    mu_imag = -mu_r_complex.imag

    tan_d_e = np.divide(eps_imag, eps_real, out=np.zeros_like(eps_imag), where=eps_real != 0)
    tan_d_m = np.divide(mu_imag, mu_real, out=np.zeros_like(mu_imag), where=mu_real != 0)

    alpha = k0 * kappa  # attenuation constant, Np/m
    beta = k0 * n_real  # phase constant, rad/m
    with np.errstate(divide="ignore"):
        penetration_depth = np.where(alpha > 0, 1.0 / alpha, np.inf)

    passivity_flag = (eps_imag >= -1e-6) & (mu_imag >= -1e-6)

    return {
        "Gamma": Gamma, "T": T, "n": n_real, "kappa": kappa, "Z_real": Z.real, "Z_imag": Z.imag,
        "eps_real": eps_real, "eps_imag": eps_imag,
        "mu_real": mu_real, "mu_imag": mu_imag,
        "tan_delta_e": tan_d_e, "tan_delta_m": tan_d_m,
        "alpha_Np_per_m": alpha, "beta_rad_per_m": beta,
        "penetration_depth_m": penetration_depth,
        "passivity_flag": passivity_flag,
    }


def compute_all(filepath, thickness_mm):
    """
    Main entry: parse file, compute every derivable quantity, return a DataFrame
    ready to export to CSV. thickness_mm: sample thickness in millimeters.
    """
    df = parse_s2p_free_space(filepath)
    freq = df["freq"].values
    S33, S43, S34, S44 = df["S33"].values, df["S43"].values, df["S34"].values, df["S44"].values

    out = pd.DataFrame()
    out["Freq_Hz"] = freq
    out["Freq_GHz"] = freq / 1e9

    # --- Raw dB/Ang passthrough ---
    out["S33_dB"] = df["S33_dB"]
    out["S33_ang_deg"] = df["S33_ang"]
    out["S43_dB"] = df["S43_dB"]
    out["S43_ang_deg"] = df["S43_ang"]
    out["S34_dB"] = df["S34_dB"]
    out["S34_ang_deg"] = df["S34_ang"]
    out["S44_dB"] = df["S44_dB"]
    out["S44_ang_deg"] = df["S44_ang"]

    # --- Return Loss / Insertion Loss ---
    out["ReturnLoss_S33_dB"] = -df["S33_dB"]
    out["ReturnLoss_S44_dB"] = -df["S44_dB"]
    out["InsertionLoss_S43_dB"] = -df["S43_dB"]
    out["InsertionLoss_S34_dB"] = -df["S34_dB"]

    # --- VSWR (per port, from reflection magnitude) ---
    def vswr_from_complex(S):
        mag = np.clip(np.abs(S), 0, 0.999999)
        return (1 + mag) / (1 - mag)

    out["VSWR_port3"] = vswr_from_complex(S33)
    out["VSWR_port4"] = vswr_from_complex(S44)

    # --- Power reflectance / transmittance / absorbance ---
    R3, R4 = np.abs(S33) ** 2, np.abs(S44) ** 2
    T3, T4 = np.abs(S43) ** 2, np.abs(S34) ** 2
    R_avg = (R3 + R4) / 2.0
    T_avg = (T3 + T4) / 2.0
    A_avg = 1.0 - R_avg - T_avg

    out["Reflectance_R3"] = R3
    out["Reflectance_R4"] = R4
    out["Reflectance_avg"] = R_avg
    out["Transmittance_T3"] = T3
    out["Transmittance_T4"] = T4
    out["Transmittance_avg"] = T_avg
    out["Absorbance_avg"] = A_avg

    # --- Shielding Effectiveness ---
    with np.errstate(divide="ignore"):
        SE_total = -10.0 * np.log10(np.clip(T_avg, 1e-12, None))
        SE_R = -10.0 * np.log10(np.clip(1.0 - R_avg, 1e-12, None))
    out["SE_Total_dB"] = SE_total
    out["SE_R_dB"] = SE_R
    out["SE_A_dB"] = SE_total - SE_R

    # --- Group delay (from transmission phase S43) ---
    ang_rad_43 = np.unwrap(np.deg2rad(df["S43_ang"].values))
    domega = 2 * np.pi * np.gradient(freq)
    group_delay = -np.gradient(ang_rad_43) / domega
    out["GroupDelay_s"] = group_delay

    # --- NRW material extraction (needs thickness) ---
    d_m = thickness_mm / 1000.0
    S11_avg = (S33 + S44) / 2.0
    S21_avg = (S43 + S34) / 2.0
    nrw = nrw_extract(S11_avg, S21_avg, freq, d_m)

    out["eps_real"] = nrw["eps_real"]
    out["eps_imag"] = nrw["eps_imag"]
    out["mu_real"] = nrw["mu_real"]
    out["mu_imag"] = nrw["mu_imag"]
    out["tan_delta_e"] = nrw["tan_delta_e"]
    out["tan_delta_m"] = nrw["tan_delta_m"]
    out["n_refractive_index"] = nrw["n"]
    out["kappa_extinction"] = nrw["kappa"]
    out["Z_wave_impedance_real"] = nrw["Z_real"]
    out["Z_wave_impedance_imag"] = nrw["Z_imag"]
    out["alpha_Np_per_m"] = nrw["alpha_Np_per_m"]
    out["beta_rad_per_m"] = nrw["beta_rad_per_m"]
    out["penetration_depth_m"] = nrw["penetration_depth_m"]
    out["passivity_flag"] = nrw["passivity_flag"]

    return out
