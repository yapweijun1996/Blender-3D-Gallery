export async function load(url,context,nextLoad){
 const r=await nextLoad(url,context);if(!url.endsWith('/scripts/test-library-browser.mjs'))return r;
 let s=r.source.toString();
 s=s.replace("const page = await context.newPage();",`const page = await context.newPage();
 const qlog=(event,data)=>console.log('QA_DIAG',JSON.stringify({at:new Date().toISOString(),case:name,event,...data}));
 page.on('request',q=>qlog('request',{url:q.url(),resource:q.resourceType()}));
 page.on('requestfailed',q=>qlog('requestfailed',{url:q.url(),failure:q.failure()}));
 page.on('response',q=>qlog('response',{url:q.url(),status:q.status()}));
 page.on('framenavigated',f=>{if(f===page.mainFrame())qlog('navigation',{url:f.url()})});
 page.on('domcontentloaded',()=>qlog('domcontentloaded',{url:page.url()}));
 page.on('console',m=>{if(m.type()==='error')qlog('console-error',{text:m.text()})});
`);
 s=s.replace("for(const kind of ['game','solar']) {","for(const kind of ['game','solar']) { console.log('QA_KIND_BEGIN',kind);");
 s=s.replace("await page.reload({waitUntil:'domcontentloaded'});","console.log('QA_BEFORE_RELOAD',kind,page.url()); await page.reload({waitUntil:'domcontentloaded'}); console.log('QA_AFTER_RELOAD',kind,page.url());");
 s=s.replace("} catch (error) {","} catch (error) { console.log('QA_FAILURE_URL',page.url(),String(error));");
 return {...r,source:s};
}
