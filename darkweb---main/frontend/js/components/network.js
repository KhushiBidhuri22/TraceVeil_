import { filteredGraph } from '../models/graph.js';
import { edgeId } from '../models/workspace.js';

export function projectPoint(position,{yaw=0,pitch=0,width,height,zoom=1,flat=false}){
  const [x,y,z]=position,unit=Math.min(width/610,height/420,1.7)*zoom;
  const cy=Math.cos(yaw),sy=Math.sin(yaw),cx=Math.cos(pitch),sx=Math.sin(pitch);
  const rx=flat?x:x*cy-z*sy,rz=flat?0:x*sy+z*cy;
  const ry=flat?y:y*cx-rz*sx,depth=flat?0:y*sx+rz*cx;
  const perspective=650/(650+depth);
  return {x:width/2+rx*unit*perspective,y:height*.48+ry*unit*perspective,z:depth,scale:unit*perspective};
}
export function distanceToSegment(point,a,b){
  const dx=b.x-a.x,dy=b.y-a.y,length=dx*dx+dy*dy;
  const t=length?Math.max(0,Math.min(1,((point.x-a.x)*dx+(point.y-a.y)*dy)/length)):0;
  return Math.hypot(point.x-a.x-t*dx,point.y-a.y-t*dy);
}
export function hitBranch(point,segments,tolerance=8){
  let closest=null,distance=tolerance;
  for(const segment of segments){const d=distanceToSegment(point,segment.a,segment.b);if(d<distance){closest=segment;distance=d;}}
  return closest?.edge??null;
}
export function normalizedWheel(delta,mode=0,height=400){
  return Math.max(-160,Math.min(160,delta*(mode===1?16:mode===2?height:1)));
}
const branchKey=edgeId;

export class NetworkScene{
  constructor(canvas,{actor,onSelect=()=>{},onEdgeSelect=()=>{},onCamera=()=>{}}){
    this.canvas=canvas;this.ctx=canvas.getContext('2d');this.actor=actor;
    this.onSelect=onSelect;this.onEdgeSelect=onEdgeSelect;this.onCamera=onCamera;
    this.yaw=-.27;this.pitch=.19;this.targetYaw=this.yaw;this.targetPitch=this.pitch;
    this.zoom=1;this.flat=false;this.orbit=false;this.motion=true;this.active=false;this.finish='matte';
    this.rootId=this.actor?.graph?.nodes.find(n=>n.type==='actor')?.id??null;this.selected=this.rootId;this.hovered=null;this.hoveredEdge=null;this.elapsed=0;this.last=0;
    this.projected=[];this.branches=[];this.pressPoint=null;this.moved=false;
    this.filters={step:null,threshold:0,types:new Set(['alias','key','wallet','source'])};
    if(!this.ctx){canvas.replaceWith(Object.assign(document.createElement('p'),{textContent:'Graph rendering is unavailable. Use the connection menu above to open each record.'}));return;}
    this.observer=new ResizeObserver(()=>this.resize());this.observer.observe(canvas);
    canvas.tabIndex=0;
    // Scrolling is the camera control; pointer movement only discovers clickable items.
    canvas.addEventListener('wheel',event=>this.wheel(event),{passive:false});
    canvas.addEventListener('pointerdown',event=>{this.pressPoint=this.getLocal(event);this.moved=false;});
    canvas.addEventListener('pointermove',event=>this.pointerMove(event));
    canvas.addEventListener('pointercancel',()=>{this.pressPoint=null;this.moved=true;});
    canvas.addEventListener('pointerleave',()=>{this.hovered=null;this.hoveredEdge=null;this.pressPoint=null;});
    canvas.addEventListener('click',event=>this.selectAt(event));
    canvas.addEventListener('keydown',event=>this.keyDown(event));
    this.resize();
    this.frame=now=>{
      if(this.active&&!document.hidden&&now-this.last>32){
        const delta=Math.min((now-this.last)/1000,.06);this.last=now;
        if(this.motion){
          this.elapsed+=delta;
          if(this.orbit&&!this.flat)this.targetYaw+=delta*.075;
          this.yaw+=(this.targetYaw-this.yaw)*.24;this.pitch+=(this.targetPitch-this.pitch)*.24;
        }else{this.yaw=this.targetYaw;this.pitch=this.targetPitch;}
        this.draw();
      }
      this.raf=requestAnimationFrame(this.frame);
    };
    this.raf=requestAnimationFrame(this.frame);
  }
  resize(){
    const box=this.canvas.getBoundingClientRect();if(!box.width||!box.height||!this.ctx)return;
    this.width=box.width;this.height=box.height;const dpr=Math.min(window.devicePixelRatio||1,2);
    this.canvas.width=Math.round(box.width*dpr);this.canvas.height=Math.round(box.height*dpr);
    this.ctx.setTransform(dpr,0,0,dpr,0,0);this.draw();
  }
  setActive(value){this.active=value;if(value)this.resize();}
  setActor(actor){this.actor=actor;this.rootId=this.actor?.graph?.nodes.find(n=>n.type==='actor')?.id??null;this.selected=this.rootId;this.hovered=null;this.hoveredEdge=null;this.draw();}
  setFilters(filters){this.filters={...this.filters,...filters};this.hovered=null;this.hoveredEdge=null;this.draw();}
  setSelected(id){this.selected=id;this.draw();}
  setMotion(value){this.motion=value;if(!value){this.yaw=this.targetYaw;this.pitch=this.targetPitch;}this.draw();}
  setFinish(value){this.finish=value==='glossy'?'glossy':'matte';this.draw();}
  zoomBy(change){this.zoom=Math.max(.6,Math.min(1.8,this.zoom+change));this.draw();this.onCamera(this);}
  reset(){this.yaw=-.27;this.pitch=.19;this.targetYaw=this.yaw;this.targetPitch=this.pitch;this.zoom=1;this.flat=false;this.orbit=false;this.onCamera(this);this.draw();}
  setFlat(value){this.flat=value;this.draw();this.onCamera(this);}
  setOrbit(value){this.orbit=value;this.onCamera(this);}
  getGraph(){return filteredGraph(this.actor,this.filters);}
  point(position){return projectPoint(position,{yaw:this.yaw,pitch:this.pitch,width:this.width,height:this.height,zoom:this.zoom,flat:this.flat});}
  getLocal(event){const b=this.canvas.getBoundingClientRect();return{x:event.clientX-b.left,y:event.clientY-b.top};}
  hitNode(p){return [...this.projected].reverse().find(n=>Math.hypot(n.x-p.x,n.y-p.y)<Math.max(n.radius+6,18)||(p.x>=n.labelBox.x&&p.x<=n.labelBox.x+n.labelBox.width&&p.y>=n.labelBox.y&&p.y<=n.labelBox.y+24));}
  pointerMove(event){
    const p=this.getLocal(event);
    if(this.pressPoint&&Math.hypot(p.x-this.pressPoint.x,p.y-this.pressPoint.y)>8)this.moved=true;
    const node=this.hitNode(p);this.hovered=node?.node.id??null;
    const edge=node?null:hitBranch(p,this.branches);this.hoveredEdge=edge?branchKey(edge):null;
    this.canvas.style.cursor=node||edge?'pointer':'default';
  }
  selectAt(event){
    if(this.moved){this.moved=false;this.pressPoint=null;return;}
    const p=this.getLocal(event),node=this.hitNode(p);this.pressPoint=null;
    this.targetYaw=this.yaw;this.targetPitch=this.pitch;
    if(node){this.selected=node.node.id;this.onSelect(node.node.id);return;}
    const edge=hitBranch(p,this.branches,10);if(edge){this.selected=edge.to;this.onEdgeSelect(edge);}
  }
  wheel(event){
    if(!this.active||!this.getGraph().nodes.length||event.ctrlKey)return; // Keep browser pinch-to-zoom available.
    event.preventDefault();this.orbit=false;this.hovered=null;this.hoveredEdge=null;
    const dy=normalizedWheel(event.deltaY,event.deltaMode,this.height),dx=normalizedWheel(event.deltaX,event.deltaMode,this.height);
    if(this.flat){this.zoomBy(-dy*.001);return;}
    this.targetYaw+=dy*.0028;
    this.targetPitch=Math.max(-.72,Math.min(.72,this.targetPitch+dx*.002));
    if(!this.motion){this.yaw=this.targetYaw;this.pitch=this.targetPitch;this.draw();}
    this.onCamera(this);
  }
  keyDown(event){
    if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','=','-'].includes(event.key))return;
    event.preventDefault();this.orbit=false;
    if(event.key==='ArrowLeft')this.targetYaw-=.14;if(event.key==='ArrowRight')this.targetYaw+=.14;
    if(event.key==='ArrowUp')this.targetPitch=Math.max(-.72,this.targetPitch-.1);
    if(event.key==='ArrowDown')this.targetPitch=Math.min(.72,this.targetPitch+.1);
    if(event.key==='+'||event.key==='=')this.zoomBy(.1);if(event.key==='-')this.zoomBy(-.1);
    if(!this.motion){this.yaw=this.targetYaw;this.pitch=this.targetPitch;this.draw();}this.onCamera(this);
  }
  polyline(points,color){const c=this.ctx;c.beginPath();points.forEach((p,i)=>{const q=this.point(p);i?c.lineTo(q.x,q.y):c.moveTo(q.x,q.y);});c.strokeStyle=color;c.lineWidth=1;c.stroke();}
  ring(radius,level,color,tilt=0){const points=[];for(let i=0;i<=90;i++){const t=i/90*Math.PI*2;points.push([Math.cos(t)*radius,Math.sin(t)*radius*Math.sin(tilt)+level,Math.sin(t)*radius*Math.cos(tilt)]);}this.polyline(points,color);}
  draw(){
    if(!this.ctx||!this.width||!this.height)return;
    const c=this.ctx,w=this.width,h=this.height,matte=this.finish==='matte';c.clearRect(0,0,w,h);
    if(!matte){const halo=c.createRadialGradient(w*.5,h*.48,0,w*.5,h*.48,Math.min(w,h)*.5);halo.addColorStop(0,'#16422c24');halo.addColorStop(1,'#03100800');c.fillStyle=halo;c.fillRect(0,0,w,h);}
    if(!this.flat)for(let t=-260;t<=260;t+=50){this.polyline([[-260,150,t],[260,150,t]],'#78b99709');this.polyline([[t,150,-260],[t,150,260]],'#78b99709');}
    this.ring(212,20,'#62a77f29',this.flat?Math.PI/2:.14);this.ring(185,10,'#62a77f16',this.flat?Math.PI/2:1.08);
    const {nodes,edges}=this.getGraph(),map=new Map(nodes.map(node=>[node.id,{...this.point(node.position),node}]));
    this.branches=[];
    for(const edge of edges){
      const a=map.get(edge.from),b=map.get(edge.to),red=b.node.type==='wallet'||a.node.type==='wallet';
      const focus=this.hoveredEdge===branchKey(edge)||this.hovered&&(edge.from===this.hovered||edge.to===this.hovered)||this.selected!==this.rootId&&(edge.from===this.selected||edge.to===this.selected);
      c.beginPath();c.moveTo(a.x,a.y);c.lineTo(b.x,b.y);c.lineWidth=focus?2.3:1.2;
      c.strokeStyle=matte?(red?focus?'#cc8b7c':'#ad796976':focus?'#95c2aa':'#668f7a90'):(red?focus?'#ed9385':'#d575665e':focus?'#81e1c0':'#60b5946b');
      c.setLineDash(edge.confidence!==null&&edge.confidence<80?[4,5]:[]);c.stroke();c.setLineDash([]);this.branches.push({a,b,edge});
      if(this.motion){const v=(this.elapsed*.12+edges.indexOf(edge)*.16)%1;c.beginPath();c.arc(a.x+(b.x-a.x)*v,a.y+(b.y-a.y)*v,1.6,0,Math.PI*2);c.fillStyle=red?'#ce8776':matte?'#8eb79f':'#6bdabb';c.fill();}
    }
    this.projected=[];const labelBoxes=[];
    for(const p of [...map.values()].sort((a,b)=>b.z-a.z)){
      const {node,x,y,scale}=p,root=node.type==='actor',red=node.type==='wallet',selected=node.id===this.selected||node.id===this.hovered;
      const radius=(root?26:node.type==='source'?9:13)*Math.min(scale,1.35),tint=red?'#d39180':matte?'#9fc8b0':'#6edcb7';
      c.save();
      if(matte){c.shadowColor='#00000077';c.shadowBlur=12;c.shadowOffsetY=5;}
      else{const glow=c.createRadialGradient(x,y,radius*.4,x,y,radius*(selected?2.8:2));glow.addColorStop(0,red?'#b03e3d30':'#2ada8c30');glow.addColorStop(1,'#00000000');c.fillStyle=glow;c.beginPath();c.arc(x,y,radius*3,0,Math.PI*2);c.fill();}
      c.beginPath();
      if(node.type==='wallet'){c.moveTo(x,y-radius);c.lineTo(x+radius,y);c.lineTo(x,y+radius);c.lineTo(x-radius,y);c.closePath();}
      else if(node.type==='key'){c.rect(x-radius*.8,y-radius*.8,radius*1.6,radius*1.6);}
      else{c.arc(x,y,radius,0,Math.PI*2);}
      const body=matte?c.createLinearGradient(x-radius,y-radius,x+radius,y+radius):c.createRadialGradient(x-radius*.35,y-radius*.45,0,x,y,radius*1.3);
      if(matte){body.addColorStop(0,red?'#997569':root?'#719879':'#587f68');body.addColorStop(1,red?'#513a30':'#274333');}
      else{body.addColorStop(0,red?'#c7796b':root?'#77cfa0':'#59a686');body.addColorStop(.25,red?'#62352d':root?'#326c4a':'#1d4734');body.addColorStop(1,'#051b0f');}
      c.fillStyle=body;c.fill();c.shadowBlur=0;c.shadowOffsetY=0;c.strokeStyle=selected?tint:red?'#bf82745d':'#7cbda66b';c.lineWidth=selected?1.5:1;c.stroke();
      if(root){c.strokeStyle=matte?'#8db69755':'#71d4a64d';c.beginPath();c.arc(x,y,radius+7,0,Math.PI*2);c.stroke();c.font=`600 ${Math.max(12,14*scale)}px "Oxanium",monospace`;c.textAlign='center';c.textBaseline='middle';c.fillStyle=matte?'#b2d0b4':'#a2dcb8';c.fillText((this.actor?.initials ?? ''),x,y+1);}
      else if(node.type==='source'){c.beginPath();c.arc(x,y,radius*.4,0,Math.PI*2);c.fillStyle='#8eb39c';c.fill();}
      c.restore();
      c.font=`${root?'600':'400'} ${root?14:13}px "Oxanium",monospace`;
      const text=node.name.length>24?node.name.slice(0,21)+'…':node.name,labelWidth=c.measureText(text).width+16;
      const candidates=[{x:x-labelWidth/2,y:y+radius+14},{x:x-labelWidth/2,y:y-radius-24},{x:x+radius+9,y:y},{x:x-labelWidth-radius-9,y:y}];
      const padded=candidates.map(q=>({x:Math.max(6,Math.min(w-labelWidth-6,q.x)),y:Math.min(h-24,Math.max(18,q.y)),width:labelWidth}));
      const candidate=padded.find(q=>!labelBoxes.some(b=>q.x<b.x+b.width+5&&q.x+q.width+5>b.x&&q.y-12<b.y+16&&q.y+16>b.y-12))??padded[0];
      labelBoxes.push(candidate);const lx=candidate.x,ly=candidate.y;
      c.beginPath();
      if (c.roundRect) c.roundRect(lx, ly-10, labelWidth, 22, 4);
      else c.rect(lx, ly-10, labelWidth, 22);
      c.fillStyle=matte?(selected?'#1c3e2ef0':(red?'#2f1915ea':'#0e261be6')):(selected?'#0b3022f2':(red?'#281310ee':'#041b11db'));
      c.fill();
      if(selected||red){
        c.strokeStyle=selected?(red?'#e08f82':'#7edbb5'):'#8d4c4477';
        c.lineWidth=selected?1.5:1;
        c.stroke();
      }
      c.fillStyle=matte?(root||selected?'#bcedd0':(red?'#f1aba0':'#9fc7af')):(root||selected?'#99efcb':(red?'#f09c8f':'#81cbb0'));
      c.textAlign='left';c.textBaseline='middle';c.fillText(text,lx+8,ly+1);
      this.projected.push({...p,radius,labelBox:{x:lx,y:ly-10,width:labelWidth,height:22}});
    }
  }
}
