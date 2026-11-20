# Image pipeline with clamped convolution, histograms, pyramid reductions and median filtering.
import time
import math
import random
import numpy as np

start = time.perf_counter()

random.seed(42)
np.random.seed(42)

WIDTH = 480
HEIGHT = 360
ITERATIONS = 3
TILE_SIZE = 16

print("Starting Image Processing Benchmark...")

image = np.random.uniform(
    0, 255, (HEIGHT, WIDTH, 3)
).astype(np.float64)

depth = np.random.uniform(
    0.1, 10.0, (HEIGHT, WIDTH)
).astype(np.float64)

noise = np.random.random(
    (HEIGHT, WIDTH)
)

global_checksum = 0.0

# ============================================================
# KERNELS
# ============================================================

GAUSSIAN = np.array([
    [1, 4, 6, 4, 1],
    [4, 16, 24, 16, 4],
    [6, 24, 36, 24, 6],
    [4, 16, 24, 16, 4],
    [1, 4, 6, 4, 1]
], dtype=np.float64) / 256.0

SOBEL_X = np.array([
    [-1, 0, 1],
    [-2, 0, 2],
    [-1, 0, 1]
], dtype=np.float64)

SOBEL_Y = np.array([
    [-1, -2, -1],
    [0, 0, 0],
    [1, 2, 1]
], dtype=np.float64)

SHARPEN = np.array([
    [0, -1, 0],
    [-1, 5, -1],
    [0, -1, 0]
], dtype=np.float64)


# ============================================================
# 1. GRAYSCALE
# ============================================================

def grayscale(img):

    h, w, _ = img.shape
    out = np.zeros((h, w), dtype=np.float64)

    for y in range(h):
        for x in range(w):

            r = img[y, x, 0]
            g = img[y, x, 1]
            b = img[y, x, 2]

            out[y, x] = (
                0.299 * r +
                0.587 * g +
                0.114 * b
            )

    return out


# ============================================================
# 2. GAUSSIAN CONVOLUTION
# ============================================================

def gaussian_blur(img):

    h, w, channels = img.shape
    out = np.zeros_like(img)

    for y in range(h):
        for x in range(w):
            for c in range(channels):

                total = 0.0

                for ky in range(5):
                    for kx in range(5):

                        iy = min(max(y + ky - 2, 0), h - 1)
                        ix = min(max(x + kx - 2, 0), w - 1)

                        total += (
                            img[iy, ix, c] *
                            GAUSSIAN[ky, kx]
                        )

                out[y, x, c] = total

    return out


# ============================================================
# 3. SHARPENING
# ============================================================

def sharpen(img):

    h, w, channels = img.shape
    out = np.zeros_like(img)

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            for c in range(channels):

                total = 0.0

                for ky in range(3):
                    for kx in range(3):

                        total += (
                            img[y + ky - 1, x + kx - 1, c] *
                            SHARPEN[ky, kx]
                        )

                out[y, x, c] = min(255.0, max(0.0, total))

    return out


# ============================================================
# 4. SOBEL
# ============================================================

def sobel(gray):

    h, w = gray.shape

    gx_array = np.zeros_like(gray)
    gy_array = np.zeros_like(gray)
    magnitude = np.zeros_like(gray)

    for y in range(1, h - 1):
        for x in range(1, w - 1):

            gx = 0.0
            gy = 0.0

            for ky in range(3):
                for kx in range(3):

                    value = gray[
                        y + ky - 1,
                        x + kx - 1
                    ]

                    gx += value * SOBEL_X[ky, kx]
                    gy += value * SOBEL_Y[ky, kx]

            gx_array[y, x] = gx
            gy_array[y, x] = gy

            magnitude[y, x] = math.sqrt(
                gx * gx + gy * gy
            )

    return gx_array, gy_array, magnitude


# ============================================================
# 5. MEDIAN FILTER
# ============================================================

def median_filter(gray):

    h, w = gray.shape
    out = np.zeros_like(gray)

    for y in range(1, h - 1):
        for x in range(1, w - 1):

            values = []

            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    values.append(
                        gray[y + dy, x + dx]
                    )

            values.sort()

            out[y, x] = values[4]

    return out


# ============================================================
# 6. ADAPTIVE THRESHOLD
# ============================================================

def adaptive_threshold(gray):

    h, w = gray.shape

    out = np.zeros((h, w), dtype=np.uint8)

    for y in range(2, h - 2):
        for x in range(2, w - 2):

            total = 0.0

            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    total += gray[y + dy, x + dx]

            mean = total / 25.0

            if gray[y, x] > mean - 5.0:
                out[y, x] = 255

    return out


# ============================================================
# 7. HISTOGRAM
# ============================================================

def histogram(gray):

    h, w = gray.shape

    hist = np.zeros(256, dtype=np.int64)

    for y in range(h):
        for x in range(w):

            value = int(gray[y, x])
            value = min(255, max(0, value))

            hist[value] += 1

    return hist


# ============================================================
# 8. HISTOGRAM EQUALIZATION
# ============================================================

def equalize(gray, hist):

    h, w = gray.shape

    cdf = np.zeros(256, dtype=np.float64)

    running = 0

    for i in range(256):

        running += hist[i]
        cdf[i] = running / (h * w)

    out = np.zeros_like(gray)

    for y in range(h):
        for x in range(w):

            value = int(gray[y, x])
            value = min(255, max(0, value))

            out[y, x] = cdf[value] * 255.0

    return out


# ============================================================
# 9. DEPTH PROCESSING
# ============================================================

def depth_processing(img, depth_map):

    h, w, channels = img.shape

    out = np.zeros_like(img)

    for y in range(h):
        for x in range(w):

            z = depth_map[y, x]

            attenuation = 1.0 / (
                1.0 + 0.05 * z * z
            )

            for c in range(channels):

                value = (
                    img[y, x, c] * attenuation +
                    z * 2.0
                )

                out[y, x, c] = min(
                    255.0, max(0.0, value)
                )

    return out


# ============================================================
# 10. IMAGE PYRAMID
# ============================================================

def image_pyramid(gray):

    h, w = gray.shape

    half = np.zeros(
        (h // 2, w // 2),
        dtype=np.float64
    )

    quarter = np.zeros(
        (h // 4, w // 4),
        dtype=np.float64
    )

    for y in range(h // 2):
        for x in range(w // 2):

            total = 0.0

            for dy in range(2):
                for dx in range(2):

                    total += gray[
                        y * 2 + dy,
                        x * 2 + dx
                    ]

            half[y, x] = total * 0.25

    for y in range(h // 4):
        for x in range(w // 4):

            total = 0.0

            for dy in range(2):
                for dx in range(2):

                    total += half[
                        y * 2 + dy,
                        x * 2 + dx
                    ]

            quarter[y, x] = total * 0.25

    return half, quarter


# ============================================================
# 11. TILE ANALYSIS
# ============================================================

def tile_analysis(gray):

    h, w = gray.shape

    results = []

    for ty in range(0, h, TILE_SIZE):
        for tx in range(0, w, TILE_SIZE):

            total = 0.0
            total_sq = 0.0

            minimum = 1e12
            maximum = -1e12

            count = 0

            for y in range(ty, min(ty + TILE_SIZE, h)):
                for x in range(tx, min(tx + TILE_SIZE, w)):

                    value = gray[y, x]

                    total += value
                    total_sq += value * value

                    minimum = min(minimum, value)
                    maximum = max(maximum, value)

                    count += 1

            mean = total / count

            variance = max(
                0.0,
                total_sq / count - mean * mean
            )

            results.append((
                mean,
                math.sqrt(variance),
                minimum,
                maximum
            ))

    return results


# ============================================================
# 12. EDGE CLASSIFICATION
# ============================================================

def classify_edges(magnitude):

    h, w = magnitude.shape

    out = np.zeros((h, w), dtype=np.uint8)

    for y in range(h):
        for x in range(w):

            value = magnitude[y, x]

            if value > 150:
                out[y, x] = 3
            elif value > 75:
                out[y, x] = 2
            elif value > 25:
                out[y, x] = 1

    return out


# ============================================================
# 13. COLOR ANALYSIS
# ============================================================

def color_analysis(img, edges, depth_map):

    h, w, _ = img.shape

    checksum = 0.0

    for y in range(h):
        for x in range(w):

            r = img[y, x, 0]
            g = img[y, x, 1]
            b = img[y, x, 2]

            edge = edges[y, x]
            z = depth_map[y, x]

            brightness = (
                0.299 * r +
                0.587 * g +
                0.114 * b
            )

            saturation = (
                max(r, g, b) -
                min(r, g, b)
            )

            difference = (
                abs(r - g) +
                abs(g - b) +
                abs(b - r)
            )

            value = (
                brightness * 0.2 +
                saturation * 0.3 +
                difference * 0.1 +
                edge * 10.0 +
                z * 2.0
            )

            if brightness > 180:
                value += math.sqrt(brightness)
            elif brightness > 90:
                value += math.log1p(brightness)
            else:
                value += brightness * 0.05

            if saturation > 100:
                value *= 1.1
            elif saturation < 20:
                value *= 0.9

            checksum += value

    return checksum


# ============================================================
# 14. MAIN PROCESSING PIPELINE
# ============================================================

for iteration in range(ITERATIONS):

    print("Processing iteration:", iteration)

    blurred = gaussian_blur(image)

    sharpened = sharpen(blurred)

    gray = grayscale(sharpened)

    denoised = median_filter(gray)

    gx, gy, magnitude = sobel(denoised)

    thresholded = adaptive_threshold(denoised)

    hist = histogram(denoised)

    equalized = equalize(denoised, hist)

    depth_processed = depth_processing(
        sharpened, depth
    )

    half, quarter = image_pyramid(equalized)

    tiles = tile_analysis(equalized)

    edge_classes = classify_edges(magnitude)

    checksum = color_analysis(
        depth_processed,
        edge_classes,
        depth
    )

    checksum += np.sum(hist) * 0.01
    checksum += np.sum(half) * 0.02
    checksum += np.sum(quarter) * 0.03
    checksum += np.sum(thresholded) * 0.001

    for mean, std, minimum, maximum in tiles:

        checksum += (
            mean * 0.1 +
            std * 0.2 +
            minimum * 0.05 +
            maximum * 0.15
        )

    global_checksum += checksum

    image = np.clip(
        depth_processed * 0.4 +
        sharpened * 0.3 +
        blurred * 0.3,
        0.0,
        255.0
    )

    depth = np.clip(
        depth +
        magnitude * 0.00001 +
        noise * 0.0001,
        0.1,
        10.0
    )

    print("Checksum:", checksum)
    print("Tiles:", len(tiles))


# ============================================================
# 15. FINAL STATISTICS
# ============================================================

print("Calculating final statistics...")

final_gray = grayscale(image)

final_hist = histogram(final_gray)

final_tiles = tile_analysis(final_gray)

image_mean = np.mean(image)
image_std = np.std(image)

depth_mean = np.mean(depth)
depth_std = np.std(depth)

histogram_checksum = 0.0

for i in range(256):

    histogram_checksum += (
        final_hist[i] * (i + 1) * 0.001
    )

tile_checksum = 0.0

for mean, std, minimum, maximum in final_tiles:

    tile_checksum += (
        mean * 0.2 +
        std * 0.3 +
        minimum * 0.1 +
        maximum * 0.4
    )

global_checksum += histogram_checksum
global_checksum += tile_checksum


# ============================================================
# 16. RESULTS
# ============================================================

elapsed = time.perf_counter() - start

print("\n========== IMAGE BENCHMARK RESULTS ==========")

print("Image dimensions:", WIDTH, HEIGHT)
print("Iterations:", ITERATIONS)

print("Image mean:", image_mean)
print("Image std:", image_std)

print("Depth mean:", depth_mean)
print("Depth std:", depth_std)

print("Histogram total:", np.sum(final_hist))

print("Tile count:", len(final_tiles))

print("Histogram checksum:", histogram_checksum)
print("Tile checksum:", tile_checksum)

print("Global checksum:", global_checksum)

print("Execution time:", elapsed)

print("========== FINISHED ==========")