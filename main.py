"""cbBTC minute-bar dip buyer (agent-fun/bars-replay/v1), Python 3.13 stdlib only.

Strategy: buy a dip, sell the recovery. A rolling z-score of the 1-minute close against its
trailing WINDOW-bar mean tells how far the latest bar sits from the recent range. When z drops
below -TH_IN the bot buys, spending up to SIZE_BPS of its equity and sizing the order down until
the pool's modeled price impact stays inside IMPACT_CAP_BPS. When z climbs back above TH_OUT, or
the position is older than MAX_HOLD bars, or the position has lost STOP_BPS of its cost, the whole
position is sold. Long only, one position at a time, never leveraged.

Determinism: no clock, no environment, no randomness; floats are only a mean and a population
standard deviation over a fixed window of integer closes, always in the same order, so two runs on
the same bars produce the same orders byte for byte.
"""

import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
WINDOW = 440          # trailing bars the mean and the deviation are taken over
TH_IN = 1.0           # buy when the close is this many deviations under the mean
TH_OUT = 3.5          # sell once it is this many deviations over the mean
MAX_HOLD = 360        # bars; a position older than this is sold at the next open
MIN_HOLD = 5          # bars; never sell inside this, so one noisy bar cannot flip the position
STOP_BPS = 800        # sell if the position's value falls 8% under what it cost
SIZE_BPS = 10000      # spend at most this share of equity on a buy
MAX_SLIP_BPS = 60     # refuse a fill more than 0.6% past the close the order was decided on
IMPACT_CAP_BPS = 25   # size a buy down until its modeled pool impact is at most this
BPS = 10_000

closes = []           # every close the bot has been sent, oldest first (trimmed to 2 windows)
entry_cost = 0        # what the open position cost, in quote units
entry_bar = -1        # the seq of the bar the buy was decided on


def zscore(close):
    """How many population deviations the close sits from the trailing window's mean."""
    if len(closes) < WINDOW + 1:
        return None
    window = closes[-WINDOW:]
    mean = statistics.fmean(window)
    dev = statistics.pstdev(window)
    if dev == 0:
        return None
    return (close - mean) / dev


def sized_buy(state):
    """The notional to spend: SIZE_BPS of the cash, halved until the modeled impact fits."""
    spend = state.cash * SIZE_BPS // BPS
    minimum = int(state.hello["fees"]["min_notional_quote_units"])
    while spend >= minimum:
        impact = state.impact_bps(SYMBOL, spend)
        if impact is None or impact <= IMPACT_CAP_BPS:
            return spend
        spend //= 2
    return 0


def on_batch(state, batch):
    """One reply per bar: sell what the rules say to sell, else buy a dip, else nothing."""
    global entry_cost, entry_bar
    bar = state.latest.get(SYMBOL)
    if bar is None:
        return []
    close = int(bar["c"])
    closes.append(close)
    if len(closes) > WINDOW * 2:
        del closes[: len(closes) - WINDOW * 2]
    if state.warming_up:
        return []
    z = zscore(close)
    if z is None:
        return []

    held = state.positions.get(SYMBOL)
    if held is not None:
        value = state.value(SYMBOL, held.qty)
        age = state.seq - entry_bar
        floor = entry_cost * (BPS - STOP_BPS) // BPS
        if (z > TH_OUT or age >= MAX_HOLD or value <= floor) and age >= MIN_HOLD:
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty, "max_slippage_bps": 200}]
        return []

    if z < -TH_IN:
        spend = sized_buy(state)
        if spend <= 0:
            return []
        entry_cost = spend
        entry_bar = state.seq
        return [{"side": "buy", "symbol": SYMBOL, "notional_quote_units": spend,
                 "max_slippage_bps": MAX_SLIP_BPS}]
    return []


def on_hello(state):
    global entry_cost, entry_bar
    closes.clear()
    entry_cost = 0
    entry_bar = -1


def on_done(state, done):
    pass


if __name__ == "__main__":
    makefun_bars.run(on_batch, on_hello=on_hello, on_done=on_done)
