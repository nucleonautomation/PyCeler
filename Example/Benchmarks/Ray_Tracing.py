# Ray/sphere intersections, lighting and pixel-result construction.

import time
import math

start = time.perf_counter()

WIDTH = 900
HEIGHT = 600
SPHERES = [
    (-1.5, 0.0, 4.0, 1.0, (1.0, 0.1, 0.1)),
    (1.3, 0.2, 5.0, 1.2, (0.1, 0.8, 0.2)),
    (0.0, -1.3, 3.0, 0.5, (0.2, 0.3, 1.0)),
    (2.5, -0.5, 8.0, 1.5, (1.0, 0.8, 0.1)),
    (-3.0, 1.0, 9.0, 1.8, (0.8, 0.2, 1.0))
]

LIGHT = (-4.0, 6.0, -3.0)

pixels = []

for y in range(HEIGHT):
    for x in range(WIDTH):

        u = (x - WIDTH / 2) / WIDTH
        v = (y - HEIGHT / 2) / WIDTH

        dx = u
        dy = -v
        dz = 1.0

        length = math.sqrt(dx*dx + dy*dy + dz*dz)

        dx /= length
        dy /= length
        dz /= length

        closest = 1e30
        color = (0.02, 0.02, 0.04)

        for sx, sy, sz, radius, rgb in SPHERES:

            ox = -sx
            oy = -sy
            oz = -sz

            b = 2.0 * (ox*dx + oy*dy + oz*dz)
            c = ox*ox + oy*oy + oz*oz - radius*radius

            discriminant = b*b - 4.0*c

            if discriminant < 0:
                continue

            t = (-b - math.sqrt(discriminant)) / 2.0

            if t > 0 and t < closest:

                closest = t

                px = dx*t
                py = dy*t
                pz = dz*t

                nx = (px-sx)/radius
                ny = (py-sy)/radius
                nz = (pz-sz)/radius

                lx = LIGHT[0]-px
                ly = LIGHT[1]-py
                lz = LIGHT[2]-pz

                ll = math.sqrt(lx*lx+ly*ly+lz*lz)

                lx /= ll
                ly /= ll
                lz /= ll

                diffuse = max(
                    0.0,
                    nx*lx + ny*ly + nz*lz
                )

                intensity = 0.12 + 0.88*diffuse

                color = tuple(
                    min(1.0, component*intensity)
                    for component in rgb
                )

        pixels.append(color)

checksum = sum(
    int(r*255) + int(g*255) + int(b*255)
    for r, g, b in pixels
)

print("Checksum:", checksum)
print("Time:", time.perf_counter()-start)
