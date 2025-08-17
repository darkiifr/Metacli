"""Create a simple test image for metadata testing."""

from PIL import Image
import os

# Create a simple test image
img = Image.new('RGB', (100, 100), color='red')

# Save the image
img.save('test_image.jpg', 'JPEG')
print("Test image created: test_image.jpg")