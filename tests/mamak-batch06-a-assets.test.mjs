import test from 'node:test';
for(const slug of ["mamak-teh-tarik-jug", "mamak-curry-pot", "mamak-stainless-steel-plate", "mamak-wall-menu-board", "satay-skewer-display"]) test(slug+' geometry and budgets',async()=>{await import('../models/'+slug+'/validate.mjs');});
