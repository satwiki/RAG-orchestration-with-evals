---
description: "Audit code against OWASP Top 10 and report prioritized, evidence-based security findings"
name: "OWASP Security Audit"
argument-hint: "[scope=workspace] [owaspVersion=latest-stable]"
agent: "agent"
---

# OWASP Security Audit

## Inputs

* ${input:scope:workspace}: (Optional, defaults to the workspace) Files, folders,
  components, or changed code to audit.
* ${input:owaspVersion:latest-stable}: (Optional, defaults to the latest stable
  release) OWASP Top 10 version to apply.

## Requirements

Perform a read-only security audit of the requested scope. Do not modify source
files unless the user separately asks for fixes.

1. Establish the system context before rating findings. Inspect relevant source,
   configuration, dependency manifests, entry points, trust boundaries, data
   flows, authentication and authorization paths, secret handling, persistence,
   external integrations, and deployment assumptions.
2. Apply every category in the requested OWASP Top 10 version. State the exact
   version used and include a compact coverage summary showing which categories
   were assessed, which had findings, and which could not be verified.
3. Use repository searches and available static analysis, dependency audit,
   secret scanning, or focused tests when they can provide evidence. Run only
   non-destructive checks. Report commands that could not run and why.
4. Trace suspected issues to reachable code paths and practical attack vectors.
   Distinguish confirmed vulnerabilities from risks that depend on unverified
   deployment or runtime assumptions. Do not report a vulnerability from a
   keyword match alone.
5. Estimate exploitation probability from the current system context, including
   reachability, attacker access, exploit complexity, existing controls, data
   sensitivity, and deployment exposure. Express the estimate as a range, state
   assumptions, and label confidence as low, medium, or high. Do not imply that
   the estimate is a measured incident probability.
6. Classify each finding into exactly one category:
   * Critical: Must fix before release or continued exposure. Include exposed
     environment credentials, committed secrets, hardcoded credentials, or a
     credible attack path with an estimated exploitation probability above 90%.
   * Medium: Does not present an immediate critical risk but warrants remediation
     within 60 days. Include actionable findings that do not meet the Critical
     threshold and are more than long-term hardening opportunities.
   * Recommendation: Long-term hardening with estimated exploitation probability
     below 10% and no evidence of immediate exposure. Do not use this category to
     downgrade a high-impact vulnerability solely because likelihood is uncertain.
7. Never print secret values. Redact credentials and tokens while retaining only
   enough context to identify their location and type.
8. Avoid duplicate findings. Group repeated instances under one root cause and
   list each affected location.
9. If no findings qualify for a category, write `None identified` and summarize
   the evidence reviewed. Do not invent findings to populate every category.

## Output Format

Start with an executive summary containing the audit scope, OWASP version,
checks performed, key assumptions, and overall residual risk.

Present findings under these headings in this exact order:

1. `Critical`
2. `Medium`
3. `Recommendation`

For every finding, provide:

* A concise title and stable finding ID
* The mapped OWASP Top 10 category
* Severity rationale and potential impact
* Exploitation probability range, confidence, and supporting assumptions
* Evidence with workspace-relative code paths and precise line number or line
  range for every affected location
* The reachable attack path or preconditions
* A concrete remediation suggestion aligned with existing project patterns
* A focused validation step that confirms the fix

Finish with:

* An OWASP coverage matrix
* A prioritized remediation plan grouped into immediate, 60-day, and long-term
  actions
* Testing and evidence gaps that limit confidence

---

Begin the audit now using the provided scope and repository context.