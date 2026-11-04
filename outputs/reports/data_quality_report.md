# Data Quality Report

Run ID: `20261030_192704_aa9e82`  
Files processed: 12

## Summary

| Metric | Value |
|---|---|
| Rows extracted | 110,076 |
| Duplicate transactions removed | 1,086 |
| Rows rejected (quarantined) | 2,457 |
| Reject rate | 2.23% |
| Rows loaded to warehouse | 106,533 |

## Rejections by rule

| Rule | Rows |
|---|---|
| invalid_quantity | 862 |
| missing_store_id | 650 |
| unknown_product_code | 430 |
| invalid_datetime | 322 |
| price_out_of_range | 213 |

All rejected rows, with the reason, are saved in `rejected_rows.csv` and in the
`dq_rejected_sales` table so they can be corrected at source and reloaded.
