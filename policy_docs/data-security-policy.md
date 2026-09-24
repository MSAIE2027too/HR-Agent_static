# Data Security Policy

## Classification

Company data has three levels: public, internal, and restricted. Customer data is always restricted. Restricted data may live only on encrypted company devices and approved systems. When in doubt, treat data as restricted. Classification labels appear in document headers; unlabeled drafts default to internal.

## Device rules

All work devices must use encryption, VPN outside the office, and pinned screen lock. Personal devices may not store customer data. Public Wi-Fi is prohibited without VPN. Lost or stolen devices must be reported to Security within 24 hours for remote wipe. Jailbroken or rooted devices may never access company systems.

## Access and passwords

Multi-factor authentication is mandatory on all accounts. Passwords must be unique per system and stored in the approved manager; sharing credentials is a conduct violation. Access is reviewed quarterly and revoked on role change or departure. Dormant accounts over 90 days are disabled automatically.

## Customer data handling

Access customer data only for the task at hand, never bulk-export without approval, and never forward it outside approved channels. Anonymize or aggregate wherever the task allows. Downloads of restricted datasets need manager approval with a stated retention date, after which copies must be deleted and confirmed.

## Incident response

On suspected incident: disconnect the affected device, preserve logs, and notify Security immediately. Do not forward or exfiltrate customer data during investigation. Security acknowledges within 4 business hours and issues a case number. Post-incident reviews are shared as anonymized lessons. Deliberate concealment of an incident is a terminable offense.

## Training

Annual security training is mandatory for all employees and must be current before any international remote stint. Engineers with production access complete an additional secure-coding module yearly. Phishing simulations run quarterly; repeated failures trigger targeted coaching.

## Vendor and third-party data

Customer data may go to vendors only under a signed data-processing agreement with Security approval. AI tools and external services need the same approval before receiving any internal or restricted data. The approved-tool list lives in the IT portal.

## Frequently asked questions

Can I use personal AI tools for work text? Only approved tools, and never with customer data. What counts as an incident? Suspected compromise, lost device, strange access prompts, or any customer-data exposure — when unsure, report. Who do I call at 2am? The Security on-call line in the IT portal.

## Handling procedures per level

Public data needs no special handling beyond normal care. Internal data stays in company systems, with sharing links set to company-only and downloads logged. Restricted data adds need-to-know access lists, retention dates on every export, and deletion confirmations filed back. Moving data up a level in protection is always allowed; moving it down needs Security approval.

## Vendor review process

New vendors handling internal or restricted data submit a security questionnaire covering encryption, access control, breach notification, and subprocessors. Security reviews within 2 weeks; high-risk findings need remediation before signing. Annual re-reviews apply to restricted-data vendors. The questionnaire template lives in the IT portal.

## Approved-tool onboarding

Teams propose tools with the data levels involved and the vendor questionnaire attached. Security decides within 2 weeks: approved, approved-with-conditions (for example no customer data), or denied with reasons. Approvals publish to the approved-tool list with the data ceiling stated. Reviews recur yearly or on vendor ownership change. Using an unapproved tool with internal data triggers coaching first; with restricted data it triggers a formal case.

## Offboarding data return

Departing vendors return or certify destruction of company data within 30 days of contract end, with a signed attestation. Data escrow applies where the contract requires continuity. Termination for breach accelerates all return clocks to 7 days with Security oversight.

## Worked examples

Example A: an Engineer needs a customer export for debugging. Manager approval with a 7-day retention date, restricted handling, deletion confirmation filed. Compliant.

Example B: a Designer pastes a customer quote into an unapproved public AI tool. That is restricted data leaving approved systems: disconnect, preserve, notify Security within the hour. The post-incident review becomes an anonymized lesson.

Example C: a lost encrypted laptop with VPN-only access and 24-hour report. Remote wipe issues, no customer data at rest outside approved sync, case closes as contained.

## Definitions glossary

Encryption renders data unreadable without the key; all work devices ship encrypted. VPN is the tunnel making remote traffic private; required offsite. MFA is the second proof of identity beyond passwords. Need-to-know limits access to the task at hand. Retention date is the deadline after which an export must be deleted and confirmed. Remote wipe is the Security-triggered erase of a lost device. Data-processing agreement is the vendor contract governing customer data handling.

## Team hygiene routine

Monthly: review who holds restricted exports and confirm retention dates. Quarterly: access review plus phishing simulation debrief. Yearly: training renewal and vendor re-reviews for restricted-data suppliers. Managers attest completion in the portal; gaps get dated remediation plans, not blame.
