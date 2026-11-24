"""Reusable cleaning pipeline for the mobile-money agent network data."""

import numpy as np
import pandas as pd

VALID_TYPES = ("Deposit", "Withdrawal")


def clean_agent_data(txns, agents):
    """Clean the agent transaction extract and merge it with the agent register.

    Rules applied, in order (every rule is data-driven; no row numbers are used):
      1. Uniqueness   - drop repeated ``txn_id`` values, keeping the first row.
      2. Consistency  - standardise ``txn_type`` to "Deposit" / "Withdrawal".
      3. Validity     - convert ``amount`` to numeric (text such as "N/A" becomes
                        missing) and ``txn_date`` to datetime (accepts both
                        YYYY-MM-DD and YYYY/MM/DD).
      4. Accuracy     - flag IQR outliers in ``is_outlier`` (never deleted).
      5. Completeness - flag missing amounts in ``amount_imputed`` and fill them
                        with the median valid, non-outlier amount of the same
                        ``txn_type``.
      6. Integrity    - left-join the agent register to add ``county``; agents
                        not in the register get county "Unknown" and
                        ``agent_known`` = False (rows are kept, not dropped).

    Parameters
    ----------
    txns : pandas.DataFrame
        Raw transactions: txn_id, agent_id, txn_type, amount, txn_date.
    agents : pandas.DataFrame
        Agent register: agent_id, county, onboarded.

    Returns
    -------
    (clean_df, log) : tuple
        clean_df - cleaned transactions with extra columns ``amount_imputed``,
                   ``is_outlier``, ``county`` and ``agent_known``.
        log      - DataFrame with columns ``step``, ``dimension``, ``action``,
                   ``rows_affected`` and ``rows_after``.
    """
    df = txns.copy()
    log = []

    def record(step, dimension, action, affected, rows_after):
        log.append({"step": step, "dimension": dimension, "action": action,
                    "rows_affected": int(affected), "rows_after": int(rows_after)})

    record("0. Input", "-", "Raw transaction rows received", 0, len(df))

    # 1. Uniqueness: key-based, because a repeat can differ in other columns
    dup_mask = df.duplicated(subset="txn_id", keep="first")
    n_exact = int(df.duplicated(keep="first").sum())
    n_conflict = int(dup_mask.sum()) - n_exact
    df = df.loc[~dup_mask].copy()
    record("1. Duplicates", "Uniqueness",
           f"Dropped repeated txn_id, kept first occurrence "
           f"({n_exact} exact copies, {n_conflict} copies with conflicting fields)",
           dup_mask.sum(), len(df))

    # 2. Consistency: txn_type
    cleaned_type = df["txn_type"].astype("string").str.strip().str.title()
    changed = (df["txn_type"].astype("string") != cleaned_type).sum()
    df["txn_type"] = cleaned_type
    bad_type = ~df["txn_type"].isin(VALID_TYPES)
    df.loc[bad_type, "txn_type"] = pd.NA
    record("2. txn_type", "Consistency",
           "Stripped spaces and standardised case to Deposit/Withdrawal",
           changed, len(df))
    if bad_type.any():
        record("2b. txn_type", "Validity", "Unrecognised txn_type set to missing",
               bad_type.sum(), len(df))

    # 3. Validity: types
    amount_raw = df["amount"].astype("string").str.strip()
    amount_num = pd.to_numeric(amount_raw, errors="coerce")
    text_invalid = amount_raw.notna() & amount_num.isna()
    df["amount"] = amount_num.astype(float)
    record("3a. amount type", "Validity",
           "Converted amount to numeric; non-numeric text (e.g. 'N/A') -> missing",
           text_invalid.sum(), len(df))

    date_raw = df["txn_date"].astype("string").str.strip()
    slash = date_raw.str.contains("/", na=False)
    df["txn_date"] = pd.to_datetime(date_raw.str.replace("/", "-", regex=False),
                                    format="%Y-%m-%d", errors="coerce")
    record("3b. txn_date type", "Consistency",
           "Parsed dates to datetime (YYYY/MM/DD variants fixed)",
           slash.sum(), len(df))
    n_bad_date = int(df["txn_date"].isna().sum())
    if n_bad_date:
        record("3c. txn_date", "Validity", "Unparseable dates left missing",
               n_bad_date, len(df))

    # 4. Accuracy: IQR outliers on valid amounts (flag only)
    q1, q3 = df["amount"].quantile([0.25, 0.75])
    iqr = q3 - q1
    low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    df["is_outlier"] = ((df["amount"] < low) | (df["amount"] > high)).fillna(False)
    record("4. Outliers", "Accuracy",
           f"Flagged amounts outside [{low:,.0f}, {high:,.0f}] (IQR rule); kept in data",
           df["is_outlier"].sum(), len(df))

    # 5. Completeness: flag, then impute with median of normal amounts by type
    df["amount_imputed"] = df["amount"].isna()
    normal = df.loc[~df["is_outlier"] & df["amount"].notna()]
    medians = normal.groupby("txn_type")["amount"].median()
    fill = df["txn_type"].map(medians).fillna(normal["amount"].median())
    df["amount"] = df["amount"].fillna(fill)
    record("5. Missing amounts", "Completeness",
           "Flagged in amount_imputed; filled with median non-outlier amount by txn_type",
           df["amount_imputed"].sum(), len(df))

    # 6. Merge with the agent register
    if not agents["agent_id"].is_unique:
        raise ValueError("agents register has duplicate agent_id values")
    before = len(df)
    df = df.merge(agents[["agent_id", "county"]], on="agent_id", how="left",
                  validate="many_to_one")
    assert len(df) == before, "merge changed the number of rows"
    df["agent_known"] = df["county"].notna()
    unknown = int((~df["agent_known"]).sum())
    df["county"] = df["county"].fillna("Unknown")
    record("6. Merge", "Consistency",
           "Left join to agent register (many_to_one); unknown agents get county 'Unknown'",
           unknown, len(df))

    df = df.sort_values("txn_id").reset_index(drop=True)
    return df, pd.DataFrame(log)
