const assert = require("node:assert/strict");
const fs = require("node:fs");
const World = require("../world.js");

function dimensions(buffer, file) {
  if (buffer.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) {
    assert.equal(buffer.toString("ascii", 12, 16), "IHDR", file);
    return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
  }
  assert.equal(buffer[0], 0xff, file);
  assert.equal(buffer[1], 0xd8, file);
  let offset = 2;
  while (offset + 9 < buffer.length) {
    if (buffer[offset] !== 0xff) { offset += 1; continue; }
    const marker = buffer[offset + 1];
    const length = buffer.readUInt16BE(offset + 2);
    if ([0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf].indexOf(marker) !== -1) {
      return { width: buffer.readUInt16BE(offset + 7), height: buffer.readUInt16BE(offset + 5) };
    }
    offset += 2 + length;
  }
  assert.fail("could not read image dimensions: " + file);
}

const nodes = Object.values(World.WORLD.nodes);
const mappedFiles = nodes.map((node) => node.image);
assert.equal(new Set(mappedFiles).size, nodes.length, "each node should have its own panorama file");
nodes.forEach((node) => {
  assert.equal(fs.existsSync(node.image), true, "missing panorama for node (" + node.x + "," + node.y + "): " + node.image);
  assert.ok(node.source === "real" || node.source === "derived", "invalid source tag for " + node.image);
});

const panoramaFiles = fs.readdirSync("assets/panoramas")
  .filter((file) => /^node_\d+_\d+\.(png|jpg)$/.test(file))
  .map((file) => "assets/panoramas/" + file);
assert.ok(panoramaFiles.length >= nodes.length, "expected the complete node panorama set");
const firstDimensions = dimensions(fs.readFileSync(panoramaFiles[0]), panoramaFiles[0]);
panoramaFiles.forEach((file) => assert.deepEqual(dimensions(fs.readFileSync(file), file), firstDimensions, file));
assert.deepEqual(firstDimensions, { width: 2048, height: 512 });

console.log("assets.test.js: all node files exist with consistent 2048x512 dimensions");
