# Bug Report: confidence_fusion parsing & fusion edge cases

Date: 2025-08-25
Module: backend/services/confidence_fusion.py
Related tests: backend/tests/test_confidence_fusion.py

Summary
- While adding unit tests, three failures were observed:
  1) parse_ai_confidence failed to handle negative numbers (e.g. "信心-1/10"), returning 1.0 instead of clamped 0.0.
  2) compute_fusion_score did not clamp tech_score mapped to 0-10 before fusion when tech_score was outside [0,1], leading to wrong results for tech>1 and tech<0.
  3) Minor mismatch in expectations due to rounding/clamping nuances.

Error Logs (pytest excerpts)
- test_parse_ai_confidence: expected 0.0 for "信心-1/10", got 1.0
- test_compute_fusion_score: expected 6.5 for (tech=1.2, ai=3.0, alpha=0.5), obtained 7.5
- test_compute_fusion_score: expected 4.5 for (tech=-0.1, ai=9.0, alpha=0.5), obtained 4.0

Root Cause
- Regex did not accept optional minus sign variants (ASCII '-' and Unicode '−'、'－').
- Fusion calculation used tech_score*10 directly without bounding; out-of-range tech values produced unbounded mapped values.

Fix Applied
1) parse_ai_confidence
   - Updated regex patterns to allow an optional minus sign [\-−－].
   - Normalized Unicode minus signs to ASCII '-' before float conversion.
   - Kept existing clamping to [0,10] with warning log when out-of-range.

2) compute_fusion_score
   - After mapping tech_score to 0-10, added clamping: tech_score_10 = max(0.0, min(10.0, tech_score*10)).
   - Kept existing info log for fallback and warn log for missing tech.

Verification
- Added/updated unit tests in backend/tests/test_confidence_fusion.py covering:
  - Negative values, full/half width digits, parentheses formats.
  - Fusion with tech outside [0,1] and ai_confidence None.
- Test run result: 21 passed.

Prevention
- Retain and run these tests in CI.
- In future changes touching parsing/fusion logic, run pytest locally before commit.

Notes
- CONF_FUSION_ALPHA reads from env (default 0.4) and prints on startup. Consider adding logger.info if centralized logging is configured.