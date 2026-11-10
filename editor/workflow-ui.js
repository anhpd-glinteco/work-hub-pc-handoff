import {canvasBox} from './templates.mjs';
import {beatFields,briefFields,cutApproved,cutKey,newWorkflow,planApproved,planKey,snap} from './workflow.mjs';

const $ = id => document.getElementById(id);
function el(tag, text) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  return node;
}
function button(text, click) {
  const node = el('button', text);
  node.type = 'button';
  node.onclick = click;
  return node;
}
function field(form, key, title, value, type = 'text') {
  const label = el('label', title);
  const input = el(type === 'textarea' ? 'textarea' : 'input');
  if (type !== 'textarea') input.type = type;
  if (type === 'number') {input.min = '0'; input.step = 'any';}
  input.name = key;
  input.value = value ?? '';
  label.append(input);
  form.append(label);
  return input;
}
function link(text, href) {
  const a = el('a', text);
  a.href = href;
  a.target = '_blank';
  a.rel = 'noopener noreferrer';
  return a;
}

export function setupWorkflow({api, safe, project, layer, time, change, flush, accept, job, status}) {
  let entries = [];
  const library = $('catalog'), panel = $('workflow-panel');
  const reload = async () => {entries = await api('/api/library'); browse();};
  $('library').onclick = safe(async () => {await reload(); library.showModal();});
  $('close').onclick = () => library.close();
  $('search').oninput = browse;
  $('library-kind').onchange = browse;

  function browse() {
    const normalize = value => value.toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '').replaceAll('đ', 'd');
    const words = normalize($('search').value).trim().split(/\s+/);
    const group = $('library-kind').value;
    const matches = entries.filter(entry => (!group || (entry.kind || 'legacy') === group) &&
      words.every(word => normalize([entry.name,entry.path,entry.group,entry.tags,entry.notes].join(' ')).includes(word)));
    $('library-count').textContent = `${Math.min(250,matches.length)} / ${matches.length} mục`;
    $('entries').replaceChildren(...matches.slice(0,250).map(entry => {
      const card = el('article');
      card.className = 'entry';
      card.append(el('strong', entry.group + ' · ' + entry.name));
      if (!entry.kind) {
        card.append(el('small', entry.status + ' · ' + entry.path));
        if (entry.group !== 'Công cụ') {
          const id = btoa(String.fromCharCode(...new TextEncoder().encode(entry.path))).replaceAll('+','-').replaceAll('/','_').replaceAll('=','');
          card.append(link('Xem tài nguyên', '/api/library/file?id='+id));
        }
        return card;
      }
      card.append(el('small',[entry.tags, entry.timestamp, entry.credits, entry.license,
        entry.kind !== 'reference' && (entry.available ? `${Number(entry.in.toFixed(3))}–${Number(entry.out.toFixed(3))} s` : 'Thiếu file: '+entry.path),
        {production:'Được dùng', pending:'Chờ xác minh', reference:'Chỉ tham khảo'}[entry.rights]].filter(Boolean).join(' · ')));
      if (entry.notes) card.append(el('p',entry.notes));
      if (entry.url) card.append(link('Mở nguồn',entry.url));
      if (entry.available) {
        card.append(button('Xem trước', () => {
          if (card.querySelector('audio,video')) {card.querySelector('audio,video').remove();return;}
          $('entries').querySelectorAll('audio,video').forEach(preview => preview.remove());
          const media = el(entry.kind === 'sfx' ? 'audio' : 'video');
          media.controls = true;
          media.preload = 'metadata';
          media.src = `/api/library/media?id=${entry.id}#t=${entry.in},${entry.out}`;
          media.addEventListener('timeupdate', () => {if (media.currentTime >= entry.out) media.pause();});
          card.append(media);
        }));
        if (entry.rights === 'production') card.append(button('Chèn tại playhead', safe(async () => {
          const current = project(), at = time();
          const {asset,item} = await api(`/api/projects/${current.id}/import`,'POST',{libraryId:entry.id});
          if (project().id !== current.id) throw Error('Project đã đổi');
          const type = item.kind === 'sfx' ? 'audio' : 'video';
          change(p => p.layers.push({id:'layer-'+crypto.randomUUID(),name:item.name,type,asset,libraryId:item.id,
            start:snap(at,p.output.fps),duration:item.out-item.in,sourceIn:item.in,
            ...canvasBox(p.output),rotation:0,opacity:1,
            volume:type === 'audio' ? .35 : 1,fontSize:44,font:'Arial',color:'#ffffff',text:'',hidden:false,locked:false}));
          library.close();
        })));
      }
      if (entry.kind === 'reference') card.append(button('Dùng làm mẫu', () => {
        change(p => {
          p.workflow ??= newWorkflow();
          p.workflow.brief.style = [entry.name,entry.url,entry.timestamp,entry.notes].filter(Boolean).join('\n').slice(0,2000);
        });
        library.close();
      }));
      card.append(button('Sửa thông tin', () => editEntry(entry)));
      return card;
    }));
  }

  $('library-add').onclick = () => editEntry({kind:['footage','reference','sfx'].includes($('library-kind').value)?$('library-kind').value:'footage'});
  function editEntry(entry) {
    const form = $('library-editor');
    form.replaceChildren();
    form.hidden = false;
    const select = el('select');
    for (const [value,label] of Object.entries({footage:'Footage',reference:'Video mẫu',sfx:'SFX'})) select.add(new Option(label,value));
    select.value = entry.kind;
    select.disabled = Boolean(entry.id);
    const label = el('label','Loại tư liệu');
    label.append(select);
    form.append(label);
    const fields = el('div');
    form.append(fields);
    function renderFields() {
      fields.replaceChildren();
      field(fields,'name','Tên',entry.name).required = true;
      field(fields,'url','Link nguồn',entry.url,'url');
      field(fields,'tags','Tag hành động, bối cảnh, mục đích',entry.tags);
      if (select.value === 'reference') field(fields,'timestamp','Mốc tham khảo',entry.timestamp);
      else {
        field(fields,'path','Đường dẫn file trên ổ D',entry.path).required = true;
        field(fields,'in','Điểm vào nguồn (giây)',entry.in,'number');
        field(fields,'out','Điểm ra nguồn (giây, trống = cuối file)',entry.out,'number');
        const rights = el('select');
        rights.name = 'rights';
        rights.replaceChildren(new Option('Chờ xác minh','pending'),new Option('Chỉ tham khảo','reference'),new Option('Được dùng','production'));
        rights.value = entry.rights || 'pending';
        const rightsLabel = el('label','Quyền sử dụng'); rightsLabel.append(rights); fields.append(rightsLabel);
        field(fields,'credits','Tác giả / chủ sở hữu',entry.credits);
        field(fields,'license','Căn cứ quyền sử dụng',entry.license);
      }
      field(fields,'notes','Kỹ thuật, tình huống và điều kiện áp dụng',entry.notes,'textarea');
    }
    select.onchange = renderFields;
    renderFields();
    const submit = el('button','Lưu tư liệu');
    form.append(submit,button('Hủy', () => {form.hidden = true;}));
    form.onsubmit = safe(async event => {
      event.preventDefault();
      submit.disabled = true;
      try {
        await api('/api/library/catalog','PUT',{...Object.fromEntries(new FormData(form)),kind:select.value,id:entry.id,version:entry.version});
        form.hidden = true;
        await reload();
      } finally {submit.disabled = false;}
    });
    fields.querySelector('input').focus();
  }

  function refreshStage() {
    const p = project();
    if (!p) return;
    $('workflow-state').textContent = !p.workflow ? 'Có thể bật cho project này' : cutApproved(p)
      ? 'Đã duyệt bản cắt · hoàn thiện' : planApproved(p) ? 'Đã duyệt beat plan · dựng thô' : 'Brief và beat plan cần duyệt';
  }

  $('workflow-open').onclick = safe(async () => {
    if (!project().workflow) change(p => {p.workflow = newWorkflow();});
    panel.showModal();
    await showWorkflow();
  });
  $('workflow-close').onclick = () => panel.close();
  const review = async (stage, jobId, note) => {
    await flush();
    const p = project();
    accept(await api(`/api/projects/${p.id}/review`,'POST',{revision:p.revision,stage,jobId,note}));
    await showWorkflow();
  };

  async function showWorkflow() {
    const p = project(), w = p.workflow;
    const body = $('workflow-body');
    body.replaceChildren(el('h3','1. Brief và mẫu'),el('p','Chọn tỷ lệ khung trong Project. Chọn Video mẫu từ Thư viện hoặc ghi link và timecode bên dưới.'));
    const bind = (target, key, title) => {
      const input = field(target.container,key,title,target.value[key],'textarea');
      input.maxLength = target.limit;
      input.onchange = () => change(() => {target.value[key] = input.value;});
    };
    for (const [key,title] of Object.entries(briefFields)) bind({container:body,value:w.brief,limit:2000},key,title);
    body.append(el('h3','2. Beat plan và take'));
    w.beats.forEach((beat,index) => {
      const row = el('fieldset'); row.append(el('legend',`Beat ${index+1}`));
      for (const [key,title] of Object.entries(beatFields)) bind({container:row,value:beat,limit:1000},key,title);
      row.append(button('Bỏ beat',safe(async () => {change(() => w.beats.splice(index,1));await showWorkflow();})));
      body.append(row);
    });
    body.append(button('Thêm beat',safe(async () => {
      if (w.beats.length >= 100) throw Error('Tối đa 100 beat');
      change(() => w.beats.push({time:time().toFixed(2)+' s'}));
      await showWorkflow();
    })), button('Duyệt beat plan',safe(() => review('plan'))));
    body.append(el('h3','3. Duyệt cắt thô và góp ý'),
      el('p','Chọn các clip chính trong Thuộc tính. Xuất bản cắt thô sau khi duyệt beat plan. Chọn đúng bản xem khi ghi góp ý.'));
    await flush();
    const jobs = await api(`/api/projects/${p.id}/jobs`);
    const renders = jobs.filter(j => j.status === 'done' && j.file && ['render','draft','delivery'].includes(j.action));
    const pick = el('select');
    pick.setAttribute('aria-label','Bản xuất để xem và góp ý');
    for (const j of renders) pick.add(new Option(`${j.action} · r${j.revision} · ${j.id.slice(0,8)}${j.current?' · timeline hiện tại':''}`,j.id));
    const open = link('Xem file đã xuất','#');
    const update = () => {
      const j = renders.find(j => j.id === pick.value);
      open.hidden = !j;
      if (j) open.href = `/api/projects/${p.id}/files/${j.file}`;
    };
    pick.onchange = update; update();
    const note = field(body,'feedback','Góp ý (đặt playhead tại đoạn cần sửa)','','textarea');
    note.maxLength = 2000;
    body.append(pick,open,button('Lưu góp ý',safe(async () => {
      if (!pick.value || !note.value.trim() || w.notes.length >= 100) throw Error('Chọn bản, nhập góp ý và kiểm tra giới hạn 100 ghi chú');
      change(() => w.notes.push({jobId:pick.value,time:time().toFixed(2),text:note.value}));
      await showWorkflow();
    })),button('Duyệt bản cắt đã chọn',safe(() => review('cut',pick.value))));
    for (const entry of w.notes) {
      const j = renders.find(j => j.id === entry.jobId);
      const line = el('p',`${entry.time} s · ${entry.text} `);
      if (j) line.append(link(`r${j.revision}`,`/api/projects/${p.id}/files/${j.file}#t=${entry.time}`));
      body.append(line);
    }
    body.append(el('h3','4. Kiểm tra bản ứng viên'));
    const qa = field(body,'qa','Thiết bị và kết quả xem trọn file',w.qa?.note,'textarea');
    qa.maxLength = 2000;
    const checked = el('input');
    checked.type = 'checkbox';
    const checkLabel = el('label','Đã xem hết trên thiết bị đích, kiểm tra hình, tiếng, phụ đề và đồng bộ');
    checkLabel.prepend(checked);
    const approvedJob = renders.find(j => j.id === w.qa?.jobId);
    if (approvedJob) {
      body.append(el('p',approvedJob.current && cutApproved(p) ? 'QA đã lưu cho bản hiện tại' : 'QA đã lưu cho bản trước'),
        link('Mở file đã ghi nhận QA',`/api/projects/${p.id}/files/${approvedJob.file}`));
    }
    body.append(checkLabel,button('Ghi nhận QA cho bản đã chọn',safe(async () => {
      if (!checked.checked) throw Error('Xác nhận đã kiểm tra trọn file trên thiết bị đích');
      await review('qa',pick.value,qa.value);
    })));
    body.append(el('h3','Bàn giao một đoạn'));
    const start=field(body,'handoff-start','Điểm vào timeline (giây)','','number');
    const end=field(body,'handoff-end','Điểm ra timeline (giây)','','number');
    body.append(button('Tạo gói đoạn',safe(async () => {
      const range={start:start.value===''?undefined:Number(start.value),end:end.value===''?undefined:Number(end.value)};
      panel.close();
      await job('handoff',range);
    })));
    body.append(el('h3','Transcript theo từ'));
    const transcripts = jobs.filter(j => j.status === 'done' && j.transcript);
    for (const j of transcripts) body.append(link(j.result,`/api/jobs/${j.id}/transcript`));
    const current = layer();
    if (current?.asset && ['video','audio'].includes(current.type)) {
      body.append(button('Tạo transcript cho '+current.name,safe(async () => {
        panel.close();
        await job('transcribe',{asset:current.asset});
      })));
    }
  }

  return refreshStage;
}

