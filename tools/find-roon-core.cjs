'use strict';
const {brokerWireId} = require('./discovery-wire.cjs');
const sood = require('../roon-controller/node_modules/node-roon-api/sood.js')({log(){}});
const seen = new Set();
sood.on('message', message => {
  if (message.props.service_id !== '00720724-5143-4a9b-abac-0e50cba674bb') return;
  const uuid = message.props.unique_id;
  if (seen.has(uuid)) return;
  try {
    const brokerId = brokerWireId(uuid);
    seen.add(uuid);
    console.log(JSON.stringify({host: message.from.ip, name: message.props.name, brokerWireId: brokerId}));
  } catch { /* Ignore malformed announcements. Never connect automatically. */ }
});
sood.start(() => sood.query({query_service_id: '00720724-5143-4a9b-abac-0e50cba674bb'}));
setTimeout(() => {sood.stop(); process.exit(seen.size ? 0 : 2);}, 10000);
