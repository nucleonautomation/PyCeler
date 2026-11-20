# Sparse graph pipeline with indirect indices, reductions and label propagation.

import time
import math
import random
import numpy as np

# ============================================================
# CONFIGURATION
# ============================================================

start = time.perf_counter()

random.seed(42)
np.random.seed(42)

NODES = 10000
AVERAGE_DEGREE = 12

ITERATIONS = 10
PROPAGATION_STEPS = 8

print("Starting Large-Scale Graph Benchmark...")

# ============================================================
# 1. GRAPH GENERATION
# ============================================================

print("Generating graph...")

edge_counts = np.random.randint(
    4,
    AVERAGE_DEGREE * 2 + 1,
    size=NODES
)

offsets = np.zeros(
    NODES + 1,
    dtype=np.int64
)

for i in range(NODES):

    offsets[i + 1] = (
        offsets[i] + edge_counts[i]
    )

TOTAL_EDGES = int(offsets[-1])

neighbors = np.random.randint(
    0,
    NODES,
    size=TOTAL_EDGES,
    dtype=np.int32
)

weights = np.random.uniform(
    0.01,
    1.0,
    size=TOTAL_EDGES
).astype(np.float64)

node_values = np.random.uniform(
    0.0,
    1.0,
    size=NODES
).astype(np.float64)

node_features = np.random.uniform(
    -1.0,
    1.0,
    size=(NODES, 8)
).astype(np.float64)

node_labels = np.random.randint(
    0,
    8,
    size=NODES,
    dtype=np.int32
)

print("Nodes:", NODES)
print("Edges:", TOTAL_EDGES)

# ============================================================
# 2. GRAPH PROPAGATION
# ============================================================

def graph_propagation(
    offsets,
    neighbors,
    weights,
    values,
    iterations
):

    N = len(offsets) - 1

    for iteration in range(iterations):

        updated = np.zeros(
            N,
            dtype=np.float64
        )

        for node in range(N):

            start_edge = offsets[node]
            end_edge = offsets[node + 1]

            total = 0.0
            weight_sum = 0.0

            for edge in range(
                start_edge,
                end_edge
            ):

                neighbor = neighbors[edge]
                weight = weights[edge]

                value = values[neighbor]

                total += value * weight
                weight_sum += weight

            if weight_sum > 1e-12:

                updated[node] = (
                    total / weight_sum
                )

            else:

                updated[node] = values[node]

        values = updated

    return values

# ============================================================
# 3. GRAPH CENTRALITY ESTIMATION
# ============================================================

def calculate_centrality(
    offsets,
    neighbors,
    weights
):

    N = len(offsets) - 1

    centrality = np.zeros(
        N,
        dtype=np.float64
    )

    for node in range(N):

        degree = (
            offsets[node + 1]
            - offsets[node]
        )

        weighted_degree = 0.0

        for edge in range(
            offsets[node],
            offsets[node + 1]
        ):

            weighted_degree += weights[edge]

        centrality[node] = (
            degree * 0.5
            + weighted_degree * 0.5
        )

    return centrality

# ============================================================
# 4. GRAPH FEATURE AGGREGATION
# ============================================================

def aggregate_features(
    offsets,
    neighbors,
    weights,
    features
):

    N = len(offsets) - 1
    FEATURE_COUNT = features.shape[1]

    output = np.zeros_like(features)

    for node in range(N):

        start_edge = offsets[node]
        end_edge = offsets[node + 1]

        for feature in range(FEATURE_COUNT):

            total = 0.0
            normalization = 0.0

            for edge in range(
                start_edge,
                end_edge
            ):

                neighbor = neighbors[edge]
                weight = weights[edge]

                total += (
                    features[neighbor, feature]
                    * weight
                )

                normalization += weight

            if normalization > 1e-12:

                output[node, feature] = (
                    total / normalization
                )

            else:

                output[node, feature] = (
                    features[node, feature]
                )

    return output

# ============================================================
# 5. GRAPH LABEL PROPAGATION
# ============================================================

def label_propagation(
    offsets,
    neighbors,
    weights,
    labels,
    classes
):

    N = len(offsets) - 1

    new_labels = labels.copy()

    for node in range(N):

        votes = np.zeros(
            classes,
            dtype=np.float64
        )

        for edge in range(
            offsets[node],
            offsets[node + 1]
        ):

            neighbor = neighbors[edge]

            label = labels[neighbor]

            weight = weights[edge]

            votes[label] += weight

        best_label = labels[node]
        best_vote = -1.0

        for label in range(classes):

            if votes[label] > best_vote:

                best_vote = votes[label]
                best_label = label

        new_labels[node] = best_label

    return new_labels

# ============================================================
# 6. GRAPH RANDOM WALK
# ============================================================

def random_walk(
    offsets,
    neighbors,
    weights,
    values,
    iterations
):

    N = len(offsets) - 1

    for iteration in range(iterations):

        updated = np.zeros(
            N,
            dtype=np.float64
        )

        for node in range(N):

            start_edge = offsets[node]
            end_edge = offsets[node + 1]

            total = 0.0
            total_weight = 0.0

            for edge in range(
                start_edge,
                end_edge
            ):

                neighbor = neighbors[edge]

                weight = weights[edge]

                total += (
                    values[neighbor] * weight
                )

                total_weight += weight

            if total_weight > 0.0:

                updated[node] = (
                    0.85 * total / total_weight
                    + 0.15 * values[node]
                )

            else:

                updated[node] = values[node]

        values = updated

    return values

# ============================================================
# 7. GRAPH TRIANGLE-LIKE NEIGHBOR ANALYSIS
# ============================================================

def neighborhood_analysis(
    offsets,
    neighbors,
    values
):

    N = len(offsets) - 1

    result = np.zeros(
        N,
        dtype=np.float64
    )

    for node in range(N):

        start_a = offsets[node]
        end_a = offsets[node + 1]

        score = 0.0
        count = 0

        for edge_a in range(
            start_a,
            end_a
        ):

            neighbor_a = neighbors[edge_a]

            start_b = offsets[neighbor_a]
            end_b = offsets[neighbor_a + 1]

            for edge_b in range(
                start_b,
                end_b
            ):

                neighbor_b = neighbors[edge_b]

                if neighbor_b == node:
                    continue

                difference = (
                    values[node]
                    - values[neighbor_b]
                )

                score += (
                    difference * difference
                )

                count += 1

        if count > 0:

            result[node] = (
                score / count
            )

    return result

# ============================================================
# 8. GRAPH CONNECTIVITY ANALYSIS
# ============================================================

def connectivity_analysis(
    offsets,
    neighbors,
    weights
):

    N = len(offsets) - 1

    checksum = 0.0

    for node in range(N):

        degree = (
            offsets[node + 1]
            - offsets[node]
        )

        weighted_sum = 0.0
        reciprocal_sum = 0.0

        for edge in range(
            offsets[node],
            offsets[node + 1]
        ):

            neighbor = neighbors[edge]

            weight = weights[edge]

            neighbor_degree = (
                offsets[neighbor + 1]
                - offsets[neighbor]
            )

            weighted_sum += (
                weight * neighbor_degree
            )

            reciprocal_sum += (
                1.0 / (neighbor_degree + 1.0)
            )

        checksum += (
            degree * 0.2
            + weighted_sum * 0.3
            + reciprocal_sum * 0.5
        )

    return checksum

# ============================================================
# 9. GRAPH FEATURE TRANSFORMATION
# ============================================================

def transform_features(
    features,
    labels,
    centrality
):

    N = len(labels)
    FEATURE_COUNT = features.shape[1]

    transformed = np.zeros_like(features)

    for node in range(N):

        label = labels[node]
        center = centrality[node]

        for feature in range(FEATURE_COUNT):

            value = features[node, feature]

            value = (
                value * 0.7
                + center * 0.02
                + label * 0.01
            )

            if value > 0.5:

                value = math.tanh(value)

            elif value < -0.5:

                value = math.sin(value)

            else:

                value = (
                    value * value * 0.5
                )

            transformed[node, feature] = value

    return transformed

# ============================================================
# 10. GLOBAL GRAPH CHECKSUM
# ============================================================

def calculate_graph_checksum(
    values,
    features,
    centrality,
    labels
):

    N = len(values)
    FEATURE_COUNT = features.shape[1]

    checksum = 0.0

    for node in range(N):

        value = values[node]

        checksum += (
            value * 0.3
            + centrality[node] * 0.2
            + labels[node] * 0.1
        )

        for feature in range(FEATURE_COUNT):

            current = features[node, feature]

            if current > 0.0:

                checksum += (
                    math.sqrt(current + 1.0) * 0.1
                )

            else:

                checksum += (
                    current * current * 0.05
                )

    return checksum

# ============================================================
# 11. MAIN GRAPH PROCESSING PIPELINE
# ============================================================

print("Starting graph processing...")

global_checksum = 0.0

propagation_history = []

for iteration in range(ITERATIONS):

    print("Processing iteration:", iteration)

    # Graph propagation

    node_values = graph_propagation(
        offsets,
        neighbors,
        weights,
        node_values,
        PROPAGATION_STEPS
    )

    # Centrality

    centrality = calculate_centrality(
        offsets,
        neighbors,
        weights
    )

    # Feature aggregation

    node_features = aggregate_features(
        offsets,
        neighbors,
        weights,
        node_features
    )

    # Label propagation

    node_labels = label_propagation(
        offsets,
        neighbors,
        weights,
        node_labels,
        8
    )

    # Random walk

    node_values = random_walk(
        offsets,
        neighbors,
        weights,
        node_values,
        3
    )

    # Neighborhood analysis

    neighborhood = neighborhood_analysis(
        offsets,
        neighbors,
        node_values
    )

    # Connectivity

    connectivity = connectivity_analysis(
        offsets,
        neighbors,
        weights
    )

    # Feature transformation

    node_features = transform_features(
        node_features,
        node_labels,
        centrality
    )

    # Checksum

    checksum = calculate_graph_checksum(
        node_values,
        node_features,
        centrality,
        node_labels
    )

    checksum += connectivity * 0.1

    checksum += np.sum(neighborhood) * 0.05

    propagation_history.append(checksum)

    global_checksum += checksum

# ============================================================
# 12. FINAL GRAPH STATISTICS
# ============================================================

print("Calculating final graph statistics...")

degree = offsets[1:] - offsets[:-1]

degree_mean = np.mean(degree)
degree_std = np.std(degree)
degree_max = np.max(degree)

centrality_mean = np.mean(centrality)
centrality_max = np.max(centrality)

feature_mean = np.mean(node_features)
feature_std = np.std(node_features)

value_mean = np.mean(node_values)
value_std = np.std(node_values)

label_distribution = np.bincount(
    node_labels,
    minlength=8
)

neighborhood_mean = np.mean(
    neighborhood
)

neighborhood_max = np.max(
    neighborhood
)

# ============================================================
# 13. ADDITIONAL NESTED EDGE ANALYSIS
# ============================================================

print("Starting additional edge analysis...")

edge_checksum = 0.0

for node in range(NODES):

    for edge in range(
        offsets[node],
        offsets[node + 1]
    ):

        neighbor = neighbors[edge]

        weight = weights[edge]

        node_value = node_values[node]
        neighbor_value = node_values[neighbor]

        difference = abs(
            node_value - neighbor_value
        )

        if difference > 0.5:

            edge_checksum += (
                difference * weight
            )

        elif difference > 0.1:

            edge_checksum += (
                math.sqrt(difference) * weight
            )

        else:

            edge_checksum += (
                difference * difference
            )

global_checksum += edge_checksum

# ============================================================
# 14. FINAL RESULTS
# ============================================================

elapsed = time.perf_counter() - start

print("\n========== GRAPH BENCHMARK RESULTS ==========")

print("Total nodes:", NODES)
print("Total edges:", TOTAL_EDGES)

print("Average degree:", degree_mean)
print("Degree standard deviation:", degree_std)
print("Maximum degree:", degree_max)

print("Average centrality:", centrality_mean)
print("Maximum centrality:", centrality_max)

print("Feature mean:", feature_mean)
print("Feature std:", feature_std)

print("Node value mean:", value_mean)
print("Node value std:", value_std)

print("Neighborhood mean:", neighborhood_mean)
print("Neighborhood maximum:", neighborhood_max)

print("Label distribution:", label_distribution)

print("Connectivity checksum:", connectivity)

print("Edge checksum:", edge_checksum)

print("Global checksum:", global_checksum)

print("Execution time:", elapsed)

print("========== FINISHED ==========")
