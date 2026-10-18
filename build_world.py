from src.world.loader import WorldLoader
from PIL import Image
import random

loader = WorldLoader('outputs')

print("Available biomes:", loader.biome_list)
print("Total tiles:", loader.tile_count())

# Create a 5x5 world strip
world_size = 5
cell_size = 256
canvas = Image.new('RGB', (world_size * cell_size, cell_size))

for x in range(world_size):
    biome = random.choice(loader.biome_list)
    tile = random.choice(loader.get_tiles_by_biome(biome))
    texture = loader.load_texture(tile).resize((cell_size, cell_size))
    canvas.paste(texture, (x * cell_size, 0))
    print(f"Cell {x}: {biome} -> {tile['id']}")

canvas.save('martian_strip.png')
print("Saved martian_strip.png")
