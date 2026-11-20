# Fluid-like grid pipeline with stencils, scalar powers and diagnostics.

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

NX = 50
NY = 50
NZ = 40

ITERATIONS = 10

DT = 0.001
VISCOSITY = 0.0001
DIFFUSION = 0.015

print("Starting 3D Fluid Dynamics Benchmark...")

# ============================================================
# GLOBAL STORAGE
# ============================================================

density = np.random.uniform(
    0.1, 2.0,
    (NX, NY, NZ)
).astype(np.float64)

pressure = np.random.uniform(
    0.1, 1.0,
    (NX, NY, NZ)
).astype(np.float64)

velocity = np.random.uniform(
    -0.5, 0.5,
    (NX, NY, NZ, 3)
).astype(np.float64)

temperature = np.random.uniform(
    250.0, 350.0,
    (NX, NY, NZ)
).astype(np.float64)

energy_history = np.zeros(
    ITERATIONS,
    dtype=np.float64
)

checksum_history = np.zeros(
    ITERATIONS,
    dtype=np.float64
)

global_checksum = 0.0

# ============================================================
# 1. THREE-DIMENSIONAL LAPLACIAN
# ============================================================

def calculate_laplacian(field):

    nx, ny, nz = field.shape

    output = np.zeros_like(field)

    for x in range(1, nx - 1):

        for y in range(1, ny - 1):

            for z in range(1, nz - 1):

                center = field[x, y, z]

                laplacian = (
                    field[x-1, y, z]
                    + field[x+1, y, z]
                    + field[x, y-1, z]
                    + field[x, y+1, z]
                    + field[x, y, z-1]
                    + field[x, y, z+1]
                    - 6.0 * center
                )

                output[x, y, z] = laplacian

    return output

# ============================================================
# 2. FLUID VELOCITY UPDATE
# ============================================================

def update_velocity(
    velocity,
    pressure,
    density,
    laplacian
):

    nx, ny, nz = density.shape

    updated = velocity.copy()

    for x in range(1, nx - 1):

        for y in range(1, ny - 1):

            for z in range(1, nz - 1):

                rho = density[x, y, z]

                p_left = pressure[x-1, y, z]
                p_right = pressure[x+1, y, z]

                p_down = pressure[x, y-1, z]
                p_up = pressure[x, y+1, z]

                p_back = pressure[x, y, z-1]
                p_front = pressure[x, y, z+1]

                gradient_x = (
                    p_right - p_left
                ) * 0.5

                gradient_y = (
                    p_up - p_down
                ) * 0.5

                gradient_z = (
                    p_front - p_back
                ) * 0.5

                lap = laplacian[x, y, z]

                vx = velocity[x, y, z, 0]
                vy = velocity[x, y, z, 1]
                vz = velocity[x, y, z, 2]

                vx += (
                    -DT * gradient_x / rho
                    + VISCOSITY * lap
                )

                vy += (
                    -DT * gradient_y / rho
                    + VISCOSITY * lap
                )

                vz += (
                    -DT * gradient_z / rho
                    + VISCOSITY * lap
                )

                speed_squared = (
                    vx * vx
                    + vy * vy
                    + vz * vz
                )

                if speed_squared > 4.0:

                    scale = 2.0 / math.sqrt(
                        speed_squared
                    )

                    vx *= scale
                    vy *= scale
                    vz *= scale

                updated[x, y, z, 0] = vx
                updated[x, y, z, 1] = vy
                updated[x, y, z, 2] = vz

    return updated

# ============================================================
# 3. DENSITY TRANSPORT
# ============================================================

def update_density(
    density,
    velocity,
    laplacian
):

    nx, ny, nz = density.shape

    updated = density.copy()

    for x in range(1, nx - 1):

        for y in range(1, ny - 1):

            for z in range(1, nz - 1):

                rho = density[x, y, z]

                vx = velocity[x, y, z, 0]
                vy = velocity[x, y, z, 1]
                vz = velocity[x, y, z, 2]

                gradient_x = (
                    density[x+1, y, z]
                    - density[x-1, y, z]
                ) * 0.5

                gradient_y = (
                    density[x, y+1, z]
                    - density[x, y-1, z]
                ) * 0.5

                gradient_z = (
                    density[x, y, z+1]
                    - density[x, y, z-1]
                ) * 0.5

                advection = (
                    vx * gradient_x
                    + vy * gradient_y
                    + vz * gradient_z
                )

                diffusion = (
                    DIFFUSION
                    * laplacian[x, y, z]
                )

                value = (
                    rho
                    - DT * advection
                    + diffusion * DT
                )

                if value < 0.01:
                    value = 0.01

                elif value > 5.0:
                    value = 5.0

                updated[x, y, z] = value

    return updated

# ============================================================
# 4. TEMPERATURE DIFFUSION
# ============================================================

def update_temperature(
    temperature,
    velocity
):

    nx, ny, nz = temperature.shape

    updated = temperature.copy()

    for x in range(1, nx - 1):

        for y in range(1, ny - 1):

            for z in range(1, nz - 1):

                center = temperature[x, y, z]

                laplacian = (
                    temperature[x-1, y, z]
                    + temperature[x+1, y, z]
                    + temperature[x, y-1, z]
                    + temperature[x, y+1, z]
                    + temperature[x, y, z-1]
                    + temperature[x, y, z+1]
                    - 6.0 * center
                )

                vx = velocity[x, y, z, 0]
                vy = velocity[x, y, z, 1]
                vz = velocity[x, y, z, 2]

                speed = math.sqrt(
                    vx*vx + vy*vy + vz*vz
                )

                heat_transfer = (
                    laplacian * 0.002
                    + speed * 0.0005
                )

                value = center + heat_transfer

                if value < 200.0:
                    value = 200.0

                elif value > 500.0:
                    value = 500.0

                updated[x, y, z] = value

    return updated

# ============================================================
# 5. PRESSURE SOLVER
# ============================================================

def update_pressure(
    pressure,
    density,
    velocity
):

    nx, ny, nz = density.shape

    updated = pressure.copy()

    for x in range(1, nx - 1):

        for y in range(1, ny - 1):

            for z in range(1, nz - 1):

                divergence = (
                    velocity[x+1, y, z, 0]
                    - velocity[x-1, y, z, 0]
                    + velocity[x, y+1, z, 1]
                    - velocity[x, y-1, z, 1]
                    + velocity[x, y, z+1, 2]
                    - velocity[x, y, z-1, 2]
                ) * 0.5

                laplacian = (
                    pressure[x-1, y, z]
                    + pressure[x+1, y, z]
                    + pressure[x, y-1, z]
                    + pressure[x, y+1, z]
                    + pressure[x, y, z-1]
                    + pressure[x, y, z+1]
                    - 6.0 * pressure[x, y, z]
                )

                value = (
                    pressure[x, y, z]
                    - DT * divergence
                    + 0.01 * laplacian
                )

                if value < 0.0:
                    value = 0.0

                updated[x, y, z] = value

    return updated

# ============================================================
# 6. FLUID ENERGY ANALYSIS
# ============================================================

def calculate_energy(
    density,
    velocity,
    temperature
):

    nx, ny, nz = density.shape

    total_energy = 0.0
    kinetic_energy = 0.0
    thermal_energy = 0.0

    for x in range(1, nx - 1):

        for y in range(1, ny - 1):

            for z in range(1, nz - 1):

                rho = density[x, y, z]

                vx = velocity[x, y, z, 0]
                vy = velocity[x, y, z, 1]
                vz = velocity[x, y, z, 2]

                speed_squared = (
                    vx*vx + vy*vy + vz*vz
                )

                kinetic = (
                    0.5 * rho * speed_squared
                )

                thermal = (
                    rho * temperature[x, y, z] * 0.001
                )

                kinetic_energy += kinetic
                thermal_energy += thermal

                total_energy += (
                    kinetic * 0.4
                    + thermal * 0.6
                )

                if speed_squared > 1.0:

                    total_energy += (
                        math.sqrt(speed_squared) * 0.1
                    )

                elif speed_squared > 0.25:

                    total_energy += (
                        speed_squared * 0.2
                    )

    return (
        total_energy,
        kinetic_energy,
        thermal_energy
    )

# ============================================================
# 7. VORTICITY ANALYSIS
# ============================================================

def calculate_vorticity(velocity):

    nx, ny, nz, _ = velocity.shape

    output = np.zeros(
        (nx, ny, nz),
        dtype=np.float64
    )

    for x in range(1, nx - 1):

        for y in range(1, ny - 1):

            for z in range(1, nz - 1):

                dvz_dy = (
                    velocity[x, y+1, z, 2]
                    - velocity[x, y-1, z, 2]
                ) * 0.5

                dvy_dz = (
                    velocity[x, y, z+1, 1]
                    - velocity[x, y, z-1, 1]
                ) * 0.5

                dvx_dz = (
                    velocity[x, y, z+1, 0]
                    - velocity[x, y, z-1, 0]
                ) * 0.5

                dvz_dx = (
                    velocity[x+1, y, z, 2]
                    - velocity[x-1, y, z, 2]
                ) * 0.5

                dvy_dx = (
                    velocity[x+1, y, z, 1]
                    - velocity[x-1, y, z, 1]
                ) * 0.5

                dvx_dy = (
                    velocity[x, y+1, z, 0]
                    - velocity[x, y-1, z, 0]
                ) * 0.5

                wx = dvz_dy - dvy_dz
                wy = dvx_dz - dvz_dx
                wz = dvy_dx - dvx_dy

                output[x, y, z] = math.sqrt(
                    wx*wx + wy*wy + wz*wz
                )

    return output

# ============================================================
# 8. MAIN FLUID SIMULATION
# ============================================================

print("Starting fluid simulation...")

for iteration in range(ITERATIONS):

    laplacian = calculate_laplacian(
        density
    )

    velocity = update_velocity(
        velocity,
        pressure,
        density,
        laplacian
    )

    density = update_density(
        density,
        velocity,
        laplacian
    )

    temperature = update_temperature(
        temperature,
        velocity
    )

    pressure = update_pressure(
        pressure,
        density,
        velocity
    )

    (
        total_energy,
        kinetic_energy,
        thermal_energy
    ) = calculate_energy(
        density,
        velocity,
        temperature
    )

    energy_history[iteration] = total_energy

    if iteration % 5 == 0:

        vorticity = calculate_vorticity(
            velocity
        )

        checksum = (
            total_energy * 0.4
            + kinetic_energy * 0.3
            + thermal_energy * 0.2
            + np.sum(vorticity) * 0.1
        )

        checksum_history[iteration] = checksum

        global_checksum += checksum

        print(
            "Iteration:",
            iteration,
            "Energy:",
            total_energy,
            "Checksum:",
            checksum
        )

    else:

        checksum = (
            total_energy
            + kinetic_energy * 0.5
            + thermal_energy * 0.25
        )

        checksum_history[iteration] = checksum

        global_checksum += checksum

# ============================================================
# 9. FINAL FIELD ANALYSIS
# ============================================================

print("Performing final field analysis...")

density_mean = np.mean(density)
density_std = np.std(density)

pressure_mean = np.mean(pressure)
pressure_std = np.std(pressure)

temperature_mean = np.mean(temperature)
temperature_std = np.std(temperature)

velocity_magnitude = np.sqrt(
    velocity[:, :, :, 0]**2
    + velocity[:, :, :, 1]**2
    + velocity[:, :, :, 2]**2
)

velocity_mean = np.mean(velocity_magnitude)
velocity_max = np.max(velocity_magnitude)

vorticity = calculate_vorticity(
    velocity
)

vorticity_mean = np.mean(vorticity)
vorticity_max = np.max(vorticity)

# ============================================================
# 10. COMPLEX NESTED FIELD ANALYSIS
# ============================================================

print("Starting nested field analysis...")

field_checksum = 0.0

for x in range(1, NX - 1):

    for y in range(1, NY - 1):

        for z in range(1, NZ - 1):

            rho = density[x, y, z]
            p = pressure[x, y, z]
            t = temperature[x, y, z]

            vx = velocity[x, y, z, 0]
            vy = velocity[x, y, z, 1]
            vz = velocity[x, y, z, 2]

            speed_squared = (
                vx*vx + vy*vy + vz*vz
            )

            value = (
                rho * 0.2
                + p * 0.3
                + t * 0.001
                + speed_squared * 0.4
            )

            if rho > 1.0:

                value += math.sqrt(
                    rho * rho + speed_squared
                )

            elif p > 0.5:

                value += math.log1p(
                    p + speed_squared
                )

            else:

                value += (
                    (t / 300.0)**2
                )

            if speed_squared > 0.5:

                value *= 1.05

            elif speed_squared < 0.1:

                value *= 0.95

            field_checksum += value

global_checksum += field_checksum

# ============================================================
# 11. FINAL RESULTS
# ============================================================

elapsed = time.perf_counter() - start

print("\n========== FLUID BENCHMARK RESULTS ==========")

print("Grid dimensions:", NX, NY, NZ)

print("Total grid cells:", NX * NY * NZ)

print("Iterations:", ITERATIONS)

print("\nDensity mean:", density_mean)
print("Density std:", density_std)

print("Pressure mean:", pressure_mean)
print("Pressure std:", pressure_std)

print("Temperature mean:", temperature_mean)
print("Temperature std:", temperature_std)

print("Average velocity:", velocity_mean)
print("Maximum velocity:", velocity_max)

print("Average vorticity:", vorticity_mean)
print("Maximum vorticity:", vorticity_max)

print("Final total energy:", total_energy)
print("Final kinetic energy:", kinetic_energy)
print("Final thermal energy:", thermal_energy)

print("Field checksum:", field_checksum)
print("Global checksum:", global_checksum)

print("Execution time:", elapsed)

print("========== FINISHED ==========")
