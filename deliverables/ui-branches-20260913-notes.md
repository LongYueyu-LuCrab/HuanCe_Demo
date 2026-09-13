# 2026-09-13 Frontend Branch Regression

Status: IN PROGRESS. Creation is not workflow completion.

All ten orders were created by sales01 through the browser. Subsequent business
actions use the rendered forms and buttons after switching role accounts. No
direct workflow API calls or database inserts are used for these orders.
Customer names and supplier names are fictional. Attachments and invoice numbers
are explicitly simulated; these records do not represent real laboratory work
or real tax invoices.

## Batch

| Order | Branch |
| --- | --- |
| LIMS-2026-0154 | Business rejection, sales edit, resubmission |
| LIMS-2026-0155 | Technical rejection, sales cancellation |
| LIMS-2026-0156 | Change before sample arrival, rescheduling |
| LIMS-2026-0157 | Change during experiment, rescheduling |
| LIMS-2026-0158 | Sales report rejection, remake, reapproval |
| LIMS-2026-0159 | General-manager report rejection, remake, reapproval |
| LIMS-2026-0160 | Outsourced execution and result submission |
| LIMS-2026-0161 | Mixed internal/outsourced paths and consolidated report |
| LIMS-2026-0162 | Multiple preliminary invoices, amount limit, invoice void |
| LIMS-2026-0163 | Final-invoice void, reopening and replacement invoice |

See ui-branches-20260913-ten.json for the incremental action log. Rows in this
table describe planned coverage, not assertions that every branch has passed.

## Confirmed Defects And Repairs

1. The assigned scheduling page consumed a dashboard slice of 50 schedules.
   A new assigned outsourced order could therefore be absent from the page.
   Replaced this with server-side paginated assigned-schedule queries, retaining
   role/owner restrictions. Verified order 0160 became searchable with scheduling
   and sample-arrival actions after deployment. Commit: 732bfff.
2. The outsourced page did not expose the full scheduling/sample workflow, and
   offered result actions before their prerequisites. It now uses the shared
   schedule workflow with an outsourced-only query filter. Result entry requires
   confirmed scheduling, sales confirmation and sample arrival. Verified order
   0160 could be scheduled with a sample image from that page. Commit: b910715.

Supplemental code checks: nine focused Django tests passed, TypeScript checking
passed, and the Vite production build passed. These are supplementary checks,
not a substitute for the browser branch tests.
