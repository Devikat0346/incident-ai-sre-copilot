import networkx as nx


def build_service_graph():
    graph = nx.DiGraph()

    edges = [
        ("api-gateway", "auth-service"),
        ("api-gateway", "payment-service"),
        ("api-gateway", "checkout-service"),
        ("checkout-service", "payment-service"),
        ("checkout-service", "inventory-service"),
        ("payment-service", "auth-service"),
        ("auth-service", "database"),
        ("notification-service", "api-gateway"),
        ("notification-service", "queue-worker"),
        ("queue-worker", "database"),
    ]

    graph.add_edges_from(edges)
    return graph


def get_dependency_edges():
    graph = build_service_graph()
    return list(graph.edges())
