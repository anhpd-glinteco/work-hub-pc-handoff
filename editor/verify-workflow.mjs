import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
import {cutApproved,planApproved,trimAt} from './workflow.mjs';

const fixtures=process.argv[2];
assert.ok(fixtures,'Usage: node verify-workflow.mjs <fixture folder> [baseline editor folder]');
const evidence=path.dirname(fixtures);
const sandbox=fs.mkdtempSync('D:/Codex/work/edit-hub-check-');
process.env.WORK_HUB_PROJECTS=path.join(sandbox,'projects');
process.env.WORK_HUB_LIBRARY=path.join(sandbox,'library');
const app=await import('./server.mjs');
const server=app.server();
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
let baseline;
const timing={};
let base='http://127.0.0.1:'+server.address().port;
async function request(url,method='GET',body,expected=200){
  const result=await fetch(base+url,{method,headers:{'Content-Type':'application/json'},body:body&&JSON.stringify(body)});
  const data=await result.json();
  assert.equal(result.status,expected,JSON.stringify(data));
  return data;
}
async function waitJob(prefix,p,action,params={}){
  const start=performance.now();
  const job=await request(prefix+'/jobs','POST',{action,revision:p.revision,...params},202);
  for(let i=0;i<1800;i++){
    const result=await request('/api/jobs/'+job.id);
    if(result.status==='done'){
      timing[action]=Math.round(performance.now()-start);
      console.log(action,result.id,timing[action],result.result);
      return result;
    }
    assert.ok(['running','queued'].includes(result.status),JSON.stringify(result));
    await delay(500);
  }
  assert.fail(action+' timed out');
}
try{
  const footage=path.join(fixtures,'take.mp4'), broll=path.join(fixtures,'broll.mp4');
  const shutter='D:/Codex/outputs/work-hub/media-library/sfx/272017.mp3';
  const add=(body,expected=200)=>request('/api/library/catalog','PUT',body,expected);
  const pending=await add({kind:'footage',name:'Cảnh mở',path:footage,in:1,out:33,rights:'pending',tags:'sân sáng đèn hook'});
  const p1=await request('/api/projects','POST',{title:'Pilot · thoại dọc'},201);
  const prefix='/api/projects/'+p1.id;
  await request(prefix+'/import','POST',{libraryId:pending.id},400);
  const item=await add({...pending,rights:'production',license:'Fixture tự tạo'});
  await add({...pending,rights:'pending'},409);
  await add({kind:'reference',name:'Link xấu',url:'javascript:alert(1)'},400);
  await add({kind:'footage',name:'Ngoài phạm vi',path:'C:/Windows/notepad.exe',rights:'pending'},400);
  await add({...item,out:1000},400);
  const reference=await add({kind:'reference',name:'Mẫu Koki',url:'https://vt.tiktok.com/ZSpM57xLy/'});
  await request(prefix+'/import','POST',{libraryId:reference.id},400);
  const start=performance.now();
  const {asset}=await request(prefix+'/import','POST',{libraryId:item.id});
  timing.catalogInsertApiMs=Math.round(performance.now()-start);
  const audio=await add({kind:'sfx',name:'Canon Shutter',path:shutter,rights:'production',license:'CC0'});
  const insertAudio=await request(prefix+'/import','POST',{libraryId:audio.id});
  const brollAsset=await request(prefix+'/import','POST',{path:broll});
  const media=await fetch(base+'/api/library/media?id='+item.id,{headers:{Range:'bytes=0-127'}});
  assert.equal(media.status,206);assert.equal((await media.arrayBuffer()).byteLength,128);
  const vanished=await add({kind:'footage',name:'Nguồn sẽ mất',path:broll,rights:'pending'});
  const moved=path.join(fixtures,'temporarily-hidden-broll.mp4');
  fs.renameSync(broll,moved);
  try {
    assert.equal((await request('/api/library')).find(row=>row.id===vanished.id).available,false);
    await add({...vanished,tags:'nguồn thiếu'});
  } finally {fs.renameSync(moved,broll);}

  let p=await request(prefix);
  p.output={width:720,height:1280,fps:30};
  const layer=(id,type,extra)=>({id,type,name:id,start:0,duration:32,sourceIn:0,x:0,y:0,width:720,height:1280,
    rotation:0,opacity:1,volume:1,fontSize:40,font:'Arial',color:'#ffffff',text:'',asset:'',hidden:false,locked:false,...extra});
  const voice=layer('voice','video',{asset,libraryId:item.id,sourceIn:1,primary:true});
  p.layers=[voice,layer('broll','video',{asset:brollAsset.asset,start:14,duration:3,sourceIn:1}),
    layer('sfx','audio',{asset:insertAudio.asset,libraryId:audio.id,start:14,duration:audio.out,volume:.35}),
    layer('caption','caption',{start:3,duration:6,x:45,y:1060,width:630,height:120,align:'center',text:'Tìm đúng đoạn cần dựng.'})];
  p.workflow={brief:{audience:'Người mới',goal:'Tìm và dùng lại một take',target:'32 giây',style:'Talking head và B-roll'},
    beats:[{time:'0–14 s',purpose:'Nêu vấn đề',source:'Cảnh mở 1–15 s'},
      {time:'14–17 s',purpose:'Minh họa',source:'B-roll 1–4 s',cue:'Canon Shutter tại 14 s'}],notes:[]};
  const save=async()=>{p=await request(prefix,'PUT',p);};
  const review=async(stage,jobId,note,expected=200)=>{
    const result=await request(prefix+'/review','POST',{revision:p.revision,stage,jobId,note},expected);
    if(expected===200)p=result;
  };
  await save();
  await request(prefix,'PUT',{...p,revision:p.revision-1},409);
  await request(prefix+'/jobs','POST',{action:'draft',revision:p.revision},400);
  await review('plan');
  assert.ok(planApproved(p));
  assert.equal(trimAt(voice,10.012,30,'left').sourceIn,11);
  const draft=await waitJob(prefix,p,'draft');
  await review('cut',draft.id);
  assert.ok(cutApproved(p));
  p.workflow.notes.push({jobId:draft.id,time:'3.00',text:'Sửa dòng chữ mở đầu'});
  p.layers.at(-1).text='Tìm đúng đoạn cần dựng trước.';
  await save();
  assert.ok(cutApproved(await request(prefix)));
  p.layers[0].sourceIn+=1/30;
  await save();
  assert.ok(!cutApproved(p));
  await review('cut',draft.id,undefined,400);
  p.layers[0].sourceIn=1;
  await save();
  const delivery=await waitJob(prefix,p,'delivery');
  assert.ok((await request(prefix+'/jobs')).find(j=>j.id===delivery.id).current);
  p.workflow.notes.push({jobId:delivery.id,time:'14.00',text:'Mốc kỹ thuật để kiểm tra clip chèn'});
  await save();
  assert.ok((await request(prefix+'/jobs')).find(j=>j.id===delivery.id).current);
  const handoff=await waitJob(prefix,p,'handoff');
  const speech=await waitJob(prefix,p,'transcribe',{asset});
  const words=await request('/api/jobs/'+speech.id+'/transcript');
  assert.ok(words.words.length>0 && Number.isFinite(words.words[0].start));
  const cached=await waitJob(prefix,p,'transcribe',{asset});
  assert.equal(cached.transcript,speech.transcript);
  const project=path.join(app.root,p.id);
  const out=job=>path.join(project,job.file);
  assert.ok(fs.existsSync(out(draft)));
  assert.notEqual(out(draft),out(delivery));
  for(const [job,name] of [[draft,'pilot-draft.mp4'],[delivery,'pilot-candidate.mp4']]){
    fs.copyFileSync(out(job),path.join(evidence,name),fs.constants.COPYFILE_EXCL);
  }
  const pack=path.join(project,'exports',handoff.id);
  assert.ok(fs.readFileSync(path.join(pack,'captions.srt'),'utf8').includes('đoạn cần dựng trước'));
  const copy=path.join(evidence,'handoff');
  fs.cpSync(pack,copy,{recursive:true,force:false,errorOnExist:true});
  fs.writeFileSync(path.join(evidence,'transcript.json'),JSON.stringify(words,null,2));
  if(process.argv[3]){
    const {pathToFileURL}=await import('node:url');
    process.env.WORK_HUB_PROJECTS=path.join(sandbox,'baseline');
    const old=await import(pathToFileURL(path.join(process.argv[3],'server.mjs')).href);
    baseline=old.server();
    await new Promise(resolve=>baseline.listen(0,'127.0.0.1',resolve));
    base='http://127.0.0.1:'+baseline.address().port;
    const oldProject=await request('/api/projects','POST',{title:'Baseline'},201);
    const oldPrefix='/api/projects/'+oldProject.id;
    const before=performance.now();
    const imported=await request(oldPrefix+'/import','POST',{path:footage});
    timing.knownPathInsertApiMs=Math.round(performance.now()-before);
    const sources={};
    sources[asset]=imported.asset;
    sources[brollAsset.asset]=(await request(oldPrefix+'/import','POST',{path:broll})).asset;
    sources[insertAudio.asset]=(await request(oldPrefix+'/import','POST',{path:shutter})).asset;
    const model=await request(oldPrefix);
    model.output=p.output;
    model.layers=p.layers.map(l=>({...l,asset:sources[l.asset]||''}));
    const saved=await request(oldPrefix,'PUT',model);
    try {await waitJob(oldPrefix,saved,'render');}
    catch (error) {
      timing.baselineRenderFailure=error.message;
      console.log('Baseline render failed on the same fixture');
    }
  }
  fs.writeFileSync(path.join(evidence,'timings.json'),JSON.stringify(timing,null,2));
  console.log('PASS',JSON.stringify(timing));
}finally{
  server.close();
  baseline?.close();
}

