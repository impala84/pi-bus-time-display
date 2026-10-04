'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const read=name=>fs.readFileSync(path.join(__dirname,'static',name),'utf8');
function element(tag){return {tag,attributes:{},children:[],setAttribute(key,value){this.attributes[key]=value;},replaceChildren(...children){this.children=children;}};}
const helpers=vm.runInNewContext(read('discovery.js')+'\n({loadingNotice,responsiveLabel})',{document:{createElement:element}});
test('all pending music navigation uses one discreet accessible loading notice',()=>{
  const status=helpers.loadingNotice();assert.equal(status.textContent,'Loading…');assert.equal(status.className,'loading-notice');assert.equal(status.attributes.role,'status');assert.equal(status.attributes['aria-live'],'polite');
  assert.match(read('app.js'),/list\.append\(loadingNotice\(\)\)/);
  assert.doesNotMatch(read('discovery.js'),/Loading your (mix|Roon recommendations)/);
});
test('responsive labels replace rather than accumulate and retain full and compact names',()=>{
  const link=element('a');for(let i=0;i<3;i++)helpers.responsiveLabel(link,'Now Playing','Playing');
  assert.equal(link.children.length,2);assert.equal(link.children[0].className,'nav-label-full');assert.equal(link.children[0].textContent,'Now Playing');assert.equal(link.children[1].textContent,'Playing');
  assert.match(read('discovery.js'),/\['daily','DAILY MIXES','MIXES'\]/);assert.match(read('discovery.js'),/\['surprise','SURPRISE ME','SURPRISE ME'\]/);
});
test('mix tracks remain visible and portrait layout uses horizontal categories with normal-flow Back',()=>{
  assert.doesNotMatch(read('discovery.js'),/createElement\('details'\)|VIEW TRACKS/);
  const css=read('discovery.css');assert.match(css,/\.discovery-view>\.browser-back\{position:static/);
  assert.match(css,/#dashboard-clock\{display:none/);assert.match(css,/\.browser-sidebar\{grid-column:1\/-1;grid-row:1;flex-direction:row/);
});
