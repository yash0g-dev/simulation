import pygame
import pymunk
import math
import random

# =====================================================
# SETUP
# =====================================================

pygame.init()

WIDTH, HEIGHT = 900, 900
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Rotating Circular Maze")

clock = pygame.time.Clock()

CENTER = (WIDTH // 2, HEIGHT // 2)

# =====================================================
# COLORS
# =====================================================

BG = (5, 5, 12)

RING = (120, 180, 255)
RING_GLOW = (40, 100, 255)

BALL = (255, 220, 100)

GRID = (18, 18, 35)

# =====================================================
# PYMUNK
# =====================================================

space = pymunk.Space()
space.gravity = (0, 350)

# =====================================================
# BALL
# =====================================================

BALL_RADIUS = 18

mass = 1

moment = pymunk.moment_for_circle(
    mass,
    0,
    BALL_RADIUS
)

ball_body = pymunk.Body(mass, moment)

ball_body.position = CENTER

ball_body.velocity = (
    random.uniform(-200, 200),
    random.uniform(-50, 50)
)

ball_shape = pymunk.Circle(
    ball_body,
    BALL_RADIUS
)

ball_shape.elasticity = 0.98
ball_shape.friction = 0.2

space.add(ball_body, ball_shape)

# =====================================================
# MAZE CONFIG
# =====================================================

RING_COUNT = 4

RING_GAP = 85

THICKNESS = 12

rings = []

# =====================================================
# CREATE RINGS
# =====================================================

def create_ring(radius, gap_angle, rotation_speed):

    body = pymunk.Body(
        body_type=pymunk.Body.KINEMATIC
    )

    body.position = CENTER

    body.angular_velocity = rotation_speed

    opening = random.uniform(0, math.pi * 2)

    segments = []

    SEGMENTS = 20

    step = (2 * math.pi) / SEGMENTS

    for i in range(SEGMENTS):

        a1 = i * step
        a2 = (i + 1) * step

        mid = (a1 + a2) / 2

        diff = (
            (mid - opening + math.pi * 3)
            % (math.pi * 2)
            - math.pi
        )

        # Skip opening
        if abs(diff) < gap_angle / 2:
            continue

        p1 = (
            radius * math.cos(a1),
            radius * math.sin(a1)
        )

        p2 = (
            radius * math.cos(a2),
            radius * math.sin(a2)
        )

        seg = pymunk.Segment(
            body,
            p1,
            p2,
            THICKNESS
        )

        seg.elasticity = 1
        seg.friction = 0.2

        segments.append(seg)

    space.add(body, *segments)

    rings.append({
        "body": body,
        "segments": segments,
        "radius": radius
    })

# =====================================================
# GENERATE MAZE
# =====================================================

for i in range(RING_COUNT):

    radius = 120 + i * RING_GAP

    gap = 1.2

    if i == RING_COUNT - 1:
        gap = 1.6

    speed = 0.8

    if i % 2 == 0:
        speed *= -1

    create_ring(
        radius,
        gap,
        speed
    )

# =====================================================
# TRAIL
# =====================================================

trail = []

# =====================================================
# MAIN LOOP
# =====================================================

running = True

while running:

    dt = clock.tick(60) / 1000

    # =================================================
    # EVENTS
    # =================================================

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

    # =================================================
    # INPUT
    # =================================================

    keys = pygame.key.get_pressed()

    if keys[pygame.K_LEFT]:
        ball_body.apply_impulse_at_local_point((-50, 0))

    if keys[pygame.K_RIGHT]:
        ball_body.apply_impulse_at_local_point((50, 0))

    if keys[pygame.K_UP]:
        ball_body.apply_impulse_at_local_point((0, -80))

    # =================================================
    # BETTER COLLISION ACCURACY
    # =================================================

    for _ in range(3):
        space.step(dt / 3)

    # =================================================
    # TRAIL UPDATE
    # =================================================

    speed = ball_body.velocity.length

    trail.append({
        "x": ball_body.position.x,
        "y": ball_body.position.y,
        "life": 1.0,
        "speed": speed
    })

    for t in trail:
        t["life"] -= dt * 2.5

    trail = [t for t in trail if t["life"] > 0]

    trail = trail[-60:]

    # =================================================
    # DRAW
    # =================================================

    screen.fill(BG)

    # Grid
    for x in range(0, WIDTH, 50):
        pygame.draw.line(
            screen,
            GRID,
            (x, 0),
            (x, HEIGHT)
        )

    for y in range(0, HEIGHT, 50):
        pygame.draw.line(
            screen,
            GRID,
            (0, y),
            (WIDTH, y)
        )

    # =================================================
    # DRAW TRAIL
    # =================================================

    for t in trail:

        radius = int(10 * t["life"])

        alpha = int(255 * t["life"])

        surf = pygame.Surface(
            (radius * 4, radius * 4),
            pygame.SRCALPHA
        )

        glow = min(
            255,
            int(t["speed"] * 0.4)
        )

        pygame.draw.circle(
            surf,
            (100, glow, 255, alpha),
            (radius * 2, radius * 2),
            radius
        )

        screen.blit(
            surf,
            (
                t["x"] - radius * 2,
                t["y"] - radius * 2
            )
        )

    # =================================================
    # DRAW RINGS
    # =================================================

    for ring in rings:

        for seg in ring["segments"]:

            a = seg.body.local_to_world(seg.a)
            b = seg.body.local_to_world(seg.b)

            p1 = (int(a.x), int(a.y))
            p2 = (int(b.x), int(b.y))

            # Glow
            pygame.draw.line(
                screen,
                RING_GLOW,
                p1,
                p2,
                THICKNESS + 8
            )

            # Main
            pygame.draw.line(
                screen,
                RING,
                p1,
                p2,
                THICKNESS
            )

    # =================================================
    # BALL
    # =================================================

    x = int(ball_body.position.x)
    y = int(ball_body.position.y)

    # Glow
    pygame.draw.circle(
        screen,
        (60, 60, 120),
        (x, y),
        BALL_RADIUS + 16
    )

    # Ball
    pygame.draw.circle(
        screen,
        BALL,
        (x, y),
        BALL_RADIUS
    )

    # =================================================
    # ESCAPE CHECK
    # =================================================

    outer_radius = 120 + (RING_COUNT - 1) * RING_GAP

    dist = math.dist(
        (x, y),
        CENTER
    )

    if dist > outer_radius + 80:

        font = pygame.font.SysFont(None, 80)

        text = font.render(
            "ESCAPED!",
            True,
            (120, 255, 180)
        )

        screen.blit(
            text,
            (WIDTH // 2 - 160, 70)
        )

    pygame.display.flip()

pygame.quit()
