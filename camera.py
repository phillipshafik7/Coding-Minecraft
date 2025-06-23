import pygame
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
from collections import defaultdict

class Camera:
    def __init__(self):
        self.x = 0.0
        self.y = 20.0
        self.z = 0.0
        self.yaw = 0.0
        self.pitch = 0.0
        self.speed = 4.3  # Minecraft walking speed (blocks per second)
        
        # Survival mode physics - More accurate to Minecraft
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.velocity_z = 0.0
        self.on_ground = False
        self.gravity = -32.0  # Minecraft-like gravity
        self.jump_force = 8.5  # Minecraft jump height
        self.terminal_velocity = -78.4  # Maximum falling speed
        
        # Player collision box (Minecraft dimensions)
        self.player_height = 1.8
        self.player_width = 0.6
        self.player_eye_height = 1.62
        
        # Movement physics
        self.ground_friction = 0.91  # Ground friction multiplier
        self.air_resistance = 0.98   # Air resistance multiplier
        self.acceleration = 10.0     # Ground acceleration
        self.air_acceleration = 2.0  # Air acceleration (much lower)
        
        # Step height (can step up blocks up to this height)
        self.step_height = 0.6
        
        # Game mode
        self.creative_mode = True
        
        # View mode
        self.view_mode = "first_person"
        self.third_person_distance = 4.0
        
        # Movement tracking for animation
        self.is_moving = False
        self.last_x = self.x
        self.last_z = self.z
        
        # Collision detection improvements
        self.collision_margin = 0.001  # Small margin to prevent getting stuck
        
    def get_bounding_box(self, x=None, y=None, z=None):
        """Get player's axis-aligned bounding box"""
        if x is None: x = self.x
        if y is None: y = self.y
        if z is None: z = self.z
        
        half_width = self.player_width / 2
        
        return {
            'min_x': x - half_width,
            'max_x': x + half_width,
            'min_y': y,
            'max_y': y + self.player_height,
            'min_z': z - half_width,
            'max_z': z + half_width
        }

    def check_collision_at_position(self, x, y, z, world):
        """Check if player would collide with blocks at given position"""
        bbox = self.get_bounding_box(x, y, z)
        
        # Get all block positions that could intersect with player
        min_block_x = int(math.floor(bbox['min_x']))
        max_block_x = int(math.floor(bbox['max_x']))
        min_block_y = int(math.floor(bbox['min_y']))
        max_block_y = int(math.floor(bbox['max_y']))
        min_block_z = int(math.floor(bbox['min_z']))
        max_block_z = int(math.floor(bbox['max_z']))
        
        # Check each potentially intersecting block
        for bx in range(min_block_x, max_block_x + 1):
            for by in range(min_block_y, max_block_y + 1):
                for bz in range(min_block_z, max_block_z + 1):
                    if world.get_block(bx, by, bz):
                        # Check if player bounding box intersects with block
                        if (bbox['min_x'] < bx + 1 and bbox['max_x'] > bx and
                            bbox['min_y'] < by + 1 and bbox['max_y'] > by and
                            bbox['min_z'] < bz + 1 and bbox['max_z'] > bz):
                            return True, (bx, by, bz)
        
        return False, None

    def resolve_collision(self, old_x, old_y, old_z, new_x, new_y, new_z, world):
        """Resolve collision using swept collision detection"""
        # Try movement in each axis separately
        final_x, final_y, final_z = old_x, old_y, old_z
        
        # Try X movement first
        collides_x, _ = self.check_collision_at_position(new_x, old_y, old_z, world)
        if not collides_x:
            final_x = new_x
        else:
            # Try step-up if moving horizontally and hitting a block
            step_up_y = old_y + self.step_height
            collides_step, _ = self.check_collision_at_position(new_x, step_up_y, old_z, world)
            if not collides_step and self.on_ground:
                # Check if there's ground to step onto
                ground_check_y = step_up_y - 0.1
                for check_y in range(int(step_up_y), int(old_y), -1):
                    if world.get_block(int(new_x), check_y, int(old_z)):
                        final_x = new_x
                        final_y = check_y + 1
                        break
            else:
                self.velocity_x = 0  # Stop horizontal movement if collision
        
        # Try Z movement
        collides_z, _ = self.check_collision_at_position(final_x, final_y, new_z, world)
        if not collides_z:
            final_z = new_z
        else:
            # Try step-up for Z axis too
            if final_y == old_y:  # Only if we haven't already stepped up
                step_up_y = final_y + self.step_height
                collides_step, _ = self.check_collision_at_position(final_x, step_up_y, new_z, world)
                if not collides_step and self.on_ground:
                    # Check if there's ground to step onto
                    for check_y in range(int(step_up_y), int(final_y), -1):
                        if world.get_block(int(final_x), check_y, int(new_z)):
                            final_z = new_z
                            final_y = check_y + 1
                            break
                else:
                    self.velocity_z = 0
            else:
                self.velocity_z = 0
        
        # Try Y movement last
        if final_y != new_y:  # Only if Y hasn't been modified by step-up
            collides_y, block_pos = self.check_collision_at_position(final_x, new_y, final_z, world)
            if not collides_y:
                final_y = new_y
            else:
                if self.velocity_y > 0:  # Hitting ceiling
                    # Find the exact Y position just below the block
                    final_y = block_pos[1] - self.player_height - self.collision_margin
                    self.velocity_y = 0
                else:  # Hitting ground
                    # Find the exact Y position on top of the block
                    final_y = block_pos[1] + 1
                    self.velocity_y = 0
                    self.on_ground = True
        
        return final_x, final_y, final_z

    def update_survival(self, keys, dt, world):
        """Improved survival mode movement with better physics"""
        # Input handling for movement direction
        move_forward = keys[pygame.K_w]
        move_backward = keys[pygame.K_s]
        move_left = keys[pygame.K_a]
        move_right = keys[pygame.K_d]
        jump = keys[pygame.K_SPACE]
        
        # Calculate movement direction based on camera yaw
        yaw_rad = math.radians(self.yaw)
        forward_x = math.sin(yaw_rad)
        forward_z = -math.cos(yaw_rad)
        right_x = math.cos(yaw_rad)
        right_z = math.sin(yaw_rad)
        
        # Calculate desired movement direction
        move_dir_x = 0
        move_dir_z = 0
        
        if move_forward:
            move_dir_x += forward_x
            move_dir_z += forward_z
        if move_backward:
            move_dir_x -= forward_x
            move_dir_z -= forward_z
        if move_right:
            move_dir_x += right_x
            move_dir_z += right_z
        if move_left:
            move_dir_x -= right_x
            move_dir_z -= right_z
        
        # Normalize movement direction
        move_length = math.sqrt(move_dir_x * move_dir_x + move_dir_z * move_dir_z)
        if move_length > 0:
            move_dir_x /= move_length
            move_dir_z /= move_length
        
        # Apply acceleration/deceleration
        max_speed = self.speed
        acceleration = self.acceleration if self.on_ground else self.air_acceleration
        
        if move_length > 0:
            # Accelerate in movement direction
            target_vel_x = move_dir_x * max_speed
            target_vel_z = move_dir_z * max_speed
            
            self.velocity_x += (target_vel_x - self.velocity_x) * acceleration * dt
            self.velocity_z += (target_vel_z - self.velocity_z) * acceleration * dt
        else:
            # Decelerate when no input
            if self.on_ground:
                self.velocity_x *= self.ground_friction
                self.velocity_z *= self.ground_friction
            else:
                self.velocity_x *= self.air_resistance
                self.velocity_z *= self.air_resistance
        
        # Jumping
        if jump and self.on_ground:
            self.velocity_y = self.jump_force
            self.on_ground = False
        
        # Apply gravity
        if not self.on_ground:
            self.velocity_y += self.gravity * dt
            # Apply terminal velocity
            if self.velocity_y < self.terminal_velocity:
                self.velocity_y = self.terminal_velocity
        
        # Store old position
        old_x, old_y, old_z = self.x, self.y, self.z
        
        # Calculate new position
        new_x = old_x + self.velocity_x * dt
        new_y = old_y + self.velocity_y * dt
        new_z = old_z + self.velocity_z * dt
        
        # Resolve collisions and update position
        self.x, self.y, self.z = self.resolve_collision(old_x, old_y, old_z, new_x, new_y, new_z, world)
        
        # Check if we're still on ground (for falling detection)
        if self.on_ground:
            # Check if there's still ground beneath us
            ground_check_y = self.y - 0.1
            bbox = self.get_bounding_box(self.x, ground_check_y, self.z)
            
            min_block_x = int(math.floor(bbox['min_x']))
            max_block_x = int(math.floor(bbox['max_x']))
            min_block_z = int(math.floor(bbox['min_z']))
            max_block_z = int(math.floor(bbox['max_z']))
            
            ground_found = False
            for bx in range(min_block_x, max_block_x + 1):
                for bz in range(min_block_z, max_block_z + 1):
                    if world.get_block(bx, int(math.floor(ground_check_y)), bz):
                        ground_found = True
                        break
                if ground_found:
                    break
            
            if not ground_found:
                self.on_ground = False

    def update_creative(self, keys, dt):
        """Creative mode movement (flying) with improved physics"""
        move_speed = self.speed * dt
        
        # Calculate horizontal movement vectors (no pitch for horizontal movement)
        yaw_rad = math.radians(self.yaw)
        
        forward_x = math.sin(yaw_rad)
        forward_z = -math.cos(yaw_rad)
        
        right_x = math.cos(yaw_rad)
        right_z = math.sin(yaw_rad)
        
        # Apply horizontal movement
        if keys[pygame.K_w]:
            self.x += forward_x * move_speed
            self.z += forward_z * move_speed
        if keys[pygame.K_s]:
            self.x -= forward_x * move_speed
            self.z -= forward_z * move_speed
        if keys[pygame.K_a]:
            self.x -= right_x * move_speed
            self.z -= right_z * move_speed
        if keys[pygame.K_d]:
            self.x += right_x * move_speed
            self.z += right_z * move_speed
        
        # Apply vertical movement (independent of camera pitch)
        if keys[pygame.K_SPACE]:
            self.y += move_speed
        if keys[pygame.K_LSHIFT]:
            self.y -= move_speed

    def update(self, keys, mouse_rel, dt, world):
        # Track movement for animation
        old_x, old_z = self.x, self.z
        
        # Mouse look with sensitivity
        sensitivity = 0.15
        self.yaw += mouse_rel[0] * sensitivity
        self.pitch += mouse_rel[1] * sensitivity
        self.pitch = max(-89, min(89, self.pitch))
        
        if self.creative_mode:
            self.update_creative(keys, dt)
        else:
            self.update_survival(keys, dt, world)
        
        # Update movement state for animation
        self.is_moving = abs(self.x - old_x) > 0.01 or abs(self.z - old_z) > 0.01

    def cycle_view_mode(self):
        """Cycle through different view modes"""
        if self.view_mode == "first_person":
            self.view_mode = "third_person"
            return "Third Person (Back)"
        elif self.view_mode == "third_person":
            self.view_mode = "third_person_front"
            return "Third Person (Front)"
        else:  # third_person_front
            self.view_mode = "first_person"
            return "First Person"

    def toggle_mode(self):
        """Toggle between creative and survival mode"""
        self.creative_mode = not self.creative_mode
        if self.creative_mode:
            self.velocity_x = 0
            self.velocity_y = 0
            self.velocity_z = 0
            self.on_ground = False
        return "Creative" if self.creative_mode else "Survival"

    def get_camera_position(self):
        """Get the actual camera position based on view mode"""
        if self.view_mode == "first_person":
            return self.x, self.y + self.player_eye_height, self.z
        else:
            distance = self.third_person_distance
            yaw_rad = math.radians(self.yaw)
            pitch_rad = math.radians(self.pitch)
            
            if self.view_mode == "third_person":
                offset_x = math.sin(yaw_rad) * distance * math.cos(pitch_rad)
                offset_y = -math.sin(pitch_rad) * distance
                offset_z = -math.cos(yaw_rad) * distance * math.cos(pitch_rad)
            else:  # third_person_front
                offset_x = -math.sin(yaw_rad) * distance * math.cos(pitch_rad)
                offset_y = -math.sin(pitch_rad) * distance
                offset_z = math.cos(yaw_rad) * distance * math.cos(pitch_rad)
            
            camera_x = self.x - offset_x
            camera_y = self.y + self.player_eye_height - offset_y
            camera_z = self.z - offset_z
            
            return camera_x, camera_y, camera_z

    def apply_transform(self):
        glLoadIdentity()
        
        if self.view_mode == "first_person":
            glRotatef(self.pitch, 1, 0, 0)
            glRotatef(self.yaw, 0, 1, 0)
            glTranslatef(-self.x, -(self.y + self.player_eye_height), -self.z)
        else:
            camera_x, camera_y, camera_z = self.get_camera_position()
            look_at_y = self.y + 1.0
            
            gluLookAt(
                camera_x, camera_y, camera_z,
                self.x, look_at_y, self.z,
                0, 1, 0
            )
