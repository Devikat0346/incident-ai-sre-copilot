import networkx as nx
import pandas as pd

from backend.app.graph.dependency_graph import build_service_graph


def get_blast_radius(service, graph=None):
    graph = graph or build_service_graph()
    if service not in graph:
        return []

    impacted_services = nx.ancestors(graph, service)
    return sorted(
        impacted_services,
        key=lambda impacted: (nx.shortest_path_length(graph, impacted, service), impacted),
    )


def get_failure_propagation_paths(root_service, affected_services=None, graph=None):
    graph = graph or build_service_graph()
    if root_service not in graph:
        return []

    propagation_graph = graph.reverse(copy=False)
    targets = affected_services or get_blast_radius(root_service, graph)
    paths = []

    for target in sorted(set(targets)):
        if target == root_service or target not in propagation_graph:
            continue
        if nx.has_path(propagation_graph, root_service, target):
            paths.append(nx.shortest_path(propagation_graph, root_service, target))

    return paths


def rank_service_risk(graph=None):
    graph = graph or build_service_graph()
    if not graph:
        return pd.DataFrame()

    betweenness = nx.betweenness_centrality(graph)
    max_blast_radius = max(len(get_blast_radius(node, graph)) for node in graph) or 1
    max_dependents = max(dict(graph.in_degree()).values()) or 1
    rows = []

    for service in graph:
        blast_radius = len(get_blast_radius(service, graph))
        dependent_count = graph.in_degree(service)
        dependency_count = graph.out_degree(service)
        blast_score = blast_radius / max_blast_radius
        dependent_score = dependent_count / max_dependents
        risk_score = (0.55 * blast_score) + (0.35 * betweenness[service]) + (0.10 * dependent_score)

        rows.append(
            {
                "service": service,
                "risk_score": round(risk_score, 4),
                "betweenness_centrality": round(betweenness[service], 4),
                "blast_radius_count": blast_radius,
                "dependent_count": dependent_count,
                "dependency_count": dependency_count,
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(["risk_score", "service"], ascending=[False, True])
        .reset_index(drop=True)
    )


def infer_probable_root_cause(cluster_events, graph=None):
    graph = graph or build_service_graph()
    if cluster_events.empty or "service" not in cluster_events:
        return None

    events = cluster_events.copy()
    events["timestamp"] = pd.to_datetime(events.get("timestamp"), errors="coerce")
    affected_services = [service for service in events["service"].dropna().unique() if service in graph]
    if not affected_services:
        return None

    earliest_by_service = events.groupby("service")["timestamp"].min()
    valid_times = earliest_by_service.dropna()
    first_time = valid_times.min() if not valid_times.empty else None
    last_time = valid_times.max() if not valid_times.empty else None
    time_span = max((last_time - first_time).total_seconds(), 1) if first_time is not None else 1
    propagation_graph = graph.reverse(copy=False)
    betweenness = nx.betweenness_centrality(graph)
    candidates = []

    for service in affected_services:
        reachable = {
            target
            for target in affected_services
            if target != service and nx.has_path(propagation_graph, service, target)
        }
        coverage = len(reachable) / max(len(affected_services) - 1, 1)

        service_time = earliest_by_service.get(service)
        if first_time is not None and pd.notna(service_time):
            time_score = 1 - ((service_time - first_time).total_seconds() / time_span)
        else:
            time_score = 0

        centrality = betweenness.get(service, 0)
        candidate_score = (0.60 * coverage) + (0.25 * time_score) + (0.15 * centrality)
        candidates.append(
            {
                "service": service,
                "score": round(candidate_score, 4),
                "affected_coverage": round(coverage, 4),
                "earliest_timestamp": str(service_time),
                "reachable_affected_services": sorted(reachable),
            }
        )

    return max(candidates, key=lambda candidate: (candidate["score"], candidate["affected_coverage"]))


def analyze_incident_cluster(cluster_events, graph=None):
    graph = graph or build_service_graph()
    root_cause = infer_probable_root_cause(cluster_events, graph)
    affected_services = sorted(set(cluster_events.get("service", pd.Series(dtype=str)).dropna()))

    if root_cause is None:
        return {
            "probable_root_service": None,
            "affected_services": affected_services,
            "blast_radius": [],
            "propagation_paths": [],
        }

    root_service = root_cause["service"]
    return {
        "probable_root_service": root_service,
        "root_cause_score": root_cause["score"],
        "affected_coverage": root_cause["affected_coverage"],
        "affected_services": affected_services,
        "blast_radius": get_blast_radius(root_service, graph),
        "propagation_paths": get_failure_propagation_paths(root_service, affected_services, graph),
    }
