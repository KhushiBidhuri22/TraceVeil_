// Positions below arrange actual backend nodes; they create no data or links.
export function layoutGraph(nodes) {
  const others = nodes.filter(node => node.type !== 'actor');
  if (!others.length) {
    return nodes.map(node => node.type === 'actor' ? {...node, position: [0, 0, 0]} : node);
  }

  // Clustered semantic layout by node category for maximum clarity
  const typeClusters = {
    alias: { baseAngle: -Math.PI / 2, spread: Math.PI * 0.5, radius: 190, zOffset: 30 },
    key: { baseAngle: Math.PI * 0.9, spread: Math.PI * 0.4, radius: 205, zOffset: -20 },
    wallet: { baseAngle: 0.1, spread: Math.PI * 0.45, radius: 215, zOffset: 45 },
    source: { baseAngle: Math.PI * 0.5, spread: Math.PI * 0.6, radius: 220, zOffset: -40 },
  };

  const groups = { alias: [], key: [], wallet: [], source: [] };
  for (const node of others) {
    if (groups[node.type]) groups[node.type].push(node);
    else groups.source.push(node);
  }

  const positions = new Map();
  for (const [type, groupNodes] of Object.entries(groups)) {
    if (!groupNodes.length) continue;
    const cfg = typeClusters[type] || typeClusters.source;
    const count = groupNodes.length;
    groupNodes.forEach((node, idx) => {
      const offset = count === 1 ? 0 : (idx - (count - 1) / 2) * (cfg.spread / Math.max(1, count - 1));
      const angle = cfg.baseAngle + offset;
      const rad = cfg.radius + (idx % 2 === 0 ? 0 : 25);
      const x = Math.cos(angle) * rad;
      const y = Math.sin(angle) * rad * 0.65;
      const z = Math.sin(angle * 2) * 35 + cfg.zOffset;
      positions.set(node.id, [Math.round(x), Math.round(y), Math.round(z)]);
    });
  }

  return nodes.map(node => {
    if (node.position) return node;
    if (node.type === 'actor') return {...node, position: [0, 0, 0]};
    const pos = positions.get(node.id) || [160, 0, 0];
    return {...node, position: pos};
  });
}
export function filteredGraph(actor, {step=null,threshold=0,types=new Set(['alias','key','wallet','source'])} = {}) {
  if (!actor?.graph) return {nodes:[],edges:[]};
  const date = step === null ? null : actor.events?.[step]?.date;
  // Unknown observation dates are never asserted to exist at a historical moment.
  const visibleAtTime = item => step === null || (date && item.observedAt && Date.parse(item.observedAt) <= Date.parse(date));
  const nodes = actor.graph.nodes.filter(n => (n.type === 'actor' || types.has(n.type)) && visibleAtTime(n));
  const ids = new Set(nodes.map(n => n.id));
  const edges = actor.graph.edges.filter(e => ids.has(e.from) && ids.has(e.to) && visibleAtTime(e) && (threshold === 0 || (e.confidence !== null && e.confidence >= threshold)));
  const used = new Set(edges.flatMap(e => [e.from,e.to]));
  return {nodes:threshold > 0 ? nodes.filter(n => n.type === 'actor' || used.has(n.id)) : nodes, edges};
}
