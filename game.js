(function () {
  "use strict";

  var canvas = document.getElementById("view");
  var ctx = canvas.getContext("2d");
  var loading = document.getElementById("loading");
  var progressBar = document.getElementById("progress-bar");
  var progressText = document.getElementById("progress-text");
  var headingReadout = document.getElementById("heading");
  var coordsReadout = document.getElementById("coords");
  var images = {};
  var state = { x: MartianWorld.WORLD.start.x, y: MartianWorld.WORLD.start.y, heading: MartianWorld.WORLD.start.heading };
  var turnInput = 0;
  var lastTime = 0;
  var ready = false;
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

  function render() {
    var node = MartianWorld.getNode(state.x, state.y);
    var image = images[node.image];
    var width = window.innerWidth;
    var height = window.innerHeight;
    ctx.fillStyle = "#351611";
    ctx.fillRect(0, 0, width, height);
    if (!image) return;
    var imageWidth = image.naturalWidth || image.width;
    var imageHeight = image.naturalHeight || image.height;
    var sourceWidth = imageWidth * MartianWorld.WORLD.fovDegrees / MartianWorld.WORLD.spanDegrees;
    var sourceX = imageWidth * MartianWorld.normalizeHeading(state.heading) / MartianWorld.WORLD.spanDegrees - sourceWidth / 2;
    drawWrapped(image, sourceX, sourceWidth, width, height);
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
  }

  function tick(time) {
    var dt = lastTime ? Math.min(0.05, (time - lastTime) / 1000) : 0;
    lastTime = time;
    if (ready && turnInput) state.heading = MartianWorld.normalizeHeading(state.heading + turnInput * 70 * dt);
    render();
    requestAnimationFrame(tick);
  }

  function setTurn(value) { turnInput = value; }

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
    if (["ArrowLeft", "ArrowRight", "a", "d", "A", "D"].indexOf(event.key) !== -1) event.preventDefault();
    if (event.key === "ArrowLeft" || event.key === "a" || event.key === "A") setTurn(-1);
    if (event.key === "ArrowRight" || event.key === "d" || event.key === "D") setTurn(1);
  });
  window.addEventListener("keyup", function (event) {
    if (["ArrowLeft", "ArrowRight", "a", "d", "A", "D"].indexOf(event.key) !== -1) setTurn(0);
  });
  resize();
  loadImages();
  requestAnimationFrame(tick);
}());
