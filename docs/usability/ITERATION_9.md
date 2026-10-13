# Iteration 9 — Completed usability evaluation and analysis

## 1. Scope, baseline and evidence status

Project: **Cross-Border Remittance DApp with Recipient Claim and Status Tracking**.
Branch: `feature/iteration-9-usability-evaluation`. Accepted preparation commit:
`5328aba65940b9eeb5d091d07f473792172410fc`; Iterations 1–8 remain frozen.
This pass changes this evidence document and the existing results CSV only. No
remediation, production/configuration change, deployment or Iteration 10 work occurs.

Five real responses were read on **13 October 2026 (Asia/Kuala_Lumpur)** from
[SC6113 Usability Evaluation — Responses](https://docs.google.com/spreadsheets/d/11OOyhUqiVFghwQ2B7IHUPHKArfrMZGiLHJeeJG1Z2FI/edit),
**Form Responses 1**, sheet ID `1495285361`. The verified title/tab match the owner's
source. A1:CA7 contains the headers and five responses; A8:B106 contains no additional
response timestamps/IDs. Row order was P02, P01, P05, P03, P04; normalization sorts
P01–P05. Form submissions span 11–13 October 2026 in the sheet's Asia/Singapore timezone;
these are submission dates, not verified session start/end times.

The owner conducted the sessions. Work did not observe them directly: “recorded
observations” below means the submitted task-observation fields, distinct from
participant feedback and analyst interpretation. No response is reconstructed from
prior smoke tests. The original approved protocol is retained in historical Appendix A.
Actual participation/measurements below supersede its pending collection status.

## 2. Sample and actual completion

Exactly **five classmates/friends**, convenience sample P01–P05, used their own
MetaMask wallets on the existing Render/Sepolia coursework deployment. The facilitator
is not a participant. User Log was outside the usability tasks. There is no evidence
that this sample represents migrant/remittance users or validates their needs.

All five submitted task outcomes and all five questionnaire ratings. This means data
collection is complete; it does **not** mean all participants completed every task.
All attempted T1–T5. P01/P05 completed all seven core tasks. P02 did not complete T6
but completed T7; P03 did not attempt T6/T7; P04 did not complete T6/T7. Only P02/P05
attempted optional cancellation T8. The source does not state why the remaining
claim/status tasks were incomplete or unattempted, or verify all planned companion
arrangements. No later success is assumed.

## 3. Normalization and data-quality notes

[Normalized results](../../results/iteration9_usability.csv): **45 rows, 19 unchanged
columns**, five participants × eight tasks plus one questionnaire row each. Frozen
perspectives remain Account, Account, Sender, Sender, Sender, Recipient, Both,
Sender (optional); Q1 is Both.

- Outcome labels become `completed`, `not_completed`, `not_attempted`.
- Explicit numeric values in the seconds-labelled fields are retained. `10sec` and
  `3 seconds` become 10 and 3. No number is inferred from “instantaneous”, “a few
  seconds”, “a few minutes”, “less than 30sec” or NA. Their original wording is
  preserved with a labelled source note in `environment_or_interruption_notes`.
  Such notes describe missing measurement, not an invented technical incident.
- Missing values remain blank. Assistance Yes/No becomes yes/no. “Not applicable /
  not attempted” becomes blank, with its original wording retained in a source note;
  it is not silently interpreted as no assistance.
- **P02 T6 not_completed / T7 completed is preserved.** T7 is inspection, not proof
  that P02 personally claimed; its success is not overridden by T6.
- P04 T6/T7 say not_completed but their assistance fields say “Not applicable / not
  attempted”. Outcomes take precedence for outcome counting; assistance is unknown.
  The inconsistency and missing reasons remain unresolved data-quality gaps.
- P04 T4 reports assistance=yes but leaves assistance notes blank. Its error and
  environment narratives record facilitator investigation of Smart Account mode;
  they do not provide a complete assistance log.
- P01 T1 total is 2 seconds while the observation says roles took half a minute.
  P01 T3/T4 totals and waits are 10 seconds while observations say confirmation took
  30 seconds; T6 total is 10 with a 30-second confirmation comment. P05 T3 total 15 /
  wait 3 contrasts with feedback of more than a minute for six confirmations; T6
  total 15 also contrasts with more than a minute. Keep both values and narrative.
  They may refer to different phases; this cannot be resolved from the form.
- Only **11/35** core rows have numeric total time, **7/35** numeric waiting time.
  All 25 rating responses are present and valid. No waiting value is imputed to zero.
- P05's server/RPC interruption and operational RPC URL change are recorded source
  history. They were not performed during this analysis and are not attributed to
  interface usability. No URL/credential value is copied.

No names, wallet-person mappings, private keys, phrases, signatures, authentication
material or other participant identifiers are added. Free-text answers are preserved;
blank comments do not mean an incident was absent.

## 4. Task completion

Independent = completed and assistance=no. Assisted = completed and assistance=yes.
Each count below uses all five participants; 1/5 equals 20%. Missing assistance on
incomplete tasks does not change these completion categories.

| Core task | Completed /5 | Independent /5 | Assisted /5 | Not completed /5 | Not attempted /5 |
|---|---:|---:|---:|---:|---:|
| T1 Authenticate | 5 (100%) | 5 (100%) | 0 | 0 | 0 |
| T2 Dashboard | 5 (100%) | 5 (100%) | 0 | 0 | 0 |
| T3 Deposit | 5 (100%) | 5 (100%) | 0 | 0 | 0 |
| T4 Create | 5 (100%) | 3 (60%) | 2 (40%) | 0 | 0 |
| T5 Status/history | 5 (100%) | 5 (100%) | 0 | 0 | 0 |
| T6 Claim | 2 (40%) | 2 (40%) | 0 | 2 (40%) | 1 (20%) |
| T7 Confirm completed state | 3 (60%) | 3 (60%) | 0 | 1 (20%) | 1 (20%) |

Core task outcomes total **30/35 completed**, including **28 independent** and **2
assisted**, **3 not completed**, **2 not attempted**. These are repeated task
observations, not 35 independent participants.

- **Complete core journey: 2/5 (40%)**, P01 and P05.
- **Independent core journey: 2/5 (40%)**, P01 and P05.
- **Optional T8:** attempted 2/5 (40%); completed 2/2 attempted (100%), both
  independent; not attempted 3/5 (60%). Optional omissions are not core failures.

No successful claim or completed journey is inferred for P02/P03/P04. Completion of
T7 for P02 remains a separately reported inspection outcome.

## 5. Timing: entered numeric values, not validated end-to-end performance

Successful tasks only. Values are seconds. Summaries below describe numeric entries
as supplied; conflicting narratives prevent interpreting them as reliable full
workflow latency. Qualitative/blank entries are excluded, not converted. `—` means
no numeric sample, not zero. A single observation is shown without a mean/median.

| Task | Total n | Total median | Total mean | Total range | Waiting n | Waiting median | Waiting mean | Waiting range |
|---|---:|---:|---:|---|---:|---:|---:|---|
| T1 | 3 | 3 | 2.67 | 2–3 | 1 | — | — | 10 (single) |
| T2 | 0 | — | — | — | 0 | — | — | — |
| T3 | 2 | 12.5 | 12.5 | 10–15 | 3 | 10 | 8.33 | 3–12 |
| T4 | 3 | 10 | 11.67 | 10–15 | 3 | 10 | 8.33 | 3–12 |
| T5 | 0 | — | — | — | 0 | — | — | — |
| T6 | 2 | 12.5 | 12.5 | 10–15 | 0 | — | — | — |
| T7 | 1 | — | — | 5 (single) | 0 | — | — | — |
| T8 optional | 0 | — | — | — | 0 | — | — | — |

T4 independent numeric totals are P01=10 and P05=10; assisted P02=15. P04 has no
numeric total. Do not pool these as evidence that assistance caused delay. For T1,
P04's waiting=10 has no total, so the total and waiting samples are different people.
Other tasks' samples also differ. Do not subtract aggregate waiting from total means
or calculate an overall journey duration. The contradictory total/confirmation
entries make a defensible end-to-end timing estimate unavailable. Confirmation
complaints remain qualitative evidence; these are not international fiat settlement
times or evidence of superior remittance speed.

## 6. Questionnaire

Project-specific 1–5 agreement ratings; not SUS. No imputation. Each item has 5/5
responses. Individual values are retained so high scores do not hide task gaps.

| Item | P01 | P02 | P03 | P04 | P05 | Responses | Mean | Median |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| Ease of use | 4 | 5 | 4 | 5 | 5 | 5/5 | 4.6 | 5 |
| Navigation | 5 | 5 | 4 | 5 | 5 | 5/5 | 4.8 | 5 |
| Status clarity | 5 | 5 | 5 | 5 | 5 | 5/5 | 5.0 | 5 |
| Workflow confidence | 4 | 4 | 5 | 5 | 5 | 5/5 | 4.6 | 5 |
| Overall usability | 4 | 4 | 4 | 5 | 4 | 5/5 | 4.2 | 4 |

These five participants rated the experience positively overall. That does not
prove general usability or negate P02/P04 claim noncompletion, P03 nonattempts,
T4 assistance or transaction uncertainty. In particular, P04's clarity rating of 5
coexists with a specific uncertain-verification narrative; preserve both.

## 7. Qualitative themes and evidence boundaries

Counts identify distinct participants, not repeated comments. Labels distinguish
submitted observation fields (O), participant feedback/open answers (F), and analyst
interpretation (I). No independent screen recording or receipt was inspected here.

| Theme | Participants | Source evidence | Interpretation / limit |
|---|---|---|---|
| Confirmation/loading feels slow | 3/5: P01, P02, P05 | O/F: P01 confirmation comments and one-confirmation suggestion; P02 loading/response complaint; P05 repeated more-than-a-minute confirmation comments | Perceived delay supported; P02 describes broader UI loading, not specifically six confirmations. Numeric timings conflict and do not quantify the full wait. |
| Smart Account/delegation and create uncertainty | 2/5: P02, P04 | O: T4 assistance=yes; P02 notes Smart Account failure; P04 records revert, mode change and temporary verification unavailability | Recoverable T4 friction; no server/chain investigation proves root cause or automatic resubmission. |
| Old authenticated wallet after MetaMask switching | 1/5: P03 | F: open answer says site stayed logged in with old account | Session presentation concern; no evidence of funds redirected or authorization bypass. |
| Created remittance ID needs clarity | 2/5: P02, P03 | F: P02 mistook remittance ID for transaction ID; P03 asks to show it immediately | Clarify different identifiers; no wrong-recipient outcome reported. |
| Delayed/stale state display | 3/5: P01, P02, P03 | O/F: P01 roles took half a minute; P02 roles/funding/activity take time; P03 balance changed only after refresh | Related but distinct mechanisms; source does not prove one code defect. P05's few-second role reflection is not counted as a complaint. |
| Straightforward navigation/visible status | 2/5: P01, P05 | F: P01 calls navigation intuitive and status clear; P05 reports no navigation friction, straightforward history and quick T7 | Recurring positive feedback, not population evidence. P04 also says overall “all is good” without specifying these aspects. |
| Technical/environment interruption | P05; warnings P03 | O: P05 server/RPC issue and operational URL change; F: P03 MetaMask deceptive-site warnings | Separate operational/tooling observations; warning cause and any false-positive status are unverified. Not automatically DApp usability defects. |

## 8. Strongest findings and recommendations

| ID / severity | Finding / tasks / support | Recorded observation | Participant feedback | Interpretation and recommendation |
|---|---|---|---|---|
| U9-01 / MEDIUM | Perceived confirmation/loading delay; T1–T4, T6/T8; 3/5 P01/P02/P05 | P01 repeated confirmation waits; P02 input-to-enable delay; P05 multiple confirmation waits | P01 wants one confirmation; P02 faster response; P05 shorter wait | Delay creates uncertainty but reported outcomes were recoverable. Later apply approved one-confirmation policy; distinguish other loading causes, which that change may not solve. |
| U9-02 / MEDIUM | Smart Account/delegation incompatibility and unresolved verification uncertainty; T4; 2/5 P02/P04 | Both required T4 help. P04 records revert and uncertain subsequent execution/verification; outcome still completed | P04 identifies Smart Account setup as most difficult | Expect ordinary accounts, add guidance, retain verification-only retry protections. Do not add Smart Account support or assert the DApp auto-resubmitted: “appeared” is an unverified report. |
| U9-03 / MEDIUM | MetaMask account/session mismatch in presentation; T1/account context; 1/5 P03 | No corresponding detailed task-field observation | P03 reports old logged-in account after switching | Later invalidate old authentication on active-account change and require fresh login. No demonstrated exploit or misdirected payment is claimed. |
| U9-04 / LOW | Remittance identifier clarity; T4/T5; 2/5 P02/P03 | Both completed T4/T5; no identifier-related failure recorded | P02 confused remittance and transaction IDs; P03 asks to display new ID | Later prominently display created remittance ID. Keep the transaction hash distinct. |
| U9-05 / MEDIUM | State visibility/refresh uncertainty; T1–T3/status; 3/5 P01/P02/P03 | P01 role delay; P02 notes delayed role/funding/activity refresh | P03 reports stale balance until refresh and requests automatic updates | Investigate context/refresh behavior later with evidence. Broader auto-refresh remains a recommendation, not approved implementation; do not undo selective caching. |

No HIGH-severity root cause is established by these responses. That is not proof
that none exists. In particular, the two T6 noncompletions and P04 T7 noncompletion
need clarification in future evaluation; they cannot be attributed to a particular
blocker without evidence. The partial journey coverage is a limitation, not erased
by freezing the analysis. There is no demonstrated unresolved HIGH issue requiring
immediate code intervention or making this five-session assessment invalid.

## 9. Owner-approved follow-up decisions — record only

**All four decisions are recorded, NOT implemented here.** Frozen runtime behavior
remains unchanged, including its six-confirmation policy.

1. **Confirmation threshold:** later change application success policy from six to
   one confirmed block. Additional confirmations can accumulate naturally. This
   reduces application-imposed waiting, not necessarily RPC/UI loading. One confirmation
   provides less protection against a short reorganization than six; accepted for
   the bounded Sepolia coursework prototype subject to remediation regression/smoke
   testing. It is not a production financial-finality guarantee.
2. **Smart Account:** do not implement support. Later add clear guidance for an
   ordinary MetaMask account on Sepolia and disabling Smart Account/delegation mode
   when it causes incompatibility.
3. **Account switching:** later invalidate the authenticated session when active
   MetaMask account changes and require re-authentication for the new account. Do
   not present the previous authenticated address as the new active account.
4. **Created ID:** later prominently display the newly created remittance ID after
   successful creation, without a broader UI redesign.

Other improvements, including broader automatic refresh, remain recommendations/
future work pending separate approval. No remediation pass or Iteration 10 begins.

## 10. Limitations and conclusions

- n=5; classmates/friends recruited as a convenience sample, not representative of
  migrant/remittance users. No validated SUS study, inferential statistics or significance.
- Participants used their own MetaMask wallets and Sepolia test ETH on the existing
  deployed prototype; no real-money suitability or speed/cost comparison is evaluated.
- Facilitator involvement is recorded for P02/P04 T4. Setup/counterparty actions were
  planned, but the form does not fully verify their execution or exact assistance.
- Incomplete/non-standardized timings, conflicting phase descriptions, blank logs,
  limited Recipient coverage and unexplained incomplete/unattempted tasks constrain
  performance and causal conclusions.
- Public RPC/server issues, wallet modes and MetaMask warnings can affect experience;
  technical/environment incidents are not automatically interface defects.
- Observations are owner-entered form records, not independently observed by Work;
  feedback and analyst interpretation remain separate. No new live verification/write.
- High ratings do not establish general usability. This sample does not validate
  migrant-user needs, production financial suitability, regulatory compliance or
  that blockchain is faster/cheaper than real remittance systems.

Conclusion: Sender-side tasks were completed by all five, with create assistance
for two. Two completed the full core journey independently. The evidence supports
bounded clarity/wait/session recommendations and explicitly incomplete Recipient
coverage. Freeze means the evidence and conservative analysis are accepted, not
that usability is flawless or approved remediation already shipped.

## 11. Verification and freeze criteria

Validation confirms 45 rows (40 task + 5 questionnaire), exactly P01–P05, T1–T8/Q1
for every participant, preserved 19-field schema/perspectives, 25 valid 1–5 ratings,
source-based timing conversion only and unchanged P02 T6/T7. No qualitative timing
was assigned seconds; missing assistance is not converted to no. T8 is analysed separately.
CSV counts, rating summaries and task timing samples were computed from the normalized
rows; source and output fields were compared during validation. Git diff is limited to
this document and the CSV; whitespace/sensitive-data checks pass. No production test
suite or blockchain writes are necessary for this evidence-only change.

Current results replace the blank template; original preparation history is retained
below. Five-session data collection and analysis are complete, with the stated gaps.
The four follow-ups require a separate authorized implementation pass.

<details>
<summary>Appendix A — Original approved preparation protocol (historical; its pending status is superseded above)</summary>

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

</details>

**ITERATION 9: APPROVED / FROZEN**
