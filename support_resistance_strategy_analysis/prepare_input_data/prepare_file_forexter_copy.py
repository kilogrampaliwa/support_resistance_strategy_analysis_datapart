import pandas as pd

def prepareFileForexter(input_path: str, output_path: str):
    """Prepare 15-minute interval data from ForexTer platform and add weighted average."""

    print(f"=== prepareFileForexter ===\nInput: {input_path}\nOutput: {output_path}")

    df = pd.read_csv(
        input_path,
        names=["TICKER", "DATE", "TIME", "OPEN", "HIGH", "LOW", "CLOSE", "VOL"],
        header=0
    )

    def normalize_time_column(time_series: pd.Series) -> pd.Series:
        time_fixed = time_series.astype(str).str.zfill(6)
        invalid_times = time_fixed[~time_fixed.str.match(r'^\d{6}$')]
        if not invalid_times.empty:
            raise ValueError(f"Wrong TIME values after normalization:\n{invalid_times}")

        hours = time_fixed.str.slice(0, 2).astype(int)
        minutes = time_fixed.str.slice(2, 4).astype(int)
        seconds = time_fixed.str.slice(4, 6).astype(int)

        if ((hours > 23) | (minutes > 59) | (seconds > 59)).any():
            raise ValueError("TIME contains unrealistic values after normalization.")

        return time_fixed

    df["TIME"] = normalize_time_column(df["TIME"])

    df["DATETIME"] = pd.to_datetime(
        df["DATE"].astype(str) + df["TIME"],
        format="%Y%m%d%H%M%S"
    )
    df = df.set_index("DATETIME")

    df_15m = df.resample("15min").agg({
        "DATE": "first",
        "TIME": "first",
        "OPEN": "first",
        "HIGH": "max",
        "LOW": "min",
        "CLOSE": "last"
    }).dropna()

    df_15m["DATE"] = df_15m.index.strftime("%Y%m%d")
    df_15m["TIME"] = df_15m.index.strftime("%H%M%S")

    df_15m["WEIGHTED_AVG"] = ((df_15m["HIGH"] + df_15m["LOW"]) / 2 + 2 * ((df_15m["OPEN"] + df_15m["CLOSE"]) / 2)) / 3

    df_15m = df_15m[["DATE", "TIME", "OPEN", "HIGH", "LOW", "CLOSE", "WEIGHTED_AVG"]]

    df_15m.to_csv(output_path, header=False, index=False, float_format="%.5f")
    print(f"No candles: {len(df_15m)} || Saved in:\n{output_path}")
