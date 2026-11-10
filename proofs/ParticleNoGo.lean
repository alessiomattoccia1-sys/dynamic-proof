-- Copyright 2026 Alessio Mattoccia
-- SPDX-License-Identifier: Apache-2.0
import Mathlib.LinearAlgebra.Matrix.Determinant.Basic

open scoped BigOperators

/-- An odd number of odd multiples cannot give the zero charge sum of a determinant term. -/
theorem dp_particle_odd_det {n : ℕ} {R : Type*} [CommRing R]
    (q : Fin n → ℤ) (d : ℤ) (M : Matrix (Fin n) (Fin n) R)
    (hn : Odd n) (hd : d ≠ 0) (hq : ∑ i, q i = 0)
    (hs : ∀ i j, M i j ≠ 0 → ∃ k : ℤ, q i + q j = d * (2 * k + 1)) :
    M.det = 0 := by
  classical
  rw [Matrix.det_apply]
  refine Finset.sum_eq_zero fun σ _ => ?_
  have hz : ∃ i, M (σ i) i = 0 := by
    by_contra missing
    have nonzero (i : Fin n) : M (σ i) i ≠ 0 := fun h => missing ⟨i, h⟩
    choose k hk using fun i => hs (σ i) i (nonzero i)
    have hperm : ∑ i, q (σ i) = ∑ i, q i := Equiv.sum_comp σ q
    have hsum : ∑ i, (q (σ i) + q i) = 0 := by
      rw [Finset.sum_add_distrib, hperm, hq, add_zero]
    have hlinear : ∑ i, (q (σ i) + q i) = d * (2 * (∑ i, k i) + (n : ℤ)) := by
      simp_rw [hk]
      rw [← Finset.mul_sum, Finset.sum_add_distrib, ← Finset.mul_sum]
      simp
    rw [hlinear] at hsum
    have h := (mul_eq_zero.mp hsum).resolve_left hd
    obtain ⟨m, hm⟩ := hn
    omega
  obtain ⟨i, hi⟩ := hz
  have hprod : (∏ j, M (σ j) j) = 0 :=
    Finset.prod_eq_zero (f := fun j => M (σ j) j) (Finset.mem_univ i) hi
  rw [hprod, smul_zero]

/-- The single complex scalar and its conjugate are the two odd multiples ±h. -/
theorem dp_particle_one_scalar {n : ℕ} {R : Type*} [CommRing R]
    (q : Fin n → ℤ) (h : ℤ) (M : Matrix (Fin n) (Fin n) R)
    (hn : Odd n) (hh : h ≠ 0) (hq : ∑ i, q i = 0)
    (hs : ∀ i j, M i j ≠ 0 → q i + q j = h ∨ q i + q j = -h) :
    M.det = 0 := by
  apply dp_particle_odd_det q h M hn hh hq
  intro i j hM
  rcases hs i j hM with same | opposite
  · exact ⟨0, by simp [same]⟩
  · refine ⟨-1, ?_⟩
    simp [opposite]
