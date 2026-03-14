(function () {
  if (!window.THREE) return;

  const container = document.getElementById('robot-container');
  if (!container) return;

  const scene = new THREE.Scene();

  const camera = new THREE.PerspectiveCamera(60, 1, 0.1, 1000);
  camera.position.set(0, 1.2, 5);

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  container.appendChild(renderer.domElement);

  const ambient = new THREE.AmbientLight(0x66ccff, 0.6);
  scene.add(ambient);

  const key = new THREE.DirectionalLight(0xffffff, 1);
  key.position.set(2, 2, 2);
  scene.add(key);

  const rim = new THREE.DirectionalLight(0x00f5ff, 0.6);
  rim.position.set(-2, 1, -2);
  scene.add(rim);

  let robot = null;
  let state = 'idle';

  function buildFallbackRobot() {
    const group = new THREE.Group();

    const bodyMat = new THREE.MeshStandardMaterial({
      color: 0x0b2233,
      metalness: 0.7,
      roughness: 0.25,
      emissive: 0x001122,
      emissiveIntensity: 0.6,
    });

    const accentMat = new THREE.MeshStandardMaterial({
      color: 0x00f5ff,
      metalness: 0.2,
      roughness: 0.1,
      emissive: 0x00f5ff,
      emissiveIntensity: 0.7,
    });

    const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.55, 1.0, 6, 12), bodyMat);
    torso.position.y = 0.6;
    group.add(torso);

    const head = new THREE.Mesh(new THREE.SphereGeometry(0.38, 18, 18), bodyMat);
    head.position.y = 1.55;
    group.add(head);

    const visor = new THREE.Mesh(new THREE.TorusGeometry(0.22, 0.06, 10, 20), accentMat);
    visor.position.set(0, 1.55, 0.32);
    visor.rotation.x = Math.PI / 2;
    group.add(visor);

    const core = new THREE.Mesh(new THREE.SphereGeometry(0.12, 14, 14), accentMat);
    core.position.set(0, 0.75, 0.52);
    group.add(core);

    const base = new THREE.Mesh(new THREE.CylinderGeometry(0.75, 0.9, 0.18, 18), bodyMat);
    base.position.y = -0.05;
    group.add(base);

    group.position.y = 0.2;
    return group;
  }

  robot = buildFallbackRobot();
  scene.add(robot);

  // Try to load a real GLB model if present
  if (THREE.GLTFLoader) {
    try {
      const loader = new THREE.GLTFLoader();
      loader.load(
        '/static/models/robot.glb',
        function (gltf) {
          if (robot) scene.remove(robot);
          robot = gltf.scene;
          robot.scale.setScalar(1.2);
          robot.position.y = 0;
          scene.add(robot);
        },
        undefined,
        function () {
          // Keep fallback robot
        }
      );
    } catch (e) {
      // Keep fallback robot
    }
  }

  function resize() {
    const w = Math.max(1, container.clientWidth || window.innerWidth);
    const h = Math.max(1, container.clientHeight || 320);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
  }

  resize();
  window.addEventListener('resize', resize);

  if (window.ResizeObserver) {
    const ro = new ResizeObserver(resize);
    ro.observe(container);
  }

  function setRobotState(next) {
    state = String(next || 'idle').toLowerCase();
  }

  window.setRobotState = setRobotState;

  let t0 = performance.now();

  function animate(now) {
    requestAnimationFrame(animate);

    const dt = Math.min(0.05, (now - t0) / 1000);
    t0 = now;

    if (robot) {
      // Baseline idle motion
      robot.rotation.y += dt * 0.35;

      if (state === 'listening') {
        robot.rotation.y += dt * 1.4;
      } else if (state === 'thinking') {
        robot.rotation.x = Math.sin(now * 0.003) * 0.15;
        robot.rotation.y += dt * 0.6;
      } else if (state === 'speaking') {
        const s = 1 + Math.sin(now * 0.01) * 0.03;
        robot.scale.set(s, s, s);
        robot.rotation.y += dt * 0.8;
      } else {
        robot.rotation.x *= 0.9;
        robot.scale.lerp(new THREE.Vector3(1, 1, 1), 0.08);
      }
    }

    renderer.render(scene, camera);
  }

  animate(t0);
})();
