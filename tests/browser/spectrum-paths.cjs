const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const handlers = {};
const context = {
  document: {addEventListener(){}, body:{addEventListener(name, handler){handlers[name]=handler;}}},
  Path2D: class {
    constructor(){ this.segments=[]; }
    moveTo(x,y){ this.segments.push(['move',x,y]); }
    lineTo(x,y){ this.segments.push(['line',x,y]); }
  },
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.resolve(__dirname, '../../src/glycomass/web/static/js/app.js'), 'utf8'), context);

test('isotope peaks are independent vertical strokes from zero, without an envelope fill', () => {
  const plot = {
    data: [[800.3,801.3,802.3], [100,40,10]],
    valToPos(value, scale, canvasPixels){
      assert.equal(canvasPixels,true);
      return scale === 'x' ? value*2 : 300-value*2;
    },
  };
  const paths=context.isotopeStickPaths(plot,1,0,2);
  assert.deepEqual(paths.stroke.segments, [
    ['move',1600.6,300],['line',1600.6,100],
    ['move',1602.6,300],['line',1602.6,220],
    ['move',1604.6,300],['line',1604.6,280],
  ]);
  assert.equal(paths.fill,null);
});

test('only the requested visible peak range is drawn', () => {
  const paths=context.isotopeStickPaths({data:[[1,2,3],[100,50,5]],valToPos:v=>v},1,1,1);
  assert.deepEqual(paths.stroke.segments,[['move',2,0],['line',2,50]]);
});

test('HTMX cleanup tolerates text nodes', () => {
  assert.doesNotThrow(() => handlers['htmx:beforeCleanupElement']({detail:{elt:{nodeType:3}}}));
});


test('table exports retain every discrete peak with the displayed precision', () => {
  assert.equal(context.peakTableText([[800.367234,100],[801.37,0.001]], ','),
    'Peak,m/z,Relative intensity (%)\r\n1,800.3672,100.00\r\n2,801.3700,0.00\r\n');
});

test('profile labels use local maxima, not every sample', () => {
  assert.equal(JSON.stringify(context.profileMaxima({mz:[1,2,3,4,5],intensity:[0,100,0,50,0]})),
    JSON.stringify([[2,100],[4,50]]));
});
