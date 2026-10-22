const assert = require("node:assert/strict");
const World = require("../world.js");

const map = { width: 4, height: 4 };

function state(x, y, heading) { return { x, y, heading }; }

assert.deepEqual(World.moveOneNode(state(1, 1, 0), 1, map).state, state(1, 0, 0));
assert.deepEqual(World.moveOneNode(state(1, 1, 90), 1, map).state, state(2, 1, 90));
assert.deepEqual(World.moveOneNode(state(1, 1, 180), 1, map).state, state(1, 2, 180));
assert.deepEqual(World.moveOneNode(state(1, 1, 270), 1, map).state, state(0, 1, 270));

assert.equal(World.moveOneNode(state(0, 1, 270), 1, map).blocked, true);
assert.equal(World.moveOneNode(state(3, 1, 90), 1, map).blocked, true);
assert.equal(World.moveOneNode(state(1, 0, 0), 1, map).blocked, true);
assert.equal(World.moveOneNode(state(1, 3, 180), 1, map).blocked, true);

assert.equal(World.normalizeHeading(-1), 359);
assert.equal(World.normalizeHeading(721), 1);
assert.equal(World.snapCardinal(359), 0);
assert.equal(World.snapCardinal(46), 1);

let origin = state(1, 1, 0);
let forward = World.moveOneNode(origin, 1, map);
let back = World.moveOneNode(forward.state, -1, map);
assert.deepEqual(back.state, origin);

console.log("logic.test.js: all movement assertions passed");
