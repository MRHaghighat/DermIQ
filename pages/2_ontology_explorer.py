import streamlit as st
import networkx as nx
import plotly.graph_objects as go

from core.ontology.mapper import TerminologyMapper
from core.ontology.graph import build_graph, path_to_root, siblings_of, malignant_leaves

st.set_page_config(page_title="Ontology Explorer — DermIQ", layout="wide")
st.title("Ontology Explorer")
st.caption("SNOMED CT disease hierarchy for Derm7pt diagnoses.")

@st.cache_resource
def get_graph():
    mapper = TerminologyMapper()
    return build_graph(mapper), mapper

G, mapper = get_graph()

# Sidebar controls
with st.sidebar:
    st.subheader("Filter")
    selected = st.selectbox(
        "Highlight diagnosis",
        options=["(none)"] + mapper.all_labels,
    )
    show_malignant_only = st.checkbox("Show malignant only", value=False)

st.divider()

# Stats
col1, col2, col3 = st.columns(3)
col1.metric("Total nodes", G.number_of_nodes())
col2.metric("IS-A edges", G.number_of_edges())
col3.metric("Malignant leaves", len(malignant_leaves(G)))

st.divider()

# Build Plotly graph
def build_plotly_figure(G: nx.DiGraph, highlight: str | None = None) -> go.Figure:
    pos = nx.spring_layout(G, seed=42, k=2.5)

    # Edges
    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(width=0.8, color="#888"),
        hoverinfo="none",
    )

    # Highlight path
    highlight_nodes = set()
    if highlight and highlight != "(none)":
        highlight_nodes = set(path_to_root(G, highlight))
        highlight_nodes.add(highlight)

    # Node colours
    node_x, node_y, node_text, node_color, node_size, hover_text = [], [], [], [], [], []

    for node, data in G.nodes(data=True):
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node if len(node) < 20 else node[:18] + "…")

        is_leaf = data.get("is_leaf", False)
        is_malignant = data.get("malignant")
        in_highlight = node in highlight_nodes

        if in_highlight and node == highlight:
            color = "#E24B4A"   # selected node
            size = 22
        elif in_highlight:
            color = "#EF9F27"   # path to root
            size = 16
        elif is_malignant:
            color = "#F09595"   # malignant leaf
            size = 14
        elif is_leaf:
            color = "#9FE1CB"   # benign leaf
            size = 14
        else:
            color = "#D3D1C7"   # intermediate node
            size = 10

        node_color.append(color)
        node_size.append(size)

        snomed = data.get("snomed_id") or "—"
        icd10 = data.get("icd10") or "—"
        cases = data.get("case_count", 0)
        hover_text.append(
            f"<b>{node}</b><br>"
            f"SNOMED: {snomed}<br>"
            f"ICD-10: {icd10}<br>"
            f"Cases: {cases}<br>"
            f"Malignant: {is_malignant}"
        )

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        hovertext=hover_text,
        hoverinfo="text",
        marker=dict(
            color=node_color,
            size=node_size,
            line=dict(width=1, color="#888"),
        ),
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            showlegend=False,
            hovermode="closest",
            margin=dict(b=0, l=0, r=0, t=0),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=600,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig

fig = build_plotly_figure(G, selected if selected != "(none)" else None)
st.plotly_chart(fig, use_container_width=True)

# Detail panel
if selected != "(none)":
    st.divider()
    st.subheader(f"Details: {selected}")
    term = mapper.get(selected)
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Codes**")
        st.write(f"SNOMED: `{term['snomed']['conceptId']}` — {term['snomed']['display']}")
        st.write(f"ICD-10: `{term['icd10']['code']}` — {term['icd10']['display']}")
        st.write(f"Malignant: `{term['malignant']}`")
        st.write(f"Cases in Derm7pt: `{term['case_count']}`")
    with col_b:
        st.markdown("**Hierarchy path**")
        path = path_to_root(G, selected)
        for i, node in enumerate(path):
            prefix = "→ " * i
            st.write(f"{prefix}`{node}`")

        st.markdown("**Siblings**")
        sibs = siblings_of(G, selected)[:5]
        for s in sibs:
            st.write(f"• {s}")
