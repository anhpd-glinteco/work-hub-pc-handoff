import {spawnSync} from 'node:child_process';
for(const file of ['verify-v2.mjs','integration-v2.mjs']){const r=spawnSync(process.execPath,[new URL(file,import.meta.url).pathname.replace(/^\/(\w:)/,'$1')],{stdio:'inherit'});if(r.status!==0)process.exit(r.status||1);}
