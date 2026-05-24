(function () {
  let scene, camera, renderer, controls;
  let stdGroup, stuGroup;
  let animData = null;
  let currentFrame = 0;
  let isPlaying = false;
  let playSpeed = 1.0;
  let lastTime = 0;
  let animFrameId = null;

  const JOINT_RADIUS = 3;
  const BONE_WIDTH = 2;
  const OFFSET_X = 150;

  const COLORS = {
    default: 0x4472c4,
    green: 0x27ae60,
    yellow: 0xf39c12,
    red: 0xe74c3c,
    stdJoint: 0x4472c4,
    stuJoint: 0xffffff,
    stdBone: 0x3a64b0,
    stuBone: 0x888888,
  };

  function init(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0d1b2a);

    camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 1, 5000);
    camera.position.set(0, 100, 500);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    const ambient = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambient);
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(100, 200, 150);
    scene.add(dirLight);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 100, 0);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.update();

    const grid = new THREE.GridHelper(600, 20, 0x2a3f5f, 0x1a2538);
    grid.position.y = 0;
    scene.add(grid);

    stdGroup = new THREE.Group();
    stdGroup.position.x = -OFFSET_X;
    scene.add(stdGroup);

    stuGroup = new THREE.Group();
    stuGroup.position.x = OFFSET_X;
    scene.add(stuGroup);

    const resizeObs = new ResizeObserver(function () {
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    });
    resizeObs.observe(container);

    render();
  }

  function createLabels() {
    if (scene.getObjectByName("labelStd")) scene.remove(scene.getObjectByName("labelStd"));
    if (scene.getObjectByName("labelStu")) scene.remove(scene.getObjectByName("labelStu"));

    function makeLabel(text, color, x) {
      const canvas = document.createElement("canvas");
      canvas.width = 256;
      canvas.height = 64;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = color;
      ctx.font = "bold 28px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(text, 128, 40);
      const tex = new THREE.CanvasTexture(canvas);
      const mat = new THREE.SpriteMaterial({ map: tex, transparent: true });
      const sprite = new THREE.Sprite(mat);
      sprite.scale.set(80, 20, 1);
      sprite.position.set(x, 280, 0);
      return sprite;
    }

    const ls = makeLabel("标准动作", "#4472c4", -OFFSET_X);
    ls.name = "labelStd";
    scene.add(ls);
    const le = makeLabel("学生动作", "#ffffff", OFFSET_X);
    le.name = "labelStu";
    scene.add(le);
  }

  function loadData(data) {
    animData = data;
    currentFrame = 0;

    clearGroup(stdGroup);
    clearGroup(stuGroup);
    createLabels();

    buildSkeleton(stdGroup, data.joint_names.length, data.bone_connections, COLORS.stdJoint, COLORS.stdBone);
    buildSkeleton(stuGroup, data.joint_names.length, data.bone_connections, COLORS.stuJoint, COLORS.stuBone);

    applyFrame(0);
    applyJointColors(data.joint_colors);

    render();
  }

  function clearGroup(group) {
    while (group.children.length > 0) {
      const c = group.children[0];
      group.remove(c);
      if (c.geometry) c.geometry.dispose();
      if (c.material) {
        if (c.material.map) c.material.map.dispose();
        c.material.dispose();
      }
    }
  }

  function buildSkeleton(group, jointCount, bones, jointColor, boneColor) {
    const jointGeo = new THREE.SphereGeometry(JOINT_RADIUS, 12, 12);
    for (let i = 0; i < jointCount; i++) {
      const mat = new THREE.MeshStandardMaterial({ color: jointColor, emissive: jointColor, emissiveIntensity: 0.3 });
      const sphere = new THREE.Mesh(jointGeo, mat);
      sphere.name = "joint_" + i;
      sphere.position.set(0, 0, 0);
      group.add(sphere);
    }

    const positions = new Float32Array(bones.length * 6);
    const boneGeo = new THREE.BufferGeometry();
    boneGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const boneMat = new THREE.LineBasicMaterial({ color: boneColor, linewidth: BONE_WIDTH });
    const lineSegs = new THREE.LineSegments(boneGeo, boneMat);
    lineSegs.name = "bones";
    group.add(lineSegs);
  }

  function applyFrame(frameIdx) {
    if (!animData) return;
    const idx = Math.min(frameIdx, animData.frame_count - 1);
    setGroupPose(stdGroup, animData.std_frames[idx], animData.bone_connections);
    setGroupPose(stuGroup, animData.stu_frames[idx], animData.bone_connections);
  }

  function setGroupPose(group, frameData, bones) {
    if (!frameData) return;
    for (let i = 0; i < animData.joint_names.length; i++) {
      const obj = group.getObjectByName("joint_" + i);
      if (obj) {
        obj.position.set(frameData[i * 3], frameData[i * 3 + 1], frameData[i * 3 + 2]);
      }
    }
    const lineSegs = group.getObjectByName("bones");
    if (lineSegs && bones) {
      const pos = lineSegs.geometry.attributes.position.array;
      for (let b = 0; b < bones.length; b++) {
        const a = group.getObjectByName("joint_" + bones[b][0]);
        const c = group.getObjectByName("joint_" + bones[b][1]);
        if (a && c) {
          pos[b * 6] = a.position.x;
          pos[b * 6 + 1] = a.position.y;
          pos[b * 6 + 2] = a.position.z;
          pos[b * 6 + 3] = c.position.x;
          pos[b * 6 + 4] = c.position.y;
          pos[b * 6 + 5] = c.position.z;
        }
      }
      lineSegs.geometry.attributes.position.needsUpdate = true;
    }
  }

  function applyJointColors(jointColors) {
    if (!jointColors) return;
    const cn = { red: 0xe74c3c, yellow: 0xf39c12, green: 0x27ae60 };
    for (const jc of jointColors) {
      const idx = animData.joint_names.indexOf(jc.joint);
      if (idx < 0) continue;
      const obj = stuGroup.getObjectByName("joint_" + idx);
      if (!obj) continue;
      const hex = cn[jc.color] || COLORS.stuJoint;
      obj.material.color.setHex(hex);
      obj.material.emissive.setHex(hex);
      obj.material.emissiveIntensity = jc.color === "default" ? 0.3 : 0.8;
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
    if (animFrameId) {
      cancelAnimationFrame(animFrameId);
      animFrameId = null;
    }
  }

  function animate() {
    if (!isPlaying) return;
    const now = performance.now();
    const elapsed = now - lastTime;
    const frameDuration = 1000 / (animData.fps * playSpeed);

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

    render();
    animFrameId = requestAnimationFrame(animate);
  }

  function seekTo(frameIdx) {
    currentFrame = Math.max(0, Math.min(frameIdx, animData ? animData.frame_count - 1 : 0));
    applyFrame(currentFrame);
    render();
  }

  function setSpeed(speed) {
    playSpeed = speed;
  }

  function render() {
    if (controls) controls.update();
    if (renderer && scene && camera) renderer.render(scene, camera);
  }

  window.Skeleton3D = {
    init: init,
    loadData: loadData,
    play: play,
    pause: pause,
    seekTo: seekTo,
    setSpeed: setSpeed,
    getFrameCount: function () { return animData ? animData.frame_count : 0; },
    getCurrentFrame: function () { return currentFrame; },
    isPlaying: function () { return isPlaying; },
  };
})();
