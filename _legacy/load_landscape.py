# load_landscape.py — Load and use the single large landscape image
from pathlib import Path
from PIL import Image

class MartianLandscape:
    def __init__(self, image_path: str):
        self.image = Image.open(image_path).convert("RGB")
        self.width, self.height = self.image.size
        print(f"Loaded landscape: {self.width}x{self.height}")
    
    def get_region(self, x: int, y: int, w: int, h: int) -> Image.Image:
        """Crop a rectangular region from the landscape."""
        return self.image.crop((x, y, min(x + w, self.width), min(y + h, self.height)))
    
    def get_tile(self, tx: int, ty: int, tile_size: int = 256) -> Image.Image:
        """Get a specific tile by grid coordinates."""
        x = tx * tile_size
        y = ty * tile_size
        return self.get_region(x, y, tile_size, tile_size)
    
    def save_region(self, x: int, y: int, w: int, h: int, output_path: str):
        region = self.get_region(x, y, w, h)
        region.save(output_path)
        print(f"Saved {output_path}")

if __name__ == "__main__":
    landscape = MartianLandscape("martian_landscape_1024.png")
    
    # Save a 512x512 region from the center
    landscape.save_region(256, 256, 512, 512, "center_region.png")
    
    # Get individual tiles
    tile = landscape.get_tile(0, 0)
    tile.save("tile_00.png")
