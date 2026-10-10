# Iteration 9 — Usability evaluation: preparation checkpoint

## 1. Scope, objective and status

Project: **Cross-Border Remittance DApp with Recipient Claim and Status Tracking**.
Exact accepted base: `30adf2f810fe66e31153e61924fbd8b8c4370a01`.
Branch: `feature/iteration-9-usability-evaluation`. Iterations 1–8 remain frozen.
Preparation date: 11 October 2026 (Asia/Kuala_Lumpur).

Objective: observe whether five classmates/friends can understand and complete the
frozen Sender/Recipient workflow, identify confusion and assistance needs, and
collect concise usability feedback. **Real participant results are pending.**
No sessions, ratings, findings or success rates are asserted in this checkpoint.
Only this protocol and the blank collection CSV are added. No production changes,
deployment, infrastructure change, live transaction or Iteration 10 work is performed.

## 2. Sample and limitations

Use exactly **five participants**, anonymously identified **P01–P05**, recruited by
the project owner as a convenience sample. The facilitator is not a sixth participant.
Each participant uses their own MetaMask wallet and tests both perspectives.

These participants are not representative of migrant/remittance users. Results
can identify usability issues in these sessions, not estimate population usability,
financial inclusion, demand, real remittance savings or financial suitability.
Wallet experience, environment and task order may affect performance. The five-item
questionnaire is a project-specific rating instrument, not SUS or a validated scale.
Admin usability is outside the required participant flow.

## 3. Frozen test environment and owner setup

- Public application: https://sc6113-ay2026t1.onrender.com
- Start participants at https://sc6113-ay2026t1.onrender.com/main, so no name
  entry is required. User Log is not part of this task flow.
- Network: Sepolia; chain ID `11155111`.
- Deployment ID: `sc6113-sepolia-11884239`; frozen manifest: `deployment/sepolia.json`.
- Financial authority: verified contracts. Activity/Turso is non-authoritative
  indexed history and may have incomplete historical catch-up.
- Application receipt policy: six confirmations and authoritative post-state
  refresh. This is an application policy, not an absolute finality guarantee.

Before the five sessions, the owner should:

1. Agree participation and anonymous recording; explain that participation may stop
   at any time. Use P01–P05 only in the dataset.
2. Have participants prepare their own MetaMask-enabled browser, select Sepolia and
   obtain sufficient faucet test ETH for the small deposit and transaction gas.
   Do not buy assets or use real ETH. Never collect recovery phrases/private keys.
3. Through the existing Admin wallet, authorize each participant's wallet as both
   Sender and Recipient. Verify those permissions before starting task timing.
   Admin must remain the frozen Admin; participant permissions do not confer Admin.
4. Prepare a distinct facilitator-controlled companion wallet, authorized as both
   Sender and Recipient, with enough test assets. Do not use Admin as the normal
   financial counterparty. The companion is an operational helper, not a participant.
5. Choose one fixed small amount for all sessions where feasible. Suggested plan:
   deposit **0.0001 test ETH**, send **0.00005 test ETH**, receive **0.00005 test ETH**;
   optional cancellation uses **0.00002 test ETH**. These are planned task amounts,
   not recorded transactions. Verify enough available balance and gas first.
6. Prepare one distinct incoming pending remittance from companion to each
   participant for T6. Supply only the needed recipient address and remittance ID
   privately on the session card; do not include full addresses in the dataset.
7. Confirm the service responds, system is unpaused and role/balance reads work.
   Record general device/browser category and technical interruptions without
   names, wallet-person mappings or sensitive screenshots.

The owner alone arranges or signs these live operations. Work does not submit them.
No configuration/schema changes are needed. Preparation, role grants, funding of
wallets and companion actions are outside scored participant timings.

### Counterparty coordination

Call the participant-created remittance **A** and the prepared incoming remittance
**B**. T4 creates A to the companion; T5 observes A while pending. After T5, the
facilitator may claim A in a separate wallet/session. T6 has the participant claim B;
T7 checks B completed and, once confirmed, A completed from the Sender perspective.
Keep companion waiting/operations outside participant timing and note any interruption.
No participant switches to or signs with someone else's wallet. Separate browser
profiles/devices prevent companion authentication from replacing the participant session.

## 4. Participant testing sheet

Give participants this section only, together with their session card. Keep the
observation and scoring notes with the facilitator.

### Introduction

You are trying a coursework remittance prototype using **Sepolia test ETH, which
has no real monetary value**. It is not a real-money remittance service. Use only
your own wallet; never share private keys or a recovery phrase. Try each task yourself
first. You may ask for help or stop. We are evaluating the interface, not you.

Session card: participant ID ___; companion recipient address ___; small test amount
___; incoming remittance B ID ___. Addresses on this temporary card are not copied
into the anonymous results. Explain only the A/B labels, not where to click.

| ID | Perspective | Task |
|---|---|---|
| T1 | Account | Connect your own MetaMask wallet and authenticate to the application. |
| T2 | Account | Explore the dashboard. Explain which wallet is authenticated, your roles, and where you would find funding, remittances and activity. |
| T3 | Sender | Deposit the supplied small amount of test ETH. Find evidence that the deposit succeeded and check the available balance. |
| T4 | Sender | Create remittance A to the supplied companion address for the agreed amount. Find its ID and status. |
| T5 | Sender | Find A's amount, recipient and pending status. Locate its transaction/history evidence and distinguish current status from indexed history. |
| T6 | Recipient | Find incoming remittance B and claim it using your own wallet. |
| T7 | Both | Confirm B is completed. Check A's completed Sender-side status once the companion has claimed it. |
| T8 | Sender; optional | Create a second small remittance to the companion, cancel it while pending, and check CANCELLED and the return to available balance. |

### After the tasks

Rate each statement from **1 (strongly disagree) to 5 (strongly agree)**; 3 is neutral.
You may leave an item unanswered. Rate this test workflow only.

| Item | Statement | Rating 1–5 |
|---|---|---|
| Ease of use | I found the workflow easy to use. | ___ |
| Navigation | I could find the pages and controls I needed. | ___ |
| Status clarity | Transaction and remittance status information was clear. | ___ |
| Workflow confidence | I felt confident carrying out the test workflow. | ___ |
| Overall usability | Overall, the application was usable for these tasks. | ___ |

1. What was the most difficult or confusing part? ___
2. What improvement would you suggest? ___

## 5. Facilitator observation and scoring

Let participants attempt independently first. Avoid click-by-click guidance. Assist
when requested or when they remain blocked for approximately two minutes of active
attempt; do not mistake normal confirmation waiting for confusion. Log the specific
hint/action. Do not ask participants to share keys or take over their wallet signing.

| Task | Completion criterion |
|---|---|
| T1 | Server-authenticated session shows the participant wallet, not connection alone. |
| T2 | Identifies wallet/roles and the three requested areas accurately. |
| T3 | Confirmed deposit plus current available balance identified. |
| T4 | Correct designated recipient/amount; new ID and PENDING state identified. |
| T5 | Correct A details; locates receipt/history evidence or correctly recognises incomplete indexing without claiming no transaction exists. |
| T6 | Participant claims designated B; confirmed result or authoritative completed state is verified. |
| T7 | Correct completed state for B and completed status for A. |
| T8 | Second remittance cancelled while pending; cancellation and unlocked balance verified. |

For an attempted task, record `completed` or `not_completed`; use `not_attempted`
when not started and explain why. Assistance is separately `yes`/`no`.
A completed task with any facilitator guidance is **assisted**, not independent.
Standard initial task wording, supplied address/ID and planned companion operations
are not assistance; an extra hint, navigation instruction or correction is assistance.

Measure approximate elapsed seconds from reading the task to reaching the criterion,
including normal loading/confirmation waits. Optionally estimate waiting seconds
within that elapsed time. Failed-task time is elapsed time to stop/defer, not a successful completion time.
If assistance leads to completion, continue timing and classify it as assisted. Note RPC outages, cold starts, insufficient pre-funded
gas and counterpart delays separately; do not label every technical interruption a
usability failure. Stop or defer a prolonged outage rather than force completion.
A deferred result remains incomplete until genuinely observed later.

If a submitted hash has an unresolved outcome, retain the hash in the application
and use **Check transaction** to verify only. Never suggest re-signing/resubmission
just because verification temporarily fails. Explicit **Refresh account & activity**
is available when the companion changed state externally; record whether participants
found it themselves or needed a hint.

The facilitator may separately check inactive reservations through the existing
read-only API for technical corroboration. Do not require a participant to inspect
an API-only field or mark its absence from the UI as task failure.

Observe errors/confusion objectively (what happened); record participant comments
as feedback. Keep interpretation for analysis. Do not treat expected empty/partial
Activity as proof that direct financial reads failed.

## 6. Anonymous CSV collection

File: [iteration9_usability.csv](../../results/iteration9_usability.csv).
It contains **45 blank templates**, not results: eight task rows and one questionnaire
row for each of P01–P05. T1–T7 are core; T8 is optional. All measurement/result fields
are empty. Do not enter placeholders such as zero ratings or assumed success.

| Fields | Use / allowed values |
|---|---|
| `participant_id`, `record_type`, `task_id`, `perspective` | Prefilled structure; IDs P01–P05; type task/questionnaire; T1–T8 or Q1. |
| `outcome` | Task only: completed / not_completed / not_attempted. |
| `completion_time_seconds`, `waiting_time_seconds` | Task only; nonnegative approximate elapsed and optional waiting subset. Blank for unattempted tasks; waiting ≤ elapsed. |
| `assistance_required`, `assistance_notes` | Task only; yes/no for attempted tasks, with details when yes. |
| `observed_errors_or_confusion` | Task only; directly observed behavior; write none only after observation. |
| `environment_or_interruption_notes` | General setup/outage/defer/counterpart notes; no identifying data. |
| `spontaneous_feedback` | Volunteered comments, including positive comments; no third required open question. |
| `ease_of_use`, `navigation`, `status_clarity`, `workflow_confidence`, `overall_usability` | Q1 only; integer 1–5 or blank if unanswered. |
| `most_difficult_or_confusing`, `suggested_improvement` | Q1 only; the two open answers. |

Do not collect names, signatures, nonces, session cookies, secrets or wallet-person
mappings. Public transaction hashes are not required in this usability CSV. If a
technical incident genuinely needs evidence, keep a minimal separate note with a
masked identifier and no personal association. Avoid identifiable screenshots.

## 7. Planned analysis — only after real data arrives

1. Validate IDs, row coverage, outcomes, time units, rating ranges and assisted-task
   notes. Blank fields are missing data, not zero/failure. Confirm five real sessions;
   do not fabricate an absent participant to reach n=5.
2. For each core task report completed/5, independent/5, assisted/5, failed/5 and
   unattempted/5, preserving raw counts alongside percentages. Independent means
   completed with assistance=no; assisted means completed with assistance=yes.
   Also give attempted denominator when relevant; never silently exclude blocked
   participants. Example format only: `4/5 independently (80%)` is not a result.
3. Report optional T8 separately as attempted/5 and completed/attempted, explaining
   omissions. Do not penalise a planned omission as core failure. Complete core journey
   means all seven core tasks observed completed; independent journey requires no
   assistance on any core task. Deferred observations need their actual follow-up.
4. Summarise successful-task elapsed times using median and, where useful, mean,
   with sample count and range. Keep assisted/independent times distinguishable;
   failed attempt times and technical waits separate. Do not pool Sender/Recipient
   tasks or compare timings as fiat settlement performance. If comparable waiting
   estimates exist, optionally show active time, explaining estimation limitations.
5. For each rating report response count out of five, individual anonymous ratings,
   mean and median. Do not impute missing answers or calculate a validated-scale score.
6. Group observation and feedback themes; count participants reporting each theme,
   not repeated mentions as extra people. Include recurring positives where actually
   volunteered. Do not invent favourable feedback or themes absent from responses.
7. Select 3–5 most important findings only if supported; fewer is acceptable. For
   each state observed behavior, participant feedback, team interpretation, affected
   task, participant count, severity, evidence and recommendation separately.

| Severity | Practical meaning |
|---|---|
| High | Blocks a core workflow despite correct setup; needs review. |
| Medium | Substantial confusion, errors or assistance needed. |
| Low | Inconvenience or cosmetic/readability suggestion. |

No inferential statistics or population generalisation. No implemented improvement
is implied by a recommendation. If a genuine usability blocker requires a production
change, stop and return it for owner review before changing frozen code. Minor
suggestions remain future work unless separately authorized.

## 8. Collection handoff and acceptance state

The owner conducts the five real sessions and returns the completed anonymous CSV
plus any essential non-identifying clarification. Work will then analyse actual data
in an Iteration 9 continuation. This checkpoint does not freeze evaluation findings.

| Criterion | Current state |
|---|---|
| Five-participant protocol, task sheet and questionnaire | Prepared |
| Blank structured results and analysis framework | Prepared |
| Five real sessions and observations | Pending owner collection |
| Results analysis, findings and recommendations | Pending real data |
| Final usability acceptance/freeze | Pending; not claimed |

**ITERATION 9: DATA COLLECTION PENDING**
