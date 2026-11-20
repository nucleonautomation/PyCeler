# Large mixed image, geometry, simulation and metrics benchmark.

import time
import math
import random

import numpy as np
import cv2
import open3d as o3d
import pandas as pd

from scipy.ndimage import gaussian_filter, sobel
from scipy.spatial import cKDTree


# ============================================================
# CONFIGURATION
# ============================================================

start = time.perf_counter()

random.seed(42)
np.random.seed(42)

WIDTH = 640
HEIGHT = 480

FRAMES = 12
ITERATIONS = 8

TILE_SIZE = 32
POINT_SAMPLE = 4

print("Starting Mega Benchmark...")


# ============================================================
# GLOBAL STORAGE
# ============================================================

all_metrics = []
all_clouds = []

global_checksum = 0.0

camera_matrix = np.array([
    [520.0, 0.0, WIDTH / 2],
    [0.0, 520.0, HEIGHT / 2],
    [0.0, 0.0, 1.0]
], dtype=np.float64)

camera_inverse = np.linalg.inv(camera_matrix)


# ============================================================
# 1. SYNTHETIC SENSOR GENERATION
# ============================================================

def generate_sensor_frame(frame_id):

    image = np.zeros(
        (HEIGHT, WIDTH, 3),
        dtype=np.uint8
    )

    depth = np.zeros(
        (HEIGHT, WIDTH),
        dtype=np.float32
    )

    for y in range(HEIGHT):

        for x in range(WIDTH):

            fx = x / WIDTH
            fy = y / HEIGHT

            wave1 = math.sin(
                fx * 20.0 + frame_id * 0.2
            )

            wave2 = math.cos(
                fy * 15.0 - frame_id * 0.1
            )

            wave3 = math.sin(
                (fx + fy) * 12.0
            )

            value = (
                120.0
                + 35.0 * wave1
                + 25.0 * wave2
                + 15.0 * wave3
            )

            noise = random.random() * 12.0

            image[y, x, 0] = int(
                max(0, min(255, value + noise))
            )

            image[y, x, 1] = int(
                max(0, min(255, value * 0.8))
            )

            image[y, x, 2] = int(
                max(0, min(255, value * 1.2))
            )

            depth[y, x] = (
                2.0
                + 0.5 * wave1
                + 0.3 * wave2
                + 0.2 * wave3
            )

    return image, depth


# ============================================================
# 2. COMPUTER VISION PROCESSING
# ============================================================

def process_image(image, depth, iteration):

    blurred = cv2.GaussianBlur(
        image,
        (7, 7),
        1.5
    )

    gray = cv2.cvtColor(
        blurred,
        cv2.COLOR_BGR2GRAY
    )

    edges = cv2.Canny(
        gray,
        50,
        150
    )

    sobel_x = cv2.Sobel(
        gray,
        cv2.CV_32F,
        1,
        0,
        ksize=3
    )

    sobel_y = cv2.Sobel(
        gray,
        cv2.CV_32F,
        0,
        1,
        ksize=3
    )

    magnitude = cv2.magnitude(
        sobel_x,
        sobel_y
    )

    normalized = (
        magnitude /
        (np.max(magnitude) + 1e-8)
    )

    normalized_depth = (
        depth / (np.max(depth) + 1e-8)
    )

    combined = (
        normalized * 0.6
        + normalized_depth * 0.4
    )

    smooth = gaussian_filter(
        combined,
        sigma=1.5
    )

    gradient = sobel(
        smooth,
        axis=0
    )

    tile_results = []

    for ty in range(0, HEIGHT, TILE_SIZE):

        for tx in range(0, WIDTH, TILE_SIZE):

            tile = smooth[
                ty:ty + TILE_SIZE,
                tx:tx + TILE_SIZE
            ]

            if tile.size == 0:
                continue

            tile_mean = np.mean(tile)
            tile_std = np.std(tile)
            tile_max = np.max(tile)

            tile_results.append((
                float(tile_mean),
                float(tile_std),
                float(tile_max)
            ))

    transformed = cv2.convertScaleAbs(
        combined,
        alpha=255.0
    )

    transformed = cv2.applyColorMap(
        transformed,
        cv2.COLORMAP_TURBO
    )

    image_matrix = np.array([
        [
            np.mean(gray),
            np.std(gray),
            np.max(gray)
        ],
        [
            np.mean(depth),
            np.std(depth),
            np.max(depth)
        ],
        [
            np.mean(gradient),
            np.std(gradient),
            np.max(gradient)
        ]
    ], dtype=np.float64)

    matrix_result = np.linalg.matrix_power(
        image_matrix + np.eye(3),
        3
    )

    return (
        edges,
        smooth,
        transformed,
        tile_results,
        matrix_result
    )


# ============================================================
# 3. POINT CLOUD GENERATION
# ============================================================

def generate_point_cloud(depth, image, frame_id):

    points = []
    colors = []

    for y in range(0, HEIGHT, POINT_SAMPLE):

        for x in range(0, WIDTH, POINT_SAMPLE):

            z = float(depth[y, x])

            if z <= 0.1:
                continue

            pixel = np.array(
                [x, y, 1.0],
                dtype=np.float64
            )

            ray = camera_inverse @ pixel

            px = ray[0] * z
            py = ray[1] * z
            pz = z

            angle = frame_id * 0.01

            rx = (
                px * math.cos(angle)
                - py * math.sin(angle)
            )

            ry = (
                px * math.sin(angle)
                + py * math.cos(angle)
            )

            points.append([
                rx,
                ry,
                pz
            ])

            colors.append([
                float(image[y, x, 2]) / 255.0,
                float(image[y, x, 1]) / 255.0,
                float(image[y, x, 0]) / 255.0
            ])

    points = np.asarray(
        points,
        dtype=np.float64
    )

    colors = np.asarray(
        colors,
        dtype=np.float64
    )

    return points, colors


# ============================================================
# 4. OPEN3D GEOMETRY PROCESSING
# ============================================================

def process_geometry(points, colors):

    cloud = o3d.geometry.PointCloud()

    cloud.points = o3d.utility.Vector3dVector(
        points
    )

    cloud.colors = o3d.utility.Vector3dVector(
        colors
    )

    downsampled = cloud.voxel_down_sample(
        voxel_size=0.08
    )

    if len(downsampled.points) > 20:

        downsampled.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=0.25,
                max_nn=20
            )
        )

    xyz = np.asarray(
        downsampled.points
    )

    rgb = np.asarray(
        downsampled.colors
    )

    normals = np.asarray(
        downsampled.normals
    )

    if len(xyz) == 0:
        return downsampled, 0.0

    tree = cKDTree(xyz)

    distances, indices = tree.query(
        xyz,
        k=min(5, len(xyz)),
        workers=1
    )

    distance_mean = float(
        np.mean(distances)
    )

    centroid = np.mean(
        xyz,
        axis=0
    )

    centered = xyz - centroid

    covariance = (
        centered.T @ centered
    ) / max(1, len(xyz))

    eigenvalues, eigenvectors = np.linalg.eigh(
        covariance
    )

    geometry_checksum = 0.0

    for i in range(len(xyz)):

        px, py, pz = xyz[i]

        nx, ny, nz = normals[i]

        r, g, b = rgb[i]

        distance = math.sqrt(
            px*px + py*py + pz*pz
        )

        normal_magnitude = math.sqrt(
            nx*nx + ny*ny + nz*nz
        )

        geometry_checksum += (
            distance * 0.2
            + normal_magnitude * 0.3
            + r * 0.1
            + g * 0.2
            + b * 0.2
        )

    geometry_checksum += float(
        np.sum(eigenvalues)
    )

    geometry_checksum += distance_mean

    return downsampled, geometry_checksum


# ============================================================
# 5. MATRIX AND NUMERICAL SIMULATION
# ============================================================

def numerical_simulation(seed, iterations):

    rng = np.random.default_rng(seed)

    N = 160

    A = rng.random((N, N))
    B = rng.random((N, N))

    velocity = np.zeros((N, N))
    temperature = rng.random((N, N))

    matrix_checksum = 0.0

    for iteration in range(iterations):

        C = A @ B

        velocity = (
            0.95 * velocity
            + 0.05 * np.sin(C)
        )

        temperature = (
            temperature
            + 0.01 * velocity
        )

        for y in range(1, N-1):

            for x in range(1, N-1):

                center = temperature[y, x]

                laplacian = (
                    temperature[y-1, x]
                    + temperature[y+1, x]
                    + temperature[y, x-1]
                    + temperature[y, x+1]
                    - 4.0 * center
                )

                velocity[y, x] += (
                    laplacian * 0.001
                )

                if velocity[y, x] > 1.0:
                    velocity[y, x] *= 0.5

                elif velocity[y, x] < -1.0:
                    velocity[y, x] *= 0.5

        matrix_checksum += float(
            np.sum(temperature)
        )

        matrix_checksum += float(
            np.linalg.norm(velocity)
        )

        A = np.tanh(
            C * 0.01 + A * 0.5
        )

    return matrix_checksum


# ============================================================
# 6. PANDAS DATA PROCESSING
# ============================================================

def process_metrics(metrics):

    df = pd.DataFrame(
        metrics,
        columns=[
            "frame",
            "points",
            "edge_count",
            "geometry",
            "image_mean",
            "image_std"
        ]
    )

    df["complexity"] = (
        df["points"] * 0.2
        + df["edge_count"] * 0.1
        + df["geometry"] * 0.01
    )

    df["normalized"] = (
        df["complexity"]
        / (df["complexity"].max() + 1e-8)
    )

    grouped = df.groupby(
        df["frame"] % 3
    ).agg({
        "points": ["mean", "max", "sum"],
        "geometry": ["mean", "std"],
        "complexity": ["mean", "sum"],
        "image_mean": ["mean"]
    })

    result = 0.0

    for index, row in df.iterrows():

        result += (
            row["complexity"] * 0.3
            + row["normalized"] * 0.7
        )

        if row["points"] > 10000:
            result += row["geometry"] * 0.001

    return df, grouped, result


# ============================================================
# 7. MAIN MULTI-STAGE PIPELINE
# ============================================================

for frame_id in range(FRAMES):

    print("Processing frame:", frame_id)

    image, depth = generate_sensor_frame(
        frame_id
    )

    frame_checksum = 0.0

    # IMAGE PROCESSING ITERATIONS

    for iteration in range(ITERATIONS):

        (
            edges,
            smooth,
            colored,
            tiles,
            matrix
        ) = process_image(
            image,
            depth,
            iteration
        )

        frame_checksum += float(
            np.sum(smooth)
        )

        frame_checksum += float(
            np.sum(matrix)
        )

        frame_checksum += len(tiles)

        image = cv2.addWeighted(
            image,
            0.85,
            cv2.cvtColor(
                colored,
                cv2.COLOR_BGR2RGB
            ),
            0.15,
            0
        )

        depth = np.clip(
            depth + smooth.astype(np.float32) * 0.001,
            0.1,
            10.0
        )

    # POINT CLOUD CONSTRUCTION

    points, colors = generate_point_cloud(
        depth,
        image,
        frame_id
    )

    # OPEN3D PROCESSING

    cloud, geometry_checksum = process_geometry(
        points,
        colors
    )

    all_clouds.append(cloud)

    # GEOMETRIC ARRAY PROCESSING

    xyz = np.asarray(
        cloud.points
    )

    if len(xyz) > 0:

        for iteration in range(5):

            center = np.mean(
                xyz,
                axis=0
            )

            xyz_centered = xyz - center

            covariance = (
                xyz_centered.T @ xyz_centered
            )

            eigenvalues = np.linalg.eigvalsh(
                covariance
            )

            for i in range(len(xyz_centered)):

                x, y, z = xyz_centered[i]

                value = (
                    x*x + y*y + z*z
                )

                if value > 1.0:
                    frame_checksum += math.sqrt(value)

                else:
                    frame_checksum += value * 0.5

            frame_checksum += float(
                np.sum(eigenvalues)
            )

    # METRIC EXTRACTION

    edge_count = int(
        np.count_nonzero(edges)
    )

    image_mean = float(
        np.mean(image)
    )

    image_std = float(
        np.std(image)
    )

    metric = (
        frame_id,
        len(points),
        edge_count,
        geometry_checksum,
        image_mean,
        image_std
    )

    all_metrics.append(metric)

    global_checksum += (
        frame_checksum
        + geometry_checksum
    )


# ============================================================
# 8. NUMERICAL SIMULATION
# ============================================================

print("Starting numerical simulation...")

simulation_checksum = numerical_simulation(
    seed=12345,
    iterations=ITERATIONS
)

global_checksum += simulation_checksum


# ============================================================
# 9. PANDAS ANALYSIS
# ============================================================

print("Starting Pandas analysis...")

df, grouped, dataframe_checksum = process_metrics(
    all_metrics
)

global_checksum += dataframe_checksum


# ============================================================
# 10. CROSS-FRAME GEOMETRY ANALYSIS
# ============================================================

print("Starting cross-frame geometry analysis...")

for i in range(len(all_clouds)):

    for j in range(i + 1, len(all_clouds)):

        cloud_a = np.asarray(
            all_clouds[i].points
        )

        cloud_b = np.asarray(
            all_clouds[j].points
        )

        if len(cloud_a) == 0 or len(cloud_b) == 0:
            continue

        tree = cKDTree(cloud_b)

        distances, indices = tree.query(
            cloud_a,
            k=1,
            workers=1
        )

        pair_checksum = 0.0

        for k in range(len(distances)):

            d = distances[k]

            if d < 0.1:
                pair_checksum += d * 2.0

            elif d < 1.0:
                pair_checksum += math.sqrt(d)

            else:
                pair_checksum += d * 0.1

        global_checksum += pair_checksum


# ============================================================
# 11. FINAL RESULTS
# ============================================================

elapsed = time.perf_counter() - start

print("\n========== BENCHMARK RESULTS ==========")

print("Frames:", FRAMES)
print("Iterations:", ITERATIONS)

print("Total point clouds:", len(all_clouds))

print(
    "Total points:",
    sum(len(cloud.points) for cloud in all_clouds)
)

print("DataFrame rows:", len(df))

print("\nGrouped statistics:")
print(grouped)

print("\nSimulation checksum:", simulation_checksum)

print("\nGlobal checksum:", global_checksum)

print("\nExecution time:", elapsed)

print("========== FINISHED ==========")
