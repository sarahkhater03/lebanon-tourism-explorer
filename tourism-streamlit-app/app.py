"""
Mapping Lebanon's Tourism Infrastructure — interactive Streamlit page
MSBA 325 · Sarah Khater

Two linked controls drive every chart on the page:
  1. Governorate (selectbox)   -> sets the scope AND the options of control 2
  2. Districts (multiselect)   -> only lists districts inside the chosen governorate;
                                  picking a single district drills the ranking chart
                                  down from districts to individual towns.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page setup & palette
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Lebanon Tourism Explorer",
    page_icon="🏨",
    layout="wide",
)

BLUE = "#2a78d6"      # primary series / "no hotel"
ORANGE = "#eb6834"    # highlight series / "has hotel"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"

DATA_PATH = Path(__file__).parent / "data" / "tourism_lebanon.csv"

# District -> governorate lookup (traditional administrative map of Lebanon).
# Byblos and Keserwan are kept under Mount Lebanon, matching how the dataset's
# DBpedia references group them.
DISTRICT_TO_GOV = {
    "Aley District": "Mount Lebanon",
    "Baabda District": "Mount Lebanon",
    "Byblos District": "Mount Lebanon",
    "Keserwan District": "Mount Lebanon",
    "Matn District": "Mount Lebanon",
    "Batroun District": "North",
    "Bsharri District": "North",
    "Miniyeh–Danniyeh District": "North",
    "Tripoli District": "North",
    "Zgharta District": "North",
    "Sidon District": "South",
    "Tyre District": "South",
    "Bint Jbeil District": "Nabatieh",
    "Hasbaya District": "Nabatieh",
    "Marjeyoun District": "Nabatieh",
    "Western Beqaa District": "Beqaa",
    "Zahlé District": "Beqaa",
    "Hermel District": "Baalbek-Hermel",
}
# Some towns are only tagged with their governorate, not a district.
GOV_LEVEL = {
    "Akkar Governorate": "Akkar",
    "Baalbek-Hermel Governorate": "Baalbek-Hermel",
    "Beqaa Governorate": "Beqaa",
    "Mount Lebanon Governorate": "Mount Lebanon",
    "Nabatieh Governorate": "Nabatieh",
    "North Governorate": "North",
    "South Governorate": "South",
}


def _fix_mojibake(text: str) -> str:
    """The source CSV double-encodes UTF-8 (e.g. 'ZahlÃ©' instead of 'Zahlé')."""
    for enc in ("cp1252", "latin-1"):
        try:
            return text.encode(enc).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return text


@st.cache_data
def load_data() -> pd.DataFrame:
    raw = pd.read_csv(DATA_PATH)
    area = (
        raw["refArea"].str.split("/").str[-1].str.replace("_", " ").map(_fix_mojibake)
        .str.replace(", Lebanon", "", regex=False)
    )
    df = pd.DataFrame(
        {
            "Town": raw["Town"].astype(str).str.strip().map(_fix_mojibake),
            "Area": area,
            "Tourism Index": raw["Tourism Index"],
            "Hotels": raw["Total number of hotels"],
            "Restaurants": raw["Total number of restaurants"],
            "Cafes": raw["Total number of cafes"],
            "Guest houses": raw["Total number of guest houses"],
        }
    )
    df["Governorate"] = df["Area"].map(DISTRICT_TO_GOV).fillna(df["Area"].map(GOV_LEVEL))
    # Akkar is a single-district governorate, so its towns belong to Akkar District.
    df["District"] = df["Area"].where(df["Area"].isin(DISTRICT_TO_GOV))
    df.loc[df["Area"] == "Akkar Governorate", "District"] = "Akkar District"
    df["District"] = df["District"].fillna(
        "Unassigned towns (" + df["Governorate"] + ")"
    )
    df["Hotel status"] = df["Hotels"].gt(0).map({True: "Has hotel(s)", False: "No hotels"})
    return df


df = load_data()


def style_fig(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(
        height=height,
        template="plotly_white",
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=INK_2, size=13),
        title_font=dict(color=INK, size=16),
        margin=dict(l=10, r=20, t=30, b=40),
        plot_bgcolor="#fcfcfb",
        paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor="#c3c2b7", tickfont_color=MUTED)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor="#c3c2b7", tickfont_color=MUTED)
    return fig


# ---------------------------------------------------------------------------
# Header & context
# ---------------------------------------------------------------------------
st.title("Where Is Lebanon's Tourism Infrastructure?")
st.markdown(
    "A drill-down look at hotels, restaurants and cafes across **1,137 Lebanese towns** · "
    "MSBA 325 · Sarah Khater"
)

with st.expander("About the data", expanded=False):
    st.markdown(
        """
**Source:** *Tourism-Lebanon-2023* dataset, published by Impact Open Data (Central Inspection
Board of Lebanon) and linked by AUB's CODEC Linked-Data project.
Each row is one town, with counts of hotels, restaurants, cafes and guest houses, plus a
**Tourism Index (0–10)** that scores how developed the town's tourism sector is.

**Things to keep in mind**
- The dataset covers towns and villages, **not Beirut**, so it's really about mountain,
  coastal and rural tourism outside the capital.
- Some towns are tagged only with their *governorate*, not a district. They show up here
  as *"Unassigned towns (…)"* so they're still counted rather than silently dropped.
- Akkar is a single-district governorate, so its towns are grouped under *Akkar District*.
- Counts are self-reported by municipalities, so read them as rough orders of magnitude.
"""
    )

# ---------------------------------------------------------------------------
# Linked controls (one row above the charts)
# ---------------------------------------------------------------------------
st.subheader("Choose where to look")
c1, c2 = st.columns([1, 2])

gov_options = ["All of Lebanon"] + sorted(df["Governorate"].unique())
with c1:
    governorate = st.selectbox(
        "① Governorate",
        gov_options,
        help="Pick a governorate to zoom in. This also changes which districts you can pick in ②.",
    )

scope = df if governorate == "All of Lebanon" else df[df["Governorate"] == governorate]
district_options = sorted(scope["District"].unique(), key=lambda d: (d.startswith("Unassigned"), d))

with c2:
    # Keying the widget by governorate resets the selection whenever ① changes,
    # so stale districts from another governorate can never linger.
    districts = st.multiselect(
        "② Districts in " + ("Lebanon" if governorate == "All of Lebanon" else f"{governorate} Governorate"),
        district_options,
        default=district_options,
        key=f"districts_{governorate}",
        help="Remove districts to compare a subset. Keep exactly ONE to drill down to its individual towns.",
    )

if not districts:
    st.warning("Select at least one district in ② to see the charts.")
    st.stop()

sel = scope[scope["District"].isin(districts)]
single_district = len(districts) == 1
scope_label = (
    districts[0] if single_district
    else ("Lebanon" if governorate == "All of Lebanon" and len(districts) == len(district_options)
          else f"{len(districts)} selected districts")
)

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
n = len(sel)
pct_zero = (sel["Tourism Index"] == 0).mean() * 100
pct_rest = (sel["Restaurants"] > 0).mean() * 100
nat_zero = (df["Tourism Index"] == 0).mean() * 100
nat_rest = (df["Restaurants"] > 0).mean() * 100

is_national = n == len(df)
k1, k2, k3, k4 = st.columns(4)
k1.metric("Towns in view", f"{n:,}")
k2.metric("Total hotels", f"{int(sel['Hotels'].sum()):,}",
          help=f"Across all {n} towns in view")
k3.metric("Towns scoring 0 on the Tourism Index", f"{pct_zero:.0f}%",
          delta=None if is_national else f"{pct_zero - nat_zero:+.0f} pts vs. national",
          delta_color="inverse")
k4.metric("Towns with ≥1 restaurant", f"{pct_rest:.0f}%",
          delta=None if is_national else f"{pct_rest - nat_rest:+.0f} pts vs. national")

st.divider()

# ---------------------------------------------------------------------------
# Chart 1 — ranking (districts, or towns when drilled down)
# ---------------------------------------------------------------------------
left, right = st.columns(2, gap="large")

with left:
    if single_district:
        st.markdown(f"#### Which towns in {districts[0]} have the hotels?")
        rank = (
            sel[sel["Hotels"] > 0]
            .sort_values(["Hotels", "Tourism Index"], ascending=False)
            .head(15)
            .rename(columns={"Town": "Place"})
        )
        rank["Towns"] = 1
    else:
        st.markdown("#### Which districts actually have the hotels?")
        rank = (
            sel.groupby("District", as_index=False)
            .agg(Hotels=("Hotels", "sum"), Towns=("Town", "count"),
                 Restaurants=("Restaurants", "sum"), Cafes=("Cafes", "sum"),
                 **{"Tourism Index": ("Tourism Index", "mean")})
            .sort_values("Hotels", ascending=False)
            .head(15)
            .rename(columns={"District": "Place"})
        )

    if rank.empty or rank["Hotels"].sum() == 0:
        st.info(f"No town in **{scope_label}** reports a hotel. "
                "Tourism here, if any, relies on day-trips or guest houses.")
    else:
        rank = rank.iloc[::-1]  # largest at top in a horizontal bar
        fig_bar = px.bar(
            rank, x="Hotels", y="Place", orientation="h", text="Hotels",
            custom_data=["Towns", "Restaurants", "Cafes", "Tourism Index"],
        )
        hover_unit = "Town" if single_district else "District"
        fig_bar.update_traces(
            marker_color=BLUE, marker_line_width=0, textposition="outside",
            textfont_color=INK_2, cliponaxis=False,
            hovertemplate=(
                f"<b>%{{y}}</b><br>Hotels: %{{x}}<br>"
                + ("" if single_district else "Towns: %{customdata[0]}<br>")
                + "Restaurants: %{customdata[1]}<br>Cafes: %{customdata[2]}<br>"
                + ("Tourism Index: %{customdata[3]}" if single_district
                   else "Avg Tourism Index: %{customdata[3]:.1f}")
                + "<extra></extra>"
            ),
        )
        fig_bar.update_layout(bargap=0.25, yaxis_title=None, xaxis_title="Total hotels")
        style_fig(fig_bar, height=max(320, 32 * len(rank) + 90))
        st.plotly_chart(fig_bar, use_container_width=True)

        top = rank.iloc[-1]
        share = top["Hotels"] / sel["Hotels"].sum() * 100
        st.caption(
            f"**{top['Place']}** alone holds **{int(top['Hotels'])} of {int(sel['Hotels'].sum())}** "
            f"hotels in {scope_label} ({share:.0f}%). "
            + ("Showing towns with at least one hotel (top 15)." if single_district
               else "Keep a single district in ② to see its individual towns.")
        )

# ---------------------------------------------------------------------------
# Chart 2 — restaurants vs cafes scatter
# ---------------------------------------------------------------------------
with right:
    st.markdown("#### Do restaurants, cafes and hotels grow together?")
    corr = sel["Restaurants"].corr(sel["Cafes"]) if n > 2 else float("nan")
    plot_df = sel.assign(Size=sel["Tourism Index"] + 1)  # +1 so index-0 towns remain visible
    fig_sc = px.scatter(
        plot_df, x="Restaurants", y="Cafes", color="Hotel status", size="Size",
        size_max=18, opacity=0.75,
        color_discrete_map={"No hotels": BLUE, "Has hotel(s)": ORANGE},
        category_orders={"Hotel status": ["No hotels", "Has hotel(s)"]},
        custom_data=["Town", "District", "Hotels", "Tourism Index"],
    )
    fig_sc.update_traces(
        marker_line=dict(width=1, color="white"),
        hovertemplate=(
            "<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
            "Restaurants: %{x}<br>Cafes: %{y}<br>Hotels: %{customdata[2]}<br>"
            "Tourism Index: %{customdata[3]}<extra></extra>"
        ),
    )
    fig_sc.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, title=None),
        xaxis_title="Restaurants in town", yaxis_title="Cafes in town",
    )
    style_fig(fig_sc, height=460)
    st.plotly_chart(fig_sc, use_container_width=True)

    hotel_share_top = (
        sel.nlargest(max(1, n // 20), "Restaurants")["Hotels"].gt(0).mean() * 100
    )
    corr_txt = f"correlation **r = {corr:.2f}**" if pd.notna(corr) else "too few towns for a correlation"
    st.caption(
        f"Bubble size = Tourism Index. In {scope_label}, restaurants and cafes move together "
        f"({corr_txt}), and **{hotel_share_top:.0f}%** of the top-5% restaurant towns also have a hotel "
        f"vs. **{sel['Hotels'].gt(0).mean() * 100:.0f}%** of all towns in view."
    )

# ---------------------------------------------------------------------------
# Chart 3 (supporting) — Tourism Index distribution
# ---------------------------------------------------------------------------
st.markdown(f"#### How is the Tourism Index spread across towns in {scope_label}?")
dist = sel["Tourism Index"].value_counts().reindex(range(11), fill_value=0).rename_axis("Score").reset_index(name="Towns")
dist["Group"] = dist["Score"].eq(0).map({True: "Score 0", False: "Score 1–10"})
fig_h = px.bar(
    dist, x="Score", y="Towns", color="Group", text="Towns",
    color_discrete_map={"Score 0": ORANGE, "Score 1–10": BLUE},
)
fig_h.update_traces(
    textposition="outside", textfont_color=INK_2, cliponaxis=False, marker_line_width=0,
    hovertemplate="Tourism Index %{x}: %{y} towns<extra></extra>",
)
fig_h.update_layout(
    showlegend=False, bargap=0.2, xaxis=dict(dtick=1, title="Tourism Index (0 = no tourism activity, 10 = highly developed)"),
    yaxis_title="Number of towns",
)
style_fig(fig_h, height=330)
st.plotly_chart(fig_h, use_container_width=True)
st.caption(
    f"**{pct_zero:.0f}%** of towns in {scope_label} score a flat zero "
    f"(national figure: {nat_zero:.0f}%). This is a 'haves and have-nots' split, not a bell curve."
)

# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------
st.divider()
st.subheader("What the data says")
i1, i2, i3 = st.columns(3)
with i1:
    st.markdown(
        """
**1 · Hotels are concentrated in a few mountain districts.**
Bsharri (the Cedars and ski country), Matn and Keserwan hold nearly 30% of all hotels in
the dataset. Drill into **North → Bsharri District** and the concentration repeats *inside*
the district: just two towns (Bqerqacha and Bcharreh) hold 35 of its 41 hotels.
"""
    )
with i2:
    st.markdown(
        f"""
**2 · Almost half of Lebanon's towns have no tourism at all.**
{nat_zero:.0f}% of towns score **0** on the Tourism Index, and only {nat_rest:.0f}% have even
one restaurant. The surprise: **Mount Lebanon**, which has the most hotels, has *more*
zero-score towns (48%) than the national average, while **North** has the fewest (34%).
Having hotels in the region doesn't mean the tourism is spread evenly across it.
"""
    )
with i3:
    st.markdown(
        f"""
**3 · Tourism infrastructure comes as a package.**
Restaurants and cafes are strongly correlated (r ≈ {df['Restaurants'].corr(df['Cafes']):.2f}
nationally), and the orange hotel bubbles sit almost entirely in the upper-right. Towns
don't add one amenity at a time; they either become destinations or stay off the map.
"""
    )

# ---------------------------------------------------------------------------
# Design justifications
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Design notes: why these two controls?")

with st.expander("① Governorate selectbox", expanded=False):
    st.markdown(
        """
**User question.** *"How does tourism infrastructure in my region compare with the rest of
Lebanon?"* Choosing a governorate re-scopes every chart and KPI to that region, and the KPI
deltas ("vs. national") keep the country-wide number in view as a reference point.

**Why a selectbox.** A governorate is one choice out of eight, so a single-select dropdown
fits and takes up almost no space. I considered a **radio button row**, but eight long
names ("Baalbek-Hermel", "Mount Lebanon"…) wrapped badly and pushed the charts below the
fold. I also considered a **clickable map**, but the dataset has no geometry, and a map
would push readers toward land area when the story is about counts. The dropdown also
has an obvious "All of Lebanon" default, so the page opens on the full national picture.

**Course concept: overview first, then zoom and filter (Shneiderman's mantra) and
providing context.** The page opens on the national overview, and the governorate is the
first zoom step. Because the KPI cards always show the difference from the national
figure, a zoomed-in view still has context: a reader looking at Baalbek-Hermel sees that it is
10 points worse than the country on zero-score towns, not only a bare number.
"""
    )

with st.expander("② District multiselect (linked to ①)", expanded=False):
    st.markdown(
        """
**User question.** *"Within this region, which districts, and then which specific towns,
hold the tourism supply?"* The multiselect lets the reader compare a hand-picked subset of
districts. Keeping exactly **one** district switches the ranking chart from *districts* to
the *towns inside it*, which is the drill-down step.

**How it's linked.** The options in ② are generated from the choice in ①. Pick *North* and
you only see Batroun, Bsharri, Miniyeh–Danniyeh, Tripoli and Zgharta (plus North towns
that have no district tag). The widget resets
whenever ① changes, so you can't end up with an impossible combination such as
"South Governorate + Matn District". That's the difference between a drill-down and two
independent filters.

**Why a multiselect.** I considered a **second selectbox**, but that allows only one
district, so you couldn't compare, say, Bsharri with Zgharta. I also considered a **list of
checkboxes**, but Mount Lebanon has six options and "All of Lebanon" has twenty-plus,
which would be a long wall of boxes. The multiselect stays compact, starts with everything
selected (so nothing is hidden by default), and removing a tag with "×" is a quick,
reversible action.

**Course concept: reducing clutter and focusing attention.** With all 1,137 towns plotted,
the scatter is a dense blob near zero. Narrowing to a few districts removes the noise so
the eye can land on the handful of towns that matter. Showing the drilled-down town ranking
only when one district is selected keeps the bar chart at a readable ≤15 bars instead of
hundreds.
"""
    )

with st.expander("See the underlying rows"):
    st.dataframe(
        sel[["Town", "District", "Governorate", "Tourism Index", "Hotels", "Restaurants", "Cafes", "Guest houses"]]
        .sort_values("Tourism Index", ascending=False),
        use_container_width=True, hide_index=True,
    )

st.caption("Data: Tourism-Lebanon-2023, Impact Open Data / AUB CODEC linked data. Built with Streamlit + Plotly.")
