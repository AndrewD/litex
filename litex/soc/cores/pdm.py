#
# This file is part of LiteX.
#
# Copyright (c) 2021 Andrew Dennison <andrew@motec.com.au>
# Copyright (c) 2015-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *

from litex.soc.interconnect.csr import *


# Pulse Width Modulation ---------------------------------------------------------------------------

class PDM(Module, AutoCSR):
    """Pulse Density Modulation

    Provides the minimal hardware to do Pulse Density Modulation.

    Pulse Density Modulation can be useful for various purposes where reducing the low frequency content
    of the signal is desirable. The output will switch far more often than PWM: there is no control
    of the frequency. Set duty to 0 to eliminate switching.
    """
    def __init__(self, out=None, bits_or_duty=8, default_duty = 0, counter=None, with_csr=False):
        if out is None:
            self.out = out = Signal()
        if isinstance(bits_or_duty, Signal):
            if default_duty:
                raise ValueError("default_duty can not be set when external duty is supplied")
            if with_csr:
                raise ValueError("with_csr can not be set when external duty is supplied")
            bits = bits_or_duty.nbits
            self.duty = duty = bits_or_duty
        else:
            self.bits = bits = bits_or_duty
            self.duty = duty = Signal(bits, reset=default_duty)
            if with_csr:
                self.add_csr()

        # # #

        if counter is None:
            self.counter = counter = Signal(bits, reset_less=True)
            self.sync += counter.eq(counter + 1)
        elif not isinstance(counter, Signal):
            raise ValueError(f"counter must be a Signal")
        elif counter.nbits < bits:
            raise ValueError(f"counter nbits < {bits}")
        else:
            self.counter = counter

        self.sync += [
            # get reversed least significant "bits" of counter
            If(self.counter[bits-1::-1] < duty,
                out.eq(1)
            ).Else(
                out.eq(0)
            ),
        ]

    def add_csr(self):
        from migen.genlib.cdc import MultiReg
        self._duty_csr = self.duty
        self.duty = None # duty not externally writable when there is a csr

        self._duty  = CSRStorage(self.bits, reset_less=True, description="""PDM Width.\n
            Defines the *Duty cycle* of the PDM. PDM is active high for *Duty* ``{cd}_clk`` cycles and
            active low for *Period - Width* ``{cd}_clk`` cycles.""".format(cd=getattr(self.sync, "clock_domains")),
            reset = self._duty_csr.reset)

        n = 0 if getattr(self.sync, "clock_domains") == "sys" else 2
        self.specials += [
            MultiReg(self._duty.storage,  self._duty_csr,  n=n),
        ]
