You are re-judging a code/document review finding produced by an automated review agent. Score it on the SAME 4-tier severity scale the original review used.

SCALE (choose exactly one):
- CRITICAL: blocks correctness/safety; must fix before proceeding; could cause data loss, security breach, or system failure
- HIGH: significant issue; should fix before shipping; meaningfully undermines the plan/code's stated goals
- MEDIUM: worth fixing; moderate risk or quality concern; not blocking
- LOW: minor issue, style/nit-level, or a design gap rather than a bug

REVIEW AGENT TYPE: {review_agent}
SUBJECT BEING REVIEWED: {subject}
FINDING LOCATION: {location}

FINDING TEXT:
{full_text}

TASK: Assign a severity tier (CRITICAL/HIGH/MEDIUM/LOW) to this finding, as if you were the original reviewer scoring it for the first time. Also give a binary confirm/reject verdict: would you CONFIRM this finding is real and worth flagging, or would you REJECT it (e.g. as a non-issue, a misunderstanding, or something already handled elsewhere)?

Respond in EXACTLY this format, no other text:
SEVERITY: <CRITICAL|HIGH|MEDIUM|LOW>
VERDICT: <CONFIRM|REJECT>
