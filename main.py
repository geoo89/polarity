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
        if self.charge < 0:
            rect = Rect(0, 0, 64, 64)  # blue
        else:
            rect = Rect(64, 0, 64, 64)  # red
        pos = (int(self.pos[0]-32), int(self.pos[1]-32))
        surface.blit(Orb.sprite_image, pos, rect)


class Physics:
    COLOUMB_CONSTANT = 4000

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


class App:
    def __init__(self):
        self._running = True
        self._display_surf = None
        self.size = self.weight, self.height = 1280, 800
        self.FPS = 60
        self.level_list = self.get_level_list("levels/")
        self.current_level = 0
        self.physics = None

    def get_level_list(self, folder):
        level_list = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith(".ipe"):
                    level_list.append(os.path.join(root, file))
        return level_list

    def load_current_level(self):
        filename = self.level_list[self.current_level]
        level_json = ipe_to_json(filename, self.height)
        self.physics = Physics.from_json(level_json, self.FPS)

    def load_next_level(self):
        self.current_level = (self.current_level + 1) % len(self.level_list)
        self.load_current_level()
 
    def load_previous_level(self):
        self.current_level = (self.current_level - 1) % len(self.level_list)
        self.load_current_level()
 
    def on_init(self):
        pygame.init()
        pygame.time.Clock().tick(self.FPS)
        self._display_surf = pygame.display.set_mode(self.size, pygame.DOUBLEBUF)
        self._running = True
        Orb.sprite_image = pygame.image.load("images/orbs.png").convert()
        Orb.sprite_image.set_colorkey((0,0,0))
        self.load_current_level()
 
    def on_event(self, event):
        if event.type == pygame.QUIT:
            self._running = False
        elif event.type == KEYDOWN:
            self.on_key_down(event)

    def on_key_down(self, event):
        if event.key == K_ESCAPE:
            self._running = False
        elif event.key == K_r:
            self.load_current_level()
        elif event.key == K_UP:
            self.load_next_level()
        elif event.key == K_DOWN:
            self.load_previous_level()
        else:
            self.physics.flip_player_polarity()

    def on_loop(self):
        self.physics.simulate()
        if self.physics.win:
            self.load_next_level()

    def on_render(self):
        self._display_surf.fill((0, 0, 0))
        self.physics.render(self._display_surf)
        pygame.display.flip()

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
        self.on_cleanup()
 

if __name__ == "__main__" :
    theApp = App()
    theApp.on_execute()
