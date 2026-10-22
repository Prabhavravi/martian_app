(function (global) {
  "use strict";

  var WORLD = {
    width: 4,
    height: 4,
    spanDegrees: 360,
    fovDegrees: 90,
    start: { x: 1, y: 3, heading: 0 },
    nodes: {}
  };

  for (var y = 0; y < WORLD.height; y += 1) {
    for (var x = 0; x < WORLD.width; x += 1) {
      WORLD.nodes[x + ":" + y] = {
        x: x,
        y: y,
        image: "assets/panoramas/node_" + x + "_" + y + ".jpg",
        source: "derived"
      };
    }
  }

  // The audited 2048x512 (4:1) panorama is the real start location. The
  // remaining slots use static offline variants derived from that panorama.
  WORLD.nodes["1:3"] = {
    x: 1,
    y: 3,
    image: "assets/panoramas/martian_panorama_seamless.png",
    source: "real",
    sourceDimensions: "2048x512"
  };

  function key(x, y) {
    return x + ":" + y;
  }

  function getNode(x, y) {
    return WORLD.nodes[key(x, y)] || null;
  }

  function normalizeHeading(degrees) {
    var value = degrees % 360;
    return value < 0 ? value + 360 : value;
  }

  function snapCardinal(heading) {
    var normalized = normalizeHeading(heading);
    return Math.round(normalized / 90) % 4;
  }

  function directionVector(cardinal) {
    return [
      { x: 0, y: -1 },
      { x: 1, y: 0 },
      { x: 0, y: 1 },
      { x: -1, y: 0 }
    ][cardinal];
  }

  function inBounds(x, y, world) {
    var map = world || WORLD;
    return x >= 0 && x < map.width && y >= 0 && y < map.height;
  }

  function moveOneNode(current, direction, world) {
    var map = world || WORLD;
    var step = direction >= 0 ? 1 : -1;
    var cardinal = snapCardinal(current.heading);
    var vector = directionVector(cardinal);
    var nextX = current.x + vector.x * step;
    var nextY = current.y + vector.y * step;
    var nextState = { x: current.x, y: current.y, heading: normalizeHeading(current.heading) };
    if (!inBounds(nextX, nextY, map)) {
      return { state: nextState, moved: false, blocked: true, direction: cardinal };
    }
    nextState.x = nextX;
    nextState.y = nextY;
    return { state: nextState, moved: true, blocked: false, direction: cardinal };
  }

  global.MartianWorld = {
    WORLD: WORLD,
    key: key,
    getNode: getNode,
    normalizeHeading: normalizeHeading,
    snapCardinal: snapCardinal,
    directionVector: directionVector,
    inBounds: inBounds,
    moveOneNode: moveOneNode
  };
  if (typeof module !== "undefined" && module.exports) module.exports = global.MartianWorld;
}(typeof window !== "undefined" ? window : globalThis));
