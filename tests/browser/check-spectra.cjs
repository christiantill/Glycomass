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
  assert.equal(await page.locator('[role=status]').textContent(),'Calculating…');
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
 assert.deepEqual(errors,[]);
 await browser.close();
 console.log('PASS: visible peak strokes and empty gaps, immediate status, disabled submit, compressed response, toggles, repeated calculation, mobile sizing');
})().catch(error=>{console.error(error);process.exit(1)});
