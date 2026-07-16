"""psadiag — K-line diagnostic tool for late-90s/early-2000s Peugeot/Citroën (PSA).

Reads and clears engine fault codes on KWP2000/ISO9141-era PSA ECUs
(Peugeot 306, 206, Citroën Saxo/Xsara etc.) through an ELM327-compatible
USB interface, including the manufacturer-specific init sequences that
generic OBD-II scanner apps never attempt.
"""

__version__ = "0.1.0"
