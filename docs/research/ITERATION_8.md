# Iteration 8 — Problem evidence and research validation

## 1. Scope and frozen baseline

Project: **Cross-Border Remittance DApp with Recipient Claim and Status Tracking**.
Branch: `feature/iteration-8-problem-evidence`. Exact accepted Iteration 7 base:
`56fd8cbe65a3ca27ed4a75bd99b3ffc8636e4cce`.
Iterations 1–7 remain approved/frozen. This iteration changes research artifacts only.
It does not start Iteration 9 or edit the Technical Report.

The MVP uses Sepolia test ETH and three roles: Sender, Recipient, Admin / Auditor.
Its lifecycle is deposit → available → create → reserve → designated recipient claim
or originating sender cancel → status/history. “Cross-border” is the intended user
context, not evidence of international fiat settlement. There is no bank-account
transfer, FX conversion, stablecoin settlement, production KYC/AML, compliance
automation, bridge or production remittance corridor.

## 2. Methodology and evidence boundaries

Research accessed **10 October 2026 (UTC)**. Twelve external sources were selected:
three Singapore government sources and nine multilateral/institutional sources from
the World Bank, FSB, OECD and BIS. Sources were opened directly; numerical findings
were checked against their table definitions. No marketing or secondary aggregators
support the major claims. Most dated publications are from 2023–2026; the 2021 FSB
target is retained as a foundational policy benchmark. This is a targeted desk review,
not a systematic review, representative user survey or new production verification.

[Evidence CSV](../../results/iteration8_evidence.csv) contains 13 paraphrased findings,
source URLs, dates/periods, geography, locators, status and qualifications. S01–S12
identify sources; E01–E13 identify findings. Publication date and reference period
are separate. An undated live page is marked explicitly. S04 bears a September 2025
report label; its April 2026 hosting directory is not treated as its publication date.
The visual issue header and cost page resolve a stale header in PDF text extraction.
S08 is dated to its September 2026 publication listing; an exact day is not relied on.

Three evidence classes must remain separate:

- **External findings:** remittance/payment-system context supported by S01–S12.
- **Frozen technical evidence:** [Iteration 7](../testing/ITERATION_7.md),
  [Iteration 6B](../integration/ITERATION_6B.md), and the frozen contract sources
  support statements about this implementation. Existing hosted lifecycle and
  owner-observed phone evidence are reused; no new live test occurred here.
- **Design inferences:** connections between real-world information needs and
  prototype features are analytical mappings, not proof of user demand or impact.

No source establishes remittance cost savings, faster fiat settlement or representative
usability for this DApp. No new questionnaire or user testing was conducted.

## 3. Refined real-world problem statement

Singapore is a relevant setting for studying remittance workflows involving foreign
workers and overseas recipients. Global evidence identifies uneven transfer costs,
delivery speeds and disclosure/tracking quality, while Singapore already has improved
real-time payment links. These frictions therefore depend on the corridor, provider
and service; they must not be attributed to every Singapore remittance user.

The coursework prototype examines one bounded response: wallet-signed test-asset
transfers with shared verifiable lifecycle state, designated-recipient claims,
pending cancellation and auditable events. It lets participants inspect what happened
within that test workflow. It does not solve the fiat, FX, banking, consumer-redress
or regulatory stack, or establish lower real-world costs or faster international
settlement. The evidenced importance of reliable information supports this evaluation;
the usefulness of the chosen claim/cancel interaction to actual users remains untested.

## 4. Singapore context

MOM reports **1,655,900** foreign workers at June 2026, including **1,243,600** Work
Permit holders (S01/E01). This establishes a relevant population context, not a count
of remittance users. Work Permit subsets must not be added again to the total.
Neither per-worker remittances nor corridor preferences are inferred.

MAS classifies cross-border money transfer as a regulated payment service, with
licensing required unless exempted (S02/E02). This frames real-world institutional
responsibilities; it is not a legal determination about the test prototype.

MAS's February 2023 PayNow–UPI launch describes real-time transfers for participating
Singapore–India customers and explicitly includes foreign workers and students in
its accessibility aims (S03/E03). It establishes remittance relevance and counterevidence
to a universal slowness claim. Launch capabilities are not evidence of current universal
access, adoption or quantified user benefit.

## 5. Global benchmarks and mechanisms

| Dimension | Evidence | Interpretation and boundary |
|---|---|---|
| Cost | World Bank Q3 2025 global USD 200 benchmark **6.36%**; digital **4.59%**, non-digital **7.30%** (S04/E04–05) | Costs differ by service. Simple global averages, not the separately flow-weighted benchmark, Singapore quotes or causal blockchain savings. |
| Definition | RPW includes fees and FX margin; standardised local-currency amounts and snapshot collection (S05/E06) | Some receiving fees/taxes or unavailable FX details can be omitted. Obtain actual provider quotes for a corridor comparison. |
| Speed | FSB 2025 KPI: **54.4%** within an hour, **76.3%** within one business day (S06/E07) | Underlying Q1 2025 RPW USD 200 services with disclosed speed only; service shares, not transaction shares. |
| Policy benchmark | FSB remittance average target **≤3% by 2030**, corridors not above **5%** (S07/E08) | An ambition, not achieved performance or an MVP compliance threshold. |
| Transparency / intermediary dependence | OECD explains disclosure/tracking difficulties across payment chains (S08/E09) | Supports a possible information problem, without quantifying Singapore user prevalence. |
| Delay mechanism | RTGS hours/time-zone gaps can constrain settlement opportunities (S09/E10) | System-level mechanism, not a universal end-to-end remittance duration. |
| Access / coordination | Interoperability and institutional coordination constrain improvements (S12/E13) | No inferred unbanked share or claim that MetaMask improves inclusion. |

Do not combine quarters: the FSB speed evidence uses Q1 2025, whereas the selected
World Bank cost observation is Q3 2025. Neither is a 2026 price/speed estimate.
Price-breakdown availability must not be confused with payment-status tracking
(S06, Table 19); this review does not assert universal opacity.

Fee level, FX margin, availability of funds and information disclosure are different
metrics; blockchain confirmation time is not a substitute for any of them.

## 6. Stakeholders and needs

| Stakeholder | Evidence-linked real-world need | Frozen role / design inference |
|---|---|---|
| Sender | Understand charges, expected delivery and status (S07–08) | Sender signs actions and views lifecycle evidence. Pending cancellation is a design choice, not a surveyed requirement. |
| Recipient | Know whether funds are available and delivery completed (S06–08) | Recipient sees designated incoming test funds and claims them; requiring claim is not proven preferable to automatic real-world delivery. |
| Operator / reviewer | Reliable activity records and operational oversight | Admin / Auditor authorizes ordinary roles, pauses and inspects events; a coursework abstraction, not a bank or regulator. |
| Banks, payment institutions, remittance providers, regulators | Settlement infrastructure, service provision and oversight context (S02, S10, S12) | Contextual entities only; no extra DApp roles or integration are introduced. |

Target users remain migrant/remittance senders and their recipients. No source supports
assigning common financial literacy, access constraints or hardship to all migrants.
Classmate/friend testing can assess usability but cannot establish representativeness.

## 7. Evidence-to-feature mapping

| Evidence-backed issue / rationale | Frozen response | Demonstration | Boundary |
|---|---|---|---|
| Status/delivery information matters (E08–09) | PENDING / COMPLETED / CANCELLED and direct reads | Verifiable test-workflow status | No bank payout or international settlement tracking |
| Traceable records support oversight (E08–09; analytical mapping) | Contract events, verified receipts, Activity | Test transaction evidence; indexed history has provenance | No regulatory audit compliance; Activity may have incomplete backfill |
| Delivery to a designated party (design inference) | Recorded Recipient-only claim | Wallet-bound authorization | No identity/KYC verification or proven user preference for claim |
| Sender control before completion (design inference) | Sender-only pending cancellation | Enforced lifecycle rule | No evidence of provider refund rights or user demand; no cancellation after claim |
| Cost/speed/access friction (E04–07, E10, E13) | Measured gas and tested lifecycle from Iteration 7 | Technical overhead and correctness can be evaluated | No demonstrated reduction in fiat fees/delays or improved inclusion |
| Operational control (coursework requirement) | Immutable Admin, roles and shared pause | Authorized administration | No claim that Admin replaces institutions; pause can block exits |

A broad problem can motivate study without every feature directly solving it. Claims
of savings or faster settlement are excluded rather than forced into this mapping.

## 8. Blockchain-specific justification and trade-offs

The frozen implementation provides shared independently inspectable state, signed
wallet transactions and deterministic claim/cancel rules. Its contracts and events
make the test workflow traceable beyond a single application database. These are
technical capabilities evidenced in Iteration 7, not empirical remittance outcomes.
Wallet signatures authenticate control of an address, not a person's legal identity.

A public ledger also reveals wallet relationships and amounts. Key loss, gas, network
confirmation, RPC availability and irreversible successful actions affect usability.
Single-Admin pause authority limits liveness. Hosting, wallet software, RPC providers
and indexing remain dependencies; the system does not eliminate intermediaries.
The BIS ecosystem assessment cautions against assuming costless or wholly decentralised
infrastructure (S11/E12). Sepolia test ETH and measured gas units are not real fiat fees.

Conventional improvements such as instant-payment interlinking already exist or are
being designed (S03, S10). Blockchain is reasonable here as an academic experiment in
verifiable state and programmable participant rights, not a universally superior
remittance rail. The research does not justify reopening frozen features.

## 9. Conventional approach versus this prototype

This is an architectural comparison, not measured competition with a commercial firm.
Conventional systems can also use strong cryptography, signatures and audit controls.

| Dimension | Conventional provider reference model | Frozen public-chain prototype |
|---|---|---|
| Authority | Provider/payment infrastructure maintains service records | Contracts determine financial test state; immutable Admin controls roles/pause |
| Signing | Provider authentication and payment authorization | MetaMask signs; Flask does not hold signing keys |
| Status | Provider/rail tracking, dependent on integration | Public lifecycle directly readable; no downstream bank status |
| Auditability | Controlled logs; strength depends on design and access | Public events/receipts; Turso is an incomplete non-authoritative index |
| Programmability | Provider rules and integration can enforce workflows | Deterministic pending claim/cancel constraints |
| Availability | Provider and rail operational arrangements | Chain, wallet, RPC and hosted app dependencies; pause risk |
| Privacy | Access-controlled data possible, with institutional disclosure | Public wallet/amount/event exposure |
| Recovery | Provider processes may support complaints/redress | No automatic recovery, dispute process or reversible completed transfer |
| Fiat / FX | Can integrate bank money and currency conversion | Neither implemented |
| Regulation | Licensed arrangements may have compliance processes | No demonstrated production regulatory compliance |
| Scale / usability | Established services can abstract infrastructure from users | Wallet/key/gas burden; low-volume direct scan; no comparative scale evidence |

The prototype's academically useful distinction is independently verifiable contract
state. Conventional services may be more suitable for fiat delivery, privacy, recovery
and everyday use; this review does not establish market superiority.

## 10. Claim validation

| Claim | Classification | Basis / corrected wording |
|---|---|---|
| Cross-border remittances are expensive | SUPPORTED WITH QUALIFICATION | E04–05: global benchmark and variation; no universal/corridor-specific assertion |
| Remittances can experience delays | SUPPORTED WITH QUALIFICATION | E07/E10; some systems already real-time (E03) |
| Users may face limited fee/status transparency | SUPPORTED WITH QUALIFICATION | E06/E09; prevalence for Singapore target users not established |
| Multiple institutions/coordination can add friction | SUPPORTED WITH QUALIFICATION | E09/E13; dependence does not prove every intermediary unnecessary |
| Blockchain improves traceability in this workflow | SUPPORTED | Frozen events and verified receipts; no guarantee UI cache/index is complete |
| Smart contracts enforce designated claim and pending cancel | SUPPORTED | Iteration 7 tests and retained 6A/6B evidence; wallet identity only |
| The prototype reduces real remittance costs | NOT SUPPORTED | No matched fee/FX/fiat comparison; gas units alone are insufficient |
| The prototype speeds real international settlement | NOT SUPPORTED | No fiat settlement measured or implemented |
| The prototype removes intermediaries | NOT SUPPORTED | RPC, wallet, hosting, Admin and off-chain settlement dependencies remain |
| All Singapore migrant remittances are slow/costly | NOT SUPPORTED | No population/corridor evidence; E03 contradicts universal delay |
| The prototype establishes regulatory compliance | NOT SUPPORTED | Role controls/signatures are not compliance evidence |
| Fiat, bank, FX, stablecoin, KYC/AML or bridge integration | OUT OF SCOPE | Explicit frozen exclusions, not latent implemented capabilities |
| Proven production financial suitability | OUT OF SCOPE | Sepolia coursework evaluation only |

## 11. Evidence gaps and limitations

No representative Singapore migrant/remittance-user study, current matched corridor
quotes, worker-level remittance volumes, language/access assessment or comparison of
claim versus automatic delivery was obtained. Those gaps limit user-demand and impact
claims, not the tested technical workflow. No questionnaire is represented as completed.

Global service aggregates cannot be projected onto Singapore or every provider.
Official policy priorities do not prove individual pain-point prevalence. Publication
and data dates differ; live tables can change. Research does not measure causality,
cost advantage, international fiat speed, user satisfaction or financial inclusion.
Owner-observed mobile usability from 6B is technical/manual evidence, not representative
usability evidence. Future evaluation can use a small questionnaire and/or user testing,
with that sampling limitation explicit; no such work is executed here.

## 12. Report-ready evidence summary

These seven findings can later support report drafting; this is not a report chapter.

1. **MOM (S01):** June 2026 workforce scale establishes Singapore relevance; it is not a remittance-demand estimate.
2. **MAS (S03):** PayNow–UPI is evidence of an existing real-time conventional alternative and explicit foreign-worker relevance, with participating-user limits.
3. **World Bank (S04–05):** The Q3 2025 global cost benchmark and channel differences support qualified cost framing; methodology and geography must accompany it.
4. **FSB (S06):** Service-speed differences support uncertainty about delivery; preserve Q1 2025 and disclosed-service denominators.
5. **FSB (S07):** Policy priorities include cost, expected delivery and tracking; these are goals, not measured success.
6. **OECD (S08):** Cross-institution disclosure/tracking complexity supports studying visible state; not a Singapore prevalence estimate.
7. **BIS (S10–12):** Alternative technologies and coordination/crypto trade-offs justify a balanced blockchain experiment rather than a superiority claim.

## 13. Source list and reproducibility

- **S01 — Singapore Ministry of Manpower.** [Foreign workforce numbers](https://www.mom.gov.sg/foreign-workforce-numbers). Publication/update: not stated (live table). Reference: June 2026. Locator: June 2026 column; totals and Work Permit rows.
- **S02 — Monetary Authority of Singapore.** [Types of Payment Services](https://www.mas.gov.sg/regulation/payments/licensing-for-payment-service-providers/types-of-payment-services). Publication/update: 2025-10-10 (last updated). Reference: classification at page update. Locator: introductory licensing statement; cross-border money transfer row.
- **S03 — Monetary Authority of Singapore / Reserve Bank of India.** [Launch of Real-time Payments between Singapore and India](https://www.mas.gov.sg/news/media-releases/2023/launch-of-real-time-payments-between-singapore-and-india). Publication/update: 2023-02-21. Reference: launch on 21 February 2023. Locator: paragraphs 1 and 5.
- **S04 — World Bank.** [Remittance Prices Worldwide, Issue 54, September 2025](https://remittanceprices.worldbank.org/sites/default/files/2026-04/RPW_main_report_and_annex_Q325.pdf). Publication/update: 2025-09 (report label; exact release day not stated). Reference: Q3 2025. Locator: printed pp.6–7; global and digital/non-digital cost sections.
- **S05 — World Bank.** [Remittance Prices Worldwide: Methodology](https://remittanceprices.worldbank.org/methodology). Publication/update: not stated (live methodology). Reference: methodology accessed October 2026; not a price observation. Locator: Amounts; Transfer fee; Exchange Rate Margin; disclaimer.
- **S06 — Financial Stability Board.** [G20 Roadmap for Cross-border Payments: Consolidated progress report for 2025](https://www.fsb.org/uploads/P091025-1.pdf). Publication/update: 2025-10-09. Reference: 2025 KPI column uses World Bank RPW Q1 2025. Locator: Table 17, printed p.58 / PDF page 62; table note.
- **S07 — Financial Stability Board.** [Targets for addressing the four challenges of cross-border payments: Final report](https://www.fsb.org/2021/10/targets-for-addressing-the-four-challenges-of-cross-border-payments-final-report/). Publication/update: 2021-10-13. Reference: policy targets for end-2027 and 2030; not outcomes. Locator: targets table; official G20 targets summary linked in research document.
- **S08 — OECD.** [Transparency in retail cross-border payments and remittances](https://www.oecd.org/content/dam/oecd/en/publications/reports/2026/09/transparency-in-retail-cross-border-payments-and-remittances_9bf43fdb/9f4da8fe-en.pdf). Publication/update: 2026-09 (publication listing; exact day not relied upon). Reference: 2025–26 work programme; questionnaire and desk research; no single consumer reference period. Locator: executive summary p.6; methodology pp.11–12; considerations/conclusions pp.41–42.
- **S09 — BIS / CPMI.** [Changing the clock: practical approaches to extend payment system operating hours](https://www.bis.org/publications/cpmi-brief-6-changing-clock-practical-approaches-extend-payment-system-operating-hours). Publication/update: 2025-01-31. Reference: jurisdictional operating-hours experiences reviewed for 2025 brief. Locator: overview; authors’ views disclaimer.
- **S10 — BIS Innovation Hub.** [Nexus: enabling instant cross-border payments](https://www.bis.org/publications/nexus-enabling-instant-cross-border-payments). Publication/update: 2024-07-01. Reference: 2024 blueprint and collaboration. Locator: overview of instant-payment-system interlinking.
- **S11 — BIS.** [The crypto ecosystem: key elements and risks](https://www.bis.org/publications/crypto-ecosystem-key-elements-and-risks). Publication/update: 2023-07-11. Reference: ecosystem assessment at publication. Locator: overview: congestion, fees, fragmentation and centralisation risks.
- **S12 — BIS.** [Cross-border payment technologies: innovations and challenges](https://www.bis.org/publications/paper-167-cross-border-payment-technologies-innovations-and-challenges). Publication/update: 2026-03-11. Reference: technology and institutional analysis at publication. Locator: abstract: interoperability and coordination constraints.

S07 supplementary official table: [G20 targets summary](https://www.fsb.org/work-of-the-fsb/financial-innovation-and-structural-change/cross-border-payments/g20-targets-for-enhancing-cross-border-payments-2/) (last updated 21 March 2025).
S06 publication page: [2025 consolidated report](https://www.fsb.org/2025/10/g20-roadmap-for-cross-border-payments-consolidated-progress-report-for-2025/).
S08 publication listing: [OECD report](https://www.oecd.org/en/publications/transparency-in-retail-cross-border-payments-and-remittances_9f4da8fe-en.html).
Institution-published author research is distinguished from binding policy; BIS/CPMI
briefs and BIS research papers should not be presented as regulatory obligations.

To reproduce: open the URLs, check the stated table/section and reference period,
then compare E01–E13 with the CSV. For later updates record a new access date and
period; do not silently replace historical figures. No full copyrighted reports are
stored. CSV validation checks required fields, unique IDs, source consistency and
HTTPS URLs. Git scope checks verify only this document and CSV differ from the base.

## 14. Final Iteration 8 acceptance criteria

| Criterion | Result |
|---|---|
| Credible Singapore primary context and global benchmarks | PASS — 12 official/institutional sources |
| Major figures traceable with dates, definitions and limitations | PASS — E01–E13 and source locators |
| Cost, speed, transparency and access/intermediaries investigated | PASS — no universal or inclusion-impact claim |
| Evidence mapped to frozen features without new roles/features | PASS — design assumptions explicitly separated |
| Balanced blockchain and conventional comparison | PASS — no superiority or real settlement claim |
| Claims classified and unsupported benefits excluded | PASS — Section 10 |
| Report-ready research artifacts, no formal-report editing | PASS — document and machine-readable CSV only |
| Frozen code/infrastructure/branches preserved | PASS — research-only scope; no deployment/write |

**ITERATION 8: APPROVED / FROZEN**
