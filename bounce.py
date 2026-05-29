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
try:
    bounce_sound = pygame.mixer.Sound("sounds/sound.mp3")
except Exception:
    print("Warning: 'sounds/sound.mp3' not found. Running without sound.")
    bounce_sound = None

# =====================================================
# COLORS & DYNAMIC HUE
# =====================================================
BG = (0, 0, 0)
GRID = (18, 18, 30)

dynamic_color = pygame.Color(0)

# =====================================================
# GAME STATE & VARIABLES
# =====================================================
game_state = "PLAYING"  # Can be "PLAYING" or "BURSTED"
particles = []          # Will hold our explosion pieces

CIRCLE_RADIUS = 150
CIRCLE_THICKNESS = 4

ball_pos = Vector2(CENTER)
ball_vel = Vector2(
    random.uniform(-420, 420),
    random.uniform(-420, 420)
)

BALL_RADIUS = 4
MAX_RADIUS = CIRCLE_RADIUS - CIRCLE_THICKNESS

GRAVITY = Vector2(0, 0)
ELASTICITY = 0.995
GROWTH_PER_HIT = 2.2

# =====================================================
# EFFECTS
# =====================================================
trail = []
camera_shake = 0
collision_count = 0
collision_lines = [] 
sound_multiplier = 1.0

# =====================================================
# MAIN LOOP
# =====================================================
running = True

while running:
    dt = min(clock.tick(60) / 1000, 0.1)

    # =================================================
    # EVENTS
    # =================================================
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # =================================================
    # PHYSICS (ONLY IF PLAYING)
    # =================================================
    if game_state == "PLAYING":
        ball_vel += GRAVITY * dt
        ball_pos += ball_vel * dt
        
        direction = ball_pos - CENTER
        distance = direction.length()

        # =================================================
        # COLLISION
        # =================================================
        if (distance + BALL_RADIUS >= CIRCLE_RADIUS and BALL_RADIUS < MAX_RADIUS):
            
            collision_count += 1
            
            if distance > 0:
                normal = direction.normalize()
            else:
                normal = Vector2(1, 0)

            # Store tether point
            wall_anchor = CENTER + normal * CIRCLE_RADIUS
            collision_lines.append(Vector2(wall_anchor))

            # Grow ball first
            BALL_RADIUS += GROWTH_PER_HIT
            BALL_RADIUS = min(BALL_RADIUS, MAX_RADIUS)

            # Push inward
            ball_pos = CENTER + normal * (CIRCLE_RADIUS - BALL_RADIUS - 1)
            
            # Reflect
            ball_vel = ball_vel.reflect(normal) * ELASTICITY
            
            # Tiny random angle variation
            ball_vel = ball_vel.rotate(random.uniform(-8, 8))

            # INCREASING SPEED EVERY COLLISION (4% boost per hit)
            ball_vel *= 1.04     
            
            # Sound Intensity
            impact_speed = min(1.0, ball_vel.length() / 900)
            sound_multiplier += 0.20
            volume = min(1.0, impact_speed * sound_multiplier)
            
            if bounce_sound:
                bounce_sound.set_volume(volume)
                bounce_sound.play()

        # =================================================
        # END STATE (THE BURST)
        # =================================================
        if BALL_RADIUS >= MAX_RADIUS:
            game_state = "BURSTED"
            camera_shake = 40  # Massive camera shake!
            
            # Play a loud boom if sound exists
            if bounce_sound:
                bounce_sound.set_volume(1.0)
                bounce_sound.play()

            # Spawn 600 particles
            for _ in range(600):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(100, 1800) # Violent explosion speeds
                vel = Vector2(math.cos(angle), math.sin(angle)) * speed
                
                # Assign rainbow colors to the pieces
                p_color = pygame.Color(0)
                p_color.hsla = (random.uniform(0, 360), 100, 50, 100)
                
                particles.append({
                    "pos": Vector2(ball_pos),
                    "vel": vel,
                    "radius": random.uniform(2, 8),
                    "life": random.uniform(1.0, 3.5), # How long they stay on screen
                    "color": p_color
                })
            
            # Clear the web and trail completely to signify everything shattered
            collision_lines.clear()
            trail.clear()
            ball_vel = Vector2(0, 0)

        # Update Trail
        speed = ball_vel.length()
        trail.append({
            "pos": Vector2(ball_pos),
            "life": 1.0,
            "radius": BALL_RADIUS,
            "speed": speed
        })

        for t in trail:
            t["life"] -= dt * 1.8
        trail = [t for t in trail if t["life"] > 0][-150:]

    # =================================================
    # UPDATE PARTICLES (IF BURSTED)
    # =================================================
    elif game_state == "BURSTED":
        for p in particles:
            p["vel"] += Vector2(0, 600) * dt # Add some gravity falling effect to pieces
            p["pos"] += p["vel"] * dt
            p["life"] -= dt
        # Remove dead particles
        particles = [p for p in particles if p["life"] > 0]

    # =================================================
    # CAMERA SHAKE
    # =================================================
    camera_shake *= 0.9
    offset_x = random.uniform(-camera_shake, camera_shake) if camera_shake > 0.5 else 0
    offset_y = random.uniform(-camera_shake, camera_shake) if camera_shake > 0.5 else 0

    # =================================================
    # DRAW
    # =================================================
    screen.fill(BG)
    
    hue = (collision_count * 5) % 360
    dynamic_color.hsla = (hue, 100, 50, 100)

    # Draw the main Ring (always stays on screen)
    center_render = (int(CENTER.x + offset_x), int(CENTER.y + offset_y))
    pygame.draw.circle(screen, dynamic_color, center_render, CIRCLE_RADIUS, CIRCLE_THICKNESS)

    if game_state == "PLAYING":
        # Draw Tethered Lines
        line_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for anchor_pos in collision_lines:
            pygame.draw.line(
                line_surface,
                (255, 255, 255, 80), 
                (int(anchor_pos.x + offset_x), int(anchor_pos.y + offset_y)),
                (int(ball_pos.x + offset_x), int(ball_pos.y + offset_y)),
                1
            )
        screen.blit(line_surface, (0, 0))

        # Draw Trail
        for t in trail:
            life = t["life"]
            radius = int(t["radius"] * 0.45 * life)
            if radius <= 0: continue
            alpha = int(180 * life)
            surf = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
            r, g, b, _ = dynamic_color
            pygame.draw.circle(surf, (r, g, b, alpha), (radius * 2, radius * 2), radius)
            screen.blit(surf, (t["pos"].x - radius * 2 + offset_x, t["pos"].y - radius * 2 + offset_y))

        # Draw Ball
        ball_render = (int(ball_pos.x + offset_x), int(ball_pos.y + offset_y))
        pygame.draw.circle(screen, dynamic_color, ball_render, int(BALL_RADIUS))

    elif game_state == "BURSTED":
        # Draw Particles
        for p in particles:
            # Shrink them slightly as they die
            r = int(p["radius"] * min(1.0, p["life"]))
            if r > 0:
                pygame.draw.circle(
                    screen, 
                    p["color"], 
                    (int(p["pos"].x + offset_x), int(p["pos"].y + offset_y)), 
                    r
                )

    # =================================================
    # UI
    # =================================================
    font = pygame.font.SysFont(None, 40)
    text = font.render(f"Bounces: {collision_count}", True, (255, 255, 255))
    text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT - 50))
    screen.blit(text, text_rect)

    pygame.display.flip()

pygame.quit()
