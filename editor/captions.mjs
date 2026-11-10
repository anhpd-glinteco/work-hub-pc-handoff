const TIMELINE_LIMIT = 3600;

export function parseCaptions(content, format) {
  const vtt = format === 'vtt';
  const lines = content.replace(/^\uFEFF/, '').split(/\r\n|\n|\r/);
  let index = 0;
  if (vtt) {
    if (!/^WEBVTT(?:[ \t].*)?$/.test(lines[0])) throw Error('Dòng 1: thiếu tiêu đề WEBVTT');
    index++;
    while (index < lines.length && lines[index].trim() && !lines[index].includes('-->')) index++;
    if (lines[index]?.includes('-->')) throw Error(`Dòng ${index+1}: cần dòng trống sau tiêu đề WEBVTT`);
  }
  const cues = [];
  while (index < lines.length) {
    if (!lines[index].trim()) { index++; continue; }
    const first = index;
    while (index < lines.length && lines[index].trim()) index++;
    const block = lines.slice(first, index);
    if (vtt && /^(NOTE(?:[ \t]|$)|STYLE$|REGION$)/.test(block[0].trim())) continue;
    const offset = block[0].includes('-->') ? 0 : 1;
    const line = first + offset + 1;
    const timing = /^([^\s]+)[ \t]+-->[ \t]+([^\s]+)(?:[ \t]+.*)?$/.exec(block[offset]?.trim() ?? '');
    if (!timing) throw Error(`Dòng ${line}: cue thiếu mốc bắt đầu hoặc kết thúc`);
    const start = seconds(timing[1], vtt), end = seconds(timing[2], vtt);
    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start || end > TIMELINE_LIMIT) {
      throw Error(`Dòng ${line}: mốc cue sai hoặc vượt timeline 60 phút`);
    }
    const text = block.slice(offset+1).join('\n').trim();
    if (!text || text.length > 10000) throw Error(`Dòng ${line}: nội dung cue trống hoặc quá dài`);
    cues.push({start, duration: end-start, text});
  }
  if (!cues.length) throw Error('Không tìm thấy cue phụ đề trong file');
  return cues;
}

function seconds(value, vtt) {
  const parts = (vtt ? /^(?:(\d{2,}):)?([0-5]\d):([0-5]\d)\.(\d{3})$/ :
    /^(\d{2,}):([0-5]\d):([0-5]\d)[,.](\d{3})$/).exec(value);
  return parts ? Number(parts[1] || 0)*3600 + Number(parts[2])*60 + Number(parts[3]) + Number(parts[4])/1000 : NaN;
}

