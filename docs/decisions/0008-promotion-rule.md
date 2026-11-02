# 0008 Promotion rule

"Promote if better" promotes noise. The Trainer promotes a candidate only if its mean validation chrF++ is at
least 0.5 above the incumbent's **re-scored on the same build**, and every direction beats the retrieval floor.
Test is scored once, at promotion, and never used to choose.
