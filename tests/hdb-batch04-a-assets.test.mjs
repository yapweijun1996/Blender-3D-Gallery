import test from 'node:test';
for(const slug of ["hdb-bin-centre", "hdb-multi-purpose-hall", "hdb-neighbourhood-shopfront", "hdb-coffee-shop-frontage", "hdb-covered-linkway-column"]) test(slug+' geometry and budgets',async()=>{await import('../models/'+slug+'/validate.mjs');});
