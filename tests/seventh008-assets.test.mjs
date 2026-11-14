import test from 'node:test';import fs from 'node:fs';import {execFileSync} from 'node:child_process';
const slugs=JSON.parse(fs.readFileSync(new URL('../seventh008-slugs.json',import.meta.url)));
for(const s of slugs)test('seventh distinct asset '+s,()=>{execFileSync(process.execPath,['models/'+s+'/validate.mjs'],{stdio:'pipe'});execFileSync(process.execPath,['models/'+s+'/verify_source_edit.mjs'],{stdio:'pipe'});});
