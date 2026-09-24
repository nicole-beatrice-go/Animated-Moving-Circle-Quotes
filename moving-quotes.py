#!/usr/bi.n/env python

import os
import os.path
import sys
import pygame
import math
from pygame.locals import *
import time
import random
from mpi4py import MPI

pygame.font.init()
font = pygame.font.SysFont('Arial', 60, bold=True)

def check_collision(ball1, ball2):
    dx = ball1.x - ball2.x
    dy = ball1.y - ball2.y
    distance = (dx**2 + dy**2)**0.5
    return distance < (ball1.size + ball2.size)

def resolve_collision(ball1, ball2):
    dx = ball1.x - ball2.x
    dy = ball1.y - ball2.y
    distance = (dx**2 + dy**2)**0.5
    overlap = (ball1.size + ball2.size) - distance
    if distance == 0:
        dx, dy = 1, 0
        distance = 1
    #nx = dx / distance
    #ny = dy / distance
    #dvx = ball1.v_x - ball2.v_x
    #dvy = ball1.v_y - ball2.v_y
    #vn = dvx * nx + dvy * ny
    #if vn > 0:
    #    return
    #ball1.v_x -= vn * nx
    #ball1.v_y -= vn * ny
    #ball2.v_x -= vn * nx
    #ball2.v_y -= vn * ny
    #if abs(dx) > abs(dy):
    ball1.x += (dx / distance) * (overlap / 2)
    ball1.y += (dy / distance) * (overlap / 2)
    ball2.x -= (dx / distance) * (overlap / 2)
    ball2.y -= (dy / distance) * (overlap / 2)
    ball1.v_x *= -1
    ball2.v_x *= -1
    #else:
    ball1.v_y *= -1
    ball2.v_y *= -1 

def wrap_text(text, font, max_width):
    words = text.split()
    lines = []
    current_line = ""
    for w in words:
        test_line = current_line + (" " if current_line else "") + w
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = w
    if current_line:
        lines.append(current_line)
    return lines

# simple thing that can move around
class Thing:
    x = 0 # x and y are relative to the whole coord system
    y = 0
    speed = 1
    universe_size = (0,0)
    color = (255, 0, 0)
    v_x = 0
    v_y = 0
    current_text = ""
    quote_list = []
    mood = "neutral"

    def __init__(self, universe_size, x, y, color, size, speed, v_x, v_y, current_text, quote_list, mood):
        self.universe_size = universe_size
        self.x = x 
        self.y = y
        self.color = color
        self.size = size
        self.speed = speed
        self.v_x = v_x
        self.v_y = v_y
        self.current_text = ""
        self.quote_list = []
        self.mood = "neutral"

  #  def wrap_text(text, font, max_width):
   #     words = text.split()
    #    lines = []
     #   current_line = ""
      #  for w in words:
       #     test_line = current_line + (" " if current_line else "") + w
        #    if font.size(test_line)[0] <= max_width:
         #       current_line = test_line
          #  else:
           #     lines.append(current_line)
            #    current_line = w
      #  if current_line:
      #      lines.append(current_line)
      #  return lines
    def draw(self, screen, offset_x, offset_y):
        pygame.draw.circle(screen, self.color, \
               (int(self.x-offset_x),int(self.y-offset_y)), int(self.size), 0)
        max_width = int(self.size)
        lines = wrap_text(self.current_text, font, max_width)
        total_height = len(lines) * font.get_linesize()
        start_y = self.y - total_height // 2 - offset_y
        for i, line in enumerate(lines):
            shadow_surface = font.render(line, True, (0, 0, 0))
            shadow_rect = shadow_surface.get_rect(center=(int(self.x - offset_x + 2), int(start_y + i*font.get_linesize() + 2)))
            screen.blit(shadow_surface, shadow_rect)
            text_surface = font.render(line, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(int(self.x - offset_x), int(start_y + i*font.get_linesize())))
            screen.blit(text_surface, text_rect)

    # tell_me is here for testing
    def tell_me(self):
        print(rank, self.x, self.y, self.color, self.size, self.speed)

    def set_color(self, color):
        self.color = color

    def get_color(self):
        return self.color

    def set_speed(self, speed):
        self.speed = speed

    def get_speed(self):
        return self.speed

    def set_size(self, size):
        self.size = size

    def set_x(self, x):
        self.x = x

    def set_y (self, y):
        self.y = y

    def get_size(self, size):
        return size

    def up(self):
        self.y = self.y - self.speed

    def down(self):
        self.y = self.y + self.speed
          
    def right(self):
        self.x = self.x + self.speed
          
    def left(self):
        self.x = self.x - self.speed

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# set window position
os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"
# get this display
os.environ['DISPLAY'] = ':0.0'
# with caffeine installed (sudo apt install caffeine) we can wake the screen
#os.system('caffeinate sleep 1') # passes caffeinate out to shell to wake screensaver 

# init clock and display
clock = pygame.time.Clock()
pygame.display.init()
pygame.mouse.set_visible(False)

# get the screen hight and width
disp_info = pygame.display.Info()
width = disp_info.current_w
height = disp_info.current_h
screen_size = (width,height)
universe_size = (width*2, height*2)

things = []
colors = [
    (255, 255, 255),
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (0, 255, 255),
    (255, 0, 255),
    (255, 255, 0)
]
quotes_by_color = {
    (255, 255, 255): [
	{"text": "I could be better at...", "mood": "sad"},
	{"text": "What's the perfect decision for...", "mood": "sad"},
	{"text": "I'm trying my best and will improve on...", "mood": "happy"},
	{"text": "This best decision right now for me is...", "mood": "happy"},
    ],
    (255, 0, 0): [
	{"text": "Am I on the right timeline for...", "mood": "sad"},
	{"text": "What will I do after...", "mood": "sad"},
	{"text": "I'll figure it out and enjoy processing...", "mood": "happy"},
	{"text": "It'll be okay even if...", "mood": "happy"},
    ],
    (0, 255, 0): [
	{"text": "There's no point in trying to...", "mood": "sad"},
	{"text": "I won't be capable of becoming a...", "mood": "sad"},
	{"text": "I'm capable of becoming a...", "mood": "happy"},
	{"text": "I want to try...", "mood": "happy"},
    ],
    (0, 0, 255): [
	{"text": "I need to do...", "mood": "sad"},
	{"text": "I must accomplish...", "mood": "sad"},
	{"text": "I can rest because...", "mood": "happy"},
	{"text": "An accomplishment I can celebrate is...", "mood": "happy"},
    ],
    (0, 255, 255): [
	{"text": "I should have...", "mood": "sad"},
	{"text": "I shouldn't have...", "mood": "sad"},
	{"text": "I can't change that...", "mood": "happy"},
	{"text": "I can recover from...", "mood": "happy"},
	{"text": "I understand why I chose to...", "mood": "happy"},
    ],
    (255, 0, 255): [
	{"text": "What if the best will happen...", "mood": "sad"},
	{"text": "What if the worst will happen...", "mood": "happy"},
	{"text": "Was I weird in that interaction...", "mood": "sad"},
	{"text": "We had a great conversation...", "mood": "happy"}, 
    ],
    (255, 255, 0): [
	{"text": "I'll miss my friends...", "mood": "sad"},
	{"text": "It won't be the same...", "mood": "sad"},
	{"text": "Why'd this conflict happen...", "mood": "sad"},
	{"text": "Who am I without them...", "mood": "sad"},
	{"text": "I'm thankful for these memories...", "mood": "happy"},
	{"text": "We'll see each other again...", "mood": "happy"},
	{"text": "It's okay we disagree...", "mood": "happy"},
	{"text": "It's okay we're drifting...", "mood": "happy"},
    ]
}

# make a thing
thing = Thing(universe_size, int(width/2), int(height/2), (0,0,0), 0, 0, 0, 0, 0, [], "neutral")

# make another thing
thing1 = Thing(universe_size, int(width/2), int(height/2), (0,0,0), 0, 0, 0, 0, 0, [], "neutral")


# make a third thing
thing2 = Thing(universe_size, int(width/2), int(height/2), (0,0,0), 0, 0, 0, 0, 0, [], "neutral")

things.append(thing)
things.append(thing1)
things.append(thing2)

for thing in things:
    thing.x = random.randint(0, universe_size[0] - size//2)
    thing.y = random.randint(0, universe_size[1] - size//2)
    thing.size = random.randint(200, 250)
    thing.color = random.choice(colors)
    thing.speed = random.randint(50, 60)
    thing.v_x = thing.speed * math.cos(math.radians(random.uniform(20, 70))) * random.choice([-1,1])
    thing.v_y = thing.speed * math.sin(math.radians(random.uniform(20,70))) * random.choice([-1,1])
    

# set up the screen
screen = pygame.display.set_mode((screen_size), pygame.NOFRAME)

# this is a function that will run the red dot
# def run_it(thing, thing1, thing2):
    #calculate rectangle steps and dimensions
    #size = random.randint(30, 60)

    
    
    #color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    #color2 = (random.randint(0, 255), random.randint(0,255), random.randint(0, 255))
    #color3 = (random.randint(0, 255), random.randint(0,255), random.randint(0,255))
    #xpos1 = random.randint(0, width - size/2)
    #xpos2 = random.randint(0, width - size/2)
    #xpos3 = random.randint(0, width - size/2)
    #ypos1 = random.randint(0, height - size/2)
    #ypos2 = random.randint(0, height - size/2)
    #ypos3 = random.randint(0, height - size/2)
    #speed = random.randint(15, 60)
    #speed2 = random.randint(15, 60)
    #speed3 = random.randint(15,60)
    #angle = random.uniform(20,70)
    #angle1 = random.uniform(20,70)
    #angle2 = random.uniform(20, 70)
    #radian = math.radians(angle)
    #radian1 = math.radians(angle1)
    #radian2 = math.radians(angle2)
    #v_x = speed * math.cos(radian) * random.choice([-1, 1])
    #v_y = speed * math.sin(radian) * random.choice([-1, 1])
    #v1_x = speed1 * math.cos(radian1) * random.choice([-1, 1]) 
    #v1_y = speed1 * math.sin(radian1) * random.choice([-1, 1])
    #v2_x = speed2 * math.cos(radian2) * random.choice([-1, 1])
    #v2_y = speed2 * math.sin(radian2) * random.choice([-1, 1])
    #thing.set_color(color) # the only difference is a new color per run 
    #thing.set_speed(speed)
    #thing.set_size(size)
    #thing.set_x(xpos1)
    #thing.set_y(ypos1)
    #thing2.set_color(color2)
    #thing2.set_speed(speed2)
    #thing2.set_x(xpos2)
    #thing2.set_y(ypos2)
    #thing2.set_size(size)
    #thing3.set_color(color3)
    #thing3.set_speed(speed3)
    #thing3.set_size(size)
    #thing3.set_x(xpos3)
    #thing3.set_y(ypos3)
    
    #calculate rectangle steps and dimensions
    # xer = int(width / thing.get_speed())
    # yer = int(height / thing.get_speed())
    # steps = 
    # animate
    # for k in range(steps): # for drawing a screen sized rectangle
# comm.Barrier() # synchronization between all nodes
       # if rank == 0:
        #    screen.fill((255, 255, 255))
         #   if k < xer:
          #      thing.right()
           #     thing1.right()
            #    thing2.right()
           # elif k < (xer + yer):
            #    thing.down()
           #     thing1.down()
          #      thing2.down()
          #  elif k < (xer * 2 + yer):
          #       thing.left()
         #        thing1.left()
         #        thing2.left()
         #   else: # k < (xer + yer) * 2
         #        thing.up()
         #        thing1.up()
         #        thing2.up()
         #   comm.bcast(thing, root=0)
            #thing.tell_me()
        #    thing.draw(screen, 0, 0)
      #  elif rank == 1:
      #      screen.fill((220,220,220))
      #      thing = comm.bcast(thing, root=0)
            #thing.tell_me()
      #      thing.draw(screen, width, 0)
      #  elif rank == 2:
      #      screen.fill((200,200,200))
      #      thing = comm.bcast(thing, root=0)
      #      thing.draw(screen, 0, height)
      #  else:      #rank == 3:
      #      screen.fill((180, 180, 180))
      #      thing = comm.bcast(thing, root=0)
      #      thing.draw(screen, width, height)
      #  pygame.display.update()    
      #  clock.tick(30)

while True:
    comm.Barrier()
    # if rank == 0:
    screen.fill((0, 0, 0))
    #for thing in [thing, thing1, thing2]:
    if rank == 0:
        #if rank == 0:
        #for thing in [thing, thing1, thing2]:
        thing.x += thing.v_x
        thing.y += thing.v_y
        if thing.x <= 0 or thing.x + thing.size >= universe_size[0]:
            thing.v_x *= -1
            thing.color = random.choice(colors)

            thing.quote_list = quotes_by_color[thing.color]

            #thing.quote_i = (thing.quote_i + 1) % len(thing.quote_list)

            current = random.choice(thing.quote_list)
            thing.current_text = current["text"]
            thing.mood = current["mood"]

            if thing.x <= 0:
                thing.x = 0
            else:
                thing.x = universe_size[0] - thing.size

            if thing.mood == "sad":
                thing.size = 300 
                thing.v_x *= 1.25
                thing.v_y *= 1.25
            else:
                thing.size = 250
                thing.v_x *= 0.75
                thing.v_y *= 0.75

        if thing.y <= 0 or thing.y + thing.size >= universe_size[1]:
            thing.v_y *= -1
            thing.color = random.choice(colors)

            thing.quote_list = quotes_by_color[thing.color]

            #thing.quote_i = (thing.quote_i + 1) % len(thing.quote_list)

            current = random.choice(thing.quote_list)
            thing.current_text = current["text"]
            thing.mood = current["mood"]

            if thing.y <= 0:
                thing.y = 0
            else:
                thing.y = universe_size[1] - thing.size

            if thing.mood == "sad":
                thing.size = 300
                thing.v_x *= 1.25
                thing.v_y *= 1.25
            else:
                thing.size = 250
                thing.v_x *= 0.75
                thing.v_y *= 0.75
        thing1.x += thing1.v_x
        thing1.y += thing1.v_y
        if thing1.x <= 0 or thing1.x + thing1.size >= universe_size[0]:
            thing1.v_x *= -1
            thing1.color = random.choice(colors)

            thing1.quote_list = quotes_by_color[thing1.color]

            # thing1.quote_i = (thing1.quote_i + 1) % len(thing1.quote_list)

            current = random.choice(thing1.quote_list)
            thing1.current_text = current["text"]
            thing1.mood = current["mood"]

            if thing1.x <= 0:
                thing1.x = 0
            else:
                thing1.x = universe_size[0] - thing1.size

            if thing1.mood == "sad":
                thing1.size = 300
                thing1.v_x *= 1.25
                thing1.v_y *= 1.25
            else:
                thing1.size = 250
                thing1.v_x *= 0.75
                thing1.v_y *= 0.75
        if thing1.y <= 0 or thing1.y + thing1.size >= universe_size[1]:
            thing1.v_y *= -1
            thing1.color = random.choice(colors)

            thing1.quote_list = quotes_by_color[thing1.color]

            # thing1.quote_i = (thing1.quote_i + 1) % len(thing1.quote_list)

            current = random.choice(thing1.quote_list)
            thing1.current_text = current["text"]
            thing1.mood = current["mood"]

            if thing1.y <= 0:
                thing1.y = 0
            else:
                thing1.y = universe_size[1] - thing1.size

            if thing1.mood == "sad":
                thing1.size = 300
                thing1.v_x *= 1.25
                thing1.v_y *= 1.25
            else:
                thing1.size = 250
                thing1.v_x *= 0.75
                thing1.v_y *=0.75
        thing2.x += thing2.v_x
        thing2.y += thing2.v_y
        if thing2.x <= 0 or thing2.x + thing2.size >= universe_size[0]:
            thing2.v_x *= -1
            thing2.color = random.choice(colors)

            thing2.quote_list = quotes_by_color[thing2.color]

            #thing2.quote_i = random

            current = random.choice(thing2.quote_list)
            thing2.current_text = current["text"]
            thing2.mood = current["mood"]

            if thing2.x <= 0:
                thing2.x = 0
            else:
                thing2.x = universe_size[0] - thing2.size

            if thing2.mood == "sad":
                thing2.size = 300
                thing2.v_x *= 1.25
                thing2.v_y *= 1.25
            else:
                thing2.size = 250
                thing2.v_x *= 0.75
                thing2.v_y *= 0.75
        if thing2.y <= 0 or thing2.y + thing2.size >= universe_size[1]:
            thing2.v_y *= -1
            thing2.color = random.choice(colors)

            thing2.quote_list= quotes_by_color[thing2.color]

            #thing2.quote_i = (thing2.quote_i + 1) % len(thing2.quote_list)

            current = random.choice(thing2.quote_list)
            thing2.current_text = current["text"]
            thing2.mood = current["mood"]

            if thing2.y <= 0:
                thing2.y = 0
            else:
                thing2.y = universe_size[1] - thing2.size

            if thing2.mood == "sad":
                thing2.size = 300
                thing2.v_x *= 1.25
                thing2.v_y *= 1.25
            else:
                thing2.size = 250
                thing2.v_x *= 0.75
                thing2.v_y *= 0.75

        if check_collision(thing, thing1):
            resolve_collision(thing, thing1)
        if check_collision(thing, thing2):
            resolve_collision(thing, thing2)
        if check_collision(thing1, thing2):
            resolve_collision(thing1, thing2)

        thing = comm.bcast(thing, root=0)
        thing1 = comm.bcast(thing1, root=0)
        thing2 = comm.bcast(thing2, root=0)
        thing.draw(screen, 0, 0)
        thing1.draw(screen, 0, 0)
        thing2.draw(screen, 0, 0)
    #else:
     #   things = comm.bcast(None, root=0)
        #thing.draw(screen, width, 0)
    elif rank == 1:
        screen.fill((0, 0, 0))
        thing = comm.bcast(thing, root=0)
        thing1 = comm.bcast(thing1, root=0)
        thing2 = comm.bcast(thing2, root=0)
        thing.draw(screen, width, 0)
        thing1.draw(screen, width, 0)
        thing2.draw(screen, width, 0)
            
    elif rank == 2:
        screen.fill((0, 0, 0))
        thing = comm.bcast(thing, root=0)
        thing1 = comm.bcast(thing1, root=0)
        thing2 = comm.bcast(thing2, root=0)
        thing.draw(screen, 0, height)
        thing1.draw(screen, 0, height)
        thing2.draw(screen, 0, height)
    else:
        screen.fill((0,0,0))
        thing = comm.bcast(thing, root=0)
        thing1 = comm.bcast(thing1, root=0)
        thing2 = comm.bcast(thing2, root=0)
        thing.draw(screen, width, height)
        thing1.draw(screen, width, height)
        thing2.draw(screen, width, height)
    #offset_x = (rank % 2) * width
    #offset_y = (rank // 2) * height
    #for thing in things:
     #   thing.draw(screen, offset_x, offset_Y)
          #  thing.draw(screen, width, height)
    pygame.display.update()
    clock.tick(30)

