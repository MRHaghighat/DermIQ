from __future__ import annotations

import logging
import networkx as nx

from core.ontology.mapper import TerminologyMapper

logger = logging.getLogger(__name__)

# Root node — all skin diseases connect here
_ROOT = "skin disorder"

# --- BUILD BY AI -----
def build_graph(mapper: TerminologyMapper | None = None) -> nx.DiGraph:
    if mapper is None:
        mapper = TerminologyMapper()

    G = nx.DiGraph()

    # Add root
    G.add_node(_ROOT, label=_ROOT, snomed_id=None, icd10=None,
               malignant=None, is_leaf=False, case_count=0)

    for label, entry in mapper.all_entries.items():
        hierarchy: list[str] = entry["hierarchy"]

        # The derm7pt label is the true leaf — prepend it if not already first
        full_path = [label] + [h for h in hierarchy if h != label]

        # Ensure root connectivity
        if not full_path or full_path[-1] != _ROOT:
            full_path = full_path + [_ROOT]

        # Add all nodes in this path
        for i, node in enumerate(full_path):
            if node not in G:
                G.add_node(node,
                           label=node,
                           snomed_id=None,
                           icd10=None,
                           malignant=None,
                           is_leaf=False,
                           case_count=0)

            # IS-A edge: current node → parent
            if i + 1 < len(full_path):
                parent = full_path[i + 1]
                if not G.has_edge(node, parent):
                    G.add_edge(node, parent)

        # Enrich the leaf node (the actual Derm7pt label)
        G.nodes[label]["snomed_id"] = entry["snomed"]["conceptId"]
        G.nodes[label]["icd10"] = entry["icd10"]["code"]
        G.nodes[label]["malignant"] = entry["malignant"]
        G.nodes[label]["is_leaf"] = True
        G.nodes[label]["case_count"] = entry["case_count"]

    logger.info(
        "Built ontology graph: %d nodes, %d edges",
        G.number_of_nodes(), G.number_of_edges()
    )
    return G


def ancestors_of(G: nx.DiGraph, label: str) -> list[str]:
    """Return all ancestor nodes (parents, grandparents...) of a label."""
    if label not in G:
        return []
    return list(nx.ancestors(G, label))


def descendants_of(G: nx.DiGraph, label: str) -> list[str]:
    """Return all descendant nodes (children, grandchildren...) of a label."""
    if label not in G:
        return []
    return list(nx.descendants(G, label))


def path_to_root(G: nx.DiGraph, label: str) -> list[str]:
    """Return the shortest path from a leaf to the root node."""
    if label not in G or _ROOT not in G:
        return [label]
    try:
        return nx.shortest_path(G, label, _ROOT)
    except nx.NetworkXNoPath:
        return [label]


def siblings_of(G: nx.DiGraph, label: str) -> list[str]:
    """Return sibling nodes (same parent, different child)."""
    if label not in G:
        return []
    parents = list(G.successors(label))
    siblings = []
    for parent in parents:
        for child in G.predecessors(parent):
            if child != label:
                siblings.append(child)
    return list(set(siblings))


def malignant_leaves(G: nx.DiGraph) -> list[str]:
    """Return all leaf nodes marked as malignant."""
    return [
        n for n, d in G.nodes(data=True)
        if d.get("is_leaf") and d.get("malignant") is True
    ]
