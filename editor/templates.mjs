export const templates = {
  'talking-head': 'Chữ lớn + phụ đề',
  process: 'Sơ đồ ba bước',
  product: 'Thẻ sản phẩm',
  intro: 'Mở đầu tối giản'
};

export const canvasBox = ({width, height}) => ({x: 0, y: 0, width, height});

export function applyTemplate(project, key, start = 0) {
  if (!Object.hasOwn(templates, key)) throw Error('Bố cục mẫu không hợp lệ');
  const {width, height} = project.output;
  const portrait = height > width;
  const shortSide = Math.min(width, height);
  const duration = key === 'intro' ? 3 : 10;
  const base = {start, duration, sourceIn: 0, rotation: 0, opacity: 1, volume: 1, font: 'Arial',
    align: 'center', hidden: false, locked: false, asset: ''};
  const layers = [];
  function add(type, name, text, [x, y, w, h], size, color = '#f7eedf') {
    layers.push({...base, id: 'layer-' + crypto.randomUUID(), type, name, text,
      x: width*x, y: height*y, width: width*w, height: height*h,
      fontSize: Math.max(1, Math.round(shortSide*size)), color});
  }
  if (key === 'talking-head') {
    add('text', 'Tiêu đề', 'Tiêu đề chính', [.08,.09,.84,.14], .06);
    add('caption', 'Phụ đề', 'Nhập lời thoại tại đây', [.08,.76,.84,.16], .04);
  } else if (key === 'intro') {
    add('text', 'Tiêu đề mở đầu', 'Tên video', [.08,.38,.84,.18], .08);
    add('shape', 'Đường nhấn', '', [.38,.58,.24,.012], .03, '#e2b880');
  } else if (key === 'product') {
    add('shape', 'Nền thẻ', '', [.08,.52,.84,.37], .04, '#403425');
    add('text', 'Tên sản phẩm', 'Tên sản phẩm', [.12,.55,.76,.09], .055);
    add('text', 'Điểm nổi bật', 'Một lợi ích nổi bật', [.12,.66,.76,.08], .04);
    add('text', 'CTA', 'Xem thêm', [.12,.78,.76,.07], .04, '#f3c587');
  } else {
    for (const [index, label] of ['Nghiên cứu', 'Thực hiện', 'Kiểm chứng'].entries()) {
      const x = portrait ? .13 : .08 + index*.29;
      const y = portrait ? .16 + index*.24 : .32;
      const w = portrait ? .74 : .26;
      const h = portrait ? .17 : .34;
      add('shape', 'Thẻ bước ' + (index+1), '', [x,y,w,h], .04, '#544d40');
      add('text', 'Nhãn bước ' + (index+1), (index+1) + '. ' + label,
        [x+.02,y+h*.3,w-.04,h*.6], portrait ? .052 : .042);
    }
  }
  project.layers.push(...layers);
  return project;
}

export function overlapsVisibleText(existing, added) {
  return existing.some(a => !a.hidden && ['text', 'caption'].includes(a.type) &&
    added.some(b => a.start < b.start+b.duration && b.start < a.start+a.duration &&
      a.x < b.x+b.width && b.x < a.x+a.width && a.y < b.y+b.height && b.y < a.y+a.height));
}

