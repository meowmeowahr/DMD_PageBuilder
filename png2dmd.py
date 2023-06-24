from PIL import Image, ImageOps
import sys
import statistics
import argparse


parser = argparse.ArgumentParser(description='Convert raster images to DMD')
parser.add_argument('input', help='Input raster')
parser.add_argument('output', help='output DMD image')

args = parser.parse_args()


def remove_transparency(im, bg_colour=(255, 255, 255)):
    # Only process if image has transparency (http://stackoverflow.com/a/1963146)
    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):

        # Need to convert to RGBA if LA format due to a bug in PIL (http://stackoverflow.com/a/1963146)
        alpha = im.convert('RGBA').split()[-1]

        # Create a new background image of our matt color.
        # Must be RGBA because paste requires both images to have the same format
        # (http://stackoverflow.com/a/8720632  and  http://stackoverflow.com/a/9459208)
        bg = Image.new("RGBA", im.size, bg_colour + (255,))
        bg.paste(im, mask=alpha)
        return bg

    else:
        return im


def slice_per(source, step):
    return [source[i::step] for i in range(step)]


def flatten(li):
    return [item for sublist in li for item in sublist]


def convert(in_file, output):
    image = Image.open(in_file)

    image = remove_transparency(image, (0, 0, 0))
    image = image.convert("RGB")

    raw_data = slice_per(list(image.getdata()), 32)

    for yi, y in enumerate(raw_data):
        for xi, x in enumerate(y):
            threshold = 100

            if statistics.mean(x) > threshold:
                raw_data[yi][xi] = (255, 255, 255)
            else:
                raw_data[yi][xi] = (0, 0, 0)

    image = Image.new(image.mode, image.size)
    image.putdata(flatten(raw_data))
    image = image.rotate(-90)
    image = ImageOps.mirror(image)

    data = list(image.getdata())

    for index, pixel in enumerate(data):
        if pixel == (255, 255, 255):
            data[index] = 0x01
        else:
            data[index] = 0x00

    data.insert(0, 1)

    with open(output, "wb") as file:
        file.write(bytes(data))


if __name__ == "__main__":
    convert(args.input, args.output)
