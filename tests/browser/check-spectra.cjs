// Run with PLAYWRIGHT_MODULE and CHROMIUM_PATH when Playwright is installed externally.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,
   headless:true,args:process.env.HOST_RESOLVER_RULES ? ['--host-resolver-rules='+process.env.HOST_RESOLVER_RULES] : []});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 await page.route('https://fonts.googleapis.com/**',route=>route.abort());
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base=process.env.BASE_URL || 'http://127.0.0.1:8765';
 for(const kind of ['glycan','peptide','protein']){
  await page.goto(base+'/'+kind);
  // Keep the response pending so progress and duplicate-submit protection are observable.
  await page.route('**/'+kind,async route=>{
   if(route.request().method()==='POST') await new Promise(resolve=>setTimeout(resolve,500));
   await route.continue();
  });
  const responsePromise=page.waitForResponse(r=>r.request().method()==='POST');
  const started=Date.now();
  await page.locator('button[type=submit]').click();
  await page.waitForFunction(()=>document.querySelector('.calc-form').getAttribute('aria-busy')==='true');
  assert.equal(await page.locator('button[type=submit]').isDisabled(),true);
  assert.equal(await page.locator('.calculation-status').textContent(),'Calculating…');
  const response=await responsePromise;
  await page.waitForFunction(()=>document.querySelector('[data-drawn="1"]') && document.querySelector('.calc-form').getAttribute('aria-busy')==='false');
  const bytes=Number(response.headers()['content-length']);
  assert.equal(response.headers()['content-encoding'],'gzip');
  assert(bytes<50000,`response too large: ${bytes}`);
  assert.equal(await page.locator('button[type=submit]').isDisabled(),false);
  assert.equal(await page.getByRole('button',{name:'Profile',exact:true}).getAttribute('aria-pressed'),'true');
  assert(await page.evaluate(()=>{
    const {chart,profile}=spectrumCharts.get(document.querySelector('[data-spectrum]'));
    return chart.series[1].paths!==isotopeStickPaths && JSON.stringify(chart.data)===JSON.stringify([profile.mz,profile.intensity]);
  }));
  const boxes=await page.evaluate(()=>spectrumCharts.get(document.querySelector('[data-spectrum]')).state.labelBoxes);
  assert(boxes.length>0);
  for(let i=0;i<boxes.length;i++) for(let j=i+1;j<boxes.length;j++) {
    const a=boxes[i],b=boxes[j];
    assert(!(a.x<b.x+b.width && a.x+a.width>b.x && a.y<b.y+b.height && a.y+a.height>b.y));
  }
  await page.locator('.result-panel').screenshot({path:'/tmp/glycomass-labelled-'+kind+'.png'});
  await page.evaluate(()=>{
    const {chart,peaks}=spectrumCharts.get(document.querySelector('[data-spectrum]'));
    chart.setScale('x',{min:peaks[0][0]-.1,max:peaks[1][0]+.1});
  });
  assert(await page.evaluate(()=>{
    const {chart,state}=spectrumCharts.get(document.querySelector('[data-spectrum]'));
    return state.labelBoxes.every(b=>b.mz>=chart.scales.x.min && b.mz<=chart.scales.x.max);
  }));
  await page.getByRole('button',{name:'Reset zoom',exact:true}).click();
  await page.getByRole('button',{name:'Show labels',exact:true}).click();
  assert.equal(await page.evaluate(()=>spectrumCharts.get(document.querySelector('[data-spectrum]')).state.labelBoxes.length),0);
  await page.getByRole('button',{name:'Show labels',exact:true}).click();
  await page.locator('.peak-data summary').click();
  const peakCount=await page.evaluate(()=>spectrumCharts.get(document.querySelector('[data-spectrum]')).peaks.length);
  assert.equal(await page.locator('.peak-table tbody tr').count(),peakCount);
  assert(await page.locator('.peak-table tbody tr[hidden]').count()>0);
  await page.getByRole('button',{name:'Show all peaks',exact:true}).click();
  assert.equal(await page.locator('.peak-table tbody tr[hidden]').count(),0);
  if(kind==='glycan') {
    await page.context().grantPermissions(['clipboard-read','clipboard-write']);
    await page.getByRole('button',{name:'Copy table',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('.peak-export-status').textContent.includes('Copied'));
    const copied=await page.evaluate(()=>navigator.clipboard.readText());
    assert.equal(copied.trim().split('\n').length,peakCount+1);
    const downloadPromise=page.waitForEvent('download');
    await page.getByRole('button',{name:'Download CSV',exact:true}).click();
    const download=await downloadPromise;
    const fs=require('node:fs');
    const csv=fs.readFileSync(await download.path(),'utf8');
    assert.equal(csv,copied.replaceAll('\t',','));
  }
  await page.locator('.peak-data summary').click();
  await page.getByRole('button',{name:'Peaks',exact:true}).click();
  const state=await page.evaluate(()=>{
    const {chart,peaks}=spectrumCharts.get(document.querySelector('[data-spectrum]'));
    const canvas=document.querySelector('[data-spectrum] canvas');
    const ctx=canvas.getContext('2d');
    const base=chart.valToPos(0,'y',true);
    const top=chart.valToPos(100,'y',true);
    function goldAt(mz){
      const x=Math.round(chart.valToPos(mz,'x',true));
      const data=ctx.getImageData(x-1,Math.ceil(top),3,Math.max(1,Math.floor(base-top)-3)).data;
      let count=0;
      for(let i=0;i<data.length;i+=4) if(data[i]>180 && data[i+1]>130 && data[i+2]<80 && data[i+3]>100) count++;
      return count;
    }
    return {stick:chart.series[1].paths===isotopeStickPaths,min:chart.scales.y.min,
      peakPixels:goldAt(peaks[0][0]),gapPixels:goldAt((peaks[0][0]+peaks[1][0])/2)};
  });
  assert(state.stick && state.min===0 && state.peakPixels>10 && state.gapPixels===0,JSON.stringify(state));
  await page.locator('.result-panel').screenshot({path:'/tmp/glycomass-verified-'+kind+'.png'});
  await page.getByRole('button',{name:'Profile',exact:true}).click();
  assert(await page.evaluate(()=>spectrumCharts.get(document.querySelector('[data-spectrum]')).chart.series[1].paths!==isotopeStickPaths));
  await page.getByRole('button',{name:'Peaks',exact:true}).click();
  const old=await page.locator('[data-spectrum]').elementHandle();
  await page.locator('button[type=submit]').click();
  await page.waitForFunction(el=>!el.isConnected,old);
  await page.waitForFunction(()=>document.querySelector('.calc-form').getAttribute('aria-busy')==='false');
  console.log(kind,JSON.stringify({elapsedMs:Date.now()-started,compressedBytes:bytes,...state}));
 }
 await page.setViewportSize({width:390,height:844});
 await page.waitForTimeout(100);
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.locator('.peak-data summary').click();
 await page.locator('.result-panel').screenshot({path:'/tmp/glycomass-table-mobile.png'});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 assert.deepEqual(errors,[]);
 await browser.close();
 console.log('PASS: peak labels and zoom, table/copy/CSV, peak strokes, progress, compressed response, toggles, repeated calculation, mobile sizing');
})().catch(error=>{console.error(error);process.exit(1)});
