"""Flappy Bird inspired arcade game implemented with pygame.

Run the game with ``python game.py``.  Use the space bar or the up arrow
key to make the bird flap.  Avoid the pipes and try to fly as far as you
can!  When you crash into a pipe or the ground you can restart by pressing
space.
"""

from __future__ import annotations

import math
import random
from array import array
from typing import List, Optional, Tuple

import pygame


# Window configuration -----------------------------------------------------
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 600
PLAYABLE_HEIGHT = WINDOW_HEIGHT - 100
FPS = 60


# Bird physics -------------------------------------------------------------
GRAVITY = 0.35
JUMP_VELOCITY = -7.5
MAX_DESCENT_SPEED = 8
TILT_VELOCITY = 5
MAX_UPWARD_TILT = 25
MAX_DOWNWARD_TILT = -90


# Pipe configuration -------------------------------------------------------
PIPE_GAP = 150
PIPE_DISTANCE = 225
PIPE_SPEED = 3.5


# Colours ------------------------------------------------------------------
SKY_BLUE = (138, 202, 234)
DEEP_BLUE = (69, 146, 196)
BASE_BROWN = (222, 161, 94)
PIPE_GREEN = (99, 201, 70)
PIPE_DARK_GREEN = (89, 178, 62)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def create_bird_frames(size: Tuple[int, int]) -> List[pygame.Surface]:
    """Generate simple wing-flapping animation frames for the bird."""

    width, height = size
    frames = []
    for angle in (-25, 0, 25):
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        body_rect = pygame.Rect(0, 0, width, height)
        pygame.draw.ellipse(surface, (255, 240, 0), body_rect)
        pygame.draw.circle(surface, WHITE, (int(width * 0.7), int(height * 0.4)), int(height * 0.2))
        pygame.draw.circle(surface, BLACK, (int(width * 0.75), int(height * 0.4)), int(height * 0.1))
        wing_points = [
            (int(width * 0.1), int(height * 0.5)),
            (int(width * 0.5), int(height * 0.5)),
            (int(width * 0.3), int(height * 0.9)),
        ]
        wing_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.polygon(wing_surface, (255, 200, 0), wing_points)
        wing_surface = pygame.transform.rotate(wing_surface, angle)
        surface.blit(wing_surface, (0, 0))
        frames.append(surface)
    return frames


def create_pipe_surface(width: int, height: int, flipped: bool = False) -> pygame.Surface:
    """Create a green pipe surface."""

    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    body_rect = pygame.Rect(0, 0, width, height - 20)
    head_rect = pygame.Rect(-8, height - 30, width + 16, 30)
    pygame.draw.rect(surface, PIPE_GREEN, body_rect)
    pygame.draw.rect(surface, PIPE_DARK_GREEN, head_rect, border_radius=6)
    if flipped:
        surface = pygame.transform.flip(surface, False, True)
    return surface


def create_base_surface(width: int, height: int) -> pygame.Surface:
    surface = pygame.Surface((width, height))
    surface.fill(BASE_BROWN)
    for x in range(0, width, 16):
        pygame.draw.rect(surface, (205, 148, 89), (x, 0, 12, height))
    return surface


def make_font(size: int) -> pygame.font.Font:
    return pygame.font.Font(pygame.font.get_default_font(), size)


class Bird:
    width: int = 36
    height: int = 26

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
        self.velocity = 0.0
        self.tilt = 0.0
        self.animation_time = 5
        self.animation_index = 0
        self.frames = create_bird_frames((self.width, self.height))
        self.current_surface = pygame.transform.rotate(self.frames[0], self.tilt)
        self.mask = pygame.mask.from_surface(self.current_surface)

    def jump(self) -> None:
        self.velocity = JUMP_VELOCITY
        self.tilt = MAX_UPWARD_TILT

    def move(self) -> None:
        self.velocity = min(self.velocity + GRAVITY, MAX_DESCENT_SPEED)
        self.y += self.velocity

        if self.velocity < 0:
            self.tilt = MAX_UPWARD_TILT
        else:
            self.tilt = max(self.tilt - TILT_VELOCITY, MAX_DOWNWARD_TILT)

    def update_animation(self) -> None:
        self.animation_index = (self.animation_index + 1) % (self.animation_time * len(self.frames))
        frame = self.frames[self.animation_index // self.animation_time]
        self.current_surface = pygame.transform.rotate(frame, self.tilt)
        self.mask = pygame.mask.from_surface(self.current_surface)

    def draw(self, window: pygame.Surface) -> None:
        rect = self.current_surface.get_rect(center=(self.x, self.y))
        window.blit(self.current_surface, rect)

    @property
    def rect(self) -> pygame.Rect:
        return self.current_surface.get_rect(center=(self.x, self.y))


class Pipe:
    def __init__(self, x: float, gap_center: int, gap: int = PIPE_GAP) -> None:
        self.x = x
        self.gap_center = gap_center
        self.gap = gap
        self.width = 60
        self.speed = PIPE_SPEED

        top_length = max(40, gap_center - gap // 2)
        bottom_length = max(40, PLAYABLE_HEIGHT - (gap_center + gap // 2))

        self.surface_top = create_pipe_surface(self.width, top_length + 30, flipped=True)
        self.surface_bottom = create_pipe_surface(self.width, bottom_length + 30)

    @property
    def top_rect(self) -> pygame.Rect:
        top_height = self.gap_center - self.gap // 2
        return self.surface_top.get_rect(midbottom=(self.x, top_height))

    @property
    def bottom_rect(self) -> pygame.Rect:
        bottom_top = self.gap_center + self.gap // 2
        return self.surface_bottom.get_rect(midtop=(self.x, bottom_top))

    def move(self) -> None:
        self.x -= self.speed

    def draw(self, window: pygame.Surface) -> None:
        window.blit(self.surface_top, self.top_rect)
        window.blit(self.surface_bottom, self.bottom_rect)

    def collide(self, bird: Bird) -> bool:
        bird_rect = bird.rect

        if bird_rect.right < self.top_rect.left or bird_rect.left > self.top_rect.right:
            return False

        bird_mask = bird.mask
        top_mask = pygame.mask.from_surface(self.surface_top)
        bottom_mask = pygame.mask.from_surface(self.surface_bottom)

        top_offset = (int(self.top_rect.left - bird_rect.left), int(self.top_rect.top - bird_rect.top))
        bottom_offset = (int(self.bottom_rect.left - bird_rect.left), int(self.bottom_rect.top - bird_rect.top))

        collision_point = bird_mask.overlap(top_mask, top_offset)
        collision_point_bottom = bird_mask.overlap(bottom_mask, bottom_offset)
        return collision_point is not None or collision_point_bottom is not None


class Base:
    def __init__(self, y: int, speed: float) -> None:
        self.y = y
        self.speed = speed
        self.surface = create_base_surface(WINDOW_WIDTH * 2, WINDOW_HEIGHT - y)
        self.x1 = 0
        self.x2 = self.surface.get_width() // 2

    def move(self) -> None:
        self.x1 -= self.speed
        self.x2 -= self.speed

        if self.x1 + self.surface.get_width() // 2 <= 0:
            self.x1 = self.x2 + self.surface.get_width() // 2
        if self.x2 + self.surface.get_width() // 2 <= 0:
            self.x2 = self.x1 + self.surface.get_width() // 2

    def draw(self, window: pygame.Surface) -> None:
        width = self.surface.get_width() // 2
        window.blit(self.surface, (self.x1, self.y), area=pygame.Rect(0, 0, width, self.surface.get_height()))
        window.blit(self.surface, (self.x2, self.y), area=pygame.Rect(0, 0, width, self.surface.get_height()))


class Game:
    def __init__(self) -> None:
        pygame.display.set_caption("Flappy Bird - Python Edition")
        self.window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_large = make_font(48)
        self.font_small = make_font(24)
        self.background = self._create_background()
        self.high_score = 0
        self.music_available = False
        self.music_sound: Optional[pygame.mixer.Sound] = None
        self.music_channel: Optional[pygame.mixer.Channel] = None
        self._setup_audio()
        self.reset()

    def reset(self) -> None:
        self.bird = Bird(WINDOW_WIDTH // 4, WINDOW_HEIGHT // 2)
        self.base = Base(PLAYABLE_HEIGHT, PIPE_SPEED)
        self.pipes: List[Pipe] = []
        self.spawn_pipe(initial=True)
        self.score = 0
        self.state = "start"
        if self.music_sound and (self.music_channel is None or not self.music_channel.get_busy()):
            try:
                channel = self.music_sound.play(loops=-1)
            except pygame.error:
                self.music_sound = None
                self.music_available = False
                self.music_channel = None
            else:
                if channel is not None:
                    channel.set_volume(0.35)
                    self.music_channel = channel
                    self.music_available = True

    def spawn_pipe(self, *, initial: bool = False) -> None:
        min_center = PIPE_GAP // 2 + 60
        max_center = PLAYABLE_HEIGHT - PIPE_GAP // 2 - 60
        gap_center = random.randint(min_center, max_center)
        x = WINDOW_WIDTH + (0 if initial else PIPE_DISTANCE)
        self.pipes.append(Pipe(x=x, gap_center=gap_center))

    def run(self) -> None:
        while True:
            self.clock.tick(FPS)
            self.handle_events()
            self.update()
            self.draw()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_UP):
                    if self.state == "start":
                        self.state = "playing"
                        self.bird.jump()
                    elif self.state == "playing":
                        self.bird.jump()
                    elif self.state == "game_over":
                        self.reset()

    def update(self) -> None:
        if self.state == "start":
            self.base.move()
            self.bird.update_animation()
            return

        if self.state == "game_over":
            self.base.move()
            return

        self.bird.move()
        self.bird.update_animation()
        self.base.move()

        remove_pipes = []
        add_pipe = False

        for pipe in self.pipes:
            pipe.move()
            if pipe.collide(self.bird):
                self.state = "game_over"
                self.high_score = max(self.high_score, self.score)
            if pipe.top_rect.right < self.bird.x and not hasattr(pipe, "passed"):
                setattr(pipe, "passed", True)
                add_pipe = True
            if pipe.top_rect.right < -pipe.width:
                remove_pipes.append(pipe)

        for pipe in remove_pipes:
            self.pipes.remove(pipe)

        if add_pipe:
            self.score += 1
            self.spawn_pipe()

        if self.bird.y >= PLAYABLE_HEIGHT - self.bird.height // 2:
            self.state = "game_over"
            self.high_score = max(self.high_score, self.score)

        if self.bird.y < 0:
            self.bird.y = 0
            self.bird.velocity = 0

    def draw_background(self) -> None:
        self.window.blit(self.background, (0, 0))

    def draw(self) -> None:
        self.draw_background()

        for pipe in self.pipes:
            pipe.draw(self.window)

        self.base.draw(self.window)
        self.bird.draw(self.window)

        if self.state == "start":
            self.draw_start_screen()
        elif self.state == "game_over":
            self.draw_game_over()
        else:
            self.draw_score()

        pygame.display.flip()

    def _setup_audio(self) -> None:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2)
        except pygame.error:
            return

        sound = self._generate_background_music()
        if sound is None:
            return

        try:
            channel = sound.play(loops=-1)
        except pygame.error:
            channel = None

        self.music_sound = sound
        if channel is not None:
            channel.set_volume(0.35)
            self.music_channel = channel
            self.music_available = True

    def _generate_background_music(self) -> Optional[pygame.mixer.Sound]:
        if not pygame.mixer.get_init():
            return None

        init_args = pygame.mixer.get_init()
        if init_args is None:
            return None
        sample_rate = init_args[0]

        tempo = 120  # beats per minute
        seconds_per_beat = 60.0 / tempo
        beat_resolution = 2  # subdivide beats into eighth-notes
        samples_per_subbeat = max(1, int(sample_rate * seconds_per_beat / beat_resolution))

        chords = [
            ([60, 64, 67], 8),  # C major
            ([57, 60, 64], 8),  # A minor
            ([62, 65, 69], 8),  # D minor
            ([55, 59, 62], 8),  # G major
        ]

        melody = [60, 62, 64, 65, 67, 69, 71, 72]

        def midi_to_freq(note: int) -> float:
            return 440.0 * 2 ** ((note - 69) / 12)

        audio = array("h")
        sample_index = 0
        melody_step = 0

        for chord_notes, subbeats in chords:
            for subbeat in range(subbeats):
                chord_freqs = [midi_to_freq(note) for note in chord_notes]
                melody_note = melody[melody_step % len(melody)]
                melody_freq = midi_to_freq(melody_note)

                for _ in range(samples_per_subbeat):
                    t = sample_index / sample_rate
                    chord_sample = sum(math.sin(2 * math.pi * freq * t) for freq in chord_freqs)
                    melody_sample = math.sin(2 * math.pi * melody_freq * t)
                    wobble = math.sin(2 * math.pi * 5 * t)
                    sample_value = 0.18 * chord_sample + 0.12 * melody_sample + 0.03 * wobble
                    sample_value = max(-1.0, min(1.0, sample_value))
                    int_sample = int(sample_value * 32767)
                    audio.append(int_sample)
                    audio.append(int_sample)
                    sample_index += 1

                melody_step += 1

        if not audio:
            return None

        audio_bytes = audio.tobytes()
        try:
            return pygame.mixer.Sound(buffer=audio_bytes)
        except pygame.error:
            return None

    def _create_background(self) -> pygame.Surface:
        gradient_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        for y in range(WINDOW_HEIGHT):
            color_ratio = y / WINDOW_HEIGHT
            r = int(SKY_BLUE[0] * (1 - color_ratio) + DEEP_BLUE[0] * color_ratio)
            g = int(SKY_BLUE[1] * (1 - color_ratio) + DEEP_BLUE[1] * color_ratio)
            b = int(SKY_BLUE[2] * (1 - color_ratio) + DEEP_BLUE[2] * color_ratio)
            pygame.draw.line(gradient_surface, (r, g, b), (0, y), (WINDOW_WIDTH, y))
        return gradient_surface

    def draw_start_screen(self) -> None:
        title = self.font_large.render("Flappy Bird", True, WHITE)
        instruction = self.font_small.render("Press Space to fly", True, WHITE)
        rect = title.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3))
        instruction_rect = instruction.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3 + 60))
        self.window.blit(title, rect)
        self.window.blit(instruction, instruction_rect)

    def draw_score(self) -> None:
        score_surface = self.font_large.render(str(self.score), True, WHITE)
        rect = score_surface.get_rect(center=(WINDOW_WIDTH // 2, 60))
        self.window.blit(score_surface, rect)

    def draw_game_over(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        self.window.blit(overlay, (0, 0))

        title = self.font_large.render("Game Over", True, WHITE)
        score_text = self.font_small.render(f"Score: {self.score}", True, WHITE)
        high_score_text = self.font_small.render(f"Best: {self.high_score}", True, WHITE)
        restart_text = self.font_small.render("Press Space to restart", True, WHITE)

        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3))
        score_rect = score_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3 + 50))
        best_rect = high_score_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3 + 90))
        restart_rect = restart_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3 + 140))

        self.window.blit(title, title_rect)
        self.window.blit(score_text, score_rect)
        self.window.blit(high_score_text, best_rect)
        self.window.blit(restart_text, restart_rect)


def main() -> None:
    pygame.init()
    try:
        Game().run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
