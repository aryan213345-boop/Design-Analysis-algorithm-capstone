"""Streamlit dashboard for Mini-Courier Planner DAA capstone."""
from pathlib import Path
import json
import math
import sys

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent
# If dashboard.py is placed in the project root, this is ROOT. If placed elsewhere,
# set PROJECT_DIR in the sidebar to the folder containing planner.py.

st.set_page_config(page_title="Mini-Courier Planner", page_icon="📦", layout="wide")

st.markdown("""\n<style>ody { background: #0b1220; }
[data-testid="stMetric"] { background: rgba(255,255,255,.04); border: 1px solid rgba(148,163,184,.16); padding: 14px; border-radius: 14px; }
.block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

st.title("📦 Mini-Courier Planner")
st.caption("DAA Capstone · Merge Sort · 0/1 Knapsack DP · Dijkstra · Nearest-Neighbour TSP")

with st.sidebar:
    st.header("⚙️ Controls")
    project_dir_text = st.text_input("Project folder", value=str(ROOT))
    project_dir = Path(project_dir_text).expanduser()
    dataset_choice = st.radio("Dataset", ["Small dataset", "Large dataset", "Generate custom data"])
    custom_parcels = 50
    custom_customers = 15
    custom_capacity = 50
    if dataset_choice == "Generate custom data":
        custom_parcels = st.slider("Number of parcels", 10, 500, 50, 10)
        custom_customers = st.slider("Number of customers", 5, 100, 15, 5)
        custom_capacity = st.slider("Vehicle capacity (kg)", 10, 200, 50, 5)
    show_dp = st.checkbox("Show DP table (small dataset only)", value=False)
    run_button = st.button("🚚 Run planner", type="primary", use_container_width=True)

# Import project modules from selected project folder
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

try:
    from planner import plan
    from data_gen import make_dataset
except Exception as import_error:
    st.error(f"Could not import project files from: {project_dir}\n\n{import_error}")
    st.info("Make sure dashboard.py is in the project folder alongside planner.py, data_gen.py, sorting.py, knapsack.py, and graph_routes.py.")
    st.stop()


def load_or_generate(choice):
    small_path = project_dir / "data" / "small_dataset.json"
    large_path = project_dir / "data" / "large_dataset.json"
    if choice == "Small dataset":
        if small_path.exists():
            return json.loads(small_path.read_text(encoding="utf-8")), "Small dataset (file)"
        return make_dataset(10, 7, 20, seed=7), "Small dataset (generated in memory)"
    if choice == "Large dataset":
        if large_path.exists():
            return json.loads(large_path.read_text(encoding="utf-8")), "Large dataset (file)"
        return make_dataset(200, 60, 100, seed=11), "Large dataset (generated in memory)"

    return make_dataset(custom_parcels, custom_customers, custom_capacity, seed=42), "Custom dataset (generated in memory)"



# Automatically calculate on initial page load; button can rerun with current settings.
if "planner_run" not in st.session_state or run_button:
    dataset, dataset_label = load_or_generate(dataset_choice)
    result = plan(dataset, with_optimal_check=True)
    st.session_state["planner_run"] = {"dataset": dataset, "result": result, "label": dataset_label}
else:
    # Keep latest calculation; re-evaluate if dataset controls changed.
    dataset, dataset_label = load_or_generate(dataset_choice)
    result = plan(dataset, with_optimal_check=True)
    st.session_state["planner_run"] = {"dataset": dataset, "result": result, "label": dataset_label}

run = st.session_state["planner_run"]
data, r, label = run["dataset"], run["result"], run["label"]
parcels = data["parcels"]
chosen = r["chosen"]
chosen_ids = {p["id"] for p in chosen}
remaining = [p for p in parcels if p["id"] not in chosen_ids]
late_ids = {p["id"] for p in r["late"]}

st.markdown(f"**Active data:** {label} · {len(data['nodes'])} nodes · {len(data['edges'])} roads")

# KPIs
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total parcels", f"{len(parcels):,}")
k2.metric("Selected parcels", f"{len(chosen):,}", f"{len(remaining)} left for later")
k3.metric("Vehicle load", f"{r['load']} kg", f"Capacity {data['capacity_kg']} kg")
k4.metric("Route distance", f"{r['length']:.1f} km")
k5.metric("Late parcels", f"{len(r['late'])}", "Deadline check")

# Tabs
overview, routes, parcels_tab, algorithms = st.tabs(["📊 Overview", "🗺️ Route graph", "📦 Parcel details", "🧠 Algorithm performance"])

with overview:
    left, right = st.columns([1.05, 1])
    with left:
        st.subheader("Parcel status")
        status_df = pd.DataFrame({"Status": ["Selected for trip", "Not selected", "Late (selected)"],
                                "Count": [len(chosen), len(remaining), len(r["late"])]})
        fig = go.Figure(go.Pie(labels=status_df["Status"], values=status_df["Count"], hole=.58))
        fig.update_layout(height=330, margin=dict(l=10, r=10, t=30, b=10), legend_title="Status")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Parcel priorities")
        prio_counts = pd.Series([p["priority"] for p in parcels]).value_counts().sort_index()
        prio_df = pd.DataFrame({"Priority": [f"Priority {x}" for x in prio_counts.index], "Parcels": prio_counts.values})
        fig = go.Figure(go.Bar(x=prio_df["Priority"], y=prio_df["Parcels"], text=prio_df["Parcels"], textposition="outside"))
        fig.update_layout(height=330, margin=dict(l=10, r=10, t=30, b=10), yaxis_title="Parcel count")
        st.plotly_chart(fig, use_container_width=True)
    st.subheader("Route summary")
    route_text = " → ".join(r["tour"])
    st.success(f"**Visit order:** {route_text}")
    st.write("**Expanded road route:**", " → ".join(r["full_route"]))
    c1, c2 = st.columns(2)
    c1.metric("Selected parcel value", r["best_value"])
    if r["optimal_length"] is not None:
        c2.metric("Brute-force optimal (small stops)", f"{r['optimal_length']:.1f} km", f"NN ratio {r['length']/r['optimal_length']:.2f}×")
    else:
        c2.metric("Route method", "Nearest Neighbour", "Approximation (not exact TSP)")

with routes:
    st.subheader("Road network and planned trip")
    # Circular layout for visualization only; edges are actual road connections.
    nodes = data["nodes"]
    pos = {node: (math.cos(2*math.pi*i/max(len(nodes), 1)), math.sin(2*math.pi*i/max(len(nodes), 1))) for i, node in enumerate(nodes)}
    edge_x, edge_y = [], []
    for u, v, w in data["edges"]:
        edge_x.extend([pos[u][0], pos[v][0], None])
        edge_y.extend([pos[u][1], pos[v][1], None])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=1, color="#64748b"), hoverinfo="none", name="Roads"))
    tour_nodes = set(r["tour"])
    full_route_nodes = set(r["full_route"])
    fig.add_trace(go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode="markers+text",
        text=nodes, textposition="top center", marker=dict(size=[20 if n == data['depot'] else 13 for n in nodes], color=["#f59e0b" if n == data['depot'] else ("#22c55e" if n in tour_nodes else "#60a5fa") for n in nodes], line=dict(width=1, color="white")),
        hovertext=[f"{n}<br>In planned tour: {'Yes' if n in tour_nodes else 'No'}" for n in nodes], hoverinfo="text", name="Nodes"))
    # overlay the planned tour as straight lines between visit-order stops, for visual emphasis
    route_x, route_y = [], []
    for a, b in zip(r["tour"], r["tour"][1:]):
        route_x.extend([pos[a][0], pos[b][0], None]); route_y.extend([pos[a][1], pos[b][1], None])
    fig.add_trace(go.Scatter(x=route_x, y=route_y, mode="lines", line=dict(width=4, color="#f97316"), hoverinfo="none", name="Planned tour"))
    fig.update_layout(height=550, template="plotly_dark", showlegend=True, margin=dict(l=5,r=5,t=20,b=5),
                    xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("The circular positions are illustrative (not geographic coordinates). The highlighted tour shows visit order; actual road paths are listed below.")
    st.markdown("**Tour:** " + " → ".join(r["tour"]))
    st.markdown("**Actual expanded path:** " + " → ".join(r["full_route"]))
    st.dataframe(pd.DataFrame([{ "From": a, "To": b, "Distance (km)": r["matrix"][a][b]} for a,b in zip(r["tour"],r["tour"][1:])]), use_container_width=True, hide_index=True)

with parcels_tab:
    st.subheader("All parcels")
    parcel_df = pd.DataFrame(parcels)
    parcel_df["Status"] = parcel_df["id"].apply(lambda pid: "Late" if pid in late_ids else ("Selected" if pid in chosen_ids else "Not selected"))
    parcel_df["Status"] = parcel_df["Status"].astype("category")
    filter_status = st.multiselect("Filter by status", parcel_df["Status"].cat.categories.tolist(), default=parcel_df["Status"].cat.categories.tolist())
    filter_prio = st.multiselect("Filter by priority", sorted(parcel_df["priority"].unique().tolist()), default=sorted(parcel_df["priority"].unique().tolist()))
    filtered = parcel_df[parcel_df["Status"].isin(filter_status) & parcel_df["priority"].isin(filter_prio)]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Download parcel table as CSV", filtered.to_csv(index=False).encode("utf-8"), "parcels_filtered.csv", "text/csv")
    st.subheader("Selected for current trip")
    st.dataframe(pd.DataFrame(chosen), use_container_width=True, hide_index=True)
    st.subheader("Left for later trips")
    st.dataframe(pd.DataFrame(remaining), use_container_width=True, hide_index=True)

with algorithms:
    st.subheader("Algorithm execution time")
    timings = r["timings"]
    time_df = pd.DataFrame({"Algorithm step": list(timings.keys()), "Time (ms)": [v*1000 for v in timings.values()]})
    fig = go.Figure(go.Bar(x=time_df["Algorithm step"], y=time_df["Time (ms)"], text=[f"{x:.4f} ms" for x in time_df["Time (ms)"]], textposition="outside"))
    fig.update_layout(height=380, template="plotly_dark", yaxis_title="Milliseconds", margin=dict(l=10,r=10,t=30,b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(time_df, use_container_width=True, hide_index=True)
    st.markdown("#### Algorithm overview")
    st.markdown("- **Merge Sort:** prioritizes parcels by deadline, priority, and weight.\n- **0/1 Knapsack DP:** selects the highest-value parcel subset within capacity.\n- **Dijkstra:** computes shortest road distances between depot and selected stops.\n- **Nearest-Neighbour TSP:** approximates the stop order; it is fast but not guaranteed optimal.")
    st.caption("Execution times are for one run and may vary between runs and machines.")

st.divider()
st.caption("Mini-Courier Planner · DAA Capstone Dashboard")