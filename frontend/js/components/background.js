// Shared, non-data background. Green dot clusters from the supplied reference
// now sit behind genuinely spatial, slowly rotating particle ribbons.
const mix = (a, b, t) => a + (b - a) * t;
const smooth = t => t * t * (3 - 2 * t);
const clamp = n => Math.max(0, Math.min(1, n));

function hash(x, y, z) {
  let n = Math.imul(x, 374761393) ^ Math.imul(y, 668265263) ^ Math.imul(z, 1274126177);
  n = Math.imul(n ^ (n >>> 13), 1274126177);
  return ((n ^ (n >>> 16)) >>> 0) / 4294967295;
}

function noise(x, y, z) {
  const ix = Math.floor(x), iy = Math.floor(y), iz = Math.floor(z);
  const u = smooth(x - ix), v = smooth(y - iy), w = smooth(z - iz);
  const layer = dz => mix(
    mix(hash(ix, iy, iz + dz), hash(ix + 1, iy, iz + dz), u),
    mix(hash(ix, iy + 1, iz + dz), hash(ix + 1, iy + 1, iz + dz), u), v);
  return mix(layer(0), layer(1), w);
}

// Exported independently of the canvas so continuity/range can be checked locally.
export function dotIntensity(x, y, seconds) {
  const t = seconds * .19;
  const u = x / 125 + 7.4 + t * .27, v = y / 125 + 12.1 - t * .21;
  const field = .69 * noise(u, v, t + 4.2)
    + .23 * noise(u * 2.07, v * 2.07, t * .8 + 17)
    + .08 * noise(u * 4.1, v * 4.1, t * .55 + 31);
  return Math.pow(clamp((field - .475) / .28), 1.35);
}

// A half-twisted ribbon: its width turns through the third dimension.
// This mathematical geometry is decorative and never represents investigation data.
export function ribbonPoint(u, v, seconds = 0) {
  const radius = 225 + Math.sin(u * 3 + seconds * .12) * 12;
  const across = v * 85;
  return [(radius + across * Math.cos(u / 2)) * Math.cos(u),
    (radius + across * Math.cos(u / 2)) * Math.sin(u),
    across * Math.sin(u / 2) + Math.sin(u * 2 + seconds * .14) * 24];
}

// Camera-space z controls scale: nearer particles grow while distant ones shrink.
export function projectSpatialPoint(point, {yaw = 0, pitch = 0, roll = 0, scale = 1, x = 0, y = 0} = {}) {
  const cy = Math.cos(yaw), sy = Math.sin(yaw), cx = Math.cos(pitch), sx = Math.sin(pitch);
  const rz = point[0] * sy + point[2] * cy;
  const rx = point[0] * cy - point[2] * sy;
  const ry = point[1] * cx - rz * sx;
  const depth = point[1] * sx + rz * cx;
  const perspective = 760 / (760 + depth);
  const cr = Math.cos(roll), sr = Math.sin(roll);
  return {x:x + (rx * cr - ry * sr) * perspective * scale,
    y:y + (rx * sr + ry * cr) * perspective * scale,
    z:depth, scale:perspective * scale};
}

export class DotBackground {
  constructor(canvas, {onParallax = () => {}} = {}) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d');
    this.motion = false; this.finish = 'matte'; this.seconds = 8;
    this.last = 0; this.raf = null; this.pointer = {x:0,y:0};
    this.target = {x:0,y:0}; this.onParallax = onParallax;
    this.scroll = 0; this.scrollTarget = 0;
    if (!this.ctx) return;
    this.makeSprites();
    this.observer = new ResizeObserver(() => this.resize()); this.observer.observe(canvas);
    window.addEventListener('pointermove', event => {
      if (!this.motion || event.pointerType === 'touch') return;
      this.target = {x:event.clientX / window.innerWidth * 2 - 1,y:event.clientY / window.innerHeight * 2 - 1};
    }, {passive:true});
    document.documentElement.addEventListener('pointerleave', () => this.target = {x:0,y:0});
    window.addEventListener('scroll', () => {
      if (this.motion) this.scrollTarget = Math.min(window.scrollY, 1600) * .035;
    }, {passive:true});
    document.addEventListener('visibilitychange', () => this.schedule());
    this.tick = now => {
      this.raf = null;
      if (!this.motion || document.hidden) return;
      if (now - this.last >= 40) {
        this.seconds += Math.min((now - this.last) / 1000, .08); this.last = now;
        this.pointer.x = mix(this.pointer.x, this.target.x, .11);
        this.pointer.y = mix(this.pointer.y, this.target.y, .11);
        this.scroll = mix(this.scroll, this.scrollTarget, .1);
        this.onParallax(this.pointer);
        this.draw();
      }
      this.raf = requestAnimationFrame(this.tick);
    };
    this.resize();
  }
  makeSprites() {
    this.sprites = {};
    for (const finish of ['glossy', 'matte']) {
      const sprite = document.createElement('canvas'); sprite.width = sprite.height = 32;
      const s = sprite.getContext('2d');
      if (finish === 'glossy') {
        const halo = s.createRadialGradient(16,16,0,16,16,16);
        halo.addColorStop(0,'#d8ffe7'); halo.addColorStop(.13,'#71ffc0');
        halo.addColorStop(.26,'#32d989d9'); halo.addColorStop(.5,'#1fb56745'); halo.addColorStop(1,'#1bab5b00');
        s.fillStyle = halo; s.fillRect(0,0,32,32);
      } else {
        // Diffuse pigment rather than a luminous bloom; geometry still supplies depth.
        const ink = s.createRadialGradient(14,13,0,16,16,6);
        ink.addColorStop(0,'#8ac39d'); ink.addColorStop(1,'#437b58');
        s.fillStyle = ink; s.beginPath(); s.arc(16,16,6,0,Math.PI*2); s.fill();
      }
      this.sprites[finish] = sprite;
    }
  }
  resize() {
    const {width, height} = this.canvas.getBoundingClientRect();
    if (!width || !height || !this.ctx) return;
    this.width = width; this.height = height;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    this.canvas.width = Math.round(width*dpr); this.canvas.height = Math.round(height*dpr);
    this.ctx.setTransform(dpr,0,0,dpr,0,0); this.draw();
  }
  setFinish(finish) { this.finish = finish === 'glossy' ? 'glossy' : 'matte'; this.draw(); }
  setMotion(motion) {
    this.motion = motion;
    if (!motion) { this.target = {x:0,y:0}; this.pointer = {x:0,y:0}; this.onParallax(this.pointer); }
    this.schedule(); this.draw();
  }
  schedule() {
    if (!this.ctx) return;
    if (this.raf !== null) cancelAnimationFrame(this.raf);
    this.raf = null;
    if (this.motion && !document.hidden) { this.last = performance.now(); this.raf = requestAnimationFrame(this.tick); }
  }
  makeRibbon(camera, index) {
    const columns = this.width < 600 ? 72 : 112, rows = this.width < 600 ? 12 : 16;
    const points = [], faces = [], grid = [];
    for (let i=0; i<=columns; i++) {
      const row = [];
      for (let j=0; j<=rows; j++) {
        const u = i/columns * Math.PI*2, v = j/rows * 2-1;
        const p = projectSpatialPoint(ribbonPoint(u,v,this.seconds),camera);
        const intensity = dotIntensity(i*12+index*407,j*22+index*231,this.seconds);
        const crest = .5 + .5*Math.cos(u*2 - this.seconds*.13);
        row.push(p); points.push({...p, brightness:.3 + intensity*.65, rim:j===0 || j===rows, crest});
        if (i>0 && j>0 && i%2===0 && j%2===0) {
          const corners = [grid[i-2][j-2],grid[i-2][j],row[j],row[j-2]];
          faces.push({corners,z:corners.reduce((a,p)=>a+p.z,0)/4,light:crest});
        }
      }
      grid.push(row);
    }
    return {points,faces,edgeA:grid.map(row=>row[0]),edgeB:grid.map(row=>row.at(-1))};
  }
  draw() {
    if (!this.ctx || !this.width) return;
    const c=this.ctx,w=this.width,h=this.height,gloss=this.finish==='glossy',sprite=this.sprites[this.finish];
    c.clearRect(0,0,w,h);
    // The distant reference-style dot matrix moves less than the foreground ribbons.
    const gap = w < 600 ? 23 : 22;
    for(let y=7;y<h+gap;y+=gap) for(let x=7;x<w+gap;x+=gap) {
      const strength=dotIntensity(x,y,this.seconds); if(strength<.08)continue;
      c.globalAlpha=strength*(gloss?.26:.3);
      c.drawImage(sprite,x+this.pointer.x*5-4,y+this.pointer.y*4-4,8,8);
    }
    c.globalAlpha=1;
    const unit=Math.min(Math.max(w/1440,.72),1.45);
    const t=this.seconds;
    const cameras=[
      {x:w*.88+this.pointer.x*24,y:h*.52+this.pointer.y*18-this.scroll,scale:unit*1.27,
        yaw:-.48+Math.sin(t*.085)*.38+this.pointer.x*.25,pitch:.43+Math.cos(t*.065)*.14+this.pointer.y*.18,roll:-.5+Math.sin(t*.035)*.18},
      {x:w*.07-this.pointer.x*15,y:h*.78-this.pointer.y*12+this.scroll*.5,scale:unit*.91,
        yaw:.82+Math.sin(t*.06)*.3-this.pointer.x*.19,pitch:-.43+this.pointer.y*.14,roll:.7-t*.018}
    ];
    const ribbons=cameras.map((camera,index)=>this.makeRibbon(camera,index));
    // Faint shaded material between the dots makes folds readable even in Matte.
    for(const ribbon of ribbons) {
      for(const face of ribbon.faces.sort((a,b)=>b.z-a.z)) {
        c.beginPath(); face.corners.forEach((p,i)=>i?c.lineTo(p.x,p.y):c.moveTo(p.x,p.y)); c.closePath();
        const depth=clamp((face.z+300)/600);
        c.fillStyle=gloss?`rgba(18,100,59,${.075+(1-depth)*.06})`:`rgba(38,75,49,${.15+(1-depth)*.11})`;
        c.fill();
      }
      for(const edge of [ribbon.edgeA,ribbon.edgeB]) {
        c.beginPath(); edge.forEach((p,i)=>i?c.lineTo(p.x,p.y):c.moveTo(p.x,p.y));
        c.strokeStyle=gloss?'#58eeab38':'#759d6b42'; c.lineWidth=gloss?1:.8;c.stroke();
      }
    }
    for(const p of ribbons.flatMap(r=>r.points).sort((a,b)=>b.z-a.z)) {
      const nearness=clamp((280-p.z)/560);
      c.globalAlpha=Math.min(.94,p.brightness*(.55+nearness*.5)*(p.rim?1.24:1));
      const size=(gloss?8:6.7)*p.scale*(p.rim?1.17:1);
      c.drawImage(sprite,p.x-size/2,p.y-size/2,size,size);
    }
    c.globalAlpha=1;
  }
}
