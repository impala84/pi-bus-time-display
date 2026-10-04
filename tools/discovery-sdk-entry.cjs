// Build only the protocol facade/history exporter, not 1,550 generated APIs.
// esbuild aliases pi-home-roon-research to the pinned upstream dist directory.
module.exports = {
  ...require('pi-home-roon-research/proto/client.js'),
  ...require('pi-home-roon-research/proto/writer.js'),
  ...require('pi-home-roon-research/proto/serializer.js'),
  ...require('pi-home-roon-research/history-export.js'),
};
