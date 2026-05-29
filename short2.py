
import pygame
import math
import random
from pygame.math import Vector2

# =====================================================
# INIT
# =====================================================

pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 90 * 4, 160 * 4

screen = pygame.display.set_mode((WIDTH, HEIGHT))

pygame.display.set_caption("Growing Ball Simulation")

clock = pygame.time.Clock()

CENTER = Vector2(WIDTH // 2, HEIGHT // 2)

# =====================================================
# SOUND
# =====================================================

# Put your sound file here
# Example: sounds/bounce.wav
bounce_sound = pygame.mixer.Sound("sounds/sound.mp3")

# =====================================================
# COLORS
# =====================================================

BG = (5, 5, 12)
GRID = (18, 18, 30)

RING = (120, 200, 255)
RING_GLOW = (50, 120, 255)

BALL = (255, 220, 120)

# =====================================================
# RING
# =====================================================

CIRCLE_RADIUS = 150
CIRCLE_THICKNESS = 1

# =====================================================
# BALL
# =====================================================

ball_pos = Vector2(CENTER)

ball_vel = Vector2(
    random.uniform(-420, 420),
    random.uniform(-420, 420)
)

BALL_RADIUS = 4
MAX_RADIUS = 200

GRAVITY = Vector2(0, 0)

ELASTICITY = 0.995
GROWTH_PER_HIT = 2.2

# =====================================================
# EFFECTS
# =====================================================

trail = []

camera_shake = 0

collision_count = 0

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
    # PHYSICS
    # =================================================

    ball_vel += GRAVITY * dt

    ball_pos += ball_vel * dt

    direction = ball_pos - CENTER

    distance = direction.length()

    # =================================================
    # COLLISION
    # =================================================

    if (
    distance + BALL_RADIUS >= CIRCLE_RADIUS
    and BALL_RADIUS < CIRCLE_RADIUS - CIRCLE_THICKNESS
):
        collision_count += 1

        normal = direction.normalize()

        # Push inward
        ball_pos = (
            CENTER
            + normal * (CIRCLE_RADIUS - BALL_RADIUS)
        )

        ball_vel = (
            ball_vel.reflect(normal)
            * ELASTICITY * 0.99
        )

        # tiny random angle variation
        ball_vel = ball_vel.rotate(
            random.uniform(-8, 8)
        )

        # Slight speed boost
        # smaller ball gains more speed
        speed_boost = max(
    1.001,
    1.01 - (BALL_RADIUS / MAX_RADIUS) * 0.009
)

        ball_vel *= speed_boost     
# Grow ball
        BALL_RADIUS += GROWTH_PER_HIT

        BALL_RADIUS = min(BALL_RADIUS, MAX_RADIUS)

        # =============================================
        # SOUND INTENSITY
        # =============================================

        impact_speed = min(1.0, ball_vel.length() / 900)

        bounce_sound.set_volume(impact_speed)

        bounce_sound.play()
    # =================================================
    # FINAL FREEZE
    # =================================================

    if BALL_RADIUS >= CIRCLE_RADIUS - CIRCLE_THICKNESS:

        BALL_RADIUS = CIRCLE_RADIUS - CIRCLE_THICKNESS

        ball_pos = Vector2(CENTER)

        ball_vel = Vector2(0, 0)

        # =============================================
        # CAMERA SHAKE
        # =============================================

        camera_shake = min(30, BALL_RADIUS * 0.12)

    # =================================================
    # CAMERA SHAKE DECAY
    # =================================================

    camera_shake *= 0.9

    offset_x = random.uniform(-camera_shake, camera_shake)
    offset_y = random.uniform(-camera_shake, camera_shake)

    # =================================================
    # TRAIL
    # =================================================

    speed = ball_vel.length()

    trail.append({

        "pos": Vector2(ball_pos),

        "life": 1.0,

        "radius": BALL_RADIUS,

        "speed": speed
    })

    for t in trail:
        t["life"] -= dt * 1.8

    trail = [t for t in trail if t["life"] > 0]

    trail = trail[-150:]

    # =================================================
    # DRAW
    # =================================================

    screen.fill(BG)

    # =================================================
    # GRID
    # =================================================

    for x in range(0, WIDTH, 60):

        pygame.draw.line(
            screen,
            GRID,
            (x + offset_x, 0),
            (x + offset_x, HEIGHT)
        )

    for y in range(0, HEIGHT, 60):

        pygame.draw.line(
            screen,
            GRID,
            (0, y + offset_y),
            (WIDTH, y + offset_y)
        )

    # =================================================
    # TRAIL
    # =================================================

    for t in trail:

        life = t["life"]

        radius = int(t["radius"] * 0.45 * life)

        alpha = int(180 * life)

        surf = pygame.Surface(
            (radius * 4, radius * 4),
            pygame.SRCALPHA
        )

        glow = min(
            255,
            int(t["speed"] * 0.25)
        )

        pygame.draw.circle(
            surf,
            (120, glow, 255, alpha),
            (radius * 2, radius * 2),
            radius
        )

        screen.blit(
            surf,
            (
                t["pos"].x - radius * 2 + offset_x,
                t["pos"].y - radius * 2 + offset_y
            )
        )

    # =================================================
    # OUTER GLOW
    # =================================================

    pygame.draw.circle(
        screen,
        RING_GLOW,
        (
            int(CENTER.x + offset_x),
            int(CENTER.y + offset_y)
        ),
        CIRCLE_RADIUS + 10,
        CIRCLE_THICKNESS + 16
    )

    # =================================================
    # MAIN RING
    # =================================================

    pygame.draw.circle(
        screen,
        RING,
        (
            int(CENTER.x + offset_x),
            int(CENTER.y + offset_y)
        ),
        CIRCLE_RADIUS,
        CIRCLE_THICKNESS
    )

    # =================================================
    # BALL GLOW
    # =================================================

    pygame.draw.circle(
        screen,
        (60, 60, 120),
        (
            int(ball_pos.x + offset_x),
            int(ball_pos.y + offset_y)
        ),
        int(BALL_RADIUS + 24)
    )

    # =================================================
    # BALL
    # =================================================

    pygame.draw.circle(
        screen,
        BALL,
        (
            int(ball_pos.x + offset_x),
            int(ball_pos.y + offset_y)
        ),
        int(BALL_RADIUS)
    )

    # =================================================
    # UI
    # =================================================

    font = pygame.font.SysFont(None, 58)

    text = font.render(
        f"COLLISIONS: {collision_count}",
        True,
        (220, 220, 220)
    )

    screen.blit(text, (40, 40))

    size_text = font.render(
        f"SIZE: {int(BALL_RADIUS)}",
        True,
        (220, 220, 220)
    )

    screen.blit(size_text, (40, 110))

    # =================================================
    # END STATE
    # =================================================

    # =================================================
# STOP WHEN FULL
# =================================================

    if BALL_RADIUS >= CIRCLE_RADIUS - CIRCLE_THICKNESS:

        BALL_RADIUS = CIRCLE_RADIUS - CIRCLE_THICKNESS

        ball_vel = Vector2(0, 0)
    if BALL_RADIUS >= MAX_RADIUS:

        end_font = pygame.font.SysFont(None, 100)

        end_text = end_font.render(
            "FULL",
            True,
            (120, 255, 180)
        )

        screen.blit(
            end_text,
            (WIDTH // 2 - 120, 120)
        )

    pygame.display.flip()

pygame.quit()
