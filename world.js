(function (global) {
  "use strict";

  var WORLD = {
    "width": 4,
    "height": 4,
    "spanDegrees": 360,
    "fovDegrees": 90,
    "start": {
        "x": 1,
        "y": 3,
        "heading": 0
    },
    "nodes": {
        "0:0": {
            "x": 0,
            "y": 0,
            "image": "assets/panoramas/derived/scene_018.jpg",
            "source": "derived",
            "sources": [
                "martian_panorama_seamless"
            ],
            "preset": "pale_haze",
            "recipe": {
                "type": "single",
                "seed": 20261040,
                "preset": "pale_haze",
                "feather_px": 0,
                "parts": [
                    {
                        "source_index": 1,
                        "roll": 1551,
                        "zoom": 0.7016,
                        "mirror": false,
                        "vertical_shift": 3
                    }
                ],
                "haze": true,
                "sources": [
                    "martian_panorama_seamless"
                ]
            }
        },
        "1:0": {
            "x": 1,
            "y": 0,
            "image": "assets/panoramas/derived/scene_005.jpg",
            "source": "derived",
            "sources": [
                "martian_panorama"
            ],
            "preset": "butte_orange",
            "recipe": {
                "type": "single",
                "seed": 20261027,
                "preset": "butte_orange",
                "feather_px": 0,
                "parts": [
                    {
                        "source_index": 0,
                        "roll": 436,
                        "zoom": 0.9221,
                        "mirror": false,
                        "vertical_shift": 12
                    }
                ],
                "haze": true,
                "sources": [
                    "martian_panorama"
                ]
            }
        },
        "2:0": {
            "x": 2,
            "y": 0,
            "image": "assets/panoramas/derived/scene_014.jpg",
            "source": "derived",
            "sources": [
                "martian_panorama_seamless"
            ],
            "preset": "dark_basalt",
            "recipe": {
                "type": "single",
                "seed": 20261036,
                "preset": "dark_basalt",
                "feather_px": 0,
                "parts": [
                    {
                        "source_index": 1,
                        "roll": 1519,
                        "zoom": 0.7288,
                        "mirror": false,
                        "vertical_shift": 4
                    }
                ],
                "haze": true,
                "sources": [
                    "martian_panorama_seamless"
                ]
            }
        },
        "3:0": {
            "x": 3,
            "y": 0,
            "image": "assets/panoramas/derived/scene_015.jpg",
            "source": "derived",
            "sources": [
                "martian_panorama"
            ],
            "preset": "butte_orange",
            "recipe": {
                "type": "single",
                "seed": 20261037,
                "preset": "butte_orange",
                "feather_px": 0,
                "parts": [
                    {
                        "source_index": 0,
                        "roll": 784,
                        "zoom": 0.7017,
                        "mirror": false,
                        "vertical_shift": -10
                    }
                ],
                "haze": true,
                "sources": [
                    "martian_panorama"
                ]
            }
        },
        "0:1": {
            "x": 0,
            "y": 1,
            "image": "assets/panoramas/derived/scene_009.jpg",
            "source": "derived",
            "sources": [
                "martian_panorama"
            ],
            "preset": "dark_basalt",
            "recipe": {
                "type": "single",
                "seed": 20261031,
                "preset": "dark_basalt",
                "feather_px": 0,
                "parts": [
                    {
                        "source_index": 0,
                        "roll": 601,
                        "zoom": 0.8372,
                        "mirror": false,
                        "vertical_shift": -9
                    }
                ],
                "haze": true,
                "sources": [
                    "martian_panorama"
                ]
            }
        },
        "1:1": {
            "x": 1,
            "y": 1,
            "image": "assets/panoramas/derived/scene_002.jpg",
            "source": "derived",
            "sources": [
                "martian_panorama_seamless"
            ],
            "preset": "rust_dusk",
            "recipe": {
                "type": "single",
                "seed": 20261024,
                "preset": "rust_dusk",
                "feather_px": 0,
                "parts": [
                    {
                        "source_index": 1,
                        "roll": 198,
                        "zoom": 0.9827,
                        "mirror": false,
                        "vertical_shift": -5
                    }
                ],
                "haze": true,
                "sources": [
                    "martian_panorama_seamless"
                ]
            }
        },
        "2:1": {
            "x": 2,
            "y": 1,
            "image": "assets/panoramas/derived/scene_001.jpg",
            "source": "derived",
            "sources": [
                "martian_panorama"
            ],
            "preset": "dusty_afternoon",
            "recipe": {
                "type": "single",
                "seed": 20261023,
                "preset": "dusty_afternoon",
                "feather_px": 0,
                "parts": [
                    {
                        "source_index": 0,
                        "roll": 1444,
                        "zoom": 0.8738,
                        "mirror": false,
                        "vertical_shift": -7
                    }
                ],
                "haze": true,
                "sources": [
                    "martian_panorama"
                ]
            }
        },
        "3:1": {
            "x": 3,
            "y": 1,
            "image": "assets/panoramas/derived/scene_012.jpg",
            "source": "derived",
            "sources": [
                "martian_panorama_seamless"
            ],
            "preset": "rust_dusk",
            "recipe": {
                "type": "splice",
                "seed": 20261034,
                "preset": "rust_dusk",
                "feather_px": 250,
                "parts": [
                    {
                        "source_index": 1,
                        "roll": 1788,
                        "zoom": 0.8846,
                        "mirror": false,
                        "vertical_shift": 1
                    },
                    {
                        "source_index": 1,
                        "roll": 364,
                        "zoom": 0.8279,
                        "mirror": false,
                        "vertical_shift": 10
                    },
                    {
                        "source_index": 1,
                        "roll": 187,
                        "zoom": 0.7379,
                        "mirror": false,
                        "vertical_shift": 0
                    }
                ],
                "haze": true,
                "sources": [
                    "martian_panorama_seamless"
                ]
            }
        },
        "0:2": {
            "x": 0,
            "y": 2,
            "image": "assets/panoramas/derived/scene_006.jpg",
            "source": "derived",
            "sources": [
                "martian_panorama_seamless"
            ],
            "preset": "dusty_afternoon",
            "recipe": {
                "type": "single",
                "seed": 20261028,
                "preset": "dusty_afternoon",
                "feather_px": 0,
                "parts": [
                    {
                        "source_index": 1,
                        "roll": 615,
                        "zoom": 0.8524,
                        "mirror": false,
                        "vertical_shift": -6
                    }
                ],
                "haze": true,
                "sources": [
                    "martian_panorama_seamless"
                ]
            }
        },
        "1:2": {
            "x": 1,
            "y": 2,
            "image": "assets/panoramas/derived/scene_003.jpg",
            "source": "derived",
            "sources": [
                "martian_panorama"
            ],
            "preset": "pale_haze",
            "recipe": {
                "type": "single",
                "seed": 20261025,
                "preset": "pale_haze",
                "feather_px": 0,
                "parts": [
                    {
                        "source_index": 0,
                        "roll": 943,
                        "zoom": 0.7704,
                        "mirror": false,
                        "vertical_shift": 10
                    }
                ],
                "haze": true,
                "sources": [
                    "martian_panorama"
                ]
            }
        },
        "2:2": {
            "x": 2,
            "y": 2,
            "image": "assets/panoramas/derived/scene_010.jpg",
            "source": "derived",
            "sources": [
                "martian_panorama_seamless"
            ],
            "preset": "butte_orange",
            "recipe": {
                "type": "single",
                "seed": 20261032,
                "preset": "butte_orange",
                "feather_px": 0,
                "parts": [
                    {
                        "source_index": 1,
                        "roll": 917,
                        "zoom": 0.8539,
                        "mirror": false,
                        "vertical_shift": 4
                    }
                ],
                "haze": true,
                "sources": [
                    "martian_panorama_seamless"
                ]
            }
        },
        "3:2": {
            "x": 3,
            "y": 2,
            "image": "assets/panoramas/derived/scene_013.jpg",
            "source": "derived",
            "sources": [
                "martian_panorama"
            ],
            "preset": "pale_haze",
            "recipe": {
                "type": "single",
                "seed": 20261035,
                "preset": "pale_haze",
                "feather_px": 0,
                "parts": [
                    {
                        "source_index": 0,
                        "roll": 851,
                        "zoom": 0.9264,
                        "mirror": false,
                        "vertical_shift": -10
                    }
                ],
                "haze": true,
                "sources": [
                    "martian_panorama"
                ]
            }
        },
        "0:3": {
            "x": 0,
            "y": 3,
            "image": "assets/panoramas/derived/scene_017.jpg",
            "source": "derived",
            "sources": [
                "martian_panorama"
            ],
            "preset": "rust_dusk",
            "recipe": {
                "type": "single",
                "seed": 20261039,
                "preset": "rust_dusk",
                "feather_px": 0,
                "parts": [
                    {
                        "source_index": 0,
                        "roll": 244,
                        "zoom": 0.8097,
                        "mirror": false,
                        "vertical_shift": 12
                    }
                ],
                "haze": true,
                "sources": [
                    "martian_panorama"
                ]
            }
        },
        "1:3": {
            "x": 1,
            "y": 3,
            "image": "assets/panoramas/martian_panorama_seamless.png",
            "source": "real",
            "sources": [
                "martian_panorama_seamless"
            ],
            "preset": "real",
            "sourceDimensions": "2048x512"
        },
        "2:3": {
            "x": 2,
            "y": 3,
            "image": "assets/panoramas/derived/scene_007.jpg",
            "source": "derived",
            "sources": [
                "martian_panorama"
            ],
            "preset": "rust_dusk",
            "recipe": {
                "type": "single",
                "seed": 20261029,
                "preset": "rust_dusk",
                "feather_px": 0,
                "parts": [
                    {
                        "source_index": 0,
                        "roll": 1847,
                        "zoom": 0.7015,
                        "mirror": false,
                        "vertical_shift": -9
                    }
                ],
                "haze": true,
                "sources": [
                    "martian_panorama"
                ]
            }
        },
        "3:3": {
            "x": 3,
            "y": 3,
            "image": "assets/panoramas/derived/scene_024.jpg",
            "source": "derived",
            "sources": [
                "martian_panorama_seamless"
            ],
            "preset": "dark_basalt",
            "recipe": {
                "type": "splice",
                "seed": 20261046,
                "preset": "dark_basalt",
                "feather_px": 250,
                "parts": [
                    {
                        "source_index": 1,
                        "roll": 57,
                        "zoom": 0.8159,
                        "mirror": false,
                        "vertical_shift": -4
                    },
                    {
                        "source_index": 1,
                        "roll": 1768,
                        "zoom": 0.706,
                        "mirror": false,
                        "vertical_shift": 11
                    },
                    {
                        "source_index": 1,
                        "roll": 1390,
                        "zoom": 0.8999,
                        "mirror": false,
                        "vertical_shift": 10
                    }
                ],
                "haze": true,
                "sources": [
                    "martian_panorama_seamless"
                ]
            }
        }
    },
    "variety": {
        "sourceIds": [
            "martian_panorama",
            "martian_panorama_seamless"
        ],
        "sourceBudget": 2,
        "minimumSourcesForNeighbourConstraint": 4,
        "requiredMinSourceDistance": 3,
        "achievedMinSourceDistance": 2,
        "constraintStatus": "source-budget-limited"
    }
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
