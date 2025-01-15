from pyzbar.pyzbar import decode
from PIL import Image

# Load the image
img = Image.open("~\Downloads\a.jpg")

# Decode the QR code
decoded_objects = decode(img)

for obj in decoded_objects:
    print(f"Type: {obj.type}")
    print(f"Data: {obj.data.decode('utf-8')}")
