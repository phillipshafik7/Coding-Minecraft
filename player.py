import pygame
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
from collections import defaultdict

class Player:
    def __init__(self):
        self.width = 0.6
        self.height = 1.8
        self.eye_height = 1.62  # Eye level from feet (standard Minecraft)
        
        # Body part dimensions (in blocks)
        self.head_size = 0.5
        self.body_width = 0.4
        self.body_height = 0.75
        self.arm_width = 0.2
        self.arm_height = 0.75
        self.leg_width = 0.2
        self.leg_height = 0.75
        
        # Animation state
        self.walk_animation = 0.0
        self.is_walking = False
        
        
    def update_animation(self, is_moving, dt):
        """Update walking animation"""
        self.is_walking = is_moving
        if is_moving:
            self.walk_animation += dt * 5.0  # Animation speed
        else:
            self.walk_animation = 0.0
    
    def draw_cube_part(self, x, y, z, width, height, depth, color):
        """Draw a cube part of the player with specified dimensions"""
        # Adjust coordinates to center the part
        x -= width / 2
        z -= depth / 2
        
        glColor3f(*color)
        
        # Define vertices for the cube
        vertices = [
            [x, y, z], [x + width, y, z], [x + width, y + height, z], [x, y + height, z],  # Front
            [x, y, z + depth], [x + width, y, z + depth], [x + width, y + height, z + depth], [x, y + height, z + depth]  # Back
        ]
        
        # Define faces
        faces = [
            [0, 1, 2, 3],  # Front
            [4, 7, 6, 5],  # Back
            [0, 4, 5, 1],  # Bottom
            [2, 6, 7, 3],  # Top
            [0, 3, 7, 4],  # Left
            [1, 5, 6, 2]   # Right
        ]
        
        # Draw faces
        glBegin(GL_QUADS)
        for face in faces:
            for vertex in face:
                glVertex3f(*vertices[vertex])
        glEnd()
    
    def render(self, x, y, z, yaw):
        """Render the player model at the given position"""
        glPushMatrix()
        
        # Move to player position
        glTranslatef(x, y, z)
        
        # Rotate player to face the right direction
        glRotatef(-yaw, 0, 1, 0)
        
        # Calculate animation values
        arm_swing = math.sin(self.walk_animation) * 30 if self.is_walking else 0
        leg_swing = math.sin(self.walk_animation) * 45 if self.is_walking else 0
        
        # Draw legs
        leg_y = self.leg_height / 2

        # Left leg
        glPushMatrix()
        glTranslatef(-self.leg_width/2, leg_y, 0)
        glRotatef(-leg_swing, 1, 0, 0)
        glTranslatef(0, -self.leg_height/2, 0)
        self.draw_cube_part(0, 0, 0, self.leg_width, self.leg_height, self.leg_width, (0.0, 0.0, 0.5))  # Dark blue pants
        glPopMatrix()
        
        # Right leg
        glPushMatrix()
        glTranslatef(self.leg_width/2, leg_y, 0)
        glRotatef(leg_swing, 1, 0, 0)
        glTranslatef(0, -self.leg_height/2, 0)
        self.draw_cube_part(0, 0, 0, self.leg_width, self.leg_height, self.leg_width, (0.0, 0.0, 0.5))
        glPopMatrix()

        # Draw arms
        arm_y = self.body_height - self.arm_height / 2
        
        # Left arm
        glPushMatrix()
        glTranslatef(-self.body_width/2 - self.arm_width/2, arm_y + self.arm_height/2, 0)
        glRotatef(arm_swing, 1, 0, 0)
        glTranslatef(0, -self.arm_height/2, 0)
        self.draw_cube_part(0, 0, 0, self.arm_width, self.arm_height, self.arm_width, (0.9, 0.7, 0.6))
        glPopMatrix()
        
        # Right arm
        glPushMatrix()
        glTranslatef(self.body_width/2 + self.arm_width/2, arm_y + self.arm_height/2, 0)
        glRotatef(-arm_swing, 1, 0, 0)
        glTranslatef(0, -self.arm_height/2, 0)
        self.draw_cube_part(0, 0, 0, self.arm_width, self.arm_height, self.arm_width, (0.9, 0.7, 0.6))
        glPopMatrix()

        # Draw body
        body_y = self.body_height / 2
        self.draw_cube_part(0, body_y, 0, self.body_width, self.body_height, self.body_width, (0.0, 0.5, 1.0))  # Blue shirt

        # Draw head
        head_y = self.body_height + self.head_size / 2
        self.draw_cube_part(0, head_y, 0, self.head_size, self.head_size, self.head_size, (0.9, 0.7, 0.6))  # Skin color
        
      
        glPopMatrix()
