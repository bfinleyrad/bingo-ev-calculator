"""
Bingo Blackout EV Calculator — Streamlit Web App
"""

import streamlit as st
import pandas as pd
import altair as alt
from math import comb

# ── Page config ──────────────────────────────────────────────
st.set_page_config(page_title="Bingo Blackout EV Calculator", layout="wide")

# ── Constants ────────────────────────────────────────────────
TOTAL_NUMBERS    = 75
SPACES_PER_BOARD = 24
BOARDS_PER_SET   = 3
SET_COST         = 2.0

# ── Hard-coded but easily changed ────────────────────────────
JACKPOT                 = 1000.0
NONJACKPOT_PAYOUT_RATIO = 0.50


# ── Math core (same as bingo_ev.py) ──────────────────────────

def p_complete_by(c):
    if c < SPACES_PER_BOARD:
        return 0.0
    if c >= TOTAL_NUMBERS:
        return 1.0
    return comb(c, SPACES_PER_BOARD) / comb(TOTAL_NUMBERS, SPACES_PER_BOARD)

def p_complete_on(c):
    if c < SPACES_PER_BOARD:
        return 0.0
    return p_complete_by(c) - p_complete_by(c - 1)

def binom_pmf(k, n, p):
    if k < 0 or k > n:
        return 0.0
    if p == 0.0:
        return 1.0 if k == 0 else 0.0
    if p == 1.0:
        return 1.0 if k == n else 0.0
    return comb(n, k) * (p ** k) * ((1.0 - p) ** (n - k))

def expected_share(your_boards, other_boards, q):
    total = your_boards + other_boards
    p_none = (1.0 - q) ** total
    p_at_least_one = 1.0 - p_none
    if p_at_least_one < 1e-300:
        return 0.0
    max_y = min(your_boards, 25)
    max_z = min(other_boards, 40)
    numerator = 0.0
    for y in range(1, max_y + 1):
        py = binom_pmf(y, your_boards, q)
        if py < 1e-300:
            continue
        for z in range(0, max_z + 1):
            pz = binom_pmf(z, other_boards, q)
            if pz < 1e-300:
                continue
            numerator += (y / (y + z)) * py * pz
    return numerator / p_at_least_one

def calculate_ev(your_sets, num_players, avg_sets, call_limit,
                 jackpot=1000.0, nonjackpot_ratio=0.50, set_cost=2.0, boards_per_set=3):
    your_boards  = your_sets * boards_per_set
    other_sets   = round((num_players - 1) * avg_sets)
    other_boards = other_sets * boards_per_set
    total_boards = your_boards + other_boards
    total_sets   = your_sets + other_sets
    revenue      = total_sets * set_cost
    consolation  = nonjackpot_ratio * revenue

    ev_payout     = 0.0
    p_jackpot_hit = 0.0
    p_you_win     = 0.0

    for c in range(SPACES_PER_BOARD, TOTAL_NUMBERS + 1):
        p_by_prev = p_complete_by(c - 1)
        p_by_c    = p_complete_by(c)
        p_no_win_before  = (1.0 - p_by_prev) ** total_boards
        p_no_win_by_c    = (1.0 - p_by_c)    ** total_boards
        p_first_win_on_c = p_no_win_before - p_no_win_by_c
        if p_first_win_on_c < 1e-300:
            continue
        if p_by_prev < 1.0:
            q = p_complete_on(c) / (1.0 - p_by_prev)
        else:
            q = 1.0
        e_share = expected_share(your_boards, other_boards, q)
        prize = jackpot if c <= call_limit else consolation
        if c <= call_limit:
            p_jackpot_hit += p_first_win_on_c
        ev_payout += p_first_win_on_c * prize * e_share
        p_none_yours = (1.0 - q) ** your_boards
        p_none_all   = (1.0 - q) ** total_boards
        if (1.0 - p_none_all) > 0:
            p_you_win += p_first_win_on_c * (1.0 - p_none_yours) / (1.0 - p_none_all)

    return {
        "your_sets":       your_sets,
        "your_boards":     your_boards,
        "total_boards":    total_boards,
        "total_sets":      total_sets,
        "expected_payout": ev_payout,
        "expected_profit": ev_payout - your_sets * set_cost,
        "p_jackpot_hit":   p_jackpot_hit,
        "p_you_win":       p_you_win,
    }


# ── Global font scaling ───────────────────────────────────────
st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 70% !important; }
    h1 { font-size: 1.8rem !important; }
    h2 { font-size: 1.4rem !important; }
    h3 { font-size: 1.2rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.85rem !important; }
</style>
""", unsafe_allow_html=True)

# ── UI ───────────────────────────────────────────────────────

# Sidebar inputs
with st.sidebar:
    st.header("Navigation")
    page = st.radio("", ["Calculator", "About"], label_visibility="collapsed")
    st.divider()
    st.header("Game Parameters")

    num_players = st.number_input(
        "Number of players", min_value=2, max_value=500, value=100, step=1
    )
    avg_sets = st.number_input(
        "Avg board sets per player", min_value=1.0, max_value=10.0, value=2.0, step=0.5
    )
    your_sets = st.number_input(
        "Your current board sets", min_value=1, max_value=20, value=2, step=1
    )
    call_limit = st.slider(
        "Jackpot call limit", min_value=48, max_value=75, value=56
    )

    st.divider()

    with st.expander("⚙️ Advanced: Prize & Cost Settings"):
        JACKPOT = st.number_input(
            "Jackpot amount ($)", min_value=100, max_value=10000, value=1000, step=50
        )
        nonjackpot_pct = st.slider(
            "Non-jackpot payout (% of final round revenue)",
            min_value=0, max_value=100, value=50, step=5,
            format="%d%%"
        )
        NONJACKPOT_PAYOUT_RATIO = nonjackpot_pct / 100
        SET_COST = st.number_input(
            "Cost per board set ($)", min_value=1.0, max_value=20.0, value=2.0, step=0.50
        )
        BOARDS_PER_SET = st.selectbox(
            "Boards per set", options=[1, 2, 3], index=2
        )

if page == "About":
    st.title("About This Calculator")
    st.markdown("""
    ### What is this?
    This tool calculates the **expected value (EV)** of buying an extra board set
    in the final blackout (coverall) round of a cash-prize bingo game.

    ### The setup
    Many bingo nights end with a **coverall round** — you must mark every number on
    your board to win. A cash jackpot is awarded if someone achieves coverall within
    a set number of calls (typically 50–60). If nobody wins within that limit, a
    smaller consolation prize is paid out instead.

    In the final round, players can buy **additional board sets** beyond their
    standard entry. The question this tool answers is:

    > *Given the number of players, the prize structure, and the call limit —
    > is spending $2 on an extra set a positive or negative expected value decision?*

    ### How it works
    The calculator uses a **deterministic, iterative probability model** — no
    random simulation. For each possible winning call number (24 through 75), it computes:

    1. The probability that the first coverall in the room occurs on exactly that call
    2. Your expected share of the prize at that call, accounting for ties and splits
    3. Whether the jackpot or consolation prize applies

    It sums these contributions across all possible call numbers to produce an exact
    expected payout, then compares the marginal value of adding one more set against
    its $2 cost.

    ### When is it +EV to buy an extra set?
    In general, extra sets become positive EV when:
    - The **jackpot call limit is generous** (58+ calls)
    - The **number of players is small** (fewer boards to compete against)
    - The **jackpot is large** relative to total board sets in play
    - The **average boards per player is low** (less competition)

    Under a revenue-share consolation prize (e.g., 50% of final round revenue),
    buying extra sets is almost always slightly negative — your extra $2 only adds
    $1 to the consolation pool, which is then shared with everyone.
    The fixed jackpot is where positive EV opportunities arise.

    ### Context
    This calculator was built for a specific local bar bingo format with a
    **$1,000 fixed jackpot** and a **50% revenue-share consolation prize**.
    The Advanced settings let you adapt it to other prize structures.

    ### Limitations
    - Assumes all players buy the same average number of sets
    - Treats boards as independent (a very good approximation for blackout)
    - Does not account for non-standard bingo card formats
    """)
    st.stop()

st.title("🎱 Bingo Blackout — Extra Board Set Calculator")
st.caption("Should you buy an extra board set in the final round?")

# ── Calculations ─────────────────────────────────────────────

kw = dict(jackpot=JACKPOT, nonjackpot_ratio=NONJACKPOT_PAYOUT_RATIO,
          set_cost=SET_COST, boards_per_set=BOARDS_PER_SET)

base   = calculate_ev(your_sets,     num_players, avg_sets, call_limit, **kw)
plus1  = calculate_ev(your_sets + 1, num_players, avg_sets, call_limit, **kw)

marginal_ev  = plus1["expected_payout"] - base["expected_payout"]
marginal_net = marginal_ev - SET_COST  # SET_COST is now the user-input value

# ── Key metrics row ───────────────────────────────────────────

st.subheader("Your Current Position")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Your boards", f"{base['your_boards']} ({your_sets} sets)")
col2.metric("Total boards in room", base["total_boards"])
col3.metric("P(jackpot hit)", f"{base['p_jackpot_hit']:.2%}")
col4.metric("P(you win a share)", f"{base['p_you_win']:.2%}")

col5, col6, col7 = st.columns(3)
col5.metric("Expected payout", f"${base['expected_payout']:.2f}")
col6.metric("Your cost", f"${your_sets * SET_COST:.2f}")
col7.metric("Expected profit", f"${base['expected_profit']:.2f}",
            delta=f"${base['expected_profit']:.2f}", delta_color="normal")

st.divider()

# ── Marginal decision ─────────────────────────────────────────

st.subheader(f"Should You Buy One More ${SET_COST:.0f} Set?")

dcol1, dcol2, dcol3 = st.columns(3)
dcol1.metric("Marginal expected payout", f"${marginal_ev:.4f}")
dcol2.metric("Cost of extra set", f"${SET_COST:.2f}")

if marginal_net > 0:
    dcol3.metric("Net edge", f"+${marginal_net:.4f}", delta="BUY — positive EV", delta_color="normal")
    st.success(f"✅ Buying one more set is **+EV** by ${marginal_net:.4f} at {call_limit} calls.")
elif marginal_net < -0.10:
    dcol3.metric("Net edge", f"${marginal_net:.4f}", delta="DON'T BUY — negative EV", delta_color="inverse")
    st.warning(f"❌ Buying one more set is **-EV** by ${abs(marginal_net):.4f} at {call_limit} calls.")
else:
    dcol3.metric("Net edge", f"${marginal_net:.4f}", delta="Approximately break-even", delta_color="off")
    st.info(f"⚖️ Buying one more set is approximately **break-even** at {call_limit} calls.")

st.divider()

# ── Call limit sweep chart ────────────────────────────────────

st.subheader("Marginal Net EV vs Jackpot Call Limit")
st.caption("How does the edge change as the call limit shifts?")

sweep_data = []
for cl in range(48, 76):
    r1 = calculate_ev(your_sets,     num_players, avg_sets, cl, **kw)
    r2 = calculate_ev(your_sets + 1, num_players, avg_sets, cl, **kw)
    net = (r2["expected_payout"] - r1["expected_payout"]) - SET_COST
    sweep_data.append({"Call limit": cl, "Net EV of extra set ($)": round(net, 4)})

df_sweep = pd.DataFrame(sweep_data)

chart = (
    alt.Chart(df_sweep)
    .mark_line(point=True)
    .encode(
        x=alt.X("Call limit:Q", title="Jackpot Call Limit"),
        y=alt.Y("Net EV of extra set ($):Q", title="Net EV of +1 Set (after $2 cost)"),
        color=alt.condition(
            alt.datum["Net EV of extra set ($)"] > 0,
            alt.value("#2ecc71"),
            alt.value("#e74c3c"),
        ),
        tooltip=["Call limit", "Net EV of extra set ($)"],
    )
    + alt.Chart(pd.DataFrame([{"y": 0}]))
    .mark_rule(strokeDash=[4, 4], color="gray")
    .encode(y="y:Q")
)

st.altair_chart(chart, use_container_width=True)

# ── Detailed table ────────────────────────────────────────────

st.subheader("Marginal EV Table (current call limit)")

max_extra = 5
rows = []
prev_payout = None
for s in range(your_sets, your_sets + max_extra + 1):
    r = calculate_ev(s, num_players, avg_sets, call_limit, **kw)
    if prev_payout is not None:
        marg = r["expected_payout"] - prev_payout
        net  = marg - SET_COST
        rows.append({
            "Sets": s,
            "Boards": r["your_boards"],
            "E[Payout]": f"${r['expected_payout']:.4f}",
            "Marginal EV": f"${marg:.4f}",
            "Net of $2":  f"${net:.4f}",
            "Decision":   "+EV" if net > 0 else "-EV",
        })
    prev_payout = r["expected_payout"]

df_table = pd.DataFrame(rows)

def highlight_ev(row):
    color = "#d4edda" if row["Decision"] == "+EV" else "#f8d7da"
    return [f"background-color: {color}"] * len(row)

st.dataframe(
    df_table.style.apply(highlight_ev, axis=1),
    use_container_width=True,
    hide_index=True,
)
