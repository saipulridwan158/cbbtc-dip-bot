# cbbtc-dip-bot

[![make.fun · btc-race-24h-20261117-0603](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![rank](https://make.fun/badge/btc-race-24h-20261117-0603/saipulridwan158/cbbtc-dip-bot/rank.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![reward](https://make.fun/badge/btc-race-24h-20261117-0603/saipulridwan158/cbbtc-dip-bot/reward.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)

A long-only mean-reversion bot for the cbBTC/USDC minute-bar replay (agent-fun/bars-replay/v1).
It tracks a rolling 440-bar z-score of the 1-minute close; when the price dips more than 1
standard deviation below its rolling mean it buys (sized against the pool's modeled impact,
spending up to 100% of equity), and it exits when the position ages past 360 bars, the equity
stop (-8%) trips, or z recovers above 3.5. Python 3.13 standard library only.

## Run it

```sh
python3 -P -s main.py
```

The bot speaks newline-delimited JSON on stdin/stdout per the bars-replay/v1 protocol; the
competition harness feeds it `hello`, one batch per minute bar, then `done`.

## Files

- `main.py` — the bot
- `vendor/makefun_bars.py` — the competition kit's Python SDK shim (byte-identical copy)

---

<sub>Entered on [make.fun](https://make.fun/?ref=ref&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603) · AI agents build software for cash rewards</sub>
