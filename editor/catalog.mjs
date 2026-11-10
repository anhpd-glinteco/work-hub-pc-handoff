import fs from 'node:fs';
import path from 'node:path';
import {randomUUID} from 'node:crypto';

export const libraryRoot = process.env.WORK_HUB_LIBRARY || 'D:/Codex/outputs/work-hub/media-library';
const catalogFile = path.join(libraryRoot, 'catalog.json');
export const roots = ['D:/Codex/outputs', 'D:/Codex/downloads', 'D:/local-video-factory/media', libraryRoot];
export const ext = new Set(['.png','.jpg','.jpeg','.webp','.mp4','.webm','.mov','.wav','.mp3','.m4a']);
const types = {footage: ['.mp4','.webm','.mov'], sfx: ['.wav','.mp3','.m4a']};
const groups = {footage: 'Footage', reference: 'Video mẫu', sfx: 'SFX'};

export function mediaPath(source, allowed = ext) {
  const real = fs.realpathSync(source);
  const inside = roots.some(root => real.toLowerCase().startsWith(path.resolve(root).toLowerCase() + path.sep));
  if (!inside || !allowed.has(path.extname(real).toLowerCase()) || !fs.statSync(real).isFile()) {
    throw Error('Media nằm ngoài vùng cho phép hoặc sai định dạng');
  }
  return real;
}

export function catalog() {
  if (!fs.existsSync(catalogFile)) return [];
  return JSON.parse(fs.readFileSync(catalogFile, 'utf8'));
}

export function catalogPath(entry) {
  if (!types[entry?.kind]) throw Error('Mục này chỉ dùng để tham khảo');
  return mediaPath(entry.path, new Set(types[entry.kind]));
}

export function catalogRows() {
  return catalog().map(entry => {
    let available = false;
    try { if (entry.path) available = Boolean(catalogPath(entry)); } catch {}
    return {...entry, group: groups[entry.kind], available};
  });
}

export async function saveEntry(input, probe, atomic) {
  const {id, kind, version} = input;
  if (!Object.hasOwn(groups, kind)) throw Error('Loại tư liệu không hợp lệ');
  const before = id && catalog().find(entry => entry.id === id);
  if (id && (!before || before.kind !== kind)) throw Error('Mục thư viện không hợp lệ');
  const row = {id: id || randomUUID(), kind, version: (before?.version || 0) + 1};
  for (const key of ['name', 'tags', 'url', 'credits', 'license', 'notes', 'path', 'timestamp']) {
    const value = input[key] ?? '';
    if (typeof value !== 'string' || value.length > 2000) throw Error('Thông tin tư liệu không hợp lệ');
    row[key] = value.trim();
  }
  if (!row.name || (row.url && !['https:', 'http:'].includes(new URL(row.url).protocol))) throw Error('Cần tên và URL web hợp lệ');
  row.rights = kind === 'reference' ? 'reference' : input.rights;
  if (!['reference', 'pending', 'production'].includes(row.rights)) throw Error('Chọn quyền sử dụng');
  if (row.rights === 'production' && !row.license) throw Error('Ghi căn cứ quyền sử dụng');
  if (kind === 'reference') {
    if (!row.url) throw Error('Cần link video mẫu');
    row.path = '';
  } else {
    let duration;
    try { duration = await probe(catalogPath(row), kind); } catch (error) {
      if (error.code !== 'ENOENT' || !before || row.path !== before.path) throw error;
      duration = before.mediaDuration;
    }
    row.mediaDuration = duration;
    row.in = Number(input.in || 0);
    row.out = input.out === '' || input.out === undefined ? duration : Number(input.out);
    if (!Number.isFinite(row.in) || !Number.isFinite(row.out) ||
        row.in < 0 || row.out <= row.in || row.out > duration + 0.001) throw Error('Khoảng chọn ngoài media');
  }
  const rows = catalog();
  const index = rows.findIndex(entry => entry.id === id);
  if (id && (index < 0 || rows[index].version !== version)) {
    const error = Error('Mục đã đổi. Tải lại thư viện rồi thử lại.');
    error.status = 409;
    throw error;
  }
  if (index < 0) rows.push(row); else rows[index] = row;
  fs.mkdirSync(libraryRoot, {recursive: true});
  atomic(catalogFile, rows);
  return row;
}

