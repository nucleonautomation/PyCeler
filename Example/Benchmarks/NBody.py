# N-body forces, integration, energies, momentum and spatial analysis.

import time
import math
import numpy as np
import random

# ============================================================
# CONFIGURATION
# ============================================================

start = time.perf_counter()

random.seed(42)
np.random.seed(42)

PARTICLES = 300
STEPS = 35
DT = 0.001

G = 6.67430e-3
SOFTENING = 1e-5

print("Starting N-Body Simulation Benchmark...")

# ============================================================
# PARTICLE INITIALIZATION
# ============================================================

positions = np.random.uniform(
    -10.0, 10.0,
    (PARTICLES, 3)
).astype(np.float64)

velocities = np.random.uniform(
    -0.5, 0.5,
    (PARTICLES, 3)
).astype(np.float64)

masses = np.random.uniform(
    0.5, 5.0,
    PARTICLES
).astype(np.float64)

accelerations = np.zeros(
    (PARTICLES, 3),
    dtype=np.float64
)

# ============================================================
# AUXILIARY STORAGE
# ============================================================

energy_history = np.zeros(
    STEPS,
    dtype=np.float64
)

momentum_history = np.zeros(
    (STEPS, 3),
    dtype=np.float64
)

force_history = np.zeros(
    (STEPS, PARTICLES),
    dtype=np.float64
)

global_checksum = 0.0

# ============================================================
# 1. GRAVITATIONAL FORCE CALCULATION
# ============================================================

def calculate_forces(
    positions,
    masses,
    accelerations,
    force_history,
    step
):

    N = len(positions)

    accelerations.fill(0.0)

    for i in range(N):

        px = positions[i, 0]
        py = positions[i, 1]
        pz = positions[i, 2]

        mi = masses[i]

        ax = 0.0
        ay = 0.0
        az = 0.0

        accumulated_force = 0.0

        for j in range(N):

            if i == j:
                continue

            dx = positions[j, 0] - px
            dy = positions[j, 1] - py
            dz = positions[j, 2] - pz

            distance_squared = (
                dx * dx
                + dy * dy
                + dz * dz
                + SOFTENING
            )

            inverse_distance = (
                1.0 / math.sqrt(distance_squared)
            )

            inverse_distance_cubed = (
                inverse_distance
                * inverse_distance
                * inverse_distance
            )

            force = (
                G
                * masses[j]
                * inverse_distance_cubed
            )

            fx = force * dx
            fy = force * dy
            fz = force * dz

            ax += fx
            ay += fy
            az += fz

            accumulated_force += math.sqrt(
                fx * fx + fy * fy + fz * fz
            )

        accelerations[i, 0] = ax
        accelerations[i, 1] = ay
        accelerations[i, 2] = az

        force_history[step, i] = accumulated_force

# ============================================================
# 2. PARTICLE INTEGRATION
# ============================================================

def integrate_particles(
    positions,
    velocities,
    accelerations,
    dt
):

    N = len(positions)

    for i in range(N):

        for axis in range(3):

            velocities[i, axis] += (
                accelerations[i, axis] * dt
            )

            positions[i, axis] += (
                velocities[i, axis] * dt
            )

# ============================================================
# 3. KINETIC ENERGY
# ============================================================

def calculate_kinetic_energy(
    velocities,
    masses
):

    N = len(masses)

    total_energy = 0.0

    for i in range(N):

        vx = velocities[i, 0]
        vy = velocities[i, 1]
        vz = velocities[i, 2]

        speed_squared = (
            vx * vx
            + vy * vy
            + vz * vz
        )

        total_energy += (
            0.5 * masses[i] * speed_squared
        )

    return total_energy

# ============================================================
# 4. POTENTIAL ENERGY
# ============================================================

def calculate_potential_energy(
    positions,
    masses
):

    N = len(masses)

    total_energy = 0.0

    for i in range(N):

        for j in range(i + 1, N):

            dx = positions[j, 0] - positions[i, 0]
            dy = positions[j, 1] - positions[i, 1]
            dz = positions[j, 2] - positions[i, 2]

            distance = math.sqrt(
                dx * dx
                + dy * dy
                + dz * dz
                + SOFTENING
            )

            total_energy -= (
                G * masses[i] * masses[j] / distance
            )

    return total_energy

# ============================================================
# 5. MOMENTUM CALCULATION
# ============================================================

def calculate_momentum(
    velocities,
    masses
):

    momentum_x = 0.0
    momentum_y = 0.0
    momentum_z = 0.0

    N = len(masses)

    for i in range(N):

        momentum_x += masses[i] * velocities[i, 0]
        momentum_y += masses[i] * velocities[i, 1]
        momentum_z += masses[i] * velocities[i, 2]

    return momentum_x, momentum_y, momentum_z

# ============================================================
# 6. PARTICLE SPATIAL ANALYSIS
# ============================================================

def spatial_analysis(
    positions,
    velocities,
    masses
):

    N = len(masses)

    center_x = 0.0
    center_y = 0.0
    center_z = 0.0

    total_mass = 0.0

    for i in range(N):

        mass = masses[i]

        center_x += positions[i, 0] * mass
        center_y += positions[i, 1] * mass
        center_z += positions[i, 2] * mass

        total_mass += mass

    center_x /= total_mass
    center_y /= total_mass
    center_z /= total_mass

    radial_checksum = 0.0

    velocity_checksum = 0.0

    for i in range(N):

        dx = positions[i, 0] - center_x
        dy = positions[i, 1] - center_y
        dz = positions[i, 2] - center_z

        radius_squared = (
            dx * dx + dy * dy + dz * dz
        )

        speed_squared = (
            velocities[i, 0] ** 2
            + velocities[i, 1] ** 2
            + velocities[i, 2] ** 2
        )

        radius = math.sqrt(radius_squared)
        speed = math.sqrt(speed_squared)

        radial_checksum += (
            radius * 0.4
            + radius_squared * 0.1
            + math.log1p(radius)
        )

        velocity_checksum += (
            speed * 0.3
            + speed_squared * 0.2
        )

        if radius > 8.0:

            radial_checksum += (
                radius_squared * 0.05
            )

        elif radius > 4.0:

            radial_checksum += (
                radius * 0.15
            )

        else:

            radial_checksum += (
                radius * 0.25
            )

    return radial_checksum, velocity_checksum

# ============================================================
# 7. MAIN SIMULATION
# ============================================================

print("Initializing simulation...")

for step in range(STEPS):

    calculate_forces(
        positions,
        masses,
        accelerations,
        force_history,
        step
    )

    integrate_particles(
        positions,
        velocities,
        accelerations,
        DT
    )

    kinetic = calculate_kinetic_energy(
        velocities,
        masses
    )

    potential = calculate_potential_energy(
        positions,
        masses
    )

    energy_history[step] = kinetic + potential

    momentum = calculate_momentum(
        velocities,
        masses
    )

    momentum_history[step] = momentum

    radial, velocity = spatial_analysis(
        positions,
        velocities,
        masses
    )

    step_checksum = (
        kinetic * 0.2
        + potential * 0.3
        + radial * 0.25
        + velocity * 0.25
    )

    global_checksum += step_checksum

    if step % 5 == 0:

        print(
            "Step:",
            step,
            "Energy:",
            energy_history[step],
            "Checksum:",
            step_checksum
        )

# ============================================================
# 8. FINAL PARTICLE ANALYSIS
# ============================================================

print("Performing final particle analysis...")

minimum_position = np.min(
    positions,
    axis=0
)

maximum_position = np.max(
    positions,
    axis=0
)

average_velocity = np.mean(
    np.linalg.norm(velocities, axis=1)
)

average_force = np.mean(
    force_history
)

energy_variance = np.var(
    energy_history
)

# ============================================================
# 9. ADDITIONAL NESTED LOOP WORKLOAD
# ============================================================

print("Starting pairwise interaction analysis...")

pair_checksum = 0.0

for i in range(PARTICLES):

    for j in range(i + 1, PARTICLES):

        dx = positions[i, 0] - positions[j, 0]
        dy = positions[i, 1] - positions[j, 1]
        dz = positions[i, 2] - positions[j, 2]

        distance_squared = (
            dx * dx + dy * dy + dz * dz
        )

        if distance_squared < 1.0:

            pair_checksum += (
                math.sqrt(distance_squared) * 0.5
            )

        elif distance_squared < 25.0:

            pair_checksum += (
                distance_squared * 0.01
            )

        else:

            pair_checksum += (
                math.log1p(distance_squared) * 0.1
            )

global_checksum += pair_checksum

# ============================================================
# 10. FINAL RESULTS
# ============================================================

elapsed = time.perf_counter() - start

print("\n========== N-BODY RESULTS ==========")

print("Particles:", PARTICLES)
print("Simulation steps:", STEPS)

print("Minimum position:", minimum_position)
print("Maximum position:", maximum_position)

print("Average velocity:", average_velocity)
print("Average force:", average_force)

print("Final kinetic energy:", kinetic)
print("Final potential energy:", potential)

print("Energy variance:", energy_variance)

print("Final momentum:", momentum)

print("Pair checksum:", pair_checksum)

print("Global checksum:", global_checksum)

print("Execution time:", elapsed)

print("========== FINISHED ==========")
