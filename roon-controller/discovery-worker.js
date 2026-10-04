'use strict';
// This process has a memory ceiling/deadline imposed by its parent. It only
// reads discovery data, closes its socket and exits; no recurring connection.
const sdk = require('./vendor/roon-research/sdk.cjs');
const {readDiscovery} = require('./discovery-read');
process.once('message', async ({host, brokerId, section, id}) => {
  const client = new sdk.RoonClient({host, serverBrokerId: Buffer.from(brokerId, 'hex')});
  try {
    await client.connect();
    const data = await readDiscovery(client, sdk, section, id);
    process.send({ok: true, data}, () => {client.close(); process.exit(0);});
  } catch {
    client.close();
    // Do not leak signed artwork URLs, profile IDs or raw graph/error dumps.
    process.send({ok: false, error: 'Roon discovery is unavailable. Your normal Roon controls are still available.'}, () => process.exit(1));
  }
});
