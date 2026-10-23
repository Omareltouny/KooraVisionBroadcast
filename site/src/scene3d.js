// KooraVision 3D moment player. Bundled with three.js into site/vendor/scene3d.js (see tools/build_scene3d.sh).
// Input: a scene JSON made by kvagents/reconstruct.py (illustrative reconstruction of synthetic tracking).
import {
  WebGLRenderer, Scene, PerspectiveCamera, Color, Fog, Group, Mesh, Vector3, CanvasTexture, SRGBColorSpace, DoubleSide,
  PlaneGeometry, CapsuleGeometry, SphereGeometry, CylinderGeometry, BoxGeometry, RingGeometry, CircleGeometry, BufferGeometry,
  BufferAttribute, MeshBasicMaterial, MeshLambertMaterial, AmbientLight, DirectionalLight, HemisphereLight, Sprite, SpriteMaterial,
  MathUtils, LinearFilter,
} from "three";

const TEXT = {
  en: { play: "Play", pause: "Pause", replay: "Replay", cam: { auto: "Auto", tactical: "Tactical", behind: "Behind play", pov: "Player view" },
        badge: "Illustrative reconstruction · synthetic tracking", speed: "Speed", legendDecoy: "Decoy run", legendMarker: "His marker", legendPass: "Pass / shot",
        legendGaze: "Where he looks", legendTarget: "His choice", pov: "Player view" },
  es: { play: "Reproducir", pause: "Pausa", replay: "Repetir", cam: { auto: "Auto", tactical: "Táctica", behind: "Desde atrás", pov: "Vista del jugador" },
        badge: "Reconstrucción ilustrativa · seguimiento sintético", speed: "Velocidad", legendDecoy: "Carrera señuelo", legendMarker: "Su marcador", legendPass: "Pase / remate",
        legendGaze: "Hacia dónde mira", legendTarget: "Su elección", pov: "Vista del jugador" },
  ar: { play: "تشغيل", pause: "إيقاف مؤقت", replay: "إعادة", cam: { auto: "تلقائي", tactical: "تكتيكي", behind: "من الخلف", pov: "من عيني اللاعب" },
        badge: "إعادة تمثيل توضيحية · تتبّع اصطناعي", speed: "السرعة", legendDecoy: "جري تمويهي", legendMarker: "المدافع المراقب", legendPass: "تمريرة / تسديدة",
        legendGaze: "اتجاه نظره", legendTarget: "اختياره", pov: "من عيني اللاعب" },
};

const css = `
.kv3d{position:relative;border:1px solid var(--line,#D3DBE3);border-radius:10px;overflow:hidden;background:#0B1822;color:#F4F7FA;font-family:var(--body,system-ui,sans-serif);font-size:13px;line-height:1.35}
.kv3d canvas{display:block;width:100%;height:auto;touch-action:pan-y}
.kv3d .kbadge{position:absolute;top:8px;inset-inline-start:8px;background:rgba(7,16,26,.78);color:#C9D7E4;padding:3px 8px;border-radius:6px;font-size:11px;max-width:70%}
.kv3d .kcamrow{position:absolute;top:8px;inset-inline-end:8px;display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end;max-width:60%}
.kv3d .kcamrow button{background:rgba(7,16,26,.78);color:#C9D7E4;border:1px solid rgba(157,176,195,.35);border-radius:6px;padding:3px 8px;font-size:12px}
.kv3d .kcamrow button[aria-pressed=true]{background:#F4F7FA;color:#0D2033;border-color:#F4F7FA;font-weight:600}
.kv3d .kcap{position:absolute;inset-inline:10px;bottom:62px;display:flex;justify-content:center;pointer-events:none}
.kv3d .kcap span{background:rgba(7,16,26,.86);color:#fff;padding:7px 12px;border-radius:8px;font-size:15px;font-weight:500;max-width:min(92%,640px);text-align:center;opacity:0;transition:opacity .25s}
.kv3d .kcap span.on{opacity:1}
.kv3d .klegend{position:absolute;inset-inline-start:8px;bottom:62px;display:flex;flex-direction:column;gap:3px;font-size:11px;color:#C9D7E4;background:rgba(7,16,26,.6);padding:5px 8px;border-radius:6px;pointer-events:none}
.kv3d .klegend i{display:inline-block;width:14px;height:4px;border-radius:2px;margin-inline-end:6px;vertical-align:middle}
.kv3d .kbar{position:absolute;inset-inline:0;bottom:0;display:flex;align-items:center;gap:10px;padding:8px 10px;background:linear-gradient(transparent,rgba(7,16,26,.92) 40%)}
.kv3d .kbar button{background:#F4F7FA;color:#0D2033;border:0;border-radius:6px;padding:5px 12px;font-weight:600;min-width:84px}
.kv3d .ktrack{position:relative;flex:1;height:22px;direction:ltr}
.kv3d .ktrack input{width:100%;margin:0;position:relative;z-index:1;background:transparent;accent-color:#7DB0FF}
.kv3d .ktick{position:absolute;top:0;width:2px;height:6px;background:#F2B632;border-radius:1px;z-index:0;transform:translateX(-1px)}
.kv3d .kbar select{background:rgba(7,16,26,.78);color:#E7EEF4;border:1px solid rgba(157,176,195,.35);border-radius:6px;padding:3px 4px;font-size:12px}
.kv3d .kbar .ktm{font-variant-numeric:tabular-nums;min-width:38px;text-align:end;color:#C9D7E4}
.kv3d .kbig{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(7,16,26,.25)}
.kv3d .kbig button{width:56px;height:56px;border-radius:50%;border:0;background:#F4F7FA;color:#0D2033;font-size:22px;padding:0;opacity:.92}
.kv3d .knogl{padding:30px 16px;text-align:center;color:#C9D7E4}
`;

function injectCss() {
  if (document.getElementById("kv3d-css")) return;
  const s = document.createElement("style");
  s.id = "kv3d-css";
  s.textContent = css;
  document.head.appendChild(s);
}

const L = 105, W = 68;
const wx = (x) => x - L / 2, wz = (y) => y - W / 2;
const lerp = (a, b, u) => a + (b - a) * u;
const smooth = (u) => { u = Math.max(0, Math.min(1, u)); return u * u * (3 - 2 * u); };
const angDiff = (a, b) => ((b - a + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
const lerpAng = (a, b, u) => a + angDiff(a, b) * u;

function colorDist(a, b) {
  const A = new Color(a), B = new Color(b);
  return Math.hypot(A.r - B.r, A.g - B.g, A.b - B.b);
}

function pitchTexture() {
  const s = 20, c = document.createElement("canvas");
  c.width = L * s; c.height = W * s;
  const g = c.getContext("2d");
  for (let i = 0; i < 20; i++) { g.fillStyle = i % 2 ? "#2F7A52" : "#2A704B"; g.fillRect(i * L / 20 * s, 0, L / 20 * s + 1, W * s); }
  g.strokeStyle = "rgba(240,247,242,.92)"; g.lineWidth = 4; g.fillStyle = "rgba(240,247,242,.92)";
  const R = (x, y, w, h) => g.strokeRect(x * s, y * s, w * s, h * s);
  R(0, 0, L, W);
  g.beginPath(); g.moveTo(L / 2 * s, 0); g.lineTo(L / 2 * s, W * s); g.stroke();
  g.beginPath(); g.arc(L / 2 * s, W / 2 * s, 9.15 * s, 0, 7); g.stroke();
  g.beginPath(); g.arc(L / 2 * s, W / 2 * s, 0.35 * s, 0, 7); g.fill();
  for (const side of [0, 1]) {
    const dir = side ? -1 : 1, gx = side ? L : 0;
    R(side ? L - 16.5 : 0, W / 2 - 20.16, 16.5, 40.32);
    R(side ? L - 5.5 : 0, W / 2 - 9.16, 5.5, 18.32);
    const px = gx + dir * 11;
    g.beginPath(); g.arc(px * s, W / 2 * s, 0.35 * s, 0, 7); g.fill();
    const a = Math.acos(5.5 / 9.15);
    g.beginPath();
    if (side) g.arc(px * s, W / 2 * s, 9.15 * s, Math.PI - a, Math.PI + a); else g.arc(px * s, W / 2 * s, 9.15 * s, -a, a);
    g.stroke();
  }
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace; t.anisotropy = 4; t.minFilter = LinearFilter; t.generateMipmaps = false;
  return t;
}

function numberSprite(n, color) {
  const c = document.createElement("canvas"); c.width = c.height = 128;
  const g = c.getContext("2d");
  g.fillStyle = "rgba(7,16,26,.88)"; g.beginPath(); g.arc(64, 64, 58, 0, 7); g.fill();
  g.lineWidth = 8; g.strokeStyle = color; g.stroke();
  g.fillStyle = "#fff"; g.font = "700 64px system-ui, Arial, sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
  g.fillText(String(n), 64, 68);
  const tex = new CanvasTexture(c); tex.colorSpace = SRGBColorSpace;
  const sp = new Sprite(new SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
  sp.scale.set(2.3, 2.3, 1); sp.renderOrder = 10;
  return sp;
}

// flat ribbon on the pitch following a polyline (world coords), width in metres
class Ribbon {
  constructor(color, width, max = 400, opacity = 0.9, y = 0.05) {
    this.max = max; this.w = width; this.y = y;
    this.geo = new BufferGeometry();
    this.pos = new Float32Array(max * 2 * 3);
    this.geo.setAttribute("position", new BufferAttribute(this.pos, 3));
    const idx = [];
    for (let i = 0; i < max - 1; i++) { const a = i * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
    this.geo.setIndex(idx);
    this.mesh = new Mesh(this.geo, new MeshBasicMaterial({ color, transparent: true, opacity, side: DoubleSide, depthWrite: false }));
    this.mesh.renderOrder = 2; this.mesh.frustumCulled = false;
    this.geo.setDrawRange(0, 0);
  }
  set(points) { // [[x,z],...] world
    const n = Math.min(points.length, this.max);
    if (n < 2) { this.geo.setDrawRange(0, 0); return; }
    for (let i = 0; i < n; i++) {
      const p = points[i], a = points[Math.max(i - 1, 0)], b = points[Math.min(i + 1, n - 1)];
      let dx = b[0] - a[0], dz = b[1] - a[1]; const d = Math.hypot(dx, dz) || 1; dx /= d; dz /= d;
      const nx = -dz * this.w / 2, nz = dx * this.w / 2;
      this.pos.set([p[0] + nx, this.y, p[1] + nz, p[0] - nx, this.y, p[1] - nz], i * 6);
    }
    this.geo.attributes.position.needsUpdate = true;
    this.geo.setDrawRange(0, (n - 1) * 6);
  }
}

export function mount(host, scene, opts = {}) {
  injectCss();
  let lang = opts.lang && TEXT[opts.lang] ? opts.lang : "en";
  const T = () => TEXT[lang];
  host.innerHTML = "";
  const root = document.createElement("div"); root.className = "kv3d"; root.dir = lang === "ar" ? "rtl" : "ltr"; host.appendChild(root);

  let renderer;
  try {
    renderer = new WebGLRenderer({ antialias: true, preserveDrawingBuffer: !!opts.preserve });
  } catch (e) {
    root.innerHTML = '<div class="knogl">3D is not available in this browser.</div>';
    return { destroy() {}, setLang() {}, seek() {}, setCam() {}, play() {}, pause() {} };
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  root.appendChild(renderer.domElement);

  const three = new Scene();
  three.background = new Color("#0B1822");
  three.fog = new Fog("#0B1822", 90, 220);
  const camera = new PerspectiveCamera(38, 16 / 9, 0.3, 400);
  three.add(new HemisphereLight("#CFE3F5", "#1B3A2A", 0.85));
  const sun = new DirectionalLight("#FFFFFF", 0.8); sun.position.set(-30, 60, 40); three.add(sun);

  // pitch + ground
  const ground = new Mesh(new PlaneGeometry(400, 300), new MeshBasicMaterial({ color: "#10281E" })); ground.rotation.x = -Math.PI / 2; ground.position.y = -0.05; three.add(ground);
  const pitch = new Mesh(new PlaneGeometry(L, W), new MeshBasicMaterial({ map: pitchTexture() })); pitch.rotation.x = -Math.PI / 2; three.add(pitch);
  const postMat = new MeshLambertMaterial({ color: "#F4F7FA" });
  for (const gx of [-L / 2, L / 2]) {
    for (const zz of [-3.66, 3.66]) { const p = new Mesh(new CylinderGeometry(0.07, 0.07, 2.44, 8), postMat); p.position.set(gx, 1.22, zz); three.add(p); }
    const bar = new Mesh(new CylinderGeometry(0.07, 0.07, 7.32, 8), postMat); bar.rotation.x = Math.PI / 2; bar.position.set(gx, 2.44, 0); three.add(bar);
    const net = new Mesh(new PlaneGeometry(7.32, 2.44), new MeshBasicMaterial({ color: "#FFFFFF", transparent: true, opacity: 0.16, side: DoubleSide }));
    net.rotation.y = Math.PI / 2; net.position.set(gx + (gx > 0 ? 1.6 : -1.6), 1.22, 0); three.add(net);
  }

  // colours
  const attC = scene.teams.att.color; let defC = scene.teams.def.color;
  const lift = (c) => { const k = new Color(c); const lum = 0.2126 * k.r + 0.7152 * k.g + 0.0722 * k.b; return lum < 0.12 ? "#" + k.lerp(new Color("#9FB3C8"), 0.55).getHexString() : c; };
  defC = lift(defC);
  const attC2 = lift(attC);
  if (colorDist(attC2, defC) < 0.45) defC = "#F2F2F2";
  const gkC = ["#E8C21A", "#3FB6F2"];
  const marks = scene.marks || {};
  const keyIds = new Set(Object.values(marks));
  const roleColor = { decoy: "#3DD9FF", marker: "#FF7A59", passer: "#FFFFFF", scorer: "#F2B632", scanner: "#3DD9FF", target: "#7CF29A" };

  // players
  const N = scene.t.length, t0 = scene.t[0], tEnd = scene.t[N - 1];
  const heads = {}, bodies = {}, groups = {}, sprites = {}, rings = {};
  const skin = new MeshLambertMaterial({ color: "#E9C3A0" });
  const shortsMat = new MeshLambertMaterial({ color: "#14202B" });
  const capsule = new CapsuleGeometry(0.3, 0.85, 4, 10), headG = new SphereGeometry(0.21, 14, 10), legG = new CylinderGeometry(0.17, 0.15, 0.7, 8), noseG = new BoxGeometry(0.16, 0.06, 0.1);
  const shadowG = new CircleGeometry(0.55, 14), shadowM = new MeshBasicMaterial({ color: "#000", transparent: true, opacity: 0.28, depthWrite: false });
  const ringG = new RingGeometry(0.85, 1.05, 32);
  for (const p of scene.players) {
    const g = new Group();
    const isGK = p.pos === "GK";
    const col = isGK ? gkC[p.side === "att" ? 0 : 1] : p.side === "att" ? attC2 : defC;
    const shirt = new MeshLambertMaterial({ color: col });
    const body = new Mesh(capsule, shirt); body.position.y = 1.15; g.add(body);
    const shorts = new Mesh(legG, shortsMat); shorts.position.y = 0.4; g.add(shorts);
    const head = new Group(); head.position.y = 1.95;
    const hm = new Mesh(headG, skin); head.add(hm);
    const nose = new Mesh(noseG, new MeshLambertMaterial({ color: "#B98E6A" })); nose.position.set(0.2, -0.02, 0); head.add(nose);
    g.add(head);
    const sh = new Mesh(shadowG, shadowM); sh.rotation.x = -Math.PI / 2; sh.position.y = 0.03; g.add(sh);
    sh.userData.keep = true;
    three.add(g);
    groups[p.id] = g; heads[p.id] = head; bodies[p.id] = body;
    const role = Object.keys(marks).find((k) => marks[k] === p.id);
    if (role) {
      const rc = roleColor[role] || "#FFFFFF";
      const ring = new Mesh(ringG, new MeshBasicMaterial({ color: rc, transparent: true, opacity: 0.95, side: DoubleSide, depthWrite: false }));
      ring.rotation.x = -Math.PI / 2; ring.position.y = 0.06; ring.renderOrder = 3; three.add(ring); rings[p.id] = ring;
      const sp = numberSprite(p.n, rc); three.add(sp); sprites[p.id] = sp;
    }
  }
  // ball
  const ball = new Mesh(new SphereGeometry(0.24, 16, 12), new MeshLambertMaterial({ color: "#FFFFFF" })); three.add(ball);
  const ballShadow = new Mesh(shadowG, shadowM); ballShadow.rotation.x = -Math.PI / 2; ballShadow.scale.setScalar(0.5); three.add(ballShadow);

  // trails
  const ribDecoy = new Ribbon(roleColor.decoy, 0.7), ribMarker = new Ribbon(roleColor.marker, 0.7), ribBall = new Ribbon("#FFFFFF", 0.35, 400, 0.85), ribShot = new Ribbon("#F2B632", 0.5, 400, 0.9);
  const ribScan = new Ribbon("#7CF29A", 0.5);
  for (const r of [ribDecoy, ribMarker, ribBall, ribShot]) three.add(r.mesh);
  // gaze fan (scan scenes)
  const FAN = 14, fanGeo = new BufferGeometry(), fanPos = new Float32Array((FAN + 2) * 3);
  fanGeo.setAttribute("position", new BufferAttribute(fanPos, 3));
  const fanIdx = []; for (let i = 1; i <= FAN; i++) fanIdx.push(0, i, i + 1); fanGeo.setIndex(fanIdx);
  const fan = new Mesh(fanGeo, new MeshBasicMaterial({ color: "#7CF29A", transparent: true, opacity: 0.22, side: DoubleSide, depthWrite: false })); fan.renderOrder = 2; fan.frustumCulled = false; fan.visible = false; three.add(fan);

  // ---- sampling
  const byId = {}; for (const p of scene.players) byId[p.id] = p;
  function kAt(t) { const f = (t - t0) / (scene.t[1] - scene.t[0]); const k = Math.max(0, Math.min(N - 1.0001, f)); return [Math.floor(k), k - Math.floor(k)]; }
  function posOf(id, t) { const [k, u] = kAt(t), a = scene.xy[id][k], b = scene.xy[id][k + 1] || a; return [lerp(a[0], b[0], u), lerp(a[1], b[1], u)]; }
  function yawOf(id, t) { const [k, u] = kAt(t), a = scene.yaw[id][k], b = scene.yaw[id][k + 1] ?? a; return lerpAng(a, b, u); }
  function ballXY(t) { const [k, u] = kAt(t), a = scene.ball[k], b = scene.ball[k + 1] || a; return [lerp(a[0], b[0], u), lerp(a[1], b[1], u)]; }
  function ballZ(t) {
    for (const f of scene.flights) {
      if (t >= f.t0 && t <= f.t1) {
        const u = (t - f.t0) / Math.max(f.t1 - f.t0, 1);
        const peak = f.type === "shot" ? 0.9 : f.len > 14 ? Math.min(2.6, f.len * 0.06) : 0.12;
        return 0.24 + peak * Math.sin(Math.PI * u);
      }
    }
    return 0.24;
  }
  const scan = scene.scan;
  function gazeYaw(t) { // dynamic: look at a player or the ball, eased between looks
    const keys = scan.keys; let i = 0;
    while (i + 1 < keys.length && t >= keys[i + 1].t) i++;
    const me = posOf(scan.pid, t);
    const at = (k) => { const q = k.look ? posOf(k.look, t) : ballXY(t); return Math.atan2(q[1] - me[1], q[0] - me[0]); };
    let yaw = at(keys[i]);
    if (i > 0) { const u = smooth((t - keys[i].t) / 280); yaw = lerpAng(at(keys[i - 1]), yaw, u); }
    if (t > scan.t_pass + 250) { yaw = lerpAng(yaw, yawOf(scan.pid, t), smooth((t - scan.t_pass - 250) / 450)); }
    return { yaw, look: t >= keys[i].t && t <= (keys[i + 1] ? keys[i + 1].t : scan.t_pass) ? keys[i].look : null };
  }

  // ---- UI
  const badge = document.createElement("div"); badge.className = "kbadge"; root.appendChild(badge);
  const camrow = document.createElement("div"); camrow.className = "kcamrow"; root.appendChild(camrow);
  const capBox = document.createElement("div"); capBox.className = "kcap"; const capSpan = document.createElement("span"); capBox.appendChild(capSpan); root.appendChild(capBox);
  const legend = document.createElement("div"); legend.className = "klegend"; root.appendChild(legend);
  const bar = document.createElement("div"); bar.className = "kbar"; root.appendChild(bar);
  const btn = document.createElement("button"); btn.type = "button"; bar.appendChild(btn);
  const track = document.createElement("div"); track.className = "ktrack"; bar.appendChild(track);
  const range = document.createElement("input"); range.type = "range"; range.min = t0; range.max = tEnd; range.step = 20; range.value = t0; track.appendChild(range);
  const tm = document.createElement("span"); tm.className = "ktm"; bar.appendChild(tm);
  const speed = document.createElement("select"); for (const [v, l] of [[0.5, "0.5×"], [1, "1×"], [2, "2×"]]) { const o = document.createElement("option"); o.value = v; o.textContent = l; if (v === 1) o.selected = true; speed.appendChild(o); }
  speed.setAttribute("aria-label", "speed"); bar.appendChild(speed);
  const big = document.createElement("div"); big.className = "kbig"; const bigBtn = document.createElement("button"); bigBtn.type = "button"; bigBtn.textContent = "▶"; big.appendChild(bigBtn); root.appendChild(big);
  for (const b of scene.beats) { const tick = document.createElement("i"); tick.className = "ktick"; tick.style.insetInlineStart = ((b.t - t0) / (tEnd - t0) * 100) + "%"; track.appendChild(tick); }

  const camNames = scene.kind === "scan" ? ["auto", "tactical", "behind", "pov"] : ["auto", "tactical", "behind"];
  let camMode = "auto", cur = t0, playing = false, last = 0;
  const camBtns = {};
  for (const c of camNames) { const b = document.createElement("button"); b.type = "button"; b.dataset.cam = c; b.addEventListener("click", () => setCam(c)); camrow.appendChild(b); camBtns[c] = b; }

  function labels() {
    root.dir = lang === "ar" ? "rtl" : "ltr";
    badge.textContent = T().badge;
    for (const c of camNames) { camBtns[c].textContent = T().cam[c]; camBtns[c].setAttribute("aria-pressed", String(c === camMode)); }
    btn.textContent = playing ? T().pause : cur >= tEnd - 1 ? T().replay : T().play;
    bigBtn.setAttribute("aria-label", T().play);
    const row = (c, s) => `<div><i style="background:${c}"></i>${s}</div>`;
    legend.innerHTML = scene.kind === "decoy"
      ? row(roleColor.decoy, T().legendDecoy) + row(roleColor.marker, T().legendMarker) + row("#fff", T().legendPass)
      : row("#7CF29A", T().legendGaze) + row("#fff", T().legendPass);
    caption();
  }
  function fmt(t) { const s = Math.max(0, (t - t0) / 1000); return s.toFixed(1) + "s"; }
  function caption() {
    let beat = null;
    for (const b of scene.beats) if (cur >= b.t - 80) beat = b;
    if (!beat || cur > beat.t + 4200 && beat !== scene.beats[scene.beats.length - 1]) { capSpan.className = ""; if (!beat) return; }
    const tpl = (scene.captions[beat.key] || {})[lang] || (scene.captions[beat.key] || {}).en || "";
    capSpan.textContent = tpl.replace("{n}", beat.n ?? "").replace("{t}", beat.t_n ?? "");
    capSpan.className = cur <= beat.t + 4200 || beat === scene.beats[scene.beats.length - 1] ? "on" : "";
  }

  // ---- camera
  const focus = new Vector3(), camPos = new Vector3(); let camInit = false;
  function focusPoint(t) {
    const pts = [ballXY(t)]; for (const id of keyIds) if (id) pts.push(posOf(id, t));
    let x = 0, y = 0, wsum = 0;
    pts.forEach((p, i) => { const w = i === 0 ? 2 : 1; x += p[0] * w; y += p[1] * w; wsum += w; });
    return [x / wsum, y / wsum];
  }
  function activeCam(t) {
    if (camMode !== "auto") return camMode;
    if (scene.kind === "scan" && t >= scan.t_send - 300 && t <= scan.t_pass + 250) return "pov";
    return "tactical";
  }
  function placeCamera(t, dt) {
    const mode = activeCam(t);
    const [fx, fy] = focusPoint(t);
    const k = camInit ? 1 - Math.exp(-dt * 3.2) : 1;
    if (mode === "pov") {
      const me = posOf(scan.pid, t), g = gazeYaw(t).yaw;
      camera.fov = 80; camera.position.set(wx(me[0]), 1.78, wz(me[1])); camPos.copy(camera.position);
      camera.lookAt(camera.position.x + Math.cos(g), 1.78 - 0.1, camera.position.z + Math.sin(g));
      camera.updateProjectionMatrix(); return mode;
    }
    camera.fov = mode === "behind" ? 52 : 38;
    const tgt = new Vector3(wx(fx), 0.5, wz(fy));
    const off = mode === "behind" ? new Vector3(-26, 9, 3) : new Vector3(-6, 32, 46);
    const want = tgt.clone().add(off);
    if (!camInit) { focus.copy(tgt); camPos.copy(want); camInit = true; }
    focus.lerp(tgt, k); camPos.lerp(want, k);
    camera.position.copy(camPos); camera.lookAt(focus); camera.updateProjectionMatrix();
    return mode;
  }

  // ---- frame update
  const tmp = new Vector3();
  function update(dt) {
    const mode = placeCamera(cur, dt);
    const gz = scan ? gazeYaw(cur) : null;
    for (const p of scene.players) {
      const [x, y] = posOf(p.id, cur), g = groups[p.id];
      g.position.set(wx(x), 0, wz(y));
      const [k] = kAt(cur), a = scene.xy[p.id][Math.max(k - 1, 0)], b = scene.xy[p.id][Math.min(k + 1, N - 1)];
      const sp = Math.hypot(b[0] - a[0], b[1] - a[1]) / (2 * (scene.t[1] - scene.t[0]) / 1000);
      let yaw = yawOf(p.id, cur);
      g.rotation.y = -yaw;
      bodies[p.id].rotation.z = -0.1 * Math.min(sp / 6, 1);
      bodies[p.id].position.y = 1.15 + 0.04 * Math.sin(cur / 90 + p.n) * Math.min(sp / 4, 1);
      heads[p.id].rotation.y = 0;
      g.visible = !(mode === "pov" && scan && p.id === scan.pid);
      if (rings[p.id]) { rings[p.id].position.set(wx(x), 0.06, wz(y)); const pulse = 1 + 0.08 * Math.sin(cur / 160); rings[p.id].scale.setScalar(pulse); }
      if (sprites[p.id]) sprites[p.id].position.set(wx(x), p.id === marks.decoy || p.id === marks.scanner ? 4.1 : 3.1, wz(y));
    }
    if (scan) { // head turns relative to body: rotation.y is -(angle) so relative = -(gaze - body)
      heads[scan.pid].rotation.y = -angDiff(yawOf(scan.pid, cur), gz.yaw);
    }
    const bxy = ballXY(cur), bz = ballZ(cur);
    ball.position.set(wx(bxy[0]), bz, wz(bxy[1])); ballShadow.position.set(wx(bxy[0]), 0.04, wz(bxy[1]));
    ballShadow.scale.setScalar(0.5 * (1 - Math.min(bz, 3) * 0.12));

    // trails
    if (scene.kind === "decoy") {
      const runStart = scene.beats[0].t - 200, ids = [marks.decoy, marks.marker];
      [[ribDecoy, ids[0]], [ribMarker, ids[1]]].forEach(([rib, id]) => {
        const pts = []; const kk = kAt(cur)[0];
        for (let k = kAt(runStart)[0]; k <= kk; k++) { const q = scene.xy[id][k]; pts.push([wx(q[0]), wz(q[1])]); }
        const c = posOf(id, cur); pts.push([wx(c[0]), wz(c[1])]); rib.set(pts);
      });
    }
    for (const r of [ribBall, ribShot, ribDecoy, ribMarker]) r.mesh.visible = mode !== "pov";
    // ball / flight lines
    const bp = [], sp2 = [];
    for (const f of scene.flights) {
      if (cur < f.t0) continue;
      const a = Math.floor((f.t0 - t0) / (scene.t[1] - scene.t[0])), b = Math.min(kAt(Math.min(cur, f.t1))[0] + 1, N - 1);
      const arr = f.type === "shot" ? sp2 : bp;
      if (arr.length) arr.push(null);
      for (let k = a; k <= b; k++) { const q = scene.ball[k]; arr.push([wx(q[0]), wz(q[1])]); }
    }
    ribBall.set(bp.filter(Boolean)); ribShot.set(sp2.filter(Boolean));

    // gaze fan + look ring
    if (scan) {
      const me = posOf(scan.pid, cur), show = mode !== "pov" && cur >= scan.t_send - 200 && cur <= scan.t_pass + 100;
      fan.visible = show;
      if (show) {
        const half = 0.62, len = 22;
        fanPos.set([wx(me[0]), 0.07, wz(me[1])], 0);
        for (let i = 0; i <= FAN; i++) { const a = gz.yaw - half + (2 * half * i) / FAN; fanPos.set([wx(me[0]) + Math.cos(a) * len, 0.07, wz(me[1]) + Math.sin(a) * len], (i + 1) * 3); }
        fanGeo.attributes.position.needsUpdate = true;
      }
      for (const o of scan.options.concat([scan.target])) {
        if (!rings[o]) { // lazily create a ring for option players
          const rc = o === scan.target ? roleColor.target : "#7CF29A";
          const ring = new Mesh(ringG, new MeshBasicMaterial({ color: rc, transparent: true, opacity: 0, side: DoubleSide, depthWrite: false }));
          ring.rotation.x = -Math.PI / 2; ring.renderOrder = 3; three.add(ring); rings[o] = ring;
        }
        const looked = gz.look === o || (o === scan.target && cur >= scan.t_pass - 650 && cur <= scan.t_pass + 400);
        rings[o].material.opacity = looked ? 0.95 : o === scan.target ? 0 : 0;
        const q = posOf(o, cur); rings[o].position.set(wx(q[0]), 0.06, wz(q[1]));
      }
    }
    renderer.render(three, camera);
    range.value = cur; tm.textContent = fmt(cur);
  }

  // ---- loop
  let raf = 0;
  function tick(now) {
    raf = requestAnimationFrame(tick);
    const dt = Math.min((now - last) / 1000, 0.1); last = now;
    if (playing) {
      cur += dt * 1000 * Number(speed.value);
      if (cur >= tEnd) { cur = tEnd; playing = false; labels(); }
      caption();
    }
    update(dt);
  }
  function resize() {
    const w = Math.max(root.clientWidth, 280), h = Math.round(Math.max(w * 9 / 16, 240));
    renderer.setSize(w, h, false); renderer.domElement.style.height = h + "px"; camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(resize) : null; ro && ro.observe(root); resize();

  function play() { if (cur >= tEnd - 1) cur = t0; playing = true; big.style.display = "none"; labels(); }
  function pause() { playing = false; labels(); }
  function seek(t) { cur = Math.max(t0, Math.min(tEnd, t)); camInit = false; caption(); update(0.016); }
  function setCam(c) { camMode = c; labels(); update(0.016); }
  btn.addEventListener("click", () => (playing ? pause() : play()));
  bigBtn.addEventListener("click", play);
  range.addEventListener("input", () => { big.style.display = "none"; cur = Number(range.value); caption(); labels(); update(0.016); });

  if (opts.cam && camNames.includes(opts.cam)) camMode = opts.cam;
  if (typeof opts.t === "number") { cur = Math.max(t0, Math.min(tEnd, opts.t)); big.style.display = cur > t0 ? "none" : "flex"; }
  labels(); last = performance.now(); camInit = false; update(0.016);
  raf = requestAnimationFrame(tick);
  if (opts.autoplay || opts.playing) play();
  return {
    play, pause, seek, setCam,
    setLang(l) { if (TEXT[l]) { lang = l; labels(); } },
    state() { return { t: cur, playing, cam: camMode }; },
    info() { return { t0, tEnd, beats: scene.beats, cam: activeCam(cur) }; },
    destroy() { cancelAnimationFrame(raf); ro && ro.disconnect(); renderer.dispose(); host.innerHTML = ""; },
  };
}
