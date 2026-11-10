import {templates,applyTemplate,canvasBox,overlapsVisibleText} from './templates.mjs';
import {parseCaptions} from './captions.mjs';
import {migrate,html,length,checkV2} from './model.mjs';
import {setupWorkflow} from './workflow-ui.js';
import {captionsSrt,cutApproved,planApproved,snap,trimAt} from './workflow.mjs';
let p,selected,clock=0,playing=false,scale=1,undo=[],redo=[],timer,zoom=30,dirty=false;
const $=id=>document.getElementById(id);
function status(text){
 for(const id of ['status','library-message','workflow-message'])$(id).textContent=text;
}
async function api(u,m='GET',b){const r=await fetch(u,{method:m,headers:{'Content-Type':'application/json'},body:b?JSON.stringify(b):undefined});const x=await r.json();if(!r.ok)throw Error(x.error);return x}
const safe=f=>async(...args)=>{try{await f(...args)}catch(e){status(e.message)}};
function checkpoint(){undo.push(JSON.stringify(p));if(undo.length>80)undo.shift();redo=[]}
function changed(){dirty=true;clearTimeout(timer);timer=setTimeout(safe(save),750)}
let saving=Promise.resolve();function save(){return saving=saving.catch(()=>{}).then(persist)}
async function persist(){
 if(!dirty)return;
 const sent=structuredClone(p);
 dirty=false;
 try{
  const saved=await api('/api/projects/'+p.id,'PUT',sent);
  p.revision=saved.revision;
  mergeReviews(saved);
  updateWorkflowButtons();
  status('Đã lưu · r'+p.revision);
 }catch(error){dirty=true;throw error;}
}
async function list(){const ps=await api('/api/projects');$('projects').replaceChildren(...ps.map(x=>new Option(x.title,x.id)));if(p)$('projects').value=p.id}
function fit(){const v=$('viewport');scale=Math.min((v.clientWidth-24)/p.output.width,(v.clientHeight-24)/p.output.height);$('canvas').style.width=p.output.width*scale+'px';$('canvas').style.height=p.output.height*scale+'px';$('frame').style.width=p.output.width+'px';$('frame').style.height=p.output.height+'px';$('frame').style.transform=`scale(${scale})`;boxes()}
function preview(){ $('frame').srcdoc=html(p,`/api/projects/${p.id}/files/`);$('frame').onload=()=>send();fit()}
function send(){ $('frame').contentWindow?.postMessage({kind:'clock',time:clock,playing},location.origin);$('time').textContent=clock.toFixed(2)+'s';$('seek').value=clock;boxes()}
function boxes(){if(!p)return;$('handles').replaceChildren();for(const l of p.layers){if(l.hidden||l.type==='audio'||clock<l.start||clock>=l.start+l.duration)continue;const b=document.createElement('div');b.className='box'+(selected===l.id?' active':'');b.style.cssText=`left:${l.x*scale}px;top:${l.y*scale}px;width:${l.width*scale}px;height:${l.height*scale}px;transform:rotate(${l.rotation}deg)`;b.title=l.name;b.onpointerdown=e=>drag(e,l,false);if(selected===l.id&&!l.locked){const grip=document.createElement('span');grip.className='grip';grip.onpointerdown=e=>{e.stopPropagation();drag(e,l,true)};b.append(grip)}$('handles').append(b)}}
function drag(e,l,resize){playing=false;selected=l.id;props();if(l.locked)return;checkpoint();const x=e.clientX,y=e.clientY,old={...l};e.currentTarget.setPointerCapture(e.pointerId);const target=e.currentTarget;target.onpointermove=ev=>{const dx=(ev.clientX-x)/scale,dy=(ev.clientY-y)/scale;if(resize){l.width=Math.max(10,old.width+dx);l.height=Math.max(10,old.height+dy)}else{l.x=old.x+dx;l.y=old.y+dy}const iframe=$('frame');const el=iframe.contentDocument?.getElementById(l.id);if(el)Object.assign(el.style,{left:l.x+'px',top:l.y+'px',width:l.width+'px',height:l.height+'px'});target.style.left=l.x*scale+'px';target.style.top=l.y*scale+'px';target.style.width=l.width*scale+'px';target.style.height=l.height*scale+'px'};target.onpointerup=()=>{target.onpointermove=null;render();changed()}}
function props(){const l=p.layers.find(x=>x.id===selected);$('props').replaceChildren();if(!l)return;l.align??='left';for(const key of ['name','text','start','duration','sourceIn','x','y','width','height','rotation','opacity','volume','fontSize','font','align','color','asset']){const label=document.createElement('label');label.textContent=({name:'Tên',text:'Nội dung',start:'Bắt đầu (s)',duration:'Thời lượng (s)',sourceIn:'Điểm vào media (s)',fontSize:'Cỡ chữ',font:'Font',asset:'Asset trong project'})[key]||key;let input=document.createElement(key==='text'?'textarea':['font','align'].includes(key)?'select':'input');if(key==='align')input.replaceChildren(...['left','center','right'].map(f=>new Option(f,f)));if(key==='font')input.replaceChildren(...['Arial','Segoe UI','Georgia','Times New Roman'].map(f=>new Option(f,f)));if(typeof l[key]==='number'){input.type='number';input.step='.033333'}if(key==='color')input.type='color';input.value=l[key];if(key==='text'){input.onfocus=()=>checkpoint();input.oninput=()=>{l.text=input.value;const el=$('frame').contentDocument?.getElementById(l.id);if(el)el.textContent=input.value;changed()};}input.onchange=()=>{checkpoint();l[key]=typeof l[key]==='number'?Number(input.value):input.value;render();changed()};label.append(input);$('props').append(label)}for(const key of ['hidden','locked']){const b=document.createElement('button');b.textContent=(l[key]?'✓ ':'')+(key==='hidden'?'Ẩn layer':'Khóa layer');b.onclick=()=>{checkpoint();l[key]=!l[key];render();changed()};$('props').append(b)}const file=document.createElement('input');file.placeholder='Đường dẫn ảnh/video/audio trên D';const b=document.createElement('button');b.textContent='Nhập asset';b.onclick=safe(async()=>{const current=p;
 b.disabled=true;
 try{
  const a=await api('/api/projects/'+p.id+'/import','POST',{path:file.value});
  if(current!==p||!p.layers.includes(l))throw Error('Project hoặc layer đã đổi. Hãy nhập lại từ layer cần chỉnh.');
  change(()=>{l.asset=a.asset;});
 }finally{b.disabled=false;}});$('props').append(file,b);
if(l.type==='video'){
 const label=document.createElement('label'), mode=document.createElement('select');
 mode.replaceChildren(new Option('Vừa khung','contain'),new Option('Phủ khung','cover'));
 mode.value=l.fit??'contain';
 mode.disabled=l.locked;
 mode.onchange=()=>change(()=>{l.fit=mode.value;});
 label.append('Khớp khung video',mode);
 const reset=document.createElement('button');
 reset.textContent='Đặt về khung canvas';
 reset.disabled=l.locked;
 reset.onclick=()=>change(()=>Object.assign(l,canvasBox(p.output)));
 $('props').append(label,reset);
}
if(p.workflow&&l.asset&&['video','audio'].includes(l.type)){
 const label=document.createElement('label'),toggle=document.createElement('input');
 toggle.type='checkbox';toggle.checked=Boolean(l.primary);label.append(toggle,' Clip chính của bản cắt');
 toggle.onchange=()=>change(()=>{l.primary=toggle.checked;});
 $('props').append(label);
}for(const delta of [-1,1]){const b=document.createElement('button');b.textContent=delta<0?'Xuống lớp':'Lên lớp';b.onclick=()=>{checkpoint();const i=p.layers.indexOf(l),j=i+delta;if(j>=0&&j<p.layers.length)[p.layers[i],p.layers[j]]=[p.layers[j],l];render();changed()};$('props').append(b)}}
const selectedLayer=()=>p?.layers.find(layer=>layer.id===selected);
function change(edit){checkpoint();edit(p);render();changed();}
const flush=()=>{clearTimeout(timer);return save();};
const refreshStage=setupWorkflow({api,safe,project:()=>p,layer:selectedLayer,time:()=>clock,
 change,flush,accept:saved=>{
  if(p.id!==saved.id)throw Error('Project đã đổi');
  p.revision=saved.revision;
  mergeReviews(saved);
  render();
 },job:runJob,status});
function mergeReviews(saved){
 if(!p.workflow)return;
 for(const key of ['plan','cut','qa']){
  delete p.workflow[key];
  if(saved.workflow?.[key])p.workflow[key]=saved.workflow[key];
 }
}
function updateWorkflowButtons(){
 refreshStage();
 document.querySelector('[data-action="render"]').hidden=Boolean(p.workflow);
 const draft=document.querySelector('[data-action="draft"]'),delivery=document.querySelector('[data-action="delivery"]');
 draft.hidden=delivery.hidden=!p.workflow;
 draft.disabled=!planApproved(p);
 delivery.disabled=!cutApproved(p);
}
function render(){
 updateWorkflowButtons();
 $('layers').replaceChildren(...p.layers.slice().reverse().map(l=>{const b=document.createElement('button');b.textContent=(l.hidden?'◌ ':l.locked?'▣ ':'◇ ')+l.name;b.className=l.id===selected?'selected':'';b.onclick=()=>{selected=l.id;render()};return b}));$('timeline').replaceChildren(...p.layers.map((l,i)=>{const row=document.createElement('div');row.className='track';row.style.width=Math.max(800,length(p)*zoom+150)+'px';const bar=document.createElement('div');bar.className='clipbar '+l.type+(selected===l.id?' selected':'');bar.textContent=l.name;bar.style.left=l.start*zoom+'px';bar.style.width=l.duration*zoom+'px';bar.onpointerdown=e=>{selected=l.id;props();if(l.locked)return;checkpoint();const x=e.clientX,start=l.start,d=l.duration;bar.setPointerCapture(e.pointerId);bar.onpointermove=ev=>{const dt=Math.round((ev.clientX-x)/zoom*p.output.fps)/p.output.fps;if(e.shiftKey)l.duration=Math.max(1/p.output.fps,d+dt);else l.start=Math.max(0,snap(start+dt,p.output.fps));bar.style.left=l.start*zoom+'px';bar.style.width=l.duration*zoom+'px'};bar.onpointerup=()=>{bar.onpointermove=null;render();changed()}};row.append(bar);return row}));$('title').value=p.title;$('background').value=p.style.background;$('aspect').value=p.output.width>p.output.height?'landscape':'portrait';$('size').textContent=`${p.output.width} × ${p.output.height} · ${p.output.fps}fps`;$('seek').max=length(p);$('seek').step=1/p.output.fps;props();preview()}
$('add').onclick=()=>{checkpoint();const type=$('kind').value;const l={id:'layer-'+crypto.randomUUID(),name:type+' '+(p.layers.length+1),type,start:clock,duration:4,...(type==='video'?canvasBox(p.output):{x:100,y:180,width:800,height:180}),rotation:0,opacity:1,volume:1,fontSize:64,font:'Arial',color:'#eee9df',hidden:false,locked:false,sourceIn:0,text:['text','caption'].includes(type)?'Nội dung mới':'',asset:''};p.layers.push(l);selected=l.id;render();changed()};$('title').onchange=()=>{checkpoint();p.title=$('title').value;changed()};$('background').onchange=()=>{checkpoint();p.style.background=$('background').value;render();changed()};$('aspect').onchange=()=>{checkpoint();p.output=$('aspect').value==='portrait'?{width:1080,height:1920,fps:30}:{width:1920,height:1080,fps:30};render();changed()};$('save').onclick=safe(save);
$('undo').onclick=()=>{if(undo.length){redo.push(JSON.stringify(p));const rev=p.revision;p=JSON.parse(undo.pop());p.revision=rev;render();changed()}};$('redo').onclick=()=>{if(redo.length){undo.push(JSON.stringify(p));const rev=p.revision;p=JSON.parse(redo.pop());p.revision=rev;render();changed()}};
$('projects').onchange=safe(async()=>{clearTimeout(timer);await save();p=migrate(await api('/api/projects/'+$('projects').value));undo=[];redo=[];clock=0;selected=p.layers[0]?.id;render()});$('new').onclick=safe(async()=>{clearTimeout(timer);await save();p=migrate(await api('/api/projects','POST',{}));await list();undo=[];redo=[];clock=0;selected=p.layers[0]?.id;render()});
$('seek').oninput=()=>{clock=+$('seek').value;send()};$('play').onclick=()=>{playing=!playing;$('play').textContent=playing?'Ⅱ':'▶';send()};let previous;const frameSamples=[];function tick(now){if(playing&&previous){frameSamples.push(now-previous);if(frameSamples.length>180)frameSamples.shift();if(frameSamples.length>=60){const a=[...frameSamples].sort((a,b)=>a-b);document.body.dataset.previewMetrics=JSON.stringify({samples:a.length,p95FrameMs:a[Math.ceil(a.length*.95)-1],meanFrameMs:a.reduce((a,b)=>a+b)/a.length,tracks:p.layers.length});}}if(playing&&previous){clock+=(now-previous)/1000;if(clock>=length(p)){clock=0;playing=false;$('play').textContent='▶'}send()}previous=now;requestAnimationFrame(tick)}requestAnimationFrame(tick);$('zoom').oninput=()=>{zoom=+$('zoom').value;render()};
function editClip(edge){
 const l=selectedLayer();
 if(!l)return;
 const left=trimAt(l,clock,p.output.fps,'right'),right=trimAt(l,clock,p.output.fps,'left');
 if(!left||!right)return status('Đặt playhead bên trong clip đang mở khóa');
 const index=p.layers.indexOf(l);
 if(edge==='split'&&p.layers.length>=300)return status('Timeline đã có 300 layer');
 change(()=>{
  if(edge==='split')p.layers.splice(index,1,left,{...right,id:'layer-'+crypto.randomUUID()});
  else p.layers[index]=edge==='left'?right:left;
 });
}
$('split').onclick=()=>editClip('split');
$('trim-left').onclick=()=>editClip('left');
$('trim-right').onclick=()=>editClip('right');
addEventListener('keydown',e=>{if(e.defaultPrevented||document.querySelector('dialog[open]')||['INPUT','TEXTAREA','SELECT','BUTTON','A'].includes(document.activeElement.tagName))return;if(e.code==='Space'){e.preventDefault();$('play').click()}if((e.ctrlKey||e.metaKey)&&e.key==='z'){e.preventDefault();$(e.shiftKey?'redo':'undo').click()}if(e.key==='Delete'){const l=p.layers.find(x=>x.id===selected);if(l&&!l.locked){checkpoint();p.layers=p.layers.filter(x=>x!==l);render();changed()}}});
async function runJob(action,params={}){
 await flush();
 const id=p.id;
 const job=await api(`/api/projects/${id}/jobs`,'POST',{action,revision:p.revision,...params});
 status('Đã xếp hàng · '+action);
 async function poll(){
  try{
   const result=await api('/api/jobs/'+job.id);
   if(p.id===id){
    $('jobs').textContent=result.status+' · '+(result.result||result.error||'');
    const href=result.file?`/api/projects/${id}/files/${result.file}`:result.url;
    if(result.status==='done'&&href){
     const a=document.createElement('a');
     a.href=href;a.target='_blank';a.rel='noopener';a.textContent='Mở kết quả';$('jobs').append(' ',a);
    }
   }
   if(['queued','running'].includes(result.status))setTimeout(poll,1200);
   else if(p.id===id)status(result.error||result.status);
  }catch(error){status(error.message);}
 }
 await poll();
}
for(const b of document.querySelectorAll('[data-action]'))b.onclick=safe(()=>runJob(b.dataset.action));
$('srt').onclick=()=>{
 const input=document.createElement('input');
 input.type='file';
 input.accept='.srt,.vtt';
 const message=$('caption-message');
 const current=p;
 input.onchange=async()=>{
  const file=input.files[0];
  if(!file)return;
  try{
   const cues=parseCaptions(await file.text(),file.name.toLowerCase().endsWith('.vtt')?'vtt':'srt');
   if(current!==p)throw Error('Project đã đổi. Hãy chọn lại file.');
   if(p.layers.length+cues.length>300)throw Error('Lượt nhập vượt giới hạn 300 layer của timeline');
   const layers=cues.map(cue=>({...cue,id:'layer-'+crypto.randomUUID(),type:'caption',name:'Phụ đề',
    x:p.output.width*.08,y:p.output.height*.79,width:p.output.width*.84,height:p.output.height*.18,
    font:'Arial',fontSize:44,color:'#ffffff',opacity:1,volume:1,sourceIn:0,rotation:0,hidden:false,locked:false,asset:''}));
   checkV2({...p,layers:[...p.layers,...layers]});
   change(()=>{p.layers.push(...layers);});
   message.textContent=`Đã nhập ${cues.length} cue`;
  }catch(error){message.textContent=error.message;}
  status(message.textContent);
 };
 input.click();
};
$('srtout').onclick=()=>{const text=captionsSrt(p.layers);const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text]));a.download='captions.srt';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
await safe(async()=>{await list();p=migrate($('projects').value?await api('/api/projects/'+$('projects').value):await api('/api/projects','POST',{}));selected=p.layers[0]?.id;render();status('Sẵn sàng · r'+p.revision)})();new ResizeObserver(()=>p&&fit()).observe($('viewport'));

$('storyboard').onclick=()=>{const value=prompt('Storyboard JSON: scenes (narration theo cảnh), whiteboard (image: assets/…, annotation theo renderer).',JSON.stringify({scenes:p.scenes,whiteboard:p.whiteboard||null},null,2));if(value){try{const data=JSON.parse(value);checkpoint();p.scenes=data.scenes;p.whiteboard=data.whiteboard;changed();status('Đã cập nhật storyboard, cần kiểm tra audio/annotation.')}catch(e){status(e.message)}}};

$('template').replaceChildren(...Object.entries(templates).map(([k,v])=>new Option(v,k)));
const templateDialog=$('template-dialog'), templateFrame=$('template-frame');
let templateDraft;
function fitTemplate(){
 if(!templateDialog.open||!templateDraft)return;
 const stage=$('template-stage');
 const {width,height}=templateDraft.output;
 const factor=Math.min(stage.clientWidth/width,stage.clientHeight/height);
 Object.assign(templateFrame.style,{width:width+'px',height:height+'px',
  left:(stage.clientWidth-width*factor)/2+'px',top:(stage.clientHeight-height*factor)/2+'px',
  transform:`scale(${factor})`});
}
new ResizeObserver(fitTemplate).observe($('template-stage'));
$('apply-template').onclick=safe(()=>{
 const key=$('template').value, start=snap(clock,p.output.fps);
 const draft=applyTemplate({...p,layers:[]},key);
 const layers=draft.layers.map(layer=>({...layer,start}));
 const overlaps=overlapsVisibleText(p.layers,layers);
 templateDraft={key,output:{...p.output},layers,overlaps};
 $('template-title').textContent=templates[key];
 $('template-message').textContent=overlaps
  ? 'Bố cục sẽ chồng lên chữ có sẵn tại playhead. Có thể đổi vị trí hoặc tạo project riêng.'
  : `Vị trí chèn ${start.toFixed(2)} s`;
 $('template-insert').textContent=overlaps?'Vẫn chèn tại playhead':'Chèn tại playhead';
 templateFrame.srcdoc=html(draft);
 templateDialog.showModal();
 fitTemplate();
});
$('template-close').onclick=()=>templateDialog.close();
$('template-insert').onclick=()=>{
 try{
  checkV2({...p,layers:[...p.layers,...templateDraft.layers]});
  change(()=>{p.layers.push(...templateDraft.layers);});
  templateDialog.close();
 }catch(error){$('template-message').textContent=error.message;}
};
$('template-new').onclick=async()=>{
 const buttons=['template-insert','template-new','template-close'].map($);
 buttons.forEach(button=>{button.disabled=true;});
 try{
  await flush();
  const {key,output}=templateDraft;
  p=migrate(await api('/api/projects','POST',{title:templates[key],template:key,output}));
  undo=[];redo=[];clock=0;playing=false;$('play').textContent='▶';
  selected=p.layers[0]?.id;
  render();
  templateDialog.close();
  await list();
  status('Đã tạo project từ mẫu');
 }catch(error){$('template-message').textContent=error.message;}
 finally{buttons.forEach(button=>{button.disabled=false;});}
};
