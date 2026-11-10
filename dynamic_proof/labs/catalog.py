# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Composition root. The deduction and verification code does not import this module."""
from . import riemann, strings, tmf

LABS = (riemann.LAB, strings.LAB, tmf.LAB)
BY_ID = {lab.id: lab for lab in LABS}
