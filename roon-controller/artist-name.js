'use strict';

// Roon separates contributor credits with spaced slashes. Never split AC/DC
// or commas: those can be part of the actual artist's name.
function leadArtist(value) {
  return String(value || '').split(/\s+\/\s+|\s*;\s*|\s+(?:feat\.?|featuring)\s+/i)[0].trim();
}

function displayArtist(playing) {
  const lines = playing?.three_line || playing?.two_line || playing?.one_line || {};
  return leadArtist(playing?.album_artist || playing?.artist || lines.line2);
}

module.exports = {leadArtist, displayArtist};
