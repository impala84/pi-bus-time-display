'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {playMix}=require('./discovery-mix'),{DiscoveryManager}=require('./discovery-state');
const sdk=require('./vendor/roon-research/sdk.cjs');
function fixture({zone=true,mix=true,count=22,limited=false}={}) {
  const calls=[],params=[];let decoded=0;
  const objects=new Map([[1n,{oid:1n,typeName:'Test.Zone',fields:{ZoneId:Buffer.alloc(18,zone?1:2)}}],[2n,{oid:2n,typeName:'Test.Mix',fields:{MixId:Buffer.from(mix?'aabb':'ccdd','hex')}}]]);
  const client={graph:{objects,getObject:id=>objects.get(id),decodeReturnValue:()=>decoded++?{ItemCount:count,DidLimitItemCount:limited}:{$ref:2n}},profile:()=>Buffer.alloc(16),serviceOid:()=>3n,structArg:(_type,fields)=>{params.push(fields);return Buffer.alloc(0);},remoting:{callMethod:async(_oid,method)=>{calls.push(method);return {success:true,payload:Buffer.alloc(0)};}}};
  return {client,calls,params};
}
const request={id:'aabb',zoneId:'01'.repeat(18),action:'play'};
test('whole mix uses one PlayMix call, exact selected zone and verified mix, with Now/Queue priorities',async()=>{
  for(const action of ['play','queue']){const f=fixture();const result=await playMix(f.client,sdk,{...request,action});assert.equal(result.count,22);assert.equal(f.calls.length,2);assert.match(f.calls[1],/Transport::PlayMix\(/);assert.deepEqual(f.params[0][0].value,sdk.buildArgs([sdk.Arg.enum_(action==='play'?0:4)]));}
});
test('wrong zone or mix refuses playback and limited/empty feedback is not claimed complete',async()=>{
  for(const options of [{zone:false},{mix:false}]){const f=fixture(options);await assert.rejects(playMix(f.client,sdk,request));assert.ok(!f.calls.some(call=>call.includes('Transport::')));}
  for(const options of [{count:0},{limited:true}])await assert.rejects(playMix(fixture(options).client,sdk,request));
});
test('mix actions reject invalid input before calls',async()=>{
  for(const change of [{action:'shuffle'},{zoneId:'unknown'},{id:'a'}]){const f=fixture();await assert.rejects(playMix(f.client,sdk,{...request,...change}));assert.equal(f.calls.length,0);}
});
test('mix requests are explicit, deduplicated, exclude background reads and never retry uncertain results',async()=>{
  const manager=new DiscoveryManager();manager.setTarget({coreId:'core'});let runs=0,finish;
  manager.run=()=>{runs++;return new Promise(resolve=>finish=resolve);};
  const nonce='12345678-1234-1234';
  const first=manager.mixAction(request.id,request.zoneId,'play',nonce);
  const same=manager.mixAction(request.id,request.zoneId,'play',nonce);
  manager.state('recent');assert.equal(manager.pending.size,0);
  await assert.rejects(manager.mixAction(request.id,request.zoneId,'queue','12345678-5678-1234'));
  finish({accepted:true,count:22,action:'play'});assert.deepEqual(await first,await same);assert.equal(runs,1);
  let failedRuns=0;manager.run=async()=>{failedRuns++;return {status:'unavailable'};};await assert.rejects(manager.mixAction(request.id,request.zoneId,'queue',nonce));
  await assert.rejects(manager.mixAction(request.id,request.zoneId,'queue',nonce));assert.equal(failedRuns,1);
});
