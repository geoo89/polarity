import json
import numpy as np
import os
import pygame
from pygame.locals import *

from ipe_to_json import ipe_to_json


class Orb:
    sprite_image = None

    def from_json(obj):
        return Orb(obj["pos"], obj["charge"], obj["mass"], obj["is_fixed"], obj["is_player"], obj["velocity"])

    def __init__(self, pos, charge, mass=1, is_fixed=True, is_player=False, velocity=(0.0, 0.0)):
        self.pos = np.array(pos, dtype=float)
        self.charge = float(charge)
        self.mass = float(mass)
        self.velocity = np.array(velocity, dtype=float)
        self.is_fixed = is_fixed
        self.is_player = is_player

    def render(self, surface):
        image_x = 0
        if self.charge > 0:
            image_x += 64   # blue -> red
        if self.mass < 2:
            image_x += 128  # decrease size
        if self.mass < 0.5:
            image_x += 128  # decrease size
        rect = Rect(image_x, 0, 64, 64)
        pos = (int(self.pos[0]-32), int(self.pos[1]-32))
        surface.blit(Orb.sprite_image, pos, rect)


class Physics:
    COLOUMB_CONSTANT = 10000

    def from_json(json, FPS):
        goals = json["orbs"]
        phy = Physics(FPS)
        for orb in json["orbs"]:
            phy.add_orb(Orb.from_json(orb))
        for goal in json["goals"]:
            phy.add_goal(Rect(*list(goal)))
        return phy

    def __init__(self, FPS):
        self.FPS = FPS
        self.orbs = []
        self.goals = []
        self.win = False

    def add_orb(self, orb):
        self.orbs.append(orb)

    def add_goal(self, goal):
        self.goals.append(goal)

    def flip_player_polarity(self):
        for orb in self.orbs:
            if orb.is_player:
                orb.charge *= -1

    def render(self, surface):
        for goal in self.goals:
            surface.fill((0, 96, 0), goal)
        for orb in self.orbs:
            orb.render(surface)

    def simulate(self):
        forces = []
        for orb1 in self.orbs:
            force = np.array([0.0, 0.0])
            for orb2 in self.orbs:
                if orb1 == orb2:
                    continue
                vector = orb2.pos - orb1.pos
                dist = np.linalg.norm(vector)
                force += Physics.COLOUMB_CONSTANT * orb1.charge * orb2.charge / dist**3 * (-vector)
            forces.append(force)
        for orb, force in zip(self.orbs, forces):
            orb.velocity += force / self.FPS
        for orb in self.orbs:
            if not orb.is_fixed:
                orb.pos += orb.velocity / self.FPS
        for orb in self.orbs:
            if orb.is_player:
                for goal in self.goals:
                    if goal.collidepoint(orb.pos):
                        self.win = True


class Level:
    def __init__(self, filename, title):
        self.filename = filename
        self.title = title

    def get_json(self, screen_height):
        return ipe_to_json(self.filename, screen_height)


class App:
    def __init__(self):
        self._running = True
        self._display_surf = None
        self.size = self.width, self.height = 1280, 800
        self.FPS = 60
        self.level_list = self.get_level_list("levels/")
        self.current_level = 0
        self.physics = None
        self.font = None
        self.state = 'preview'
        self.clock = pygame.time.Clock()
        self.physics_updates_per_frame = 8
        self.is_paused = False

    def get_level_list(self, folder):
        json_list = json.load(open("level_list.json"))
        level_list = []
        for level in json_list:
            level_list.append(Level(level["filename"], level["title"]))
        return level_list

    def preview_current_level(self):
        self.state = 'preview'

    def start_current_level(self):
        self.state = 'ingame'
        level = self.level_list[self.current_level]
        self.physics = Physics.from_json(level.get_json(self.height), self.FPS)

    def preview_next_level(self):
        self.current_level = (self.current_level + 1) % len(self.level_list)
        self.preview_current_level()
 
    def preview_previous_level(self):
        self.current_level = (self.current_level - 1) % len(self.level_list)
        self.preview_current_level()
 
    def on_init(self):
        pygame.init()
        self.font = pygame.font.SysFont(None, 96)
        self._display_surf = pygame.display.set_mode(self.size, pygame.DOUBLEBUF, 24)
        self._running = True
        Orb.sprite_image = pygame.image.load("images/orbs.png").convert()  # convert_alpha()
        Orb.sprite_image.set_colorkey((255, 0, 255))
        self.preview_current_level()
 
    def on_event(self, event):
        if event.type == pygame.QUIT:
            self._running = False
        elif event.type == KEYDOWN:
            self.on_key_down(event)

    def on_key_down(self, event):
        if event.key == K_ESCAPE:
            self._running = False
        elif event.key == K_r:
            self.start_current_level()
        elif event.key == K_p:
            self.is_paused = not self.is_paused
        elif event.key == K_UP:
            self.preview_next_level()
        elif event.key == K_DOWN:
            self.preview_previous_level()
        elif event.key not in [K_f, K_s]:  # f/s is fast/slow mode
            if self.state == 'preview':
                self.start_current_level()
            elif self.state == 'success':
                self.preview_next_level()
            else:
                self.physics.flip_player_polarity()

    def on_loop(self):
        if self.state == 'ingame' and not self.is_paused:
            physics_updates_per_frame = self.physics_updates_per_frame
            keys = pygame.key.get_pressed()
            if keys[pygame.K_f]:    # fast forward
                physics_updates_per_frame *= 4
            if keys[pygame.K_s]:    # slow mode
                physics_updates_per_frame //= 4
            for _ in range(physics_updates_per_frame):
                self.physics.simulate()
            if self.physics.win:
                self.state = 'success'

    def on_render(self):
        self._display_surf.fill((0, 0, 0))
        if self.state == 'preview':
            level = self.level_list[self.current_level]
            self.render_centered_text(f"Level {self.current_level}", 250)
            self.render_centered_text(f"{level.title}", 400)
        elif self.state == 'success':
            self.render_centered_text("Success!", 300)
        else:
            self.physics.render(self._display_surf)
        pygame.display.flip()

    def render_centered_text(self, text, ypos):
        img = self.font.render(text, True, (255, 255, 255))
        xpos = (self.width - img.get_width())//2
        self._display_surf.blit(img, (xpos, ypos))

    def render_text(self, text, pos):
        img = self.font.render(text, True, (255, 255, 255))
        self._display_surf.blit(img, pos)

    def on_cleanup(self):
        pygame.quit()
 
    def on_execute(self):
        if self.on_init() == False:
            self._running = False
 
        while self._running:
            for event in pygame.event.get():
                self.on_event(event)
            self.on_loop()
            self.on_render()
            self.clock.tick(self.FPS)
        self.on_cleanup()
 

if __name__ == "__main__" :
    theApp = App()
    theApp.on_execute()
