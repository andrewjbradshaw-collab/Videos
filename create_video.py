import cv2
import numpy as np

WIDTH, HEIGHT = 640, 480
FPS = 30
DURATION = 3  # seconds
OUTPUT = "simple_video.mp4"

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(OUTPUT, fourcc, FPS, (WIDTH, HEIGHT))

ball_radius = 30
ball_x = WIDTH // 2
ball_y = HEIGHT // 2
vx, vy = 5, 4

total_frames = FPS * DURATION

for frame_num in range(total_frames):
    t = frame_num / total_frames

    # Gradient background shifting from blue to purple
    bg_b = int(50 + 100 * t)
    bg_g = int(20 + 30 * t)
    bg_r = int(20 + 120 * t)
    frame = np.full((HEIGHT, WIDTH, 3), (bg_b, bg_g, bg_r), dtype=np.uint8)

    # Update ball position
    ball_x += vx
    ball_y += vy
    if ball_x - ball_radius <= 0 or ball_x + ball_radius >= WIDTH:
        vx = -vx
        ball_x = max(ball_radius, min(WIDTH - ball_radius, ball_x))
    if ball_y - ball_radius <= 0 or ball_y + ball_radius >= HEIGHT:
        vy = -vy
        ball_y = max(ball_radius, min(HEIGHT - ball_radius, ball_y))

    # Draw ball with a glow effect
    color_r = int(255 * abs(np.sin(frame_num * 0.05)))
    color_g = int(255 * abs(np.sin(frame_num * 0.05 + 2)))
    color_b = int(255 * abs(np.sin(frame_num * 0.05 + 4)))
    cv2.circle(frame, (ball_x, ball_y), ball_radius + 8, (color_b // 3, color_g // 3, color_r // 3), -1)
    cv2.circle(frame, (ball_x, ball_y), ball_radius, (color_b, color_g, color_r), -1)

    # Frame counter text
    cv2.putText(frame, f"Frame {frame_num + 1}/{total_frames}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    writer.write(frame)

writer.release()
print(f"Created {OUTPUT} ({total_frames} frames, {FPS}fps, {DURATION}s)")
