import test from 'node:test';
for (const slug of ['hdb-staircase','hdb-lift-door','hdb-lift-interior','hdb-corridor-window']) {
 test(slug+' GLB geometry, dimensions, parts and budgets',async()=>{ await import('../models/'+slug+'/validate.mjs'); });
}
