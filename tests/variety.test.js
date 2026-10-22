const assert = require("node:assert/strict");
const World = require("../world.js");

const nodes = Object.values(World.WORLD.nodes);
const byPosition = new Map(nodes.map((node) => [`${node.x}:${node.y}`, node]));
const variety = World.WORLD.variety;
assert.ok(variety, "world.js must include variety assignment metadata");
assert.ok(variety.sourceBudget >= 1);
assert.equal(variety.achievedMinSourceDistance, Math.max(1, variety.achievedMinSourceDistance));
assert.equal(new Set(nodes.map((node) => node.image)).size, nodes.length, "nodes must use distinct image files");

function shared(left, right) { return left.sources.some((source) => right.sources.includes(source)); }
function kingAdjacent(left, right) { return Math.max(Math.abs(left.x - right.x), Math.abs(left.y - right.y)) <= 1; }

let actualMinimum = Infinity;
for (let i = 0; i < nodes.length; i += 1) {
  assert.ok(Array.isArray(nodes[i].sources) && nodes[i].sources.length > 0, "every node needs source provenance");
  for (let j = i + 1; j < nodes.length; j += 1) {
    if (shared(nodes[i], nodes[j])) {
      const distance = Math.abs(nodes[i].x - nodes[j].x) + Math.abs(nodes[i].y - nodes[j].y);
      actualMinimum = Math.min(actualMinimum, distance);
      if (variety.sourceBudget >= variety.minimumSourcesForNeighbourConstraint) {
        assert.ok(distance > 1, `neighbouring nodes share a source: ${nodes[i].x},${nodes[i].y} and ${nodes[j].x},${nodes[j].y}`);
        assert.ok(distance > 3, `source repeated within Manhattan distance 3: ${nodes[i].x},${nodes[i].y} and ${nodes[j].x},${nodes[j].y}`);
      }
    }
    if (kingAdjacent(nodes[i], nodes[j])) {
      assert.notEqual(nodes[i].preset, nodes[j].preset, `neighbouring colour grades match at ${nodes[i].x},${nodes[i].y}`);
    }
  }
}
assert.equal(actualMinimum, variety.achievedMinSourceDistance);
if (variety.sourceBudget < variety.minimumSourcesForNeighbourConstraint) {
  assert.equal(variety.constraintStatus, "source-budget-limited");
}

console.log(`variety.test.js: passed; min same-source distance ${actualMinimum}; status ${variety.constraintStatus}`);
