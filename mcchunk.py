import pygame
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
from collections import defaultdict

from block import *

class Chunk:
    def __init__(self, chunk_x, chunk_z, size=16):
        self.chunk_x = chunk_x
        self.chunk_z = chunk_z
        self.size = size
        self.blocks = {}
        self.display_list = None
        self.needs_update = True
        self.is_compiled = False
        self.generate_terrain()
        
    def generate_terrain(self):
        # Simpler, faster terrain generation
        for x in range(self.size):
            for z in range(self.size):
                world_x = self.chunk_x * self.size + x
                world_z = self.chunk_z * self.size + z
                
                # Simple height with less computation
                height = int(10 + 3 * math.sin(world_x * 0.2) + 2 * math.cos(world_z * 0.2))
                height = max(1, min(15, height))
                
                # Generate terrain layers
                for y in range(max(0, height - 2), height + 1):
                    block_type = 1  # Grass/dirt
                    self.blocks[(world_x, y, world_z)] = Block(world_x, y, world_z, block_type)
                
                # Generate trees on top of terrain (2% chance)
                if random.random() < 0.02:
                    self.generate_tree(world_x, height + 1, world_z)
    
    def generate_tree(self, x, base_y, z):
        """Generate a simple tree structure"""
        # Tree trunk height (3-5 blocks)
        trunk_height = random.randint(3, 5)
        
        # Generate trunk
        for y in range(base_y, base_y + trunk_height):
            self.blocks[(x, y, z)] = Block(x, y, z, 4)  # Brown trunk blocks
        
        # Generate leaves (simple cross pattern around top of trunk)
        leaf_y = base_y + trunk_height
        leaf_positions = [
            # Center leaves
            (x, leaf_y, z),
            (x, leaf_y + 1, z),
            # Cardinal directions
            (x + 1, leaf_y, z), (x - 1, leaf_y, z),
            (x, leaf_y, z + 1), (x, leaf_y, z - 1),
            # Diagonals
            (x + 1, leaf_y, z + 1), (x - 1, leaf_y, z + 1),
            (x + 1, leaf_y, z - 1), (x - 1, leaf_y, z - 1),
            # Some upper leaves
            (x, leaf_y + 1, z + 1), (x, leaf_y + 1, z - 1),
            (x + 1, leaf_y + 1, z), (x - 1, leaf_y + 1, z),
        ]
        
        # Add leaf blocks (with some randomness)
        for leaf_x, leaf_y_pos, leaf_z in leaf_positions:
            if random.random() < 0.8:  # 80% chance for each leaf block
                self.blocks[(leaf_x, leaf_y_pos, leaf_z)] = Block(leaf_x, leaf_y_pos, leaf_z, 2)
    
    def get_block(self, x, y, z):
        return self.blocks.get((x, y, z))
    
    def add_block(self, x, y, z, block_type=1):
        self.blocks[(x, y, z)] = Block(x, y, z, block_type)
        self.needs_update = True
    
    def remove_block(self, x, y, z):
        if (x, y, z) in self.blocks:
            del self.blocks[(x, y, z)]
            self.needs_update = True
            self.is_compiled = False
    
    def compile_chunk(self, world):
        """Compile the chunk into a display list for efficient rendering"""
        if self.display_list is not None:
            glDeleteLists(self.display_list, 1)
        
        self.display_list = glGenLists(1)
        glNewList(self.display_list, GL_COMPILE)
        
        # Render all blocks in this chunk
        for block in self.blocks.values():
            if world.is_block_visible(block.x, block.y, block.z):
                world.draw_cube_for_chunk(block.x, block.y, block.z, block.type, self)
        
        glEndList()
        self.needs_update = False
        self.is_compiled = True
    
    def render(self):
        """Render the compiled chunk"""
        if self.display_list is not None and self.is_compiled:
            glCallList(self.display_list)
    
    def cleanup(self):
        """Clean up OpenGL resources"""
        if self.display_list is not None:
            glDeleteLists(self.display_list, 1)
            self.display_list = None
            self.is_compiled = False
