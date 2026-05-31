import math
import random

import pygame
from pygame.math import Vector2

# =====================================================
# INIT
# =====================================================
pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 90 * 4, 160 * 4
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Rainbow Paint Fill Bounce")
clock = pygame.time.Clock()

CENTER = Vector2(WIDTH // 2, HEIGHT // 2)

# =====================================================
# SOUND
# =====================================================
try:
    bounce_sound = pygame.mixer.Sound("sounds/sound.mp3")
except Exception:
    print("Warning: 'sounds/sound.mp3' not found. Running without sound.")
    bounce_sound = None

last_sound_time = 0

# =====================================================
# COLORS
# =====================================================
BG = (0, 0, 0)
WHITE = (255, 255, 255)

# =====================================================
# ARENA & BALL
# =====================================================
CIRCLE_RADIUS = 165
CIRCLE_THICKNESS = 4
BALL_RADIUS = 24
MAX_SPEED = 1800
ELASTICITY = 1.0
SPEED_BOOST = 1.012
BALL_GRAVITY = 1000

ball_pos = Vector2(CENTER)
ball_vel = Vector2(random.uniform(-520, 520), random.uniform(-520, 520))
if ball_vel.length() < 250:
    ball_vel.scale_to_length(420)

# =====================================================
# PAINT COVERAGE
# =====================================================
paint_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
painted_cells = set()
CELL_SIZE = 4
FILL_TARGET = 1.0

fillable_cells = []
for gy in range(0, HEIGHT, CELL_SIZE):
    for gx in range(0, WIDTH, CELL_SIZE):
        cell_center = Vector2(gx + CELL_SIZE / 2, gy + CELL_SIZE / 2)
        if cell_center.distance_to(CENTER) <= CIRCLE_RADIUS - CIRCLE_THICKNESS:
            fillable_cells.append((gx // CELL_SIZE, gy // CELL_SIZE))

total_fillable_cells = len(fillable_cells)
coverage = 0.0

# =====================================================
# EFFECTS
# =====================================================
game_state = "PLAYING"
collision_count = 0
particles = []
camera_shake = 0
start_time = pygame.time.get_ticks()
last_stamp_pos = None


def color_from_hue(hue):
    color = pygame.Color(0)
    color.hsla = (hue % 360, 100, 52, 100)
    return color


def make_ball_texture(radius):
    size = radius * 2
    texture = pygame.Surface((size, size), pygame.SRCALPHA)
    stripe_colors = [
        (255, 0, 0, 255),
        (255, 150, 0, 255),
        (255, 255, 0, 255),
        (0, 230, 0, 255),
        (0, 190, 255, 255),
        (0, 65, 255, 255),
        (150, 0, 255, 255),
    ]
    stripe_width = max(2, size // 7)

    for y in range(size):
        for x in range(size):
            stripe_index = int((x - y + size) // stripe_width) % len(stripe_colors)
            texture.set_at((x, y), stripe_colors[stripe_index])

    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (radius, radius), radius)
    texture.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return texture


ball_texture = make_ball_texture(BALL_RADIUS)


def draw_rainbow_ring(surface, center, radius, thickness, spin):
    segments = 96
    rect = pygame.Rect(0, 0, radius * 2, radius * 2)
    rect.center = center

    for i in range(segments):
        start = (i / segments) * math.tau
        end = ((i + 1.35) / segments) * math.tau
        color = color_from_hue(i * 360 / segments + spin)
        pygame.draw.arc(surface, color, rect, start, end, thickness)


def draw_rainbow_ball(surface, pos, radius):
    texture = ball_texture
    if texture.get_width() != radius * 2:
        texture = pygame.transform.smoothscale(ball_texture, (radius * 2, radius * 2))

    surface.blit(texture, (int(pos.x - radius), int(pos.y - radius)))


def stamp_paint(pos, radius):
    global coverage

    draw_rainbow_ball(paint_surface, pos, radius)

    min_x = max(0, int((pos.x - radius) // CELL_SIZE))
    max_x = min(WIDTH // CELL_SIZE, int((pos.x + radius) // CELL_SIZE) + 1)
    min_y = max(0, int((pos.y - radius) // CELL_SIZE))
    max_y = min(HEIGHT // CELL_SIZE, int((pos.y + radius) // CELL_SIZE) + 1)

    radius_sq = radius * radius
    arena_radius = CIRCLE_RADIUS - CIRCLE_THICKNESS

    for cy in range(min_y, max_y):
        for cx in range(min_x, max_x):
            cell_pos = Vector2(cx * CELL_SIZE + CELL_SIZE / 2, cy * CELL_SIZE + CELL_SIZE / 2)
            if cell_pos.distance_squared_to(pos) > radius_sq:
                continue
            if cell_pos.distance_to(CENTER) > arena_radius:
                continue
            painted_cells.add((cx, cy))

    coverage = len(painted_cells) / total_fillable_cells


def spawn_burst():
    for _ in range(650):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(180, 1800)
        vel = Vector2(math.cos(angle), math.sin(angle)) * speed
        particles.append({
            "pos": Vector2(ball_pos),
            "vel": vel,
            "radius": random.uniform(2, 7),
            "life": random.uniform(1.0, 3.0),
            "color": color_from_hue(random.uniform(0, 360)),
        })


# =====================================================
# MAIN LOOP
# =====================================================
running = True

while running:
    dt = min(clock.tick(60) / 1000, 0.1)
    current_time = pygame.time.get_ticks()
    elapsed_time = current_time - start_time

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    hue = (elapsed_time * 0.09 + collision_count * 18) % 360
    if game_state == "PLAYING":
        ball_vel.y += BALL_GRAVITY * dt
        ball_pos += ball_vel * dt

        direction = ball_pos - CENTER
        distance = direction.length()
        inner_limit = CIRCLE_RADIUS - CIRCLE_THICKNESS - BALL_RADIUS

        if distance >= inner_limit:
            collision_count += 1
            normal = direction.normalize() if distance > 0 else Vector2(1, 0)
            ball_pos = CENTER + normal * inner_limit
            ball_vel = ball_vel.reflect(normal) * ELASTICITY
            ball_vel = ball_vel.rotate(random.uniform(-10, 10))
            ball_vel *= SPEED_BOOST
            camera_shake = min(8, camera_shake + 2)

            if ball_vel.length() > MAX_SPEED:
                ball_vel.scale_to_length(MAX_SPEED)

            if bounce_sound and current_time - last_sound_time > 35:
                impact_volume = min(1.0, 0.25 + ball_vel.length() / MAX_SPEED)
                bounce_sound.set_volume(impact_volume)
                bounce_sound.play()
                last_sound_time = current_time

        if last_stamp_pos is None or ball_pos.distance_to(last_stamp_pos) >= BALL_RADIUS * 0.35:
            stamp_paint(ball_pos, BALL_RADIUS)
            last_stamp_pos = Vector2(ball_pos)

        if coverage >= FILL_TARGET:
            game_state = "FILLED"
            camera_shake = 35
            spawn_burst()

    elif game_state == "FILLED":
        for p in particles:
            p["vel"] += Vector2(0, 650) * dt
            p["pos"] += p["vel"] * dt
            p["life"] -= dt
        particles = [p for p in particles if p["life"] > 0]

    camera_shake *= 0.88
    offset_x = random.uniform(-camera_shake, camera_shake) if camera_shake > 0.5 else 0
    offset_y = random.uniform(-camera_shake, camera_shake) if camera_shake > 0.5 else 0

    screen.fill(BG)
    screen.blit(paint_surface, (offset_x, offset_y))

    center_render = (int(CENTER.x + offset_x), int(CENTER.y + offset_y))
    draw_rainbow_ring(screen, center_render, CIRCLE_RADIUS, CIRCLE_THICKNESS, hue)

    if game_state == "PLAYING":
        draw_rainbow_ball(
            screen,
            Vector2(ball_pos.x + offset_x, ball_pos.y + offset_y),
            BALL_RADIUS,
        )
    else:
        for p in particles:
            radius = int(p["radius"] * min(1.0, p["life"]))
            if radius > 0:
                pygame.draw.circle(
                    screen,
                    p["color"],
                    (int(p["pos"].x + offset_x), int(p["pos"].y + offset_y)),
                    radius,
                )

    font = pygame.font.SysFont(None, 34)
    fill_text = font.render(f"Filled: {coverage * 100:05.1f}%", True, WHITE)
    hit_text = font.render(f"Bounces: {collision_count}", True, WHITE)
    screen.blit(fill_text, fill_text.get_rect(center=(WIDTH // 2, HEIGHT - 75)))
    screen.blit(hit_text, hit_text.get_rect(center=(WIDTH // 2, HEIGHT - 40)))

    pygame.display.flip()

pygame.quit()
