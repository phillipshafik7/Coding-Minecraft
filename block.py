class Block:
    def __init__(self, x, y, z, block_type=1, texture_id = 0, solid = True, transparent = False, hardness = 1, light_level = 0):
        self.x = x
        self.y = y
        self.z = z
        self.type = block_type
        self.texture_id = texture_id
        self.transparent = transparent
        self.hardness = hardness
        self.light_level = light_level
