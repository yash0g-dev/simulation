import argparse
import math
import os
import random
import subprocess
from dataclasses import dataclass

import pygame
import pymunk
from pygame.math import Vector2


WIDTH, HEIGHT = 360, 640
FPS = 60
CENTER = Vector2(WIDTH // 2, HEIGHT // 2 + 8)

BG = (7, 7, 9)
WHITE = (245, 247, 252)
MUTED = (190, 190, 190)

BALL_RADIUS = 7
START_SPEED = 300
SPEED_GAIN = 1.018
MAX_SPEED = 900


@dataclass
class Ring:
    radius: float
    color: tuple[int, int, int]
    gap_angle: float
    gap_width: float
    spin: float
    alive: bool = True
    alpha: int = 255


def angle_delta(a, b):
    return (a - b + math.pi) % (math.tau) - math.pi


def polar(radius, angle):
    return CENTER + Vector2(math.cos(angle), math.sin(angle)) * radius


def draw_glow_circle(surface, color, pos, radius, alpha):
    size = int(radius * 2 + 6)
    glow = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*color, alpha), (size // 2, size // 2), int(radius))
    surface.blit(glow, (pos[0] - size // 2, pos[1] - size // 2), special_flags=pygame.BLEND_ADD)


def draw_ring(surface, ring):
    if not ring.alive and ring.alpha <= 0:
        return

    # Faint full orbit guide, visible in the reference after pieces break.
    guide = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(guide, (70, 70, 76, 38), CENTER, int(ring.radius), 1)
    surface.blit(guide, (0, 0))

    gap_start = ring.gap_angle - ring.gap_width / 2
    gap_end = ring.gap_angle + ring.gap_width / 2
    segments = [(gap_end, gap_start + math.tau)]
    alpha = max(0, min(255, int(ring.alpha)))
    color = (*ring.color, alpha)
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    for start, end in segments:
        points = []
        steps = max(20, int((end - start) * ring.radius / 4))
        for i in range(steps + 1):
            angle = start + (end - start) * i / steps
            p = polar(ring.radius, angle)
            points.append((int(p.x), int(p.y)))

        if len(points) > 1:
            pygame.draw.lines(layer, (*ring.color, min(80, alpha)), False, points, 10)
            pygame.draw.lines(layer, color, False, points, 4)

    surface.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)


def make_particles(pos, color, count, speed_min=45, speed_max=220):
    particles = []
    for _ in range(count):
        direction = Vector2(1, 0).rotate(random.uniform(0, 360))
        particles.append(
            {
                "pos": Vector2(pos),
                "vel": direction * random.uniform(speed_min, speed_max),
                "life": random.uniform(0.35, 0.9),
                "radius": random.uniform(1.4, 3.2),
                "color": color,
            }
        )
    return particles


def make_space():
    space = pymunk.Space()
    space.gravity = (0, 0)

    mass = 1
    moment = pymunk.moment_for_circle(mass, 0, BALL_RADIUS)
    body = pymunk.Body(mass, moment)
    body.position = (CENTER.x, CENTER.y)
    initial_velocity = Vector2(START_SPEED, -150).rotate(random.uniform(-25, 25))
    body.velocity = (initial_velocity.x, initial_velocity.y)

    shape = pymunk.Circle(body, BALL_RADIUS)
    shape.elasticity = 1.0
    shape.friction = 0.0
    space.add(body, shape)
    return space, body


def collision_with_ring(body, ring):
    pos = Vector2(body.position.x, body.position.y)
    rel = pos - CENTER
    distance = rel.length()
    if distance == 0:
        return False, False

    angle = math.atan2(rel.y, rel.x)
    in_gap = abs(angle_delta(angle, ring.gap_angle)) < ring.gap_width / 2

    touching = distance + BALL_RADIUS >= ring.radius
    if in_gap and distance - BALL_RADIUS > ring.radius:
        return False, True

    if not in_gap and touching:
        normal = rel.normalize()
        new_pos = CENTER + normal * (ring.radius - BALL_RADIUS - 0.5)
        body.position = (new_pos.x, new_pos.y)
        velocity = Vector2(body.velocity.x, body.velocity.y)
        reflected = velocity.reflect(normal) * SPEED_GAIN
        if reflected.length() > MAX_SPEED:
            reflected.scale_to_length(MAX_SPEED)
        reflected = reflected.rotate(random.uniform(-3.0, 3.0))
        body.velocity = (reflected.x, reflected.y)
        return True, False

    return False, False


def draw_speed_text(screen, font, initial_speed):
    text = font.render(f"Initial ball speed: {initial_speed:0.2f} px/f", True, (218, 218, 218))
    rect = text.get_rect(center=(WIDTH // 2, HEIGHT - 38))
    screen.blit(text, rect)


def start_recorder(path):
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{WIDTH}x{HEIGHT}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-an",
        "-vcodec",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        path,
    ]
    return subprocess.Popen(command, stdin=subprocess.PIPE)


def main():
    parser = argparse.ArgumentParser(description="Pygame + Pymunk spiral ring escape short.")
    parser.add_argument("--frames", type=int, default=0, help="Stop after this many frames. 0 runs until closed.")
    parser.add_argument("--record", default="", help="Optional mp4 output path, encoded with ffmpeg.")
    args = parser.parse_args()

    pygame.init()
    if not os.environ.get("SDL_AUDIODRIVER"):
        pygame.mixer.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Spiral Escape - Pymunk")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 13)

    space, ball_body = make_space()

    colors = [
        (255, 34, 34),
        (255, 176, 24),
        (250, 224, 28),
        (66, 255, 38),
        (14, 226, 127),
        (16, 190, 250),
        (31, 80, 235),
        (154, 25, 248),
        (246, 0, 166),
    ]
    rings = [
        Ring(172 - i * 17, colors[i], math.radians(8 + i * 37), math.radians(46), math.radians((25 + i * 4) * (-1 if i % 2 else 1)))
        for i in range(len(colors))
    ]

    particles = []
    trail = []
    burst_bodies = []
    active_ring = len(rings) - 1
    score_speed = 0.0
    final_burst = False
    frame = 0
    recorder = start_recorder(args.record) if args.record else None

    running = True
    while running:
        dt = clock.tick(FPS) / 1000
        frame += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        for ring in rings:
            ring.gap_angle = (ring.gap_angle + ring.spin * dt) % math.tau
            if not ring.alive:
                ring.alpha -= 420 * dt

        if not final_burst:
            space.step(dt)
            velocity = Vector2(ball_body.velocity.x, ball_body.velocity.y)
            score_speed = velocity.length() / FPS

            if active_ring >= 0:
                ring = rings[active_ring]
                bounced, escaped = collision_with_ring(ball_body, ring)
                if bounced:
                    hit_pos = Vector2(ball_body.position.x, ball_body.position.y)
                    particles.extend(make_particles(hit_pos, ring.color, 18, 55, 185))
                if escaped:
                    ring.alive = False
                    particles.extend(make_particles(Vector2(ball_body.position.x, ball_body.position.y), ring.color, 36, 80, 270))
                    active_ring -= 1
            else:
                final_burst = True
                for _ in range(140):
                    mass = 0.25
                    radius = random.uniform(3, 5)
                    moment = pymunk.moment_for_circle(mass, 0, radius)
                    body = pymunk.Body(mass, moment)
                    pos = CENTER + Vector2(random.uniform(-16, 16), random.uniform(-16, 16))
                    vel = Vector2(random.uniform(260, 860), 0).rotate(random.uniform(0, 360))
                    body.position = (pos.x, pos.y)
                    body.velocity = (vel.x, vel.y)
                    shape = pymunk.Circle(body, radius)
                    shape.elasticity = 0.98
                    space.add(body, shape)
                    burst_bodies.append((body, radius, Vector2(body.velocity.x, body.velocity.y)))

            trail.append({"pos": Vector2(ball_body.position.x, ball_body.position.y), "life": 1.0})
            trail = trail[-42:]
        else:
            space.step(dt)
            score_speed = min(47.0, score_speed + 0.15)

        for particle in particles:
            particle["life"] -= dt
            particle["vel"] *= 0.965
            particle["pos"] += particle["vel"] * dt
        particles = [p for p in particles if p["life"] > 0]

        screen.fill(BG)
        vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for radius, alpha in [(260, 24), (230, 18), (200, 12)]:
            pygame.draw.circle(vignette, (55, 55, 60, alpha), CENTER, radius, 1)
        screen.blit(vignette, (0, 0))

        for item in trail:
            item["life"] -= dt * 2.4
            alpha = max(0, int(95 * item["life"]))
            draw_glow_circle(screen, WHITE, item["pos"], 11 * item["life"], alpha)
        trail = [item for item in trail if item["life"] > 0]

        for ring in rings:
            draw_ring(screen, ring)

        for particle in particles:
            alpha = max(0, min(255, int(255 * particle["life"])))
            color = (*particle["color"], alpha)
            surface = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(surface, color, (5, 5), int(particle["radius"]))
            screen.blit(surface, particle["pos"] - Vector2(5, 5))

        if not final_burst:
            pos = Vector2(ball_body.position.x, ball_body.position.y)
            draw_glow_circle(screen, WHITE, pos, 16, 110)
            pygame.draw.circle(screen, WHITE, (int(pos.x), int(pos.y)), BALL_RADIUS)
            pygame.draw.circle(screen, (214, 218, 226), (int(pos.x - 2), int(pos.y - 2)), 2)
        else:
            for body, radius, start_vel in burst_bodies:
                pos = Vector2(body.position.x, body.position.y)
                direction = Vector2(body.velocity.x, body.velocity.y)
                if direction.length_squared() > 0:
                    direction = direction.normalize()
                tail = pos - direction * min(42, max(12, start_vel.length() * 0.045))
                pygame.draw.line(screen, (205, 207, 214), tail, pos, int(radius * 2))
                pygame.draw.circle(screen, WHITE, (int(pos.x), int(pos.y)), int(radius))

        draw_speed_text(screen, font, score_speed)

        pygame.display.flip()

        if recorder:
            frame_data = pygame.image.tostring(screen, "RGB")
            recorder.stdin.write(frame_data)

        if args.frames and frame >= args.frames:
            running = False

    if recorder:
        recorder.stdin.close()
        recorder.wait()

    pygame.quit()


if __name__ == "__main__":
    main()
