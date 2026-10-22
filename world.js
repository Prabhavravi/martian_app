(function (global) {
  "use strict";

  var WORLD = {
    width: 4,
    height: 4,
    spanDegrees: 360,
    fovDegrees: 90,
    start: { x: 1, y: 1, heading: 0 },
    nodes: {}
  };

  for (var y = 0; y < WORLD.height; y += 1) {
    for (var x = 0; x < WORLD.width; x += 1) {
      WORLD.nodes[x + ":" + y] = {
        x: x,
        y: y,
        image: "assets/panoramas/node_" + x + "_" + y + ".png",
        kind: "placeholder"
      };
    }
  }

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

  global.MartianWorld = {
    WORLD: WORLD,
    key: key,
    getNode: getNode,
    normalizeHeading: normalizeHeading,
    snapCardinal: snapCardinal
  };
}(window));
