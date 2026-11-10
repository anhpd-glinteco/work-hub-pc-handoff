import {connect} from './concat.mjs';
import {applyTemplate,templates} from './templates.mjs';
import {migrate,checkV2,html,length} from './model.mjs';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {randomUUID,createHash} from 'node:crypto';
import {catalog,catalogPath,catalogRows,ext,mediaPath,saveEntry} from './catalog.mjs';
import {captionsSrt,checkWorkflow,cutApproved,cutKey,planApproved,planKey} from './workflow.mjs';
import {spawn} from 'node:child_process';
export const home=path.dirname(fileURLToPath(import.meta.url));
export const root=process.env.WORK_HUB_PROJECTS||'D:/Codex/outputs/work-hub/editor-projects';
const hf='D:/Codex/work/local-tools/hyperframes/node_modules/hyperframes/bin/hyperframes.mjs';
const concat='C:/Users/ASUS/AppData/Local/Programs/Concat/Concat.exe';
export const tasks=['content-ideas','video-style','video-rough-cut','video-template-edit','video-whiteboard','image-edit','product-creative','motion-graphics','video-generative','video-shorts','audio-production','podcast-create'];

export function checked(base,relative){const p=path.resolve(base,relative);if(!p.startsWith(path.resolve(base)+path.sep))throw Error('Đường dẫn ngoài thư mục project');return p;}
function dir(id){if(!/^[a-f0-9-]{36}$/.test(id))throw Error('Project ID không hợp lệ');return checked(root,id);}
export function validate(p){
 checkV2(p);checkWorkflow(p);
 if(!tasks.includes(p.task)||!Number.isInteger(p.revision)||!Array.isArray(p.scenes)||p.scenes.length<1||p.scenes.length>100)throw Error('Project không hợp lệ');
 if(typeof p.title!=='string'||p.title.length>200)throw Error('Tên project không hợp lệ');
 const ids=new Set();for(const s of p.scenes){if(!/^[a-z0-9-]+$/.test(s.id)||ids.has(s.id))throw Error('ID cảnh trùng/không hợp lệ');ids.add(s.id);
 if(!Number.isFinite(s.duration)||s.duration<0.2||s.duration>600)throw Error('Thời lượng cảnh phải từ 0.2 đến 600 giây');
 for(const k of ['text','caption','narration'])if(typeof s[k]!=='string'||s[k].length>4000)throw Error('Nội dung cảnh không hợp lệ');
 for(const k of ['media','audio'])if(s[k]&&!/^assets\/[a-f0-9-]+\.[a-z0-9]+$/.test(s[k]))throw Error('Asset không hợp lệ');
 }if(!/^#[a-f0-9]{6}$/i.test(p.style.background)||!/^#[a-f0-9]{6}$/i.test(p.style.color))throw Error('Màu không hợp lệ');return p;
}
function atomic(file,data){const temp=file+'.'+randomUUID()+'.tmp';fs.writeFileSync(temp,JSON.stringify(data,null,2));fs.renameSync(temp,file);}
export function load(id){return migrate(JSON.parse(fs.readFileSync(path.join(dir(id),'project.json'),'utf8')));}
export function save(id,p,review=false){validate(p);const current=load(id);if(current.revision!==p.revision){const e=Error('Project đã đổi. Tải lại trước khi lưu.');e.status=409;throw e;}
 if(p.workflow&&!review){
  for(const key of ['plan','cut','qa']){delete p.workflow[key];if(current.workflow?.[key])p.workflow[key]=current.workflow[key];}
 }
 for(const s of [...p.scenes,...(p.layers||[]).map(l=>({media:l.asset}))])for(const k of ['media','audio'])if(s[k]&&!fs.existsSync(checked(dir(id),s[k])))throw Error('Thiếu asset '+s[k]);
 if(p.id!==id)throw Error('Sai project ID');fs.mkdirSync(path.join(dir(id),'history'),{recursive:true});fs.copyFileSync(path.join(dir(id),'project.json'),path.join(dir(id),'history',`${current.revision}-${randomUUID()}.json`));p={...p,revision:p.revision+1};atomic(path.join(dir(id),'project.json'),p);return p;
}
export function create(title='Project mới',task='video-template-edit',options={}){
 const id=randomUUID();let p={schemaVersion:1,id,title,task,revision:0,brief:'',sources:[],style:{background:'#132b3a',color:'#f6edcf'},scenes:[{id:'scene-1',duration:4,text:'Một yêu cầu. Nhiều khả năng.',caption:'Nghiên cứu → Thực hiện → Kiểm chứng',narration:'',media:'',audio:''}]};
 if(options.template!==undefined){
  if(!Object.hasOwn(templates,options.template))throw Error('Bố cục mẫu không hợp lệ');
  p=migrate(p);p.layers=[];
  if(options.output!==undefined){
   const {width,height,fps}=options.output||{};
   p.output={width,height,fps};
  }
  checkV2(p);
  applyTemplate(p,options.template);
 }
 validate(p);
 fs.mkdirSync(path.join(dir(id),'assets'),{recursive:true});atomic(path.join(dir(id),'project.json'),p);return p;
}
export function importAsset(id,source){const real=mediaPath(source);const name='assets/'+randomUUID()+path.extname(real).toLowerCase();fs.copyFileSync(real,checked(dir(id),name),fs.constants.COPYFILE_EXCL);return name;}
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export async function composition(p,folder){
 fs.mkdirSync(folder,{recursive:true});
 const assets=path.join(dir(p.id),'assets');
 fs.cpSync(assets,path.join(folder,'assets'),{recursive:true});
 const authored=structuredClone(p), audio=new Map();
 for(const layer of authored.layers.filter(l=>l.type==='video'&&!l.hidden&&l.asset)){
  if(!audio.has(layer.asset)){
   const info=await run('ffprobe',['-v','error','-select_streams','a','-show_entries','stream=index','-of','csv=p=0',checked(folder,layer.asset)],folder);
   audio.set(layer.asset,Boolean(info.trim()));
  }
  layer.hasAudio=audio.get(layer.asset);
 }
 fs.writeFileSync(path.join(folder,'index.html'),html(authored));
 atomic(path.join(folder,'snapshot.json'),p);
 return folder;
}
export function run(cmd,args,cwd){return new Promise((resolve,reject)=>{const child=spawn(cmd,args,{cwd,windowsHide:true,shell:false});let output='';const timer=setTimeout(()=>{child.kill();reject(Error('Tác vụ quá 20 phút'));},1200000);for(const stream of [child.stderr,child.stdout])stream?.on('data',d=>output=(output+d).slice(-6000));child.on('error',e=>{clearTimeout(timer);reject(e)});child.on('exit',code=>{clearTimeout(timer);code===0?resolve(output):reject(Error(output||`Mã lỗi ${code}`))});});}
const jobRoot=path.join(root,'jobs');fs.mkdirSync(jobRoot,{recursive:true});const jobs=new Map();for(const f of fs.readdirSync(jobRoot)){if(!f.endsWith('.json'))continue;try{const j=JSON.parse(fs.readFileSync(path.join(jobRoot,f)));if(['running','queued'].includes(j.status)){j.status='interrupted';atomic(path.join(jobRoot,f),j);}jobs.set(j.id,j);}catch{}}let queue=Promise.resolve();function record(j){atomic(path.join(jobRoot,j.id+'.json'),j);}
const renderKey=p=>createHash('sha256').update(html(p)).digest('hex');
const videoUse='D:/Codex/work/local-tools/video-use';
const assetPattern=/^assets\/[a-f0-9-]+\.(mp4|mov|webm|wav|mp3|m4a)$/;
async function probeMedia(file,kind){
 const info=JSON.parse(await run('ffprobe',['-v','error','-show_entries','format=duration:stream=codec_type','-of','json',file],root));
 const duration=Number(info.format?.duration);
 if(!info.streams?.some(s=>s.codec_type===(kind==='sfx'?'audio':'video'))||!(duration>0))throw Error('Không đọc được thời lượng hoặc stream media');
 return duration;
}
function reviewProject(p,body){
 const w=p.workflow;
 if(!w)throw Error('Bật quy trình trước khi duyệt');
 if(body.stage==='plan'){
  if(!w.brief.audience?.trim()||!w.brief.goal?.trim()||!w.brief.target?.trim()||
     !w.beats.length||w.beats.some(b=>!b.time?.trim()||!b.purpose?.trim()))throw Error('Điền người xem, mục tiêu, thời lượng và mốc/mục đích từng beat');
  const key=planKey(p);
  if(w.plan!==key){w.plan=key;delete w.cut;}
 }else{
  const job=jobs.get(body.jobId);
  if(!job||job.project!==p.id||job.status!=='done'||!job.file||!fs.existsSync(checked(dir(p.id),job.file)))throw Error('Chọn bản xuất đã hoàn tất của project');
  if(body.stage==='cut'){
   const key=cutKey(p);
   if(!planApproved(p)||!p.layers.some(l=>l.primary&&l.asset&&!l.hidden)||job.action!=='draft'||job.cut!==key||job.plan!==planKey(p))throw Error('Cần duyệt beat plan, đánh dấu clip chính và xem bản nháp của bản cắt hiện tại');
   w.cut={key,jobId:job.id};
  }else if(body.stage==='qa'){
   if(!cutApproved(p)||job.action!=='delivery'||job.renderKey!==renderKey(p))throw Error('Cần bản cắt đã duyệt và bản ứng viên của timeline hiện tại');
   if(typeof body.note!=='string'||!body.note.trim()||body.note.length>2000)throw Error('Ghi kết quả xem file trên thiết bị đích');
   w.qa={jobId:job.id,note:body.note};
  }else throw Error('Mốc duyệt không hợp lệ');
 }
 return save(p.id,p,true);
}
async function execute(job,p,action){
 const folder=path.join(dir(p.id),'exports',job.id);fs.mkdirSync(folder,{recursive:true});atomic(path.join(folder,'snapshot.json'),p);
 if(action==='transcribe'){
  const file=checked(dir(p.id),job.asset), stat=fs.statSync(file);
  const cache=checked(dir(p.id),`analysis/${path.basename(file)}-${stat.size}-${stat.mtimeMs}`);
  const transcript=path.join(cache,'transcripts',path.parse(file).name+'.json');
  if(!fs.existsSync(transcript))await run(path.join(videoUse,'.venv/Scripts/python.exe'),
    ['-X','utf8',path.join(videoUse,'helpers/transcribe.py'),file,'--edit-dir',cache,'--language','vi'],folder);
  const result=JSON.parse(fs.readFileSync(transcript,'utf8'));
  if(!Array.isArray(result.words))throw Error('Transcript thiếu timestamp từng từ');
  job.transcript=path.relative(dir(p.id),transcript);
  job.result=`Transcript tiếng Việt · ${result.words.length} từ`;
  return;
 }
 if(action==='handoff'){
  const {start,end}=job.range;
  const layers=p.layers.filter(l=>!l.hidden&&l.start<end&&l.start+l.duration>start).map(l=>{
   const from=Math.max(start,l.start), to=Math.min(end,l.start+l.duration);
   return {...l,start:from-start,duration:to-from,
    sourceIn:['video','audio'].includes(l.type)?l.sourceIn+from-l.start:l.sourceIn};
  });
  const cuts=layers.map(({name,type,start,duration,sourceIn,asset,primary,volume,fit},index)=>
    ({layer:index+1,name,type,start,end:start+duration,sourceIn,sourceOut:sourceIn+duration,asset,primary,volume,...(fit?{fit}:{})}));
  fs.mkdirSync(path.join(folder,'assets'),{recursive:true});
  for(const asset of new Set(layers.map(l=>l.asset).filter(Boolean))){
   for(const layer of layers.filter(l=>l.asset===asset&&l.libraryId)){
    if(catalog().find(row=>row.id===layer.libraryId)?.rights!=='production')throw Error('Xác minh lại quyền dùng: '+layer.name);
   }
   fs.copyFileSync(checked(dir(p.id),asset),checked(folder,asset),fs.constants.COPYFILE_EXCL);
  }
  atomic(path.join(folder,'cuts.json'),{output:p.output,range:job.range,cuts,beats:p.workflow?.beats||[]});
  fs.writeFileSync(path.join(folder,'captions.srt'),captionsSrt(layers));
  fs.writeFileSync(path.join(folder,'handoff.md'),[
   '# '+p.title,'Revision '+p.revision,'',
   'Dựng theo cuts.json. Số layer tăng từ dưới lên. Nhập captions.srt.',
   `Mốc trong cuts.json và SRT tính từ đầu đoạn bàn giao. Beat plan giữ timecode project; trừ ${start} giây khi áp vào đoạn.`,
   'Bài Koki: nền gốc → các dải chữ nhật → lớp nhân vật đã tách nền.',
   'Đặt từng dải tại beat đã ghi. Chớp ngắn ở beat cuối. Xuất riêng đoạn cần ghép lại vào Hub.'
  ].join('\n'));
  job.result='Gói bàn giao: '+folder;
  return;
 }
 if(action==='whiteboard'){const wb=p.whiteboard;if(!wb||!/^assets\/[a-f0-9-]+\.(png|jpg|jpeg)$/.test(wb.image)||!wb.annotation?.canvas||!Array.isArray(wb.annotation.elements))throw Error('Cần ảnh line-art và annotation trong Storyboard');const annotation=path.join(folder,'annotation.json');atomic(annotation,wb.annotation);await run('D:/Codex/work/local-tools/srt-whiteboard-animation/.venv/Scripts/python.exe',['-X','utf8','D:/Codex/work/local-tools/srt-whiteboard-animation/scripts/render_stream_whiteboard.py',checked(dir(p.id),wb.image),annotation,path.join(folder,'whiteboard.mp4'),'--bare-tip'],folder);job.file=`exports/${job.id}/whiteboard.mp4`;job.result='Whiteboard đã render từ ảnh/annotation của project';return;}
 if(action==='narrate'){
  for(const s of p.scenes)if(s.narration.trim()){const file=path.join(folder,s.id+'.wav');await run('D:/Codex/work/local-tools/vieneu-env/Scripts/python.exe',['-X','utf8','D:/local-video-factory/scripts/narrate.py','--text',s.narration,'--output',file],folder);}
  job.result='Đã tạo WAV theo cảnh trong '+folder+'; nhập WAV để chọn sử dụng.';return;
 }
 if(action==='hyperframes'){const project=await composition(p,path.join(folder,'hyperframes'));const output=await run(process.execPath,[hf,'preview',project,'--background','--no-open'],folder);job.url=output.match(/http:\/\/(?:localhost|127\.0\.0\.1):\d+[^\s"<>]*/)?.[0];job.result='Project HyperFrames: '+project+'\n'+output;return;}
 if(action==='concat'){const c=await connect(dir(p.id));const name='native-project',native=path.join(folder,name);try{await c.tool('project_create',{location:folder,name,video:{width:p.output.width,height:p.output.height,rateNum:p.output.fps,rateDen:1}});for(const l of p.layers.filter(l=>!l.hidden)){if(l.sourceIn>0)throw Error('ConCat: điểm vào sourceIn chưa được ánh xạ; dùng project HyperFrames cho bản trim này.');const state=await c.tool('track_add',{path:native});const trackId=state.timeline.tracks.at(-1).id;if(['text','caption','shape'].includes(l.type)){await c.tool('title_add',{path:native,trackId,start:l.start,duration:l.duration,offsetY:(l.y+l.height/2)/p.output.height-.5,style:{content:l.text||' ',fontFamily:l.font,fontSize:l.fontSize/p.output.height,color:l.color,maxWidth:l.width/p.output.width,background:l.type==='shape'?l.color:undefined,opacity:l.opacity}});}else if(l.asset){const state=await c.tool('media_import',{path:native,file:checked(dir(p.id),l.asset)});const mediaId=state.media.at(-1).id;const added=await c.tool('clip_add',{path:native,mediaId,trackId,start:l.start});const clip=added.timeline.clips.at(-1);const clipId=clip.id;if(l.type==='image'||l.duration<clip.duration)await c.tool('clip_trim',{path:native,clipId,edge:'end',delta:l.duration-clip.duration});await c.tool('clip_transform',{path:native,clipId,offsetX:(l.x+l.width/2)/p.output.width-.5,offsetY:(l.y+l.height/2)/p.output.height-.5,rotation:l.rotation});await c.tool('clip_update',{path:native,clipId,patch:{volume:l.volume,opacity:l.opacity,name:l.name}});}}await c.tool('project_save',{path:native});await c.tool('project_close',{path:native,save:true});await c.tool('project_open',{path:native});const started=await c.tool('export_start',{path:native,output:path.join(folder,'concat-output.mp4'),width:p.output.width,height:p.output.height,rateNum:p.output.fps,rateDen:1,codec:'h264'});const result=await c.tool('export_wait',{job:started.job,timeoutSeconds:120});if(result.state!=='done')throw Error('ConCat export chưa xong: '+JSON.stringify(result));job.file=`exports/${job.id}/concat-output.mp4`;job.result='Đã tạo, lưu và mở lại project ConCat: '+native;await c.tool('project_close',{path:native,save:true});}finally{c.close()}return;}
 if(!['render','draft','delivery'].includes(action))throw Error('Tác vụ không hỗ trợ');
 const project=await composition(p,path.join(folder,'hyperframes'));await run(process.execPath,[hf,'render',project,'--fps',String(p.output?.fps||30),'--quality',action==='delivery'?'delivery':'draft','--workers','1','-o',path.join(folder,'output.mp4')],folder);
 job.file=`exports/${job.id}/output.mp4`;job.result='Đã xuất bản revision '+p.revision;
}
function json(res,status,value){res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});res.end(JSON.stringify(value));}
export function server(){fs.mkdirSync(root,{recursive:true});return http.createServer(async(req,res)=>{
 try{
  if(!/^127\.0\.0\.1:\d+$/.test(req.headers.host||'')||(req.headers.origin&&req.headers.origin!==`http://${req.headers.host}`))return json(res,403,{error:'Chỉ phục vụ cùng origin local'});
  const url=new URL(req.url,'http://localhost'),bits=url.pathname.split('/').filter(Boolean);let body={};if(['POST','PUT'].includes(req.method)){if(!req.headers['content-type']?.startsWith('application/json'))return json(res,415,{error:'Cần JSON'});let raw='';for await(const chunk of req){raw+=chunk;if(raw.length>1000000)throw Error('Yêu cầu quá lớn');}body=JSON.parse(raw||'{}');}
  if(url.pathname==='/api/projects'&&req.method==='GET')return json(res,200,fs.readdirSync(root).filter(x=>/^[a-f0-9-]{36}$/.test(x)).map(id=>{const p=load(id);return {id,title:p.title,task:p.task,revision:p.revision}}));
  if(url.pathname==='/api/projects'&&req.method==='POST')return json(res,201,create(body.title,body.task,body));
  if(url.pathname==='/api/library/catalog'&&req.method==='PUT')return json(res,200,await saveEntry(body,probeMedia,atomic));
  if(url.pathname==='/api/library/media'&&['GET','HEAD'].includes(req.method)){
   return streamMedia(req,res,catalogPath(catalog().find(row=>row.id===url.searchParams.get('id'))));
  }
  if(url.pathname==='/api/library/file'){const entry=library().find(x=>Buffer.from(x.path).toString('base64url')===url.searchParams.get('id'));if(!entry||!fs.statSync(entry.path).isFile())throw Error('Không tìm thấy tài nguyên');const suffix=path.extname(entry.path).toLowerCase();const mime={'.mp4':'video/mp4','.wav':'audio/wav','.png':'image/png','.jpg':'image/jpeg'}[suffix]||'text/plain; charset=utf-8';res.writeHead(200,{'Content-Type':mime});fs.createReadStream(entry.path).on('error',()=>res.destroy()).pipe(res);return;}
  if(url.pathname==='/api/library')return json(res,200,[...catalogRows(),...library()]);
  if(url.pathname==='/api/preview'&&req.method==='POST'){validate(body);res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});res.end(html(body,`/api/projects/${body.id}/files/`));return;}
  if(url.pathname==='/api/tasks')return json(res,200,tasks);
  if(bits[0]==='api'&&bits[1]==='jobs'&&bits[3]==='transcript'){
   const job=jobs.get(bits[2]);
   if(job?.status!=='done'||!job.transcript)throw Error('Transcript chưa sẵn sàng');
   return json(res,200,JSON.parse(fs.readFileSync(checked(dir(job.project),job.transcript),'utf8')));
  }
  if(bits[0]==='api'&&bits[1]==='jobs')return json(res,200,jobs.get(bits[2])||{status:'unknown'});
  if(bits[0]==='api'&&bits[1]==='projects'&&bits[2]){
   const id=bits[2];if(bits.length===3&&req.method==='GET')return json(res,200,load(id));if(bits.length===3&&req.method==='PUT')return json(res,200,save(id,body));
   if(bits[3]==='import'&&req.method==='POST'){
    if(!body.libraryId)return json(res,200,{asset:importAsset(id,body.path)});
    const item=catalog().find(row=>row.id===body.libraryId);
    if(item?.rights!=='production')throw Error('Tư liệu chưa được xác nhận quyền dùng');
    const source=catalogPath(item);
    const duration=await probeMedia(source,item.kind);
    if(item.out>duration+0.001)throw Error('Nguồn đã đổi, cập nhật đoạn chọn trong thư viện');
    if(catalog().find(row=>row.id===item.id)?.version!==item.version)throw Error('Mục đã đổi, tải lại thư viện');
    return json(res,200,{asset:importAsset(id,source),item});
   }
   if(bits[3]==='review'&&req.method==='POST'){
    const p=load(id);
    if(p.revision!==body.revision)return json(res,409,{error:'Project đã đổi, hãy tải lại'});
    return json(res,200,reviewProject(p,body));
   }
   if(bits[3]==='jobs'&&req.method==='GET'){
    const p=load(id), key=renderKey(p);
    return json(res,200,[...jobs.values()].filter(job=>job.project===id).reverse().map(job=>({...job,current:job.renderKey===key})));
   }
   if(bits[3]==='jobs'&&req.method==='POST'){const p=load(id);if(p.revision!==body.revision)return json(res,409,{error:'Lưu và tải lại project trước khi chạy'});if(!['render','draft','delivery','handoff','transcribe','hyperframes','concat','narrate','whiteboard'].includes(body.action))throw Error('Tác vụ không hợp lệ');if(body.action==='transcribe'&&(!assetPattern.test(body.asset)||!p.layers.some(l=>l.asset===body.asset)))throw Error('Chọn layer có tiếng để tạo transcript');
   if(p.workflow&&body.action==='draft'&&!planApproved(p))throw Error('Duyệt beat plan trước khi xuất bản cắt thô');
   if(p.workflow&&body.action==='delivery'&&!cutApproved(p))throw Error('Duyệt bản cắt trước khi xuất ứng viên');
   if(body.action==='concat'&&p.layers.some(l=>l.type==='video'&&!l.hidden&&l.asset&&l.fit==='cover'))
    throw Error('ConCat chưa hỗ trợ Phủ khung. Chọn Xuất video hoặc HyperFrames để giữ crop.');
   const job={id:randomUUID(),project:id,revision:p.revision,status:'queued',action:body.action};
   if(body.action==='transcribe')job.asset=body.asset;
   if(body.action==='handoff'){
    const start=body.start??0,end=body.end??length(p);
    if(!Number.isFinite(start)||!Number.isFinite(end)||start<0||end<=start||end>length(p))throw Error('Khoảng bàn giao ngoài timeline');
    job.range={start,end};
   }
   if(body.action==='draft'){job.cut=cutKey(p);job.plan=planKey(p);}
   if(['draft','delivery'].includes(body.action))job.renderKey=renderKey(p);jobs.set(job.id,job);record(job);queue=queue.then(async()=>{job.status='running';job.startedAt=Date.now();record(job);try{await execute(job,p,body.action);job.status='done';}catch(e){job.status='failed';job.error=e.message;}job.elapsedMs=Date.now()-job.startedAt;record(job);});return json(res,202,job);}
   if(bits[3]==='files'&&['GET','HEAD'].includes(req.method)){const file=checked(dir(id),bits.slice(4).join('/'));if(!ext.has(path.extname(file).toLowerCase()))throw Error('Loại file không hợp lệ');return streamMedia(req,res,file);}
  }
  const files={'/':'index.html','/app.js':'app.js','/model.mjs':'model.mjs','/templates.mjs':'templates.mjs','/workflow.mjs':'workflow.mjs','/workflow-ui.js':'workflow-ui.js','/captions.mjs':'captions.mjs','/style.css':'style.css'};
  if(files[url.pathname]&&req.method==='GET'){
   res.writeHead(200,{'Content-Type':url.pathname==='/'?'text/html; charset=utf-8':url.pathname.endsWith('.css')?'text/css':'text/javascript; charset=utf-8'});
   res.end(fs.readFileSync(path.join(home,files[url.pathname])));return;
  }
  json(res,404,{error:'Không tìm thấy'});
 }catch(e){if(res.headersSent)res.destroy();else json(res,e.status||400,{error:e.message});}
 });}
function streamMedia(req,res,file){
 const size=fs.statSync(file).size;let start=0,end=size-1;const range=req.headers.range;if(range){const m=/^bytes=(\d+)-(\d*)$/.exec(range);if(!m||+m[1]>=size){res.writeHead(416,{'Content-Range':`bytes */${size}`});res.end();return;}start=+m[1];end=m[2]?Math.min(+m[2],size-1):end;if(end<start)throw Error('Range không hợp lệ');}const mime={'.mp4':'video/mp4','.webm':'video/webm','.wav':'audio/wav','.mp3':'audio/mpeg','.m4a':'audio/mp4','.mov':'video/quicktime','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp'}[path.extname(file)]||'application/octet-stream';res.writeHead(range?206:200,{'Content-Type':mime,'Accept-Ranges':'bytes','Content-Length':end-start+1,...(range?{'Content-Range':`bytes ${start}-${end}/${size}`}:{})});if(req.method==='HEAD')res.end();else{const stream=fs.createReadStream(file,{start,end});stream.on('error',()=>res.destroy());res.on('close',()=>stream.destroy());stream.pipe(res)}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))server().listen(4317,'127.0.0.1',()=>console.log('Work Hub Editor: http://127.0.0.1:4317'));

function library(){const rows=[];const walk=(folder,group,depth=0)=>{if(depth>5||!fs.existsSync(folder))return;for(const e of fs.readdirSync(folder,{withFileTypes:true})){if(e.name.startsWith('.')||['node_modules','assets','history'].includes(e.name))continue;const f=path.join(folder,e.name);if(e.isDirectory())walk(f,group,depth+1);else if(/\.(md|json|mp4|wav|png|jpg|vtt|srt)$/i.test(f))rows.push({name:e.name,path:f,group,bytes:fs.statSync(f).size,status:'Chưa nghiệm thu riêng'});}};walk('D:/Codex/outputs/work-hub/2026-11-01','Kết quả / mẫu');walk('D:/local-video-factory/.agents/skills','Skills');walk('D:/Codex/downloads/work-hub/2026-11-01/tiktok-research','Nguồn tham khảo');for(const [name,file]of [['ConCat',concat],['HyperFrames',hf],['VieNeu','D:/Codex/work/local-tools/vieneu-env/Scripts/python.exe'],['VoiceStudio','D:/Codex/work/local-tools/VoiceStudio'],['Whiteboard','D:/Codex/work/local-tools/srt-whiteboard-animation'],['Recordly','D:/Codex/work/local-tools/Recordly/Recordly.exe']])rows.push({name,path:file,group:'Công cụ',status:fs.existsSync(file)?'Đã có · xem TOOLS.md để biết mức thử':'Thiếu'});return rows;}
