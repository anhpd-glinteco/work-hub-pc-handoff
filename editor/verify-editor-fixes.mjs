import assert from 'node:assert/strict';
import fs from 'node:fs';
import {parseCaptions} from './captions.mjs';
import {migrate,html,checkV2} from './model.mjs';
import {applyTemplate,canvasBox,overlapsVisibleText,templates} from './templates.mjs';

const short='\uFEFFWEBVTT\r\n\r\nNOTE ghi chú\r\n\r\ncue-1\r\n00:01.000 --> 00:03.000 line:90%\r\nPhụ đề tiếng Việt\r\nDòng thứ hai\r\n';
assert.deepEqual(parseCaptions(short,'vtt'),[{start:1,duration:2,text:'Phụ đề tiếng Việt\nDòng thứ hai'}]);
assert.deepEqual(parseCaptions('WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nMột dòng','vtt'),
  parseCaptions('1\r\n00:00:01,000 --> 00:00:03,000\r\nMột dòng','srt'));
assert.throws(()=>parseCaptions(short+'\r\n00:05.000 --> 00:04.000\r\nSai','vtt'),/Dòng 10/);
assert.throws(()=>parseCaptions('1\n00:59:59,000 --> 01:00:01,000\nQuá dài','srt'),/60 phút/);
assert.throws(()=>parseCaptions('WEBVTT\n\n','vtt'),/Không tìm thấy/);

for(const output of [{width:1920,height:1080,fps:30},{width:1080,height:1920,fps:30}]){
 const p={schemaVersion:2,output,style:{background:'#222222'},layers:[]};
 const signatures=new Set();
 for(const key of Object.keys(templates)){
  const draft=applyTemplate({...p,layers:[]},key,3);
  checkV2(draft);
  assert.ok(draft.layers.every(l=>l.start===3 && l.x+l.width<=output.width && l.y+l.height<=output.height));
  signatures.add(JSON.stringify(draft.layers.map(({id,...l})=>l)));
  assert.equal(overlapsVisibleText(draft.layers,draft.layers),true);
  assert.equal(overlapsVisibleText(draft.layers,draft.layers.map(l=>({...l,start:20}))),false);
 }
 assert.equal(signatures.size,4);
 assert.throws(()=>applyTemplate(p,'constructor'),/không hợp lệ/);
 const layer={...applyTemplate(p,'intro').layers[0],type:'video',asset:'assets/111.mp4',...canvasBox(output)};
 p.layers=[layer];
 const oldMarkup=html(p);
 layer.fit='contain';
 assert.equal(html(p),oldMarkup);
 layer.fit='cover';
 assert.match(html(p),/object-fit:cover/);
 layer.fit='stretch';
 assert.throws(()=>checkV2(p),/khớp khung/);
}

process.env.WORK_HUB_PROJECTS=fs.mkdtempSync('D:/Codex/work/editor-fixes-');
const {server}=await import('./server.mjs');
const app=server();
await new Promise(resolve=>app.listen(0,'127.0.0.1',resolve));
const base='http://127.0.0.1:'+app.address().port;
const post=(url,data)=>fetch(base+url,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(data)});
try{
 const output={width:1080,height:1920,fps:30};
 const response=await post('/api/projects',{title:'Mẫu thử',template:'product',output});
 assert.equal(response.status,201);
 const created=await response.json();
 const reopened=await (await fetch(base+'/api/projects/'+created.id)).json();
 assert.deepEqual(reopened.output,output);
 assert.deepEqual(reopened.layers.map(l=>l.name),['Nền thẻ','Tên sản phẩm','Điểm nổi bật','CTA']);
 assert.ok(reopened.layers.every(l=>l.start===0));
 assert.equal((await post('/api/projects',{template:'unknown'})).status,400);
 assert.equal((await post('/api/projects',{template:'intro',output:{width:0}})).status,400);
 const legacy=await (await post('/api/projects',{})).json();
 assert.equal(legacy.schemaVersion,1);
 assert.equal(migrate(legacy).layers.length,2);
 console.log('PASS · VTT/SRT, mốc lỗi, bốn mẫu, tương thích fit mặc định, tạo project v2 từ mẫu');
}finally{app.close();}

