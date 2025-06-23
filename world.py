import pygame
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
from collections import defaultdict

from mcchunk import *

class World:
    def __init__(self):
        self.chunks = {}
        self.render_distance = 4  # Render distance in chunks
        self.loaded_chunks = set()  # Track which chunks are currently loaded
        
    def get_chunk_coords(self, x, z):
        # Use consistent chunk size with Chunk class
        return int(x // 16), int(z // 16)
    
    def get_chunk(self, chunk_x, chunk_z):
        if (chunk_x, chunk_z) not in self.chunks:
            self.chunks[(chunk_x, chunk_z)] = Chunk(chunk_x, chunk_z)
        return self.chunks[(chunk_x, chunk_z)]
    
    def get_block(self, x, y, z):
        """Get block at world coordinates, handling chunk boundaries properly"""
        # Handle Y bounds
        if y < 0 or y > 255:
            return None
        
        chunk_x, chunk_z = self.get_chunk_coords(x, z)
        if (chunk_x, chunk_z) in self.chunks:
            chunk = self.chunks[(chunk_x, chunk_z)]
            return chunk.get_block(x, y, z)
        return None
    
    def add_block(self, x, y, z, block_type=1):
        chunk_x, chunk_z = self.get_chunk_coords(x, z)
        chunk = self.get_chunk(chunk_x, chunk_z)
        chunk.add_block(x, y, z, block_type)
        # Mark adjacent chunks for update if block is on chunk boundary
        self.mark_adjacent_chunks_for_update(x, y, z)
    
    def remove_block(self, x, y, z):
        chunk_x, chunk_z = self.get_chunk_coords(x, z)
        if (chunk_x, chunk_z) in self.chunks:
            chunk = self.chunks[(chunk_x, chunk_z)]
            chunk.remove_block(x, y, z)
            # Mark adjacent chunks for update if block is on chunk boundary
            self.mark_adjacent_chunks_for_update(x, y, z)
    
    def mark_adjacent_chunks_for_update(self, x, y, z):
        """Mark adjacent chunks for update when blocks change on chunk boundaries"""
        chunk_x, chunk_z = self.get_chunk_coords(x, z)
        local_x = x - (chunk_x * 16)
        local_z = z - (chunk_z * 16)
        
        # Check if block is on chunk boundary and mark adjacent chunks
        if local_x == 0 and (chunk_x - 1, chunk_z) in self.chunks:
            self.chunks[(chunk_x - 1, chunk_z)].needs_update = True
            self.chunks[(chunk_x - 1, chunk_z)].is_compiled = False
        if local_x == 15 and (chunk_x + 1, chunk_z) in self.chunks:
            self.chunks[(chunk_x + 1, chunk_z)].needs_update = True
            self.chunks[(chunk_x + 1, chunk_z)].is_compiled = False
        if local_z == 0 and (chunk_x, chunk_z - 1) in self.chunks:
            self.chunks[(chunk_x, chunk_z - 1)].needs_update = True
            self.chunks[(chunk_x, chunk_z - 1)].is_compiled = False
        if local_z == 15 and (chunk_x, chunk_z + 1) in self.chunks:
            self.chunks[(chunk_x, chunk_z + 1)].needs_update = True
            self.chunks[(chunk_x, chunk_z + 1)].is_compiled = False
    
    def is_block_visible(self, x, y, z):
        """Check if any face is visible (not surrounded by blocks)"""
        # Check if block exists
        if not self.get_block(x, y, z):
            return False
        
        # Check all 6 directions
        directions = [(0,1,0), (0,-1,0), (1,0,0), (-1,0,0), (0,0,1), (0,0,-1)]
        for dx, dy, dz in directions:
            if not self.get_block(x+dx, y+dy, z+dz):
                return True
        return False
    
    def get_visible_chunks(self, camera_x, camera_z):
        """Get chunks within render distance, sorted by proximity to player"""
        visible_chunks = []
        cam_chunk_x, cam_chunk_z = self.get_chunk_coords(camera_x, camera_z)
        
        # Collect chunks within render distance
        chunk_distances = []
        for dx in range(-self.render_distance, self.render_distance + 1):
            for dz in range(-self.render_distance, self.render_distance + 1):
                chunk_x = cam_chunk_x + dx
                chunk_z = cam_chunk_z + dz
                
                # Calculate distance from player to chunk center
                chunk_center_x = chunk_x * 16 + 8
                chunk_center_z = chunk_z * 16 + 8
                distance_sq = (chunk_center_x - camera_x) ** 2 + (chunk_center_z - camera_z) ** 2
                distance = math.sqrt(distance_sq)
                
                # Only include chunks within circular render distance
                if distance <= self.render_distance * 16:
                    if (chunk_x, chunk_z) not in self.chunks:
                        # Generate chunk on demand
                        self.get_chunk(chunk_x, chunk_z)
                    
                    chunk_distances.append((distance, self.chunks[(chunk_x, chunk_z)]))
        
        # Sort by distance (closest first)
        chunk_distances.sort(key=lambda x: x[0])
        visible_chunks = [chunk for distance, chunk in chunk_distances]
        
        # Update loaded chunks set
        self.loaded_chunks = {(chunk.chunk_x, chunk.chunk_z) for chunk in visible_chunks}
        
        # Clean up chunks that are too far away
        self.cleanup_distant_chunks(cam_chunk_x, cam_chunk_z)
        
        return visible_chunks
    
    def cleanup_distant_chunks(self, cam_chunk_x, cam_chunk_z):
        """Remove chunks that are too far from the player to save memory"""
        cleanup_distance = self.render_distance + 2
        chunks_to_remove = []
        
        for (chunk_x, chunk_z), chunk in self.chunks.items():
            distance = max(abs(chunk_x - cam_chunk_x), abs(chunk_z - cam_chunk_z))
            if distance > cleanup_distance:
                chunks_to_remove.append((chunk_x, chunk_z))
        
        for chunk_coords in chunks_to_remove:
            chunk = self.chunks[chunk_coords]
            chunk.cleanup()  # Clean up OpenGL resources
            del self.chunks[chunk_coords]
            if chunk_coords in self.loaded_chunks:
                self.loaded_chunks.remove(chunk_coords)
    
    def draw_cube_for_chunk(self, x, y, z, block_type, chunk):
        """Draw a cube for chunk compilation with proper face culling"""
        color = {
            1: (0.2, 0.8, 0.2),  # Grass green
            2: (0.1, 0.6, 0.1),  # Dark green (leaves)
            3: (0.6, 0.6, 0.6),  # Stone gray
            4: (0.4, 0.2, 0.1)   # Brown (tree trunk)
        }.get(block_type, (0.5, 0.5, 0.5))
        
        # Define cube vertices
        vertices = [
            [x,   y,   z  ],  # 0: front-bottom-left
            [x+1, y,   z  ],  # 1: front-bottom-right
            [x+1, y+1, z  ],  # 2: front-top-right
            [x,   y+1, z  ],  # 3: front-top-left
            [x,   y,   z+1],  # 4: back-bottom-left
            [x+1, y,   z+1],  # 5: back-bottom-right
            [x+1, y+1, z+1],  # 6: back-top-right
            [x,   y+1, z+1]   # 7: back-top-left
        ]
        
        # Define faces with correct winding order
        faces = [
            # Face indices, direction offset, normal, brightness
            ([0, 3, 2, 1], (0, 0, -1), (0, 0, -1), 0.8),   # Front face
            ([5, 6, 7, 4], (0, 0, 1),  (0, 0, 1),  0.8),   # Back face
            ([0, 1, 5, 4], (0, -1, 0), (0, -1, 0), 0.6),   # Bottom face
            ([3, 7, 6, 2], (0, 1, 0),  (0, 1, 0),  1.0),   # Top face
            ([0, 4, 7, 3], (-1, 0, 0), (-1, 0, 0), 0.7),   # Left face
            ([1, 2, 6, 5], (1, 0, 0),  (1, 0, 0),  0.9)    # Right face
        ]
        
        # Draw faces that are not occluded by adjacent blocks
        for face_indices, direction, normal, brightness in faces:
            dx, dy, dz = direction
            # Check adjacent block using proper world lookup
            adjacent_block = self.get_block(x + dx, y + dy, z + dz)
            
            # If there's no adjacent block in this direction, draw the face
            if not adjacent_block:
                glColor3f(color[0] * brightness, color[1] * brightness, color[2] * brightness)
                glNormal3f(*normal)
                
                glBegin(GL_QUADS)
                for idx in face_indices:
                    glVertex3f(*vertices[idx])
                glEnd()
