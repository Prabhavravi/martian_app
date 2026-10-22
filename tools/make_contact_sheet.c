#include <CoreFoundation/CoreFoundation.h>
#include <CoreGraphics/CoreGraphics.h>
#include <CoreText/CoreText.h>
#include <ImageIO/ImageIO.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *arg_value(int argc, char **argv, const char *name) {
    for (int i = 1; i + 1 < argc; i++) if (strcmp(argv[i], name) == 0) return argv[i + 1];
    fprintf(stderr, "missing argument %s\n", name);
    exit(2);
}

static CFURLRef file_url(const char *path) {
    return CFURLCreateFromFileSystemRepresentation(NULL, (const UInt8 *)path, strlen(path), false);
}

static CGImageRef thumbnail(const char *path, int max_size) {
    CFURLRef url = file_url(path);
    CGImageSourceRef source = CGImageSourceCreateWithURL(url, NULL);
    CFRelease(url);
    if (!source) return NULL;
    int max = max_size;
    CFNumberRef max_number = CFNumberCreate(NULL, kCFNumberIntType, &max);
    const void *keys[] = { kCGImageSourceCreateThumbnailFromImageAlways, kCGImageSourceThumbnailMaxPixelSize, kCGImageSourceCreateThumbnailWithTransform };
    const void *values[] = { kCFBooleanTrue, max_number, kCFBooleanTrue };
    CFDictionaryRef options = CFDictionaryCreate(NULL, keys, values, 3, &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
    CGImageRef image = CGImageSourceCreateThumbnailAtIndex(source, 0, options);
    CFRelease(options);
    CFRelease(max_number);
    CFRelease(source);
    return image;
}

static void draw_label(CGContextRef context, const char *label, CGFloat x, CGFloat y) {
    CFStringRef text = CFStringCreateWithCString(NULL, label, kCFStringEncodingUTF8);
    CTFontRef font = CTFontCreateWithName(CFSTR("Menlo"), 13, NULL);
    CGColorRef color = CGColorCreateGenericRGB(0.94, 0.94, 0.94, 1.0);
    const void *keys[] = { kCTFontAttributeName, kCTForegroundColorAttributeName };
    const void *values[] = { font, color };
    CFDictionaryRef attributes = CFDictionaryCreate(NULL, keys, values, 2, &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
    CFAttributedStringRef attributed = CFAttributedStringCreate(NULL, text, attributes);
    CTLineRef line = CTLineCreateWithAttributedString(attributed);
    CGContextSetTextPosition(context, x, y);
    CTLineDraw(line, context);
    CFRelease(line);
    CFRelease(attributed);
    CFRelease(attributes);
    CGColorRelease(color);
    CFRelease(font);
    CFRelease(text);
}

int main(int argc, char **argv) {
    const char *manifest_path = arg_value(argc, argv, "--manifest");
    const char *output_path = arg_value(argc, argv, "--output");
    FILE *manifest = fopen(manifest_path, "r");
    if (!manifest) return 3;
    const int thumb_width = 384, thumb_height = 96, cell_width = 420, cell_height = 132;
    const int sheet_width = 4 * cell_width, sheet_height = 4 * cell_height;
    CGColorSpaceRef color_space = CGColorSpaceCreateDeviceRGB();
    CGContextRef context = CGBitmapContextCreate(NULL, sheet_width, sheet_height, 8, sheet_width * 4, color_space, kCGImageAlphaPremultipliedLast);
    CGColorSpaceRelease(color_space);
    if (!context) return 4;
    CGContextSetRGBFillColor(context, 0.06, 0.035, 0.025, 1.0);
    CGContextFillRect(context, CGRectMake(0, 0, sheet_width, sheet_height));
    char line[8192];
    while (fgets(line, sizeof(line), manifest)) {
        int x, y;
        char source[256], path[4096];
        if (sscanf(line, "%d|%d|%255[^|]|%4095[^\n]", &x, &y, source, path) != 4) return 5;
        CGImageRef image = thumbnail(path, thumb_width);
        if (!image) return 6;
        CGFloat cell_x = x * cell_width + 18;
        CGFloat cell_y = sheet_height - (y + 1) * cell_height + 26;
        CGContextDrawImage(context, CGRectMake(cell_x, cell_y, thumb_width, thumb_height), image);
        char label[512];
        snprintf(label, sizeof(label), "(%d,%d)  %s", x, y, source);
        draw_label(context, label, cell_x, sheet_height - (y + 1) * cell_height + 8);
        CGImageRelease(image);
    }
    fclose(manifest);
    CGImageRef sheet = CGBitmapContextCreateImage(context);
    CFURLRef output_url = file_url(output_path);
    CGImageDestinationRef destination = CGImageDestinationCreateWithURL(output_url, CFSTR("public.jpeg"), 1, NULL);
    float quality = 0.9;
    CFNumberRef quality_number = CFNumberCreate(NULL, kCFNumberFloatType, &quality);
    const void *keys[] = { kCGImageDestinationLossyCompressionQuality };
    const void *values[] = { quality_number };
    CFDictionaryRef options = CFDictionaryCreate(NULL, keys, values, 1, &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
    CGImageDestinationAddImage(destination, sheet, options);
    int ok = CGImageDestinationFinalize(destination) ? 0 : 7;
    CFRelease(options);
    CFRelease(quality_number);
    CFRelease(destination);
    CFRelease(output_url);
    CGImageRelease(sheet);
    CGContextRelease(context);
    return ok;
}
