(function () {
  var scene, camera, renderer, controls;
  var stdGroup, stuGroup;
  var trailGroup;
  var animData = null;
  var currentFrame = 0;
  var isPlaying = false;
  var playSpeed = 1.0;
  var lastTime = 0;
  var animFrameId = null;

  // Data is in mm (~1500mm height). SCALE maps to a ~180 unit scene height.
  var SCALE = 0.12;
  var OFFSET_X = 70;

  var COLORS = {
    stdJoint: 0x3399ff,
    stdBone: 0x2277cc,
    stdBody: 0x1a5fa0,
    stuJoint: 0xeeeeee,
    stuBone: 0xaaaaaa,
    stuBody: 0x888888,
    green: 0x27ae60,
    yellow: 0xf39c12,
    red: 0xe74c3c,
  };

  var TRAIL_COUNT = 5;
  var TRAIL_FRAMES = [3, 7, 12, 18, 26];

  // Body-volume semi-transparent capsules (radii already in scene units, NOT mm)
  var BODY_PARTS = [
    { a: "Spine3", b: "Hips", r: 2.2 },
    { a: "LeftShoulder", b: "RightShoulder", r: 0.8 },
    { a: "LeftUpLeg", b: "RightUpLeg", r: 1.5 },
    { a: "LeftShoulder", b: "LeftArm", r: 0.7 },
    { a: "RightShoulder", b: "RightArm", r: 0.7 },
    { a: "LeftArm", b: "LeftForeArm", r: 0.6 },
    { a: "RightArm", b: "RightForeArm", r: 0.6 },
    { a: "LeftForeArm", b: "LeftHand", r: 0.5 },
    { a: "RightForeArm", b: "RightHand", r: 0.5 },
    { a: "LeftUpLeg", b: "LeftLeg", r: 1.0 },
    { a: "RightUpLeg", b: "RightLeg", r: 1.0 },
    { a: "LeftLeg", b: "LeftFoot", r: 0.7 },
    { a: "RightLeg", b: "RightFoot", r: 0.7 },
    { a: "Neck", b: "Spine3", r: 0.7 },
    { a: "Head", b: "Neck", r: 1.0 },
  ];

  var errorJointSet = {};

  function _s(v) { return v * SCALE; }

  function init(containerId) {
    var container = document.getElementById(containerId);
    if (!container) return;

    scene = new THREE.Scene();

    var bgCv = document.createElement("canvas");
    bgCv.width = 2; bgCv.height = 512;
    var bgCtx = bgCv.getContext("2d");
    var grad = bgCtx.createLinearGradient(0, 0, 0, 512);
    grad.addColorStop(0, "#0f1a2e");
    grad.addColorStop(0.5, "#0a1220");
    grad.addColorStop(1, "#060b14");
    bgCtx.fillStyle = grad;
    bgCtx.fillRect(0, 0, 2, 512);
    scene.background = new THREE.CanvasTexture(bgCv);
    scene.fog = new THREE.FogExp2(0x0a1220, 0.002);

    camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.5, 3000);
    camera.position.set(0, 80, 300);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    container.appendChild(renderer.domElement);

    // Lighting
    scene.add(new THREE.AmbientLight(0x223344, 0.5));
    scene.add(new THREE.HemisphereLight(0x334466, 0x111122, 0.4));

    var key = new THREE.DirectionalLight(0xddeeff, 1.0);
    key.position.set(60, 200, 150);
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    key.shadow.camera.left = -200;
    key.shadow.camera.right = 200;
    key.shadow.camera.top = 200;
    key.shadow.camera.bottom = -50;
    key.shadow.bias = -0.001;
    scene.add(key);

    scene.add(Object.assign(new THREE.DirectionalLight(0x4466aa, 0.4), { position: new THREE.Vector3(-150, 100, -80) }));

    // Rim lights
    scene.add(Object.assign(new THREE.DirectionalLight(0x3366cc, 0.5), { position: new THREE.Vector3(-120, 30, -200) }));
    scene.add(Object.assign(new THREE.DirectionalLight(0xcc6633, 0.25), { position: new THREE.Vector3(120, 30, -200) }));

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 75, 0);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 40;
    controls.maxDistance = 1200;
    controls.update();

    // Ground
    var gCv = document.createElement("canvas");
    gCv.width = 512; gCv.height = 512;
    var gCtx = gCv.getContext("2d");
    var gGrad = gCtx.createRadialGradient(256, 256, 0, 256, 256, 360);
    gGrad.addColorStop(0, "#181828");
    gGrad.addColorStop(0.5, "#101018");
    gGrad.addColorStop(1, "#08080e");
    gCtx.fillStyle = gGrad;
    gCtx.fillRect(0, 0, 512, 512);

    var ground = new THREE.Mesh(
      new THREE.PlaneGeometry(1200, 1200),
      new THREE.MeshStandardMaterial({ map: new THREE.CanvasTexture(gCv), roughness: 0.6, metalness: 0.3 })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.5;
    ground.receiveShadow = true;
    scene.add(ground);

    var grid = new THREE.GridHelper(1200, 30, 0x1a2a44, 0x0d1520);
    grid.material.opacity = 0.4;
    grid.material.transparent = true;
    scene.add(grid);

    // Spotlights on each skeleton
    var s1 = new THREE.SpotLight(0x3388dd, 0.7, 400, Math.PI / 5, 0.6, 1);
    s1.position.set(-OFFSET_X, 200, 80);
    s1.target.position.set(-OFFSET_X, 0, 0);
    scene.add(s1); scene.add(s1.target);

    var s2 = new THREE.SpotLight(0xdddddd, 0.7, 400, Math.PI / 5, 0.6, 1);
    s2.position.set(OFFSET_X, 200, 80);
    s2.target.position.set(OFFSET_X, 0, 0);
    scene.add(s2); scene.add(s2.target);

    stdGroup = new THREE.Group();
    stdGroup.position.x = -OFFSET_X;
    scene.add(stdGroup);

    stuGroup = new THREE.Group();
    stuGroup.position.x = OFFSET_X;
    scene.add(stuGroup);

    trailGroup = new THREE.Group();
    scene.add(trailGroup);

    new ResizeObserver(function () {
      var cw = container.clientWidth, ch = container.clientHeight;
      camera.aspect = cw / ch;
      camera.updateProjectionMatrix();
      renderer.setSize(cw, ch);
    }).observe(container);

    render();
  }

  function createLabels() {
    ["labelStd", "labelStu"].forEach(function (n) {
      var o = scene.getObjectByName(n);
      if (o) { scene.remove(o); o.material.map.dispose(); o.material.dispose(); }
    });
    function mkLabel(text, color, x) {
      var cv = document.createElement("canvas");
      cv.width = 512; cv.height = 128;
      var ctx = cv.getContext("2d");
      ctx.shadowColor = color; ctx.shadowBlur = 20;
      ctx.fillStyle = color;
      ctx.font = "bold 44px sans-serif";
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(text, 256, 64);
      ctx.fillText(text, 256, 64);
      var sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(cv), transparent: true, depthWrite: false }));
      sp.scale.set(60, 15, 1);
      sp.position.set(x, 200, 0);
      return sp;
    }
    var ls = mkLabel("标准动作", "#3399ff", -OFFSET_X);
    ls.name = "labelStd"; scene.add(ls);
    var le = mkLabel("学生动作", "#ffffff", OFFSET_X);
    le.name = "labelStu"; scene.add(le);
  }

  function loadData(data) {
    animData = data;
    currentFrame = 0;
    errorJointSet = {};
    clearGroup(stdGroup);
    clearGroup(stuGroup);
    clearGroup(trailGroup);
    createLabels();

    var jointNames = data.joint_names;
    var nameMap = {};
    for (var i = 0; i < jointNames.length; i++) nameMap[jointNames[i]] = i;

    buildSkeleton(stdGroup, jointNames, data.bone_connections, COLORS.stdJoint, COLORS.stdBone, COLORS.stdBody, nameMap);
    buildSkeleton(stuGroup, jointNames, data.bone_connections, COLORS.stuJoint, COLORS.stuBone, COLORS.stuBody, nameMap);
    buildTrails();

    applyFrame(0);
    applyJointColors(data.joint_colors);
    render();
  }

  function clearGroup(group) {
    while (group.children.length > 0) {
      var ch = group.children[0];
      group.remove(ch);
      if (ch.geometry) ch.geometry.dispose();
      if (ch.material) { if (ch.material.map) ch.material.map.dispose(); ch.material.dispose(); }
    }
  }

  function buildSkeleton(group, jointNames, bones, jointColor, boneColor, bodyColor, nameMap) {
    for (var i = 0; i < jointNames.length; i++) {
      var isHead = (jointNames[i] === "Head");
      var geo;
      if (isHead) {
        geo = new THREE.SphereGeometry(1.8, 20, 20);
        geo.scale(1, 1.15, 1);
      } else {
        geo = new THREE.SphereGeometry(0.6, 12, 12);
      }
      var m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
        color: jointColor, emissive: jointColor, emissiveIntensity: 0.3,
        roughness: 0.3, metalness: 0.4,
      }));
      m.castShadow = true;
      m.name = "joint_" + i;
      group.add(m);
    }

    for (var b = 0; b < bones.length; b++) {
      var r = getBoneRadius(jointNames, bones[b]);
      var geo = new THREE.CylinderGeometry(r[1], r[0], 1, 8);
      geo.translate(0, 0.5, 0);
      var m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
        color: boneColor, emissive: boneColor, emissiveIntensity: 0.12,
        roughness: 0.35, metalness: 0.3,
      }));
      m.castShadow = true;
      m.visible = false;
      m.name = "bone_" + b;
      group.add(m);
    }

    for (var p = 0; p < BODY_PARTS.length; p++) {
      var bp = BODY_PARTS[p];
      var aIdx = nameMap[bp.a], bIdx = nameMap[bp.b];
      if (aIdx === undefined || bIdx === undefined) continue;
      var geo = new THREE.CylinderGeometry(bp.r, bp.r, 1, 12);
      geo.translate(0, 0.5, 0);
      var m = new THREE.Mesh(geo, new THREE.MeshPhysicalMaterial({
        color: bodyColor, transparent: true, opacity: 0.12,
        roughness: 0.7, metalness: 0.1, side: THREE.DoubleSide,
        clearcoat: 0.3, clearcoatRoughness: 0.5,
      }));
      m.castShadow = false;
      m.visible = false;
      m.name = "body_" + aIdx + "_" + bIdx;
      m.userData = { aIdx: aIdx, bIdx: bIdx };
      group.add(m);
    }
  }

  function getBoneRadius(jointNames, bonePair) {
    var a = jointNames[bonePair[0]], b = jointNames[bonePair[1]];
    var r = 0.4;
    if (a.indexOf("Leg") >= 0 || b.indexOf("Leg") >= 0 ||
        a.indexOf("UpLeg") >= 0 || b.indexOf("UpLeg") >= 0) r = 0.55;
    if (a.indexOf("Spine") >= 0 || b.indexOf("Spine") >= 0) r = 0.5;
    if (a.indexOf("Shoulder") >= 0 || b.indexOf("Shoulder") >= 0) r = 0.45;
    return [r, r * 0.7];
  }

  function buildTrails() {
    if (!animData) return;
    var bones = animData.bone_connections;
    for (var t = 0; t < TRAIL_COUNT; t++) {
      var opacity = 0.04 + 0.05 * (TRAIL_COUNT - t) / TRAIL_COUNT;
      var s = 0.5 + 0.4 * t / TRAIL_COUNT;
      for (var b = 0; b < bones.length; b++) {
        var geo = new THREE.CylinderGeometry(0.25 * s, 0.2 * s, 1, 6);
        geo.translate(0, 0.5, 0);
        var m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({
          color: COLORS.stuBone, transparent: true, opacity: opacity, depthWrite: false,
        }));
        m.visible = false;
        m.name = "trail_" + t + "_bone_" + b;
        trailGroup.add(m);
      }
    }
  }

  var _up = new THREE.Vector3(0, 1, 0);
  var _dir = new THREE.Vector3();
  var _quat = new THREE.Quaternion();

  function _orientCylinder(mesh, pA, pB) {
    _dir.subVectors(pB, pA);
    var len = _dir.length();
    if (len < 0.1) { mesh.visible = false; return; }
    mesh.visible = true;
    mesh.scale.set(1, len, 1);
    mesh.position.copy(pA);
    _dir.normalize();
    _quat.setFromUnitVectors(_up, _dir);
    mesh.quaternion.copy(_quat);
  }

  function applyFrame(frameIdx) {
    if (!animData) return;
    var idx = Math.min(frameIdx, animData.frame_count - 1);
    setGroupPose(stdGroup, animData.std_frames[idx]);
    setGroupPose(stuGroup, animData.stu_frames[idx]);
    updateTrails(idx);
    updateErrorLines(idx);
  }

  function setGroupPose(group, frameData) {
    if (!frameData) return;
    var n = animData.joint_names.length;
    for (var i = 0; i < n; i++) {
      var obj = group.getObjectByName("joint_" + i);
      if (obj) obj.position.set(_s(frameData[i * 3]), _s(frameData[i * 3 + 1]), _s(frameData[i * 3 + 2]));
    }
    var bones = animData.bone_connections;
    for (var b = 0; b < bones.length; b++) {
      var bm = group.getObjectByName("bone_" + b);
      if (!bm) continue;
      var a = group.getObjectByName("joint_" + bones[b][0]);
      var c = group.getObjectByName("joint_" + bones[b][1]);
      if (a && c) _orientCylinder(bm, a.position, c.position);
    }
    for (var ci = 0; ci < group.children.length; ci++) {
      var ch = group.children[ci];
      if (!ch.name || !ch.name.startsWith("body_")) continue;
      var aObj = group.getObjectByName("joint_" + ch.userData.aIdx);
      var bObj = group.getObjectByName("joint_" + ch.userData.bIdx);
      if (aObj && bObj) _orientCylinder(ch, aObj.position, bObj.position);
    }
  }

  function updateTrails(frameIdx) {
    var bones = animData.bone_connections;
    for (var t = 0; t < TRAIL_COUNT; t++) {
      var trailFrame = frameIdx - TRAIL_FRAMES[t];
      if (trailFrame < 0) {
        for (var b = 0; b < bones.length; b++) {
          var m = trailGroup.getObjectByName("trail_" + t + "_bone_" + b);
          if (m) m.visible = false;
        }
        continue;
      }
      var frameData = animData.stu_frames[trailFrame];
      if (!frameData) continue;
      for (var b = 0; b < bones.length; b++) {
        var m = trailGroup.getObjectByName("trail_" + t + "_bone_" + b);
        if (!m) continue;
        var ai = bones[b][0], bi = bones[b][1];
        _orientCylinder(m,
          new THREE.Vector3(_s(frameData[ai * 3]) + OFFSET_X, _s(frameData[ai * 3 + 1]), _s(frameData[ai * 3 + 2])),
          new THREE.Vector3(_s(frameData[bi * 3]) + OFFSET_X, _s(frameData[bi * 3 + 1]), _s(frameData[bi * 3 + 2])));
      }
    }
  }

  var errorLineGroup = null;

  function updateErrorLines(frameIdx) {
    if (errorLineGroup) { scene.remove(errorLineGroup); clearGroup(errorLineGroup); }
    if (!animData || !animData.joint_colors) return;
    var hasErrors = false;
    for (var i = 0; i < animData.joint_colors.length; i++) {
      if (animData.joint_colors[i].color !== "default") { hasErrors = true; break; }
    }
    if (!hasErrors) return;

    errorLineGroup = new THREE.Group();
    var idx = Math.min(frameIdx, animData.frame_count - 1);
    var stdF = animData.std_frames[idx], stuF = animData.stu_frames[idx];
    if (!stdF || !stuF) return;

    var n = animData.joint_names.length;
    for (var i = 0; i < n; i++) {
      if (!errorJointSet[i]) continue;
      // std skeleton is at x=-OFFSET_X, stu at +OFFSET_X in world space
      var sx = _s(stdF[i * 3]) - OFFSET_X, sy = _s(stdF[i * 3 + 1]), sz = _s(stdF[i * 3 + 2]);
      var ux = _s(stuF[i * 3]) + OFFSET_X, uy = _s(stuF[i * 3 + 1]), uz = _s(stuF[i * 3 + 2]);
      var dist = Math.sqrt((sx - ux) * (sx - ux) + (sy - uy) * (sy - uy) + (sz - uz) * (sz - uz));
      if (dist < 2) continue;

      var geo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(sx, sy, sz), new THREE.Vector3(ux, uy, uz)
      ]);
      var lineColor = dist > 40 ? COLORS.red : dist > 15 ? COLORS.yellow : 0x4488ff;
      errorLineGroup.add(new THREE.Line(geo, new THREE.LineBasicMaterial({
        color: lineColor, transparent: true, opacity: 0.5, depthWrite: false,
      })));
    }
    scene.add(errorLineGroup);
  }

  function applyJointColors(jointColors) {
    if (!jointColors) return;
    errorJointSet = {};
    var cn = { red: COLORS.red, yellow: COLORS.yellow, green: COLORS.green };

    for (var i = 0; i < jointColors.length; i++) {
      var jc = jointColors[i];
      if (jc.color === "default") continue;
      var color = cn[jc.color] || COLORS.stuJoint;
      errorJointSet[jc.joint] = { color: color, level: jc.color };

      var obj = stuGroup.getObjectByName("joint_" + i);
      if (!obj) continue;
      obj.material.color.setHex(color);
      obj.material.emissive.setHex(color);
      obj.material.emissiveIntensity = 0.8;
      obj.scale.set(1.8, 1.8, 1.8);
    }

    var bones = animData.bone_connections;
    for (var b = 0; b < bones.length; b++) {
      var errInfo = errorJointSet[bones[b][0]] || errorJointSet[bones[b][1]];
      if (!errInfo) continue;
      var bm = stuGroup.getObjectByName("bone_" + b);
      if (bm) {
        bm.material.color.setHex(errInfo.color);
        bm.material.emissive.setHex(errInfo.color);
        bm.material.emissiveIntensity = 0.5;
      }
    }

    for (var ci = 0; ci < stuGroup.children.length; ci++) {
      var ch = stuGroup.children[ci];
      if (!ch.name || !ch.name.startsWith("body_")) continue;
      var errInfo2 = errorJointSet[ch.userData.aIdx] || errorJointSet[ch.userData.bIdx];
      if (errInfo2) {
        ch.material.color.setHex(errInfo2.color);
        ch.material.opacity = 0.22;
      }
    }
  }

  function play() {
    if (!animData) return;
    isPlaying = true;
    lastTime = performance.now();
    animate();
  }

  function pause() {
    isPlaying = false;
    if (animFrameId) { cancelAnimationFrame(animFrameId); animFrameId = null; }
  }

  function animate() {
    if (!isPlaying) return;
    var now = performance.now();
    var elapsed = now - lastTime;
    var frameDuration = 1000 / (animData.fps * playSpeed);
    if (elapsed >= frameDuration) {
      currentFrame++;
      if (currentFrame >= animData.frame_count) {
        currentFrame = animData.frame_count - 1;
        isPlaying = false;
        if (typeof window.on3dPlaybackEnd === "function") window.on3dPlaybackEnd();
        render();
        return;
      }
      applyFrame(currentFrame);
      lastTime = now;
      if (typeof window.on3dFrameChange === "function") window.on3dFrameChange(currentFrame);
    }
    pulseErrorJoints(now);
    render();
    animFrameId = requestAnimationFrame(animate);
  }

  function pulseErrorJoints(time) {
    var pulse = 0.5 + 0.5 * Math.sin(time * 0.005);
    for (var idx in errorJointSet) {
      var obj = stuGroup.getObjectByName("joint_" + idx);
      if (obj) {
        obj.material.emissiveIntensity = 0.4 + pulse * 0.6;
        var s = 1.5 + pulse * 0.5;
        obj.scale.set(s, s, s);
      }
    }
  }

  function seekTo(frameIdx) {
    currentFrame = Math.max(0, Math.min(frameIdx, animData ? animData.frame_count - 1 : 0));
    applyFrame(currentFrame);
    render();
  }

  function setSpeed(speed) { playSpeed = speed; }

  function render() {
    if (controls) controls.update();
    if (renderer && scene && camera) renderer.render(scene, camera);
  }

  window.Skeleton3D = {
    init: init, loadData: loadData, play: play, pause: pause,
    seekTo: seekTo, setSpeed: setSpeed,
    getFrameCount: function () { return animData ? animData.frame_count : 0; },
    getCurrentFrame: function () { return currentFrame; },
    isPlaying: function () { return isPlaying; },
  };
})();
