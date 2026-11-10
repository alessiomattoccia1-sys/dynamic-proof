-- Copyright 2026 Alessio Mattoccia
-- SPDX-License-Identifier: Apache-2.0
import Mathlib.Tactic.Ring
import Mathlib.Tactic.NormNum
import Mathlib.Data.Rat.Defs

theorem dp_tmf_cleared (w a b da db dw : ℚ) :
    a * b * (w * da + (1 - w) * db + dw * (a - b))
      - (w * a + (1 - w) * b) * (w * b * da + (1 - w) * a * db)
    = w * (1 - w) * (a - b) * (b * da - a * db) + a * b * dw * (a - b) := by
  ring

theorem dp_tmf_mean_gap :
    (1 / 6 : ℚ) - (0 + 1 / 4) / 2 = 1 / 24 := by
  norm_num

theorem dp_divisors_5040 :
    (2 : ℕ)^4 * 3^2 * 5 * 7 = 5040 ∧
    (1 + 2 + 2^2 + 2^3 + 2^4 : ℕ) * (1 + 3 + 3^2) * (1 + 5) * (1 + 7) = 19344 := by
  norm_num
