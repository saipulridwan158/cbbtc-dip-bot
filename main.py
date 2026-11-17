"""cbBTC minute-bar mean-reversion bot (agent-fun/bars-replay/v1), Python 3.13 stdlib only.

Strategy: rolling z-score mean reversion on 1-minute closes. When the latest close drops more
TH_IN standard deviations below the trailing WINDOW-bar mean, buy with most of the cash (sized
against the pool depth so impact + slippage stays under a cap); when z recovers above TH_OUT
(meaning the price popped back toward/above the mean), sell the whole position. A hard time stop
(MAX_HOLD) exits a stale position, and an equity stop exits if the position lost STOP_BPS of
equity. Long only, one position, deterministic: no clock, no random, no environment.
"""

import os
import sys
import statistics

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

WINDOW = 440          # trailing bars for mean/std
TH_IN = 1.0           # buy when z below this
TH_OUT = 3.5          # sell when z above this
MAX_HOLD = 360        # bars; exit a position older than this
STOP_BPS = 800        # exit if position value fell 8% below entry cost
SIZE_BPS = 10000       # spend up to 95% of equity on a buy
MAX_SLIP_BPS = 60     # max slippage+impact per order
IMPACT_CAP_BPS = 25   # max modeled pool impact on a buy
BPS = 10_000

seen = []             # closes history
entry_cost = 0
entry_bar = -1
SYMBOL = "CBBTC"


def zscore(close):
    if len(seen) < WINDOW + 1:
        return None
    w = seen[-WINDOW:]
    m = statistics.fmean(w)
    sd = statistics.pstdev(w)
    if sd == 0:
        return None
    return (close - m) / sd


def on_batch(state, batch):
    global entry_cost, entry_bar
    bar = state.latest.get(SYMBOL)
    if bar is None:
        return []
    close = int(bar["c"])
    seen.append(close)
    if len(seen) > WINDOW * 2:
        del seen[:len(seen) - WINDOW * 2]
    if state.warming_up:
        return []
    z = zscore(close)
    if z is None:
        return []

    held = state.positions.get(SYMBOL)
    if held is not None:
        # exits first
        val = state.value(SYMBOL, held.qty)
        held_bars = state.seq - entry_bar
        stop = entry_cost * (BPS - STOP_BPS) // BPS
        if z > TH_OUT or held_bars >= MAX_HOLD or val <= stop:
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty, "max_slippage_bps": 200}]
        return []

    if z < -TH_IN:
        # size against depth: impact of a trade worth a is a/D per hop; keep impact under half the slip cap
        spend = state.cash * SIZE_BPS // BPS
        # halve spend until its modeled impact is within the cap
        while spend >= state.hello["fees"]["min_notional_quote_units"]:
            imp = state.impact_bps(SYMBOL, spend)
            if imp is None or imp <= IMPACT_CAP_BPS:
                break
            spend //= 2
        min_notional = state.hello["fees"]["min_notional_quote_units"]
        if spend < min_notional:
            return []
        entry_cost = spend
        entry_bar = state.seq
        return [{"side": "buy", "symbol": SYMBOL, "notional_quote_units": spend,
                 "max_slippage_bps": MAX_SLIP_BPS}]
    return []


def on_hello(state):
    global entry_cost, entry_bar
    entry_cost = 0
    entry_bar = -1


def on_done(state, done):
    pass


if __name__ == "__main__":
    makefun_bars.run(on_batch, on_hello=on_hello, on_done=on_done)
