import pandas as pd
import numpy as np
from scipy.ndimage import gaussian_filter1d


def interpolate_missing(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = df.select_dtypes(include=["float64", "int64"]).columns
    skip = {"frame"}
    for col in numeric_cols:
        if col in skip:
            continue
        df[col] = df[col].interpolate(method="linear", limit_direction="both")
    df = df.ffill().bfill()
    return df


def gaussian_smooth(df: pd.DataFrame, sigma: float = 2.0) -> pd.DataFrame:
    numeric_cols = df.select_dtypes(include=["float64", "int64"]).columns
    skip = {"frame", "time"}
    for col in numeric_cols:
        if col in skip:
            continue
        df[col] = gaussian_filter1d(df[col].astype(float), sigma=sigma)
    return df


def normalize_by_hips(df: pd.DataFrame) -> pd.DataFrame:
    coords = [c for c in df.columns if c.endswith(("_x", "_y", "_z"))]
    if "Hips_x" not in df.columns:
        return df
    for axis in ("_x", "_y", "_z"):
        origin = df[f"Hips{axis}"].values
        for col in coords:
            if col.endswith(axis) and not col.startswith("Hips"):
                df[col] = df[col] - origin
    return df


def preprocess(input_path: str, output_path: str, sigma: float = 2.0) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    before_missing = df.isnull().sum().sum()

    df = interpolate_missing(df)
    df = normalize_by_hips(df)
    df = gaussian_smooth(df, sigma=sigma)

    after_missing = df.isnull().sum().sum()
    print(f"Preprocess: {before_missing} missing → {after_missing} missing")

    df.to_csv(output_path, index=False)
    return df


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        preprocess(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python preprocess.py <input.csv> <output.csv>")
