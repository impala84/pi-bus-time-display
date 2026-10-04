'use strict';
const test=require('node:test');const assert=require('node:assert/strict');const {matches,openDiscovery}=require('./discovery-bridge');
const track={kind:'track',title:'Song',artist:'Artist'};
test('only exact title, artist and category resolve; private IDs are never browse keys',()=>{
  assert.ok(matches(track,{title:'Song',subtitle:'Artist, Guest',result_type:'tracks'}));
  for(const candidate of [{title:'Song live',subtitle:'Artist',result_type:'tracks'},{title:'Song',subtitle:'Other',result_type:'tracks'},{title:'Song',subtitle:'Artist',result_type:'albums'},{title:'Song',subtitle:'Artist',result_type:'tracks',action:true}])assert.equal(matches(track,candidate),false);
});
test('a verified track preview unwraps to controls, without selecting a playback action',async()=>{
  const calls=[];const responses=[{items:[{title:'Song',subtitle:'Artist',result_type:'tracks',item_key:'official-track'}]},{items:[{title:'Song',hint:'action_list',item_key:'official-controls'}]},{items:[{title:'Play Now',action:true,item_key:'play'}]}];
  const browser={run:async(...args)=>{calls.push(args);return responses.shift();}};
  const result=await openDiscovery(browser,'isolated',track);
  assert.equal(result.items[0].title,'Play Now');assert.equal(calls.length,3);assert.deepEqual(calls[2],['isolated','open',{item_key:'official-controls'}]);assert.ok(!calls.some(call=>call[2].item_key==='play'));
});
test('ambiguous editions remain a manual choice and never auto-open or play',async()=>{
  let calls=0;const result=await openDiscovery({run:async()=>{calls++;return {items:[1,2].map(id=>({title:'Song',subtitle:'Artist',result_type:'tracks',item_key:String(id)}))};}},'s',track);
  assert.equal(calls,1);assert.equal(result.discovery_ambiguous,true);
});
test('expired selections fail before any official API call',async()=>{
  await assert.rejects(()=>openDiscovery({run:()=>{throw new Error('Must not call');}},'s',null),/no longer available/);
});
