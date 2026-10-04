'use strict';
const test=require('node:test');const assert=require('node:assert/strict');const {dailyPicks}=require('./discovery-read');
const sdk=require('./vendor/roon-research/sdk.cjs');
function client(status){const calls=[];return {calls,profile:()=>Buffer.alloc(16),serviceOid:()=>2n,structArg:(_type,fields)=>{assert.deepEqual(fields.map(f=>f.propType),[20,2,2,2]);return Buffer.alloc(1);},remoting:{callMethod:async(_oid,method)=>{calls.push(method);return {status:calls.length===1?status:'Success',success:true};}}};}
test('current DailyPicks parameter struct is tried once and retained when available',async()=>{const c=client('Success');await dailyPicks(c,sdk,'2026-01-01T00:00:00Z');assert.equal(c.calls.length,1);assert.match(c.calls[0],/DailyPicksParameters/);});
test('only MissingMethod permits the single legacy fallback',async()=>{const c=client('MissingMethod');await dailyPicks(c,sdk,'2026-01-01T00:00:00Z');assert.equal(c.calls.length,2);assert.match(c.calls[1],/string, bool/);const denied=client('Denied');await dailyPicks(denied,sdk,'time');assert.equal(denied.calls.length,1);});
