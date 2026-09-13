# 2026-09-13 Frontend Branch Regression

Status: COMPLETE for this ten-order branch batch. Stopped after the current fix
at the user's request. Final sales-page readback: nine closed, one cancelled.

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

See ui-branches-20260913-ten.json for the action log and final UI evidence.
Order 0155 ended by cancellation; the other nine reached final invoicing and
closure. This batch does not assert exhaustive coverage of every combination.

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

3. Sales could confirm requirements while a change request was still pending.
   Reproduced on order 0156 through the sales UI. Added a server-side advancement
   guard and invalidated stale schedule/confirmation flags in the UI. Processing
   a change now applies the revised requirement to the order and active task,
   records the before/after values, and requires sales reconfirmation. Browser
   verification showed the premature confirmation button disappear, the new
   October 4-5 schedule and revised five-sample/48-hour requirement appear, and
   the task become available only after reconfirmation and sample arrival.
   Commit: 429908c.

4. A remade report reused the prior round's approved sales audit in the workflow
   graph. Reproduced through order 0159: the report was waiting for sales review
   while step 11 displayed completed. Restricted graph audits to timestamps at
   or after the report's current generated_at, preserving historical audits.
   After deployment and browser reload, step 11 displayed current and step 12
   pending. Three additional regression checks passed. Commit: 1d9ff6e.

5. The preliminary-invoice void button remained visible while a valid final
   invoice existed. The backend correctly rejected the UI submission on order
   0163, without changing the invoice. Aligned can_void with that rule. After
   deployment and a new accountant login, final F2 retained its void button;
   preliminary P1 and already-voided F1 did not. Added four regression tests,
   including ownership and prefetched-query coverage.

Supplemental code checks: 60 Django tests passed against an isolated local test
database; 14 focused checks also passed. TypeScript checking and the Vite
production build passed. These are supplementary checks, not a substitute for
the browser branch tests or the ten production demo records.

## Verified Intermediate Financial Results

- Order 0162: a full-balance preliminary invoice attempt for 20000 was blocked.
- Preliminary invoices of 4000 and 3000 were entered from the accountant UI.
- Voiding the 4000 invoice changed the remaining balance from 13000 to 17000.
  The voided record and reason remained visible; the order stayed open.
- The remaining 3000 invoice was marked paid through the UI.
- After the experiment ended, the accountant saw an explicit results-not-yet-
  submitted label and could add a further 2000 preliminary invoice.
- Order 0163: a 5000 preliminary invoice was entered; the remaining balance was
  15000. Final F1 for 15000 closed the order. Voiding F1 restored a 15000 balance
  and reopened final invoicing, without voiding the preliminary invoice. Final
  F2 for 15000 closed the order again. The voided F1 and reason stayed visible.
- Seven orders received final invoices of 20000; orders 0162 and 0163 received
  final invoices of 15000 after valid preliminary invoices totaling 5000 each.
  Final sales-page readback confirmed all nine were closed, and 0155 cancelled.

## Reports And Remaining Scope

- Nine initial reports were generated, covering formal, draft and data-only
  versions. Sales rejected 0158 and the general manager rejected 0159. Both
  were remade and passed a new sales review followed by a new general-manager
  review. Eleven PDF download events were observed including the remakes.
- Internal and outsourced execution, mixed-path consolidation, both change
  loops, both commercial/technical rejection paths, both report rejection
  loops, preliminary/final invoicing and both invoice void paths were exercised.
- No additional business tests will run after this checkpoint. Concurrency,
  load, exhaustive permission combinations and every possible invalid input
  are not claimed as covered. Production test records are not a local database
  mirror; source and test artifacts are synchronized separately.

Browser download events are recorded as such. They do not assert independent
rendering or visual verification of every generated PDF.
