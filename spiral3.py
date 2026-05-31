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
PHYSICS_FPS = 240
FIXED_DT = 1 / PHYSICS_FPS
MAX_FRAME_DT = 1 / 30
TIME_SCALE = 0.58
CENTER = Vector2(WIDTH // 2, HEIGHT // 2 + 8)

BG = (7, 7, 9)
WHITE = (245, 247, 252)
MUTED = (190, 190, 190)

BALL_RADIUS = 7
START_SPEED = 155
SPEED_GAIN = 1.004
MAX_SPEED = 430
RING_RENDER_SCALE = 4
BALL_RENDER_SCALE = 4
TRAIL_LENGTH = 95
TRAIL_SAMPLE_DISTANCE = 0.75


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


def draw_soft_ball(surface, pos):
    scale = BALL_RENDER_SCALE
    size = int((BALL_RADIUS + 9) * 2 * scale)
    layer = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2

    pygame.draw.circle(layer, (255, 255, 255, 42), (center, center), int((BALL_RADIUS + 8) * scale))
    pygame.draw.circle(layer, (255, 255, 255, 84), (center, center), int((BALL_RADIUS + 4) * scale))
    pygame.draw.circle(layer, WHITE, (center, center), BALL_RADIUS * scale)
    pygame.draw.circle(
        layer,
        (214, 218, 226, 230),
        (center - 2 * scale, center - 2 * scale),
        2 * scale,
    )

    smooth = pygame.transform.smoothscale(layer, (size // scale, size // scale))
    surface.blit(
        smooth,
        (int(pos.x - smooth.get_width() / 2), int(pos.y - smooth.get_height() / 2)),
        special_flags=pygame.BLEND_ADD,
    )


def ring_point(radius, angle, scale):
    center = CENTER * scale
    return center + Vector2(math.cos(angle), math.sin(angle)) * radius * scale


def draw_ring_to_layer(layer, ring, scale):
    if not ring.alive and ring.alpha <= 0:
        return

    gap_start = ring.gap_angle - ring.gap_width / 2
    gap_end = ring.gap_angle + ring.gap_width / 2
    segments = [(gap_end, gap_start + math.tau)]
    alpha = max(0, min(255, int(ring.alpha)))
    color = (*ring.color, alpha)

    pygame.draw.circle(
        layer,
        (70, 70, 76, 38),
        (int(CENTER.x * scale), int(CENTER.y * scale)),
        int(ring.radius * scale),
        scale,
    )

    for start, end in segments:
        points = []
        steps = max(140, int((end - start) * ring.radius * scale / 2))
        for i in range(steps + 1):
            angle = start + (end - start) * i / steps
            p = ring_point(ring.radius, angle, scale)
            points.append((int(p.x), int(p.y)))

        if len(points) > 1:
            pygame.draw.lines(layer, (*ring.color, min(58, alpha)), False, points, 13 * scale)
            pygame.draw.lines(layer, (*ring.color, min(128, alpha)), False, points, 7 * scale)
            pygame.draw.lines(layer, color, False, points, 3 * scale)


def draw_rings(surface, rings):
    scale = RING_RENDER_SCALE
    layer = pygame.Surface((WIDTH * scale, HEIGHT * scale), pygame.SRCALPHA)
    for ring in rings:
        draw_ring_to_layer(layer, ring, scale)
    smooth = pygame.transform.smoothscale(layer, (WIDTH, HEIGHT))
    surface.blit(smooth, (0, 0), special_flags=pygame.BLEND_ADD)


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
    initial_velocity = Vector2(START_SPEED, -72).rotate(random.uniform(-18, 18))
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

    previous_distance = getattr(ring, "previous_distance", distance)
    touching = distance + BALL_RADIUS >= ring.radius
    crossed_outward = previous_distance <= ring.radius and distance - BALL_RADIUS > ring.radius
    ring.previous_distance = distance

    if in_gap and crossed_outward:
        return False, True

    if not in_gap and touching:
        normal = rel.normalize()
        new_pos = CENTER + normal * (ring.radius - BALL_RADIUS - 1.0)
        body.position = (new_pos.x, new_pos.y)
        velocity = Vector2(body.velocity.x, body.velocity.y)
        reflected = velocity.reflect(normal).rotate(random.uniform(-1.5, 1.5)) * SPEED_GAIN
        if reflected.length() > MAX_SPEED:
            reflected.scale_to_length(MAX_SPEED)
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
    accumulator = 0.0
    recorder = start_recorder(args.record) if args.record else None

    running = True
    while running:
        frame_dt = min(clock.tick(FPS) / 1000, MAX_FRAME_DT)
        sim_dt = frame_dt * TIME_SCALE
        accumulator += sim_dt
        frame += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        for ring in rings:
            ring.gap_angle = (ring.gap_angle + ring.spin * sim_dt) % math.tau
            if not ring.alive:
                ring.alpha -= 300 * sim_dt

        if not final_burst:
            while accumulator >= FIXED_DT:
                space.step(FIXED_DT)
                velocity = Vector2(ball_body.velocity.x, ball_body.velocity.y)
                score_speed = velocity.length() / FPS

                if active_ring >= 0:
                    ring = rings[active_ring]
                    bounced, escaped = collision_with_ring(ball_body, ring)
                    if bounced:
                        hit_pos = Vector2(ball_body.position.x, ball_body.position.y)
                        particles.extend(make_particles(hit_pos, ring.color, 14, 55, 185))
                    if escaped:
                        ring.alive = False
                        particles.extend(
                            make_particles(
                                Vector2(ball_body.position.x, ball_body.position.y),
                                ring.color,
                                36,
                                80,
                                270,
                            )
                        )
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
                    break

                accumulator -= FIXED_DT

            current_pos = Vector2(ball_body.position.x, ball_body.position.y)
            if not trail or current_pos.distance_to(trail[-1]["pos"]) > TRAIL_SAMPLE_DISTANCE:
                trail.append({"pos": current_pos, "life": 1.0})
            trail = trail[-TRAIL_LENGTH:]
        else:
            while accumulator >= FIXED_DT:
                space.step(FIXED_DT)
                accumulator -= FIXED_DT
            score_speed = min(47.0, score_speed + 0.15)

        for particle in particles:
            particle["life"] -= sim_dt
            particle["vel"] *= 0.982
            particle["pos"] += particle["vel"] * sim_dt
        particles = [p for p in particles if p["life"] > 0]

        screen.fill(BG)
        vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for radius, alpha in [(260, 24), (230, 18), (200, 12)]:
            pygame.draw.circle(vignette, (55, 55, 60, alpha), CENTER, radius, 1)
        screen.blit(vignette, (0, 0))

        for item in trail:
            item["life"] -= sim_dt * 1.35
            alpha = max(0, int(95 * item["life"]))
            draw_glow_circle(screen, WHITE, item["pos"], 10 * item["life"], alpha)
        trail = [item for item in trail if item["life"] > 0]

        draw_rings(screen, rings)

        for particle in particles:
            alpha = max(0, min(255, int(255 * particle["life"])))
            color = (*particle["color"], alpha)
            surface = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(surface, color, (5, 5), int(particle["radius"]))
            screen.blit(surface, particle["pos"] - Vector2(5, 5))

        if not final_burst:
            pos = Vector2(ball_body.position.x, ball_body.position.y)
            draw_soft_ball(screen, pos)
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
