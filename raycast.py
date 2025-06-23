import pygame
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
from collections import defaultdict

class RaycastResult:
    def __init__(self, hit=False, block_pos=None, face_normal=None, hit_point=None, distance=None):
        self.hit = hit
        self.block_pos = block_pos  # (x, y, z) of the block that was hit
        self.face_normal = face_normal  # Normal vector of the face that was hit
        self.hit_point = hit_point  # Exact point where ray hit the block
        self.distance = distance  # Distance from ray origin to hit point

def raycast_precise(world, start_pos, direction, max_distance=5.0):
    """
    Precise raycast that returns detailed hit information including which face was hit.
    """
    start_x, start_y, start_z = start_pos
    dx, dy, dz = direction
    
    # Normalize direction vector
    length = math.sqrt(dx*dx + dy*dy + dz*dz)
    if length == 0:
        return RaycastResult()
    
    dx, dy, dz = dx/length, dy/length, dz/length
    
    # Use small steps for precision
    step_size = 0.01
    max_steps = int(max_distance / step_size)
    
    for i in range(max_steps):
        # Calculate current ray position
        t = i * step_size
        ray_x = start_x + dx * t
        ray_y = start_y + dy * t
        ray_z = start_z + dz * t
        
        # Get block coordinates at current ray position
        block_x = int(math.floor(ray_x))
        block_y = int(math.floor(ray_y))
        block_z = int(math.floor(ray_z))

        # Skip if block coordinates are out of reasonable bounds
        if abs(block_x) > 1000 or abs(block_y) > 256 or abs(block_z) > 1000:
            continue
        
        # Check if we hit a block
        if world.get_block(block_x, block_y, block_z):
            # Determine which face was hit
            face_normal = determine_hit_face(ray_x, ray_y, ray_z, block_x, block_y, block_z)
            
            return RaycastResult(
                hit=True,
                block_pos=(block_x, block_y, block_z),
                face_normal=face_normal,
                hit_point=(ray_x, ray_y, ray_z),
                distance=t
            )
    
    return RaycastResult()

def determine_hit_face(ray_x, ray_y, ray_z, block_x, block_y, block_z):
    """
    Determine which face of the block was hit based on the ray position within the block.
    """
    # Get position within the block (0 to 1)
    local_x = ray_x - block_x
    local_y = ray_y - block_y
    local_z = ray_z - block_z
    
    # Clamp to ensure we're within the block
    local_x = max(0, min(1, local_x))
    local_y = max(0, min(1, local_y))
    local_z = max(0, min(1, local_z))
    
    # Calculate distance to each face
    distances = {
        'west':  local_x,          # -X face (left)
        'east':  1 - local_x,      # +X face (right)
        'down':  local_y,          # -Y face (bottom)
        'up':    1 - local_y,      # +Y face (top)
        'north': local_z,          # -Z face (front)
        'south': 1 - local_z,      # +Z face (back)
    }
    
    # Find the face with minimum distance (closest to the edge)
    closest_face = min(distances.items(), key=lambda x: x[1])[0]
    
    # Return the normal vector for the closest face
    face_normals = {
        'west':  (-1, 0, 0),   # -X
        'east':  (1, 0, 0),    # +X
        'down':  (0, -1, 0),   # -Y
        'up':    (0, 1, 0),    # +Y
        'north': (0, 0, -1),   # -Z
        'south': (0, 0, 1),    # +Z
    }
    
    return face_normals[closest_face]
