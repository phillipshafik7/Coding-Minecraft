import pygame
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
from collections import defaultdict

from raycast import *
from block import *
from player import *
from camera import *
from mcchunk import *
from world import *

class MinecraftGame:
    def __init__(self):
        pygame.init()
        
        # Initialize display
        self.width, self.height = 800, 600
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.OPENGL)
        pygame.display.set_caption("PhilCraft")
        
        # Setup OpenGL
        self.setup_opengl()
        
        # Initialize game objects
        self.camera = Camera()
        self.world = World()
        self.player = Player()
        self.clock = pygame.time.Clock()    

        # Mouse setup
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        
        # Colors for different block types
        self.colors = {
            1: (0.2, 0.8, 0.2),  # Grass green
            2: (0.1, 0.6, 0.1),  # Dark green (leaves)
            3: (0.6, 0.6, 0.6),  # Stone gray
            4: (0.4, 0.2, 0.1)   # Brown (tree trunk)
        }
        
        print("Game initialized successfully!")
        
    def setup_opengl(self):
        # Enable depth testing
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        
        # Setup perspective
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(60, self.width/self.height, 0.1, 1000.0)  # Increased far plane
        
        # Setup modelview
        glMatrixMode(GL_MODELVIEW)
        
        # Enable backface culling for performance
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        glFrontFace(GL_CCW)
        
        # Basic lighting setup
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
    def handle_input(self):
        keys = pygame.key.get_pressed()
        mouse_rel = pygame.mouse.get_rel()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_r:
                    # Reset camera
                    self.camera.x = 0
                    self.camera.y = 20
                    self.camera.z = 0
                    self.camera.velocity_y = 0
                    print(f"Camera reset to: {self.camera.x}, {self.camera.y}, {self.camera.z}")
                elif event.key == pygame.K_g:
                    # Toggle game mode
                    mode = self.camera.toggle_mode()
                    print(f"Switched to {mode} mode")
                elif event.key == pygame.K_f:  # F key to cycle view modes
                    view_mode = self.camera.cycle_view_mode()
                    print(f"Switched to {view_mode}")
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click - remove block
                    self.raycast_interaction(remove=True)
                elif event.button == 3:  # Right click - place block
                    self.raycast_interaction(remove=False)

        # Update camera
        dt = self.clock.get_time() / 1000.0
        self.camera.update(keys, mouse_rel, dt, self.world)

        # Update player animation based on camera movement
        self.player.update_animation(self.camera.is_moving, dt)
        
        return True  # Continue running
    
    def raycast_interaction(self, remove=True):
        # Get the actual camera position based on view mode
        if self.camera.view_mode == "first_person":
            start_x = self.camera.x
            start_y = self.camera.y + 1.62  # Eye level
            start_z = self.camera.z
        else:
            cam_x, cam_y, cam_z = self.camera.get_camera_position()
            start_x = cam_x
            start_y = cam_y
            start_z = cam_z
        
        # Calculate ray direction based on camera rotation
        yaw_rad = math.radians(self.camera.yaw)
        pitch_rad = math.radians(self.camera.pitch)
        
        # Direction vector
        dx = math.sin(yaw_rad) * math.cos(pitch_rad)
        dy = -math.sin(pitch_rad)
        dz = -math.cos(yaw_rad) * math.cos(pitch_rad)
        
        # Perform precise raycast
        result = raycast_precise(self.world, (start_x, start_y, start_z), (dx, dy, dz), max_distance=5.0)
        
        if result.hit:
            hit_x, hit_y, hit_z = result.block_pos
            
            if remove:
                # Remove the block that was hit
                self.world.remove_block(hit_x, hit_y, hit_z)
                print(f"Removed block at {hit_x}, {hit_y}, {hit_z}")
            else:
                # Place block on the face that was hit
                face_normal = result.face_normal
                place_x = hit_x + face_normal[0]
                place_y = hit_y + face_normal[1]
                place_z = hit_z + face_normal[2]
                
                # Check if placement position is valid (no existing block)
                if not self.world.get_block(place_x, place_y, place_z):
                    # Check if the new block would collide with the player
                    # We need to check collision with the player's current position
                    collision, _ = self.camera.check_collision_at_position(
                        self.camera.x, self.camera.y, self.camera.z, self.world
                    )
                    
                    # Temporarily place the block to test collision
                    temp_block = Block(place_x, place_y, place_z, 3)
                    chunk_x, chunk_z = self.world.get_chunk_coords(place_x, place_z)
                    if (chunk_x, chunk_z) in self.world.chunks:
                        self.world.chunks[(chunk_x, chunk_z)].blocks[(place_x, place_y, place_z)] = temp_block
                    else:
                        # Create chunk if it doesn't exist
                        chunk = self.world.get_chunk(chunk_x, chunk_z)
                        chunk.blocks[(place_x, place_y, place_z)] = temp_block
                    
                    # Test collision with the new block in place
                    would_collide, _ = self.camera.check_collision_at_position(
                        self.camera.x, self.camera.y, self.camera.z, self.world
                    )
                    
                    if not would_collide:
                        # Safe to place - block is already in world from temp placement
                        # Just mark chunk for update
                        chunk = self.world.get_chunk(chunk_x, chunk_z)
                        chunk.needs_update = True
                        self.world.mark_adjacent_chunks_for_update(place_x, place_y, place_z)
                        print(f"Placed block at {place_x}, {place_y}, {place_z} on face {face_normal}")
                    else:
                        # Would collide with player - remove the temporary block
                        chunk = self.world.get_chunk(chunk_x, chunk_z)
                        if (place_x, place_y, place_z) in chunk.blocks:
                            del chunk.blocks[(place_x, place_y, place_z)]
                        print(f"Cannot place block at {place_x}, {place_y}, {place_z} - would collide with player")

    def get_target_block(self):
        """Get the block the player is currently looking at"""
        # Get the actual camera position based on view mode
        if self.camera.view_mode == "first_person":
            start_x = self.camera.x
            start_y = self.camera.y + 1.62  # Eye level
            start_z = self.camera.z
        else:
            cam_x, cam_y, cam_z = self.camera.get_camera_position()
            start_x = cam_x
            start_y = cam_y
            start_z = cam_z
        
        # Calculate ray direction based on camera rotation
        yaw_rad = math.radians(self.camera.yaw)
        pitch_rad = math.radians(self.camera.pitch)
        
        # Direction vector
        dx = math.sin(yaw_rad) * math.cos(pitch_rad)
        dy = -math.sin(pitch_rad)
        dz = -math.cos(yaw_rad) * math.cos(pitch_rad)
        
        # Perform precise raycast
        result = raycast_precise(self.world, (start_x, start_y, start_z), (dx, dy, dz), max_distance=5.0)
        
        if result.hit:
            return result.block_pos
        
        return None

    def draw_crosshair(self):
        """Draw crosshair in the center of the screen"""
        # Switch to 2D rendering mode
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Disable depth testing for 2D overlay
        glDisable(GL_DEPTH_TEST)
        
        # Draw crosshair
        center_x = self.width / 2
        center_y = self.height / 2
        crosshair_size = 10
        
        glColor3f(1.0, 1.0, 1.0)  # White color
        glLineWidth(2.0)
        
        glBegin(GL_LINES)
        # Horizontal line
        glVertex2f(center_x - crosshair_size, center_y)
        glVertex2f(center_x + crosshair_size, center_y)
        # Vertical line
        glVertex2f(center_x, center_y - crosshair_size)
        glVertex2f(center_x, center_y + crosshair_size)
        glEnd()
        
        # Re-enable depth testing
        glEnable(GL_DEPTH_TEST)
        
        # Restore matrices
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

    def draw_cube_face(self, vertices, face_indices, normal, color, brightness):
        """Draw a single face of a cube with proper normal and color"""
        glColor3f(color[0] * brightness, color[1] * brightness, color[2] * brightness)
        glNormal3f(*normal)
        
        glBegin(GL_QUADS)
        for idx in face_indices:
            glVertex3f(*vertices[idx])
        glEnd()
    
    def draw_cube(self, x, y, z, color):
        """Draw a cube with proper face culling and normals"""
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
        
        # Define faces with correct winding order (counter-clockwise when viewed from outside)
        faces = [
            # Face indices, direction offset, normal, brightness
            ([0, 3, 2, 1], (0, 0, -1), (0, 0, -1), 0.8),   # Front face
            ([5, 6, 7, 4], (0, 0, 1),  (0, 0, 1),  0.8),   # Back face
            ([0, 1, 5, 4], (0, -1, 0), (0, -1, 0), 0.6),   # Bottom face
            ([3, 7, 6, 2], (0, 1, 0),  (0, 1, 0),  1.0),   # Top face
            ([0, 4, 7, 3], (-1, 0, 0), (-1, 0, 0), 0.7),   # Left face
            ([1, 2, 6, 5], (1, 0, 0),  (1, 0, 0),  0.9)    # Right face
        ]
        
        # Only draw faces that are exposed (not hidden by adjacent blocks)
        for face_indices, direction, normal, brightness in faces:
            dx, dy, dz = direction
            adjacent_block = self.world.get_block(x + dx, y + dy, z + dz)
            
            # If there's no adjacent block in this direction, draw the face
            if not adjacent_block:
                self.draw_cube_face(vertices, face_indices, normal, color, brightness)
    
    def render(self):
        # Clear buffers
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glClearColor(0.5, 0.8, 1.0, 1.0)  # Sky blue
        
        # Apply camera transform
        self.camera.apply_transform()
        
        # Get visible chunks sorted by proximity
        visible_chunks = self.world.get_visible_chunks(self.camera.x, self.camera.z)
        
        # Compile chunks that need updating
        for chunk in visible_chunks:
            if chunk.needs_update or not chunk.is_compiled:
                chunk.compile_chunk(self.world)
        
        # Render chunks (closest first for better performance)
        chunks_rendered = 0
        total_blocks = 0

        for chunk in visible_chunks:
            # Calculate distance to chunk for LOD (Level of Detail) if needed
            chunk_center_x = chunk.chunk_x * 16 + 8
            chunk_center_z = chunk.chunk_z * 16 + 8
            dx = chunk_center_x - self.camera.x
            dz = chunk_center_z - self.camera.z
            distance = math.sqrt(dx*dx + dz*dz)
            
            # Render the entire chunk at once
            if distance < self.world.render_distance * 16 + 32:  # Small buffer for smooth transitions
                chunk.render()
                chunks_rendered += 1
                total_blocks += len(chunk.blocks)

        # Render player in third person mode
        if self.camera.view_mode != "first_person":
            # Draw the player model at the camera's world position
            self.player.render(self.camera.x, self.camera.y, self.camera.z, self.camera.yaw)

        # Draw crosshair overlay
        self.draw_crosshair()
        
        # Display frame
        pygame.display.flip()
        
        # Print debug info occasionally
        if pygame.time.get_ticks() % 1000 < 50:  # Every second
            fps = self.clock.get_fps()
            loaded_chunks = len(self.world.chunks)
            print(f"FPS: {fps:.1f}, Chunks rendered: {chunks_rendered}/{loaded_chunks}, Total blocks: {total_blocks}, Camera: ({self.camera.x:.1f}, {self.camera.y:.1f}, {self.camera.z:.1f})")
    
    def run(self):
        print("Starting game loop...")
        running = True
        frame_count = 0
        
        while running:
            frame_count += 1
            running = self.handle_input()
            self.render()
            self.clock.tick(60)  # Target 60 FPS
            
            # Debug output for first few frames
            if frame_count <= 5:
                print(f"Frame {frame_count} rendered")
        
        print("Game shutting down...")
        pygame.quit()

if __name__ == "__main__":
    try:
        print("Minecraft Clone Controls:")
        print("WASD - Move around")
        print("Space - Move up")
        print("Shift - Move down")
        print("Mouse - Look around")
        print("Left Click - Remove block")
        print("Right Click - Place block")
        print("F - Cycle view mode (First Person/Third Person Back/Third Person Front)")
        print("R - Reset camera position")
        print("ESC - Exit game")
        print("\nInitializing game...")
        
        game = MinecraftGame()
        game.run()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")