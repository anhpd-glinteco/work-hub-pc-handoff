export const briefFields = {
  audience: 'Người xem', goal: 'Mục tiêu', target: 'Thời lượng dự kiến', keep: 'Cảnh cần giữ',
  style: 'Mẫu và phong cách', missing: 'Cảnh còn thiếu'
};
export const beatFields = {
  time: 'Mốc dựng', purpose: 'Lời / mục đích', source: 'Take và timecode nguồn',
  caption: 'Chữ / hình', cue: 'Cue âm thanh'
};

export function newWorkflow() {
  return {brief: {}, beats: [], notes: []};
}

export const planKey = p => JSON.stringify([p.output,
  Object.keys(briefFields).map(key => p.workflow?.brief[key] || ''),
  p.workflow?.beats.map(beat => Object.keys(beatFields).map(key => beat[key] || ''))]);

export const cutKey = p => JSON.stringify([p.output, p.layers
  .filter(layer => layer.primary && !layer.hidden && layer.asset)
  .map(({asset, start, duration, sourceIn}) => [asset, start, duration, sourceIn])]);

export const planApproved = p => Boolean(p.workflow && p.workflow.plan === planKey(p));
export const cutApproved = p => Boolean(planApproved(p) && p.workflow.cut?.key === cutKey(p));

export function checkWorkflow(p) {
  const w = p.workflow;
  if (w === undefined) return;
  const strings = (value, limit) => value && typeof value === 'object' && !Array.isArray(value) &&
    Object.values(value).every(text => typeof text === 'string' && text.length <= limit);
  if (!w || !strings(w.brief, 2000) || !Array.isArray(w.beats) || w.beats.length > 100 ||
      !w.beats.every(beat => strings(beat, 1000)) || !Array.isArray(w.notes) || w.notes.length > 100 ||
      !w.notes.every(note => strings(note, 2000))) throw Error('Quy trình dựng không hợp lệ');
}

export const snap = (time, fps) => Math.round(time * fps) / fps;

export function trimAt(layer, time, fps, edge) {
  const at = snap(time, fps), end = layer.start + layer.duration;
  if (layer.locked || at - layer.start < 0.999 / fps || end - at < 0.999 / fps) return;
  if (edge === 'right') return {...layer, duration: at - layer.start};
  const sourceIn = ['video', 'audio'].includes(layer.type) ? layer.sourceIn + at - layer.start : layer.sourceIn;
  return {...layer, start: at, duration: end - at, sourceIn};
}

export function captionsSrt(layers) {
  const stamp = time => new Date(Math.round(time * 1000)).toISOString().slice(11, 23).replace('.', ',');
  return layers.filter(layer => layer.type === 'caption' && !layer.hidden).sort((a, b) => a.start - b.start)
    .map((layer, i) => `${i + 1}\n${stamp(layer.start)} --> ${stamp(layer.start + layer.duration)}\n${layer.text}\n`).join('\n');
}

