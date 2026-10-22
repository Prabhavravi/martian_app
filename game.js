(function () {
  "use strict";

  var canvas = document.getElementById("view");
  var ctx = canvas.getContext("2d");
  var loading = document.getElementById("loading");
  var progressBar = document.getElementById("progress-bar");
  var progressText = document.getElementById("progress-text");
  var headingReadout = document.getElementById("heading");
  var coordsReadout = document.getElementById("coords");
  var compassNeedle = document.getElementById("compass-needle");
  var minimapMarker = document.getElementById("minimap-marker");
  var minimapFacing = document.getElementById("minimap-facing");
  var images = {};
  var state = { x: MartianWorld.WORLD.start.x, y: MartianWorld.WORLD.start.y, heading: MartianWorld.WORLD.start.heading };
  var transition = null;
  var bumpTimer = 0;
  var turnInput = 0;
  var lastTime = 0;
  var ready = false;
  var transitionDuration = 700;
  var cardinalNames = ["N", "E", "S", "W"];

  function resize() {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(window.innerWidth * dpr);
    canvas.height = Math.floor(window.innerHeight * dpr);
    canvas.style.width = window.innerWidth + "px";
    canvas.style.height = window.innerHeight + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function drawWrapped(image, sourceX, sourceWidth, width, height) {
    var imageWidth = image.naturalWidth || image.width;
    var sourceHeight = image.naturalHeight || image.height;
    var remaining = sourceWidth;
    var cursor = 0;
    var x = sourceX;
    while (remaining > 0.01) {
      var wrappedX = ((x % imageWidth) + imageWidth) % imageWidth;
      var chunk = Math.min(remaining, imageWidth - wrappedX);
      ctx.drawImage(image, wrappedX, 0, chunk, sourceHeight, cursor * width / sourceWidth, 0, chunk * width / sourceWidth, height);
      cursor += chunk;
      remaining -= chunk;
      x += chunk;
    }
  }

  function drawNode(node, heading, zoom, alpha, width, height) {
    var image = images[node.image];
    if (!image) return;
    var imageWidth = image.naturalWidth || image.width;
    var sourceWidth = imageWidth * MartianWorld.WORLD.fovDegrees / MartianWorld.WORLD.spanDegrees / zoom;
    var sourceX = imageWidth * MartianWorld.normalizeHeading(heading) / MartianWorld.WORLD.spanDegrees - sourceWidth / 2;
    ctx.globalAlpha = alpha;
    drawWrapped(image, sourceX, sourceWidth, width, height);
    ctx.globalAlpha = 1;
  }

  function render() {
    var width = window.innerWidth;
    var height = window.innerHeight;
    ctx.fillStyle = "#351611";
    ctx.fillRect(0, 0, width, height);
    if (!ready) return;
    var shake = bumpTimer > 0 ? Math.sin(bumpTimer * 0.09) * Math.min(5, bumpTimer * 0.03) : 0;
    ctx.save();
    ctx.translate(shake, 0);
    if (transition) {
      var progress = Math.min(1, Math.max(0, (performance.now() - transition.startedAt) / transitionDuration));
      if (transition.direction > 0) {
        drawNode(transition.fromNode, state.heading, 1 + 0.2 * progress, 1 - progress, width, height);
        drawNode(transition.toNode, state.heading, 0.9 + 0.1 * progress, progress, width, height);
      } else {
        drawNode(transition.fromNode, state.heading, 0.9 + 0.1 * progress, 1 - progress, width, height);
        drawNode(transition.toNode, state.heading, 1.2 - 0.2 * progress, progress, width, height);
      }
    } else {
      drawNode(MartianWorld.getNode(state.x, state.y), state.heading, 1, 1, width, height);
    }
    ctx.restore();
    var shade = ctx.createLinearGradient(0, 0, 0, height);
    shade.addColorStop(0, "rgba(12, 5, 4, 0.12)");
    shade.addColorStop(0.68, "rgba(12, 5, 4, 0)");
    shade.addColorStop(1, "rgba(12, 5, 4, 0.2)");
    ctx.fillStyle = shade;
    ctx.fillRect(0, 0, width, height);
    updateHud();
  }

  function updateHud() {
    var normalized = MartianWorld.normalizeHeading(state.heading);
    var cardinal = cardinalNames[Math.round(normalized / 90) % 4];
    headingReadout.textContent = String(Math.round(normalized)).padStart(3, "0") + "° " + cardinal;
    coordsReadout.textContent = String(state.x + 1).padStart(2, "0") + " · " + String(state.y + 1).padStart(2, "0");
    compassNeedle.style.transform = "translateX(-50%) rotate(" + normalized + "deg)";
    minimapMarker.style.left = (10 + (state.x + 0.5) / MartianWorld.WORLD.width * 90) + "px";
    minimapMarker.style.top = (10 + (state.y + 0.5) / MartianWorld.WORLD.height * 90) + "px";
    minimapFacing.style.transform = "rotate(" + normalized + "deg)";
  }

  function requestMove(direction) {
    if (!ready || transition) return;
    var result = MartianWorld.moveOneNode(state, direction, MartianWorld.WORLD);
    if (!result.moved) {
      bumpTimer = 220;
      return;
    }
    transition = {
      fromNode: MartianWorld.getNode(state.x, state.y),
      toNode: MartianWorld.getNode(result.state.x, result.state.y),
      direction: direction,
      targetState: result.state,
      startedAt: performance.now()
    };
    turnInput = 0;
  }

  function tick(time) {
    var dt = lastTime ? Math.min(0.05, (time - lastTime) / 1000) : 0;
    lastTime = time;
    if (bumpTimer > 0) bumpTimer = Math.max(0, bumpTimer - dt * 1000);
    if (transition && time - transition.startedAt >= transitionDuration) {
      state = transition.targetState;
      transition = null;
    }
    if (ready && !transition && turnInput) state.heading = MartianWorld.normalizeHeading(state.heading + turnInput * 70 * dt);
    render();
    requestAnimationFrame(tick);
  }

  function setTurn(value) { turnInput = value; }

  function bindControls() {
    var holdButtons = [
      ["turn-left", -1],
      ["turn-right", 1]
    ];
    holdButtons.forEach(function (entry) {
      var button = document.getElementById(entry[0]);
      button.addEventListener("pointerdown", function (event) { event.preventDefault(); if (!transition) setTurn(entry[1]); });
      button.addEventListener("pointerup", function () { setTurn(0); });
      button.addEventListener("pointerleave", function () { setTurn(0); });
      button.addEventListener("pointercancel", function () { setTurn(0); });
    });
    document.getElementById("drive-forward").addEventListener("click", function () { requestMove(1); });
    document.getElementById("drive-back").addEventListener("click", function () { requestMove(-1); });
  }

  function loadImages() {
    var nodes = MartianWorld.WORLD.nodes;
    var keys = Object.keys(nodes);
    var loaded = 0;
    keys.forEach(function (nodeKey) {
      var path = nodes[nodeKey].image;
      var image = new Image();
      image.onload = function () {
        images[path] = image;
        loaded += 1;
        var percent = Math.round(loaded / keys.length * 100);
        progressBar.style.width = percent + "%";
        progressText.textContent = "Loading Martian panoramas · " + percent + "%";
        if (loaded === keys.length) {
          ready = true;
          loading.classList.add("ready");
          render();
        }
      };
      image.onerror = function () { progressText.textContent = "Panorama failed to load: " + path; };
      image.src = path;
    });
  }

  window.addEventListener("resize", resize);
  window.addEventListener("keydown", function (event) {
    var turnKeys = ["ArrowLeft", "ArrowRight", "a", "d", "A", "D"];
    var moveKeys = ["ArrowUp", "ArrowDown", "w", "s", "W", "S"];
    if (turnKeys.indexOf(event.key) !== -1 || moveKeys.indexOf(event.key) !== -1) event.preventDefault();
    if (transition) return;
    if (event.key === "ArrowLeft" || event.key === "a" || event.key === "A") setTurn(-1);
    if (event.key === "ArrowRight" || event.key === "d" || event.key === "D") setTurn(1);
    if (!event.repeat && (event.key === "ArrowUp" || event.key === "w" || event.key === "W")) requestMove(1);
    if (!event.repeat && (event.key === "ArrowDown" || event.key === "s" || event.key === "S")) requestMove(-1);
  });
  window.addEventListener("keyup", function (event) {
    if (["ArrowLeft", "ArrowRight", "a", "d", "A", "D"].indexOf(event.key) !== -1) setTurn(0);
  });
  resize();
  bindControls();
  loadImages();
  requestAnimationFrame(tick);
}());
