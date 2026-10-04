'use strict';
const {field,resolve}=require('./discovery-model');
// One explicit operation, no track-by-track queue mutation and no fuzzy zone match.
async function prepareMix(client,sdk,{id,zoneId,action}) {
  if(!/^[a-f0-9]{2,160}$/i.test(id||'')||id.length%2||!/^[a-f0-9]{36}$/i.test(zoneId||'')||!['play','queue'].includes(action))throw Error('Invalid mix action');
  const zones=[...client.graph.objects.values()].filter(object=>/\.Zone$/.test(object.typeName)&&Buffer.isBuffer(field(object,'ZoneId'))&&field(object,'ZoneId').toString('hex')===zoneId.toLowerCase());
  if(zones.length!==1)throw Error('The selected Roon zone could not be matched safely');
  const {Arg,buildArgs}=sdk, ns='Sooloos.Broker.Api';
  const mixResult=await client.remoting.callMethod(client.serviceOid('Library'),`${ns}.Library::GetMix(System.Sooid, Base.ResultCallback<${ns}.Mix>)`,buildArgs([Arg.sooid(Buffer.from(id,'hex'))]));
  if(!mixResult.success)throw Error('The mix is unavailable');
  const reference=client.graph.decodeReturnValue(Uint8Array.from(mixResult.payload));
  if(reference?.$ref&&!resolve(client.graph,reference))await new Promise(resolve=>setTimeout(resolve,500));
  const mix=resolve(client.graph,reference);
  if(!reference?.$ref||!mix||!Buffer.isBuffer(field(mix,'MixId'))||field(mix,'MixId').toString('hex')!==id.toLowerCase())throw Error('The mix identity could not be verified');
  return {zone:zones[0],reference};
}
async function playMix(client,sdk,request) {
  const {zone,reference}=await prepareMix(client,sdk,request);
  const {action}=request,{Arg,buildArgs}=sdk,ns='Sooloos.Broker.Api';
  const type=`${ns}.PlayParameters`;
  // Current installed API enum: Now=0, Queue=4. Never substitute Next/Interrupt.
  const parameters=client.structArg(type,[{name:`${ns}.PlayPriority ${type}::Priority`,propType:9,value:buildArgs([Arg.enum_(action==='play'?0:4)])},{name:`bool ${type}::Shuffle`,propType:2,value:buildArgs([Arg.bool(false)])}]);
  const result=await client.remoting.callMethod(client.serviceOid('Transport'),`${ns}.Transport::PlayMix(${ns}.Zone, System.Sooid, ${type}, ${ns}.Mix, int, Base.ResultCallback<${ns}.PlayFeedback>)`,Buffer.concat([buildArgs([Arg.ref(zone.oid),Arg.sooid(client.profile())]),parameters,buildArgs([Arg.ref(BigInt(reference.$ref)),Arg.int(0)])]));
  if(!result.success)throw Error('Roon did not confirm the mix request; check its queue before retrying');
  const feedback=resolve(client.graph,client.graph.decodeReturnValue(Uint8Array.from(result.payload)));
  const count=Number(field(feedback,'ItemCount'));
  if(!Number.isSafeInteger(count)||count<1||field(feedback,'DidLimitItemCount'))throw Error('Roon did not confirm the complete mix; check its queue before retrying');
  return {accepted:true,count,action};
}
module.exports={playMix,prepareMix};
