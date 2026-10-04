# v1.1 Discover beta — 4 October 2026

Development branch: `discover-v1.1`. Production `main` and `v1.0.0` remain unchanged.
This branch contains the v1.1.0-beta.1 candidate, not completed stable v1.1.

## Starting point and isolation

Inspected [Arthur Soares' MIT-licensed research client](https://github.com/arthursoares/roon-api-reverse-engineering), pinned research revision `8b67208f640e760f3b18431140e17469a059e90c`. Its TypeScript build and 145 upstream tests passed locally. Generated method wrappers are not evidence of live compatibility.

The beta bundles only the client's protocol facade and history exporter in `roon-controller/vendor/roon-research/sdk.cjs`, with its MIT notice alongside it. The official controller never imports this bundle: a short-lived child worker reads discovery data, closes its socket and exits. The parent imposes a 128 MiB heap ceiling and 20-second deadline, serialises/coalesces reads, caches successful results for five minutes and failures for one minute, and clears personal state on unpairing. History uses upstream retain/release/dispose. Longer-running server-resource validation is still pending. No RoonMCP integration is involved.

Local official SOOD discovery located the user's actual Roon Server without SSH. A first private handshake using UUID text byte order was rejected; .NET GUID mixed-endian conversion succeeded. The root object graph and active profile were readable. Do not hard-code the user's server address, broker/profile IDs or listening history in the public repository.

## Actual-server findings

| Area | Live result | Metadata and remaining gap |
| --- | --- | --- |
| TIDAL Daily Mixes | Received ten playlist references; inspected first five | Names such as My Daily Discovery/My Mix, opaque playlist IDs, source and availability. Artwork has HTTPS TIDAL URLs. These are TIDAL mixes, not Roon mixes; signed artwork URLs must not be committed or logged by production. |
| Roon personalised mixes | Received six; normalised first five and one detail/track-list call | Inline performer descriptions, five artist touchstones per mix, avatar/photo artwork, opaque mix IDs. The first mix has 22 track groups; five sampled tracks have title, artist, album, source, internal IDs and artwork. Initial inspection incorrectly omitted nested descriptions and image URL fields; corrected decoding recovered them. |
| Daily Picks | Old generated call returns `MissingMethod`; current call repeatedly succeeds | Read the installed `Roon.Broker.Api.dll` metadata without launching or altering Roon. Current signature uses `(System.Sooid, DailyPicksParameters, callback)` with LocalTime, OverrideCache, RecentlyAddedOnly, NewReleasesOnly fields. Retrieved five personalised groups with 30 albums per group, seed album, reason (`recent`, `added`, `all_time`), category and generated date. Normalised five albums per group with artwork and artist. |
| New Releases for You | Received a collection advertising 180 entries; inspected first five | Album title, performer credit, Roon album/release IDs, source and artwork image IDs. Some contextual extras are not yet normalised. Numeric sources remain uninterpreted until their upstream enum mapping is verified. |
| Recent listening | Received a bounded history preview | Timestamp, track, album, artist, completion percentage and Roon track reference. The beta hydrates unique album artwork from the same fresh object graph; all 20 preview images loaded in the local browser. Missing art remains a neutral placeholder. |

These numbers reflect one server at one point in time, not a guarantee across Roon versions/accounts. Partial methods returning data do not establish reliable end-to-end discovery.

## Official API bridge

A real New Releases album was searched by exact title in a separate official browse session. The matching title/artist returned an official artwork key and browse item key. Opening it produced its track list and Play Album action without starting audio. Thus an exact title/artist search bridge is feasible for this sample; opaque internal IDs are **not** interchangeable with official `item_key`/`image_key` values.

Playback and queue actions were not executed. Atomic whole-mix playback and audio-confirmed play/queue remain unverified. Exact title/artist/category matching refuses ambiguous editions and leaves manual selection to the user. Never automatically play the first fuzzy search hit or reuse an expired session key.

Further live bridge checks resolved an exact Daily Pick album into its official track list and Play Album entry. An exact Recent track and an exact track from the Roon mix resolved through `action_list` previews into official Play Now, Add Next, Queue and Start Radio menus. None of those actions was selected. This establishes metadata-to-official-action resolution for album/track samples, not audio-confirmed playback or an atomic whole-mix queue. Full mixes require ordered per-track resolution, explicit user actions and ambiguity handling; never pretend a private mix ID is an official playlist key.

## Current gate

The four-source **read-only data proof passed**, including repeated current Daily Picks calls. A decoder omission and actual signature drift were diagnosed and corrected rather than removing those features. Worker isolation, caching/timeouts, local registered-artwork delivery, exact-match official action resolution and web/native Discover screens are implemented. Browser verification with live read-only data passed at 1280×720 and 390×844, including Recent artwork, mix previews and new-release artwork, with no detected JavaScript errors. Automated checks: 117 Python and 72 Node. These do not establish physical GTK acceptance or audio-confirmed playback.

Daily Mix artist portraits use black/purple duotone only in the Roon theme. Fresh Mint retains full-colour portraits; album covers remain full colour in both themes. Web rendering applies grayscale/multiply compositing, while native GTK uses a luminance colour matrix. Actual native rendering still requires touchscreen acceptance.

The five tabs are Recent | Browse | Daily Mixes | NEW | Surprise. NEW is the short navigation label; the page heading remains New Releases for You. At 1280×720 the browser tabs occupy about 600 pixels and retain 48-pixel-high targets. Native landscape uses the existing 18-pixel/54-pixel navigation styles. Mobile wraps into two rows with 44-pixel-high targets. Browse and Surprise retain their official API behaviour. Successful content caches are bounded to 24 sections/mixes, artwork registrations to 256. Recent/New show the first 20 selections; Daily shows five mixes and five groups of five picks; mix detail previews the first 20 groups. Whole-mix play/queue is deliberately not advertised.

The user explicitly requested continuing the full Discover integration. Do not narrow it to Recent/New Releases. Physical five-tab testing and Beta acceptance remain separate gates, not replaced by a local browser fixture. Do not publish stable v1.1 before those gates are satisfied.

## Reproduce the manual proof

Use a Roon Server you own on a trusted LAN. This unsupported protocol can affect server resources even when calls are read-only. Do not schedule the spike or run an automatic retry loop.

```sh
# In the Pi Home development checkout:
npm --prefix roon-controller ci --omit=dev --no-audit --no-fund
node tools/find-roon-core.cjs
node --test tools/discovery-wire.test.cjs

# Separate research checkout (not production /opt):
git clone https://github.com/arthursoares/roon-api-reverse-engineering.git roon-research
git -C roon-research checkout 8b67208f640e760f3b18431140e17469a059e90c
npm --prefix roon-research/roon-internal-api ci --ignore-scripts --no-audit --no-fund
npm --prefix roon-research/roon-internal-api run build
npm --prefix roon-research/roon-internal-api test -- --runInBand

# Substitute your own discovered values and absolute research dist path:
ROON_HOST='<your-server>' ROON_SERVER_BROKER_ID='<wire-order-32-hex>' \
ROON_RESEARCH_CLIENT='/absolute/path/roon-research/roon-internal-api/dist' \
node --max-old-space-size=256 tools/discovery-spike.cjs
```

Exit 3 means the calls completed but the requested data gate remains incomplete. Exit 2 is the watchdog limit; other nonzero exits indicate setup/connection failure. `uiGatePassed` and `playbackVerified` remain false. Output can contain personal listening metadata: inspect locally and do not commit it. No raw object graph, credentials, pairing state or captured server data is checked in.

The helper code is original Pi Home code under its existing MIT licence. The pinned upstream bundle retains Arthur Soares' MIT notice in `roon-controller/vendor/roon-research/LICENSE`. Rebuild it from the pinned research checkout's compiled `dist` using:

```sh
npm exec --yes --package=esbuild@0.25.5 -- esbuild tools/discovery-sdk-entry.cjs \
  --bundle --platform=node --target=node20 --minify \
  --alias:pi-home-roon-research=/absolute/path/roon-research/roon-internal-api/dist \
  --outfile=roon-controller/vendor/roon-research/sdk.cjs
```

No extra npm runtime dependency, Roon credentials, personal host address or captured history is included. The manual spike's 90-second watchdog is separate from the production worker's shorter deadline. Before stable promotion: test all five tabs, touch/scroll behaviour and artwork on the actual Pi; exercise explicit Play/Queue with the intended zone; validate optional-module navigation and repeated discovery use across reconnects/Roon updates.
