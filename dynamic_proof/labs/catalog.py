# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Composition root. The deduction and verification code does not import this module."""
from . import particle_theory, riemann, strings, tmf

LABS = (riemann.LAB, strings.LAB, tmf.LAB, particle_theory.LAB)
BY_ID = {lab.id: lab for lab in LABS}
