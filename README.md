# Assignment 3: Duka Sales Exploration and Agent Network Clean-Up

**`**Analyst:**`** `*Leah Atieno J.* | **Cohort:** *1MilionDevs *`

Two client engagements for a Nairobi analytics consultancy, in one repository.

## Summary of both engagements

**Engagement 1: Duka Electronics (sales exploration).** Pandas analysis of 1,000 orders from January to June 2026\. I loaded the data with date parsing, inspected it, derived `revenue`, `month`, `weekday`, `is_weekend` and `price_band`, and answered the Head of Sales' questions: branch ranking (Nairobi leads, and the ranking is the same by revenue and orders), top products (Laptop, Tablet and Phone in both lists, but Tablets sell more units while Laptops earn more), weekend against weekday (almost identical average order), best and worst month (April against June) and the Premium online segment in Nairobi and Mombasa. An Excel workbook reproduces the branch totals with `SUMIFS`, adds an `XLOOKUP` region column and a PivotTable, and the notebook confirms the totals match pandas.

**Engagement 2: Mobile money agent network (audit and clean-up).** Audit of a deliberately flawed transaction extract: duplicates (including one that differs from its original), inconsistent `txn_type`, missing and `N/A` amounts, mixed date formats, five identical KES 250,000 amounts and transactions from an agent missing in the register. All rules are coded in `cleaning_pipeline.py` as `clean_agent_data(txns, agents)`, which returns the clean data and a log. The notebook shows the audit table, merge validation, county and weekly summaries and a one-page Data Quality Report with a privacy paragraph.

### Duka Executive Summary

- Duka Electronics took **KES 71,792,500** from **1,000 orders** between 1 January and 29 June 2026, an average of **KES 71,792** per order.  
- **Nairobi** is the leading branch with **KES 26,106,100** (36.4% of revenue, 376 orders), and the branch ranking is the same by revenue and by order count.  
- **Laptops** bring in **57.9%** of revenue (KES 41,535,000) while **Tablets** sell the most units (691 against 639 for laptops).  
- Weekends account for **277 orders (27.7%)** and the average order is KES 71,972 against KES 71,724 on weekdays, a gap of only 0.3%.  
- **April 2026** was the best month (KES 13,518,300) and **June 2026** the worst (KES 10,903,400), a **24.0%** difference, and the 83 Premium online orders from Nairobi and Mombasa are worth **KES 10,218,000** (14.2% of revenue).

### Agent data: before and after cleaning

|  | Rows |
| :---- | :---- |
| Raw `agent_transactions.csv` | **612** |
| Duplicate `txn_id` rows removed | 12 (11 exact, 1 with a conflicting agent) |
| **Clean `agent_transactions_clean.csv`** | **600** |

Also in the clean file: 20 imputed amounts (flagged in `amount_imputed`), 40 IQR outliers (flagged in `is_outlier`, including 5 at KES 250,000), and 7 transactions from unknown agent `AG099` (kept, county `Unknown`). The agent register has 20 rows.

## How to regenerate the data and run the notebooks

The raw CSVs are not committed; they are created by `generate_data.py`.

```sh
pip install -r requirements.txt
python generate_data.py            # writes duka_sales.csv, agents.csv, agent_transactions.csv
jupyter notebook duka_sales_exploration.ipynb   # Kernel > Restart & Run All
jupyter notebook agent_cleanup.ipynb            # Kernel > Restart & Run All
```

In Google Colab, upload the files, then run `!python generate_data.py` in a cell before the notebooks. `cleaning_pipeline.py` must sit in the same folder as `agent_cleanup.ipynb`. The Duka notebook also reads `excel/duka_branch_summary.xlsx` for the Task 8 check.

## Repository layout

```
README.md
generate_data.py                 both generators, unchanged (seeds 2026 and 44)
duka_sales_exploration.ipynb     Engagement 1
agent_cleanup.ipynb              Engagement 2
cleaning_pipeline.py             clean_agent_data(txns, agents) -> (clean_df, log)
requirements.txt
excel/duka_branch_summary.xlsx   SUMIFS, XLOOKUP, PivotTable
outputs/premium_online_coast_capital.csv
outputs/agent_transactions_clean.csv
```

## Notes on decisions

- Duplicates are removed by `txn_id`, not by whole row, because one copy differs in `agent_id`.  
- Missing amounts are flagged then filled with the median non-outlier amount per transaction type; outliers are flagged, never deleted.  
- Unknown agents are kept through a left join so no money is silently dropped.  
- The Excel region mapping is my assumption; the brief does not define regions. `XLOOKUP` needs Excel 2021/365 or Google Sheets.