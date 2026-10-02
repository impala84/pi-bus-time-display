# Changelog

## 0.10.8 — 2 October 2026

- Make an explicit manual Sleep cancel any earlier temporary tap-to-wake allowance.
- Hold the local sleep screen while the controller confirms the new mode, preventing a stale poll from switching the backlight on again.
- Retry a failed manual sleep request and log each transition for targeted diagnostics.

## 0.10.7 — 2 October 2026

- Return the web update control to normal page flow so it cannot obscure settings content.
- Place View display directly beneath the update control in the masthead.

## 0.10.6 — 2 October 2026

- Align the fixed web update control with the centred settings wrapper instead of the browser window edge.

## 0.10.5 — 2 October 2026

- Added an always-visible Check for updates control at the top-right of web settings.
- Unified both web update controls so they share disabled/progress state and cannot queue overlapping installations.
- Reloaded web settings automatically after the updated Pi Home services come back, making the newly installed version immediately visible.

## 0.10.4 — 2 October 2026

- Fixed manual Sleep immediately waking again when the low-level copy of the Sleep-button touch reached GTK after the panel had gone dark.
- Wake handling now compares the original kernel contact time with the moment sleep began, so only a genuinely new touch can wake the display.
- Applied the same fresh-contact guard when entering daytime inactivity sleep.

## 0.10.3 — 2 October 2026

- Added overflow-aware Now Playing text movement for long track and artist/album names: pause for ten seconds, scroll at a readable speed, pause at the end, then return.
- Kept short text static, recalculated movement after viewport changes and respected reduced-motion preferences without polling.
- Added opt-in OpenObserve logging with a bounded background queue, compact batching, retry backoff and a connection test in System settings.
- Logged operational state changes without sending listening history, Home Assistant entity IDs, artwork or credentials.

## 0.10.2 — 2 October 2026

- Added a safe compilation fallback for album enrichment: when Roon's track artists are not the album artist, Pi Home accepts MusicBrainz metadata only if the album search has exactly one exact-title match.
- Continued to reject ambiguous album titles rather than showing potentially incorrect information.

## 0.10.1 — 2 October 2026

- Collapsed the mobile Roon selector to the last word of each configured label so inputs fit as compact uppercase names such as TV, LP, ROON and QUEUE.
- Fixed album enrichment when Roon reports track collaborators instead of the album artist, while retaining exact album-and-artist validation.

## 0.10.0 — 2 October 2026

- Removed the redundant Back button from album details; tapping the large artwork now returns to Now Playing.
- Added an automatic, cached album-enrichment pass when the playing album changes, with no polling or touchscreen-thread work.
- Added confidently matched MusicBrainz release date, genre, album type, country, label, format, edition count and track count.
- Added a concise album write-up from a MusicBrainz-linked Wikipedia article, falling back to the artist's own Bandcamp album notes, with the source shown in the interface.
- Kept enrichment failure-safe: unmatched albums retain the Roon artwork, titles and track list without guessed metadata.

## 0.9.9 — 2 October 2026

- Fixed the main touchscreen Now Playing artwork at a genuinely smaller centred size instead of relying on a minimum-size rule that GTK could expand.
- Vertically centred the album/artist information while retaining the Back control at the bottom margin.
- Made the large detail artwork itself return to Now Playing when tapped, on both touchscreen and web.
- Shortened the native page heading from “Touchscreen settings” to “Settings”.
- Added deliberate spacing between every Settings checkbox and its label, including Roon Bridge and bus services.

## 0.9.8 — 2 October 2026

- Reduced the main touchscreen Now Playing artwork by 10% without expanding surrounding content.
- Doubled the album/artist Back target and anchored it at the bottom of the information column.
- Enlarged playback glyphs, elapsed/remaining times and the volume value without materially increasing their control circles.

## 0.9.7 — 2 October 2026

- Clarified the Roon naming fields as bottom navigation, top navigation play screen and top navigation queue names.
- Corrected the Home touchscreen header to “Pi Home” and aligned it vertically with Bus Times.
- Moved the album/artist Back control beneath the information column and made it smaller on both touchscreen and web.

## 0.9.6 — 2 October 2026

- Made the NAD/BluOS volume step controls truly circular by preventing GTK from stretching them with the volume row, and enlarged the volume readout with a lighter weight.
- Restricted Settings and Sleep header actions to their visible labels instead of broad invisible regions across the top row.
- Moved the Roon source indicator closer to the top edge and enlarged Home panel names and status text again.
- Simplified Touchscreen Settings into a flatter layout without the redundant tinted outer card, while restoring deliberate outer margins above and below it.
- Applied the configured Roon navigation name consistently across every web view and the web Settings screen.
- Stopped the example “Display settings applied” message from being reconstructed indefinitely from an old reboot marker.

## 0.9.5 — 2 October 2026

- Added separate editable names for the Roon Now Playing and Queue selectors, shared by the touchscreen and web player.
- Enlarged the external-input volume, circular step controls and mute target, while adding more space between source selectors.
- Rebalanced Touchscreen Settings spacing to keep its bottom actions fully visible within the 1280×720 display.
- Moved Bus Times content upward, softened secondary bus/footer text and enlarged Home tile labels for better distance legibility.

## 0.9.4 — 2 October 2026

- Fixed NAD/BlueOS source switching by preventing already encoded Capture URLs from being encoded a second time before the M33 `/Play` request.
- Removed the routine Debian package-index refresh from ordinary updates when every required system component is already installed, and made Node installation prefer its local cache.
- Added a quiet black appliance boot followed by a centred mint Pi Home startup mark, suppressing incorrectly oriented firmware and console graphics.
- Refined the 1280×720 touchscreen: stronger bus and Home borders, more separation between bus rows, a smaller stop heading, better header alignment and tighter Roon secondary navigation.
- Increased padding throughout Touchscreen Settings, separated its controls and condensed health information onto one line.

## 0.9.3 — 2 October 2026

- Fixed manual-sleep wake detection for the Goodix Touch Display 2 by accepting native multitouch contact-start events as well as legacy `BTN_TOUCH` events.
- Made native touchscreen logging unbuffered so the active low-level wake listener and each wake event are visible immediately in the service journal.
- Stopped unchanged Touch Display 2 configuration from generating another reboot requirement during every software update.
- Restored the web settings action bar's green keyline and made display/reboot messages temporary rather than permanently pinned.

## 0.9.2 — 2 October 2026

- Replaced ineffective generic Touch Display 2 input matrices with Raspberry Pi's supported Device Tree `swapxy`/axis-inversion calibration for non-desktop rotation.
- Split the 5-inch and 7-inch Touch Display 2 profiles so each uses its correct hardware overlay, while migrating the legacy combined profile to 7-inch.
- Added a persistent web action bar that follows the user across settings tabs, saves every dirty section together, shows centred status messages and keeps Reboot immediately available.
- Made display calibration explicitly report that a reboot is required and retain that prompt only for the current boot.
- Gave touchscreen Settings more vertical and horizontal breathing room.
- Matched the BluOS player refresh button to its field height, widened it and prevented its label from wrapping.

## 0.9.1 — 2 October 2026

- Corrected Touch Display 2 landscape input by using the inverse Wayland quarter-turn once, fixing the remaining 180° touch offset without changing picture orientation.
- Added a dedicated 1280×720 touchscreen layout with larger Settings controls, Roon selectors and touch targets while reserving room for both fixed navigation rows.
- Enlarged and vertically centred bus service numbers and arrival groups on the high-resolution landscape display.
- Added a configurable name for the Roon section in the touchscreen bottom navigation.

## 0.9.0 — 1 October 2026

- Reorganised web settings into Overview, Display, Automation, Services and System, with a compact responsive hierarchy on desktop and mobile.
- Added isolated section saves, persistent unsaved-change state, a fixed save bar and visible toast feedback so one page cannot overwrite unrelated settings.
- Moved common screen controls to Overview, display hardware to Display, behavioural rules to Automation and all maintenance actions into one System location.
- Added conditional Home Assistant and BluOS options, collapsible advanced groups and human-readable minute inputs for timeouts.
- Separated software-update progress from unrelated system actions and stopped routine web refreshes from collecting expensive diagnostics.
- Fixed Touch Display 2 landscape input calibration by applying the documented libinput rotation once, without a second compositor output mapping.

## 0.8.6 — 1 October 2026

- Added a confirmed **Reboot Pi** control to the web System settings.
- Routed reboot through Pi Home's existing fixed-action privileged broker without exposing arbitrary commands or broader sudo access.

## 0.8.5 — 1 October 2026

- Fixed Touch Display 2 touch coordinates after landscape rotation by applying the matching libinput calibration as well as binding touch to the DSI output.
- Corrected the opposing clockwise conventions used by Raspberry Pi settings and Wayland output transforms.
- Restored boot-console rotation so the new display is landscape from the beginning of startup.
- Scaled the native touchscreen typography, controls, artwork and Home icons for the denser 720p 7-inch panel.
- Stopped display changes and updates from causing multiple mid-install restarts; a display change now restarts only the touchscreen application.

## 0.8.4 — 1 October 2026

- Fixed Touch Display 2 rotation at the Cage/Wayland output layer, where the GTK application is actually rendered, instead of relying on kernel console rotation.
- Kept the original Touch Display on its established kernel rotation path to avoid reintroducing double rotation.
- Mapped Touch Display 2 input to the transformed DSI output so landscape picture and touch coordinates remain aligned.
- Added the lightweight `wlr-randr` output-management client to installation and update dependencies.

## 0.8.3 — 1 October 2026

- Replaced the lossy single-file privileged action handoff with an ordered atomic queue, preventing rapid sleep/wake, brightness or service requests from overwriting one another.
- Made the privileged broker continue draining later actions after an individual request fails and retained legacy request compatibility during updates.
- Kept the web Queue and album/artist detail views current while an external BluOS input is displayed.
- Reduced synchronous controller configuration reads to at most one per second without adding polling or a background process.
- Kept BluOS status and volume available when a player does not support Capture input browsing.
- Added a concise runtime architecture map and a prioritised V8 stabilization audit for subsequent reliability work.

## 0.8.2 — 1 October 2026

- Separated Roon views from BluOS inputs: Now Playing and Queue never change the amplifier source.
- Made Play explicitly reclaim Roon only when a physical input is active.
- Kept physical-input buttons responsible only for selecting their corresponding BluOS source.
- Added a dedicated full-screen GTK wake gesture plus a blocking Linux touchscreen event listener, removing reliance on GTK window events for manual wake.

## 0.8.1 — 1 October 2026

- Replaced the BluOS source dropdown with enabled inputs beside Now Playing and Queue.
- Added optional Pi Home display names for amplifier inputs.
- Fixed returning from a physical input to Roon by forcing a clean playback transition when BluOS left Roon reporting an already-playing state.
- Added a dedicated physical-input display with a large live volume number, large minus/plus controls and a compact mute button.
- Fixed manual touchscreen sleep becoming permanently unwakeable when its delayed wake-arm callback did not complete; fresh touches are now accepted using a deterministic gesture-tail guard.

## 0.8.0 — 1 October 2026

- Added lightweight NAD/BluOS amplifier discovery and configuration.
- Subscribed to the selected player using BluOS long polling, without a background polling loop.
- Added real amplifier input selection on both the touchscreen and web interface.
- Made the Roon screen pivot to a simplified external-input display with native amplifier volume control.
- Kept Roon metadata, queue and transport authoritative whenever Roon is the active source.

## 0.7.19 — 1 October 2026

- Fixed touchscreen sleep at the native backlight layer: sleep now writes brightness `0` while leaving panel power and the touch controller active, and wake restores the saved brightness.
- Added real updater progress stages covering version checks, download, dependencies, application files, services, readiness checks and touchscreen restart.
- Added a compact live update history to the web System page that reconnects through service restarts and highlights the current installation stage.
- Made touchscreen Settings refresh and display the current updater stage throughout installation instead of stopping at a generic queued or working message.

## 0.7.18 — 1 October 2026

- Prevented a manually selected Sleep override from surviving a Pi Home service restart or Raspberry Pi reboot and immediately blacking the touchscreen again.
- Startup now safely returns only an explicit Sleep override to Automatic; visible manual selections such as Roon, Bus Times and Home remain unchanged.

## 0.7.17 — 1 October 2026

- Added automatic recovery for a display pipeline left disabled by an earlier release, allowing this update to restore an already-dark panel without a reboot.
- The pipeline is enabled when waking but remains active during all future sleeps; only the native backlight is switched off.

## 0.7.16 — 1 October 2026

- Fixed the underlying touchscreen wake failure by keeping the Raspberry Pi display pipeline active while the panel sleeps.
- Sleep now switches off only the native Linux backlight, leaving GTK and the touch device able to receive the wake contact; no software dimming overlay or polling was added.

## 0.7.15 — 1 October 2026

- Made sleeping-screen wake detection accept both the start and end of a deliberate touch, covering panels that consume the first contact while restoring hardware power.
- Kept the guarded arming period after entering sleep, so accepting touch releases cannot revive the display from the gesture that put it to sleep.
- Added event-specific touchscreen wake logging to make any remaining hardware-path issue directly diagnosable.

## 0.7.14 — 1 October 2026

- Fixed the scheduled morning wake being immediately cancelled by the daytime inactivity timeout after a full night asleep.
- Reset the daytime inactivity clock when the overnight schedule ends, giving the newly awakened display its configured daytime interval from that point.

## 0.7.13 — 1 October 2026

- Restored reliable one-tap waking after manual or scheduled sleep by ignoring only the remainder of the initiating sleep gesture, then arming the next fresh touchscreen press.
- Unified manual-sleep waking with the global touchscreen activity path already used successfully by daytime inactivity sleep.

## 0.7.12 — 1 October 2026

- Made manual and scheduled sleep resistant to initiating releases and intermittent touchscreen ghost touches by requiring a deliberate double-tap to wake.
- Reset the wake gesture whenever the backend transitions into scheduled sleep and log only a confirmed wake, making unexpected transitions easier to distinguish from schedule-boundary resumes.

## 0.7.11 — 1 October 2026

- Kept the touchscreen update button in its in-progress state after a request is queued and surfaced the privileged updater's real status instead of immediately implying completion.
- Made the updater re-launch the newly fetched updater before installation so updater and system-component changes take effect during the same run.
- Prevented an unsupported status-light device from aborting an otherwise successful Pi Home application update.

## 0.7.10 — 1 October 2026

- Fixed a manual top-right sleep tap being immediately treated as a wake gesture by ignoring the release from the initiating tap.
- Changed the touchscreen artwork detail into a full-display takeover with near full-height artwork, information alongside it, and the normal interface heavily tinted behind it.
- Added a persistent System toggle for the Raspberry Pi ACT/PWR status lights. The restricted helper manages only recognised Pi LED devices, and the lights default to off after installation or update.
- Added a boot-time oneshot service that reapplies the saved Pi status-light preference without running a background process.

## 0.7.9 — 30 September 2026

- Fixed daytime inactivity sleep being immediately cancelled by incidental pointer, window or display events; only deliberate touch, click or key input now resets the timer and wakes the panel.
- Removed the outlined container around the fixed web dashboard navigation.

## 0.7.8 — 30 September 2026

- Added a configurable daytime touchscreen inactivity timeout that uses native panel power, wakes on touch, and leaves the overnight schedule authoritative.
- Added a lightweight album-and-artist panel to the touchscreen and web Roon views, opened by tapping the current artwork and populated asynchronously through Roon Browse with cached artwork and graceful metadata fallbacks.
- Renamed the main Music tab to Roon throughout the touchscreen, web dashboard, and display selector.

## 0.7.7 — 30 September 2026

- Made scheduled sleep take precedence over an open touchscreen Settings panel and stopped transient backend timeouts from incorrectly waking a sleeping display or forcing Bus Times.
- Replaced the malformed browser settings symbol with a clean stroked cog and added the Pi Home favicon to every display, sign-in, fallback and Roon page.
- Restored the browser navigation order to Music, Bus Times, Home on every page and gave the desktop navigation a taller inset panel with comfortable bottom spacing.
- Slightly enlarged the desktop bus-stop name and clock while preserving the compact portrait treatment.

## 0.7.6 — 30 September 2026

- Added the subscribed Roon Queue to the web Music view with instant Now Playing / Queue navigation, cached thumbnails and bounded touch scrolling.
- Retained up to ten recently departed queue entries in memory, shown dimmed above the current track on web and touchscreen, with best-effort replay through Roon's queue item IDs.
- Replaced the prominent web Settings pills with a fixed, understated cog and fixed the three-section bottom navigation consistently across Bus Times, Music and Home.
- Compacted the portrait Music view so artwork, transport and volume controls fit inside the available mobile viewport without page scrolling.

## 0.7.5 — 30 September 2026

- Increased the consistently rendered Home icon box from 48 to 72 pixels and restored balanced switch proportions, retaining sharp scalable SVG output and full-size touch targets.
- Routine application updates now restart the backend, Roon controller and native touchscreen services instead of rebooting the Pi; display profile and orientation changes continue to reboot when required.
- Rebuilt portrait web layouts: Music now isolates smaller artwork above non-overlapping controls, Bus Times uses a route-number headline above three arrivals, Settings uses a consistent rounded rectangle, and the bottom navigation has more breathing room.

## 0.7.4 — 30 September 2026

- Load Home SVG artwork through GTK's scalable icon path instead of the file-image path that ignored the requested pixel size and stretched wide symbols.
- Standardised Home icons on a centred 48-pixel optical box with consistent source stroke weight, and reduced the visual size of switch controls without shrinking their touch targets.
- Load current Roon state immediately in the web player and disable reverse-proxy buffering for subsequent live events, fixing a false “Waiting for Roon” screen behind Nginx without adding polling.
- Reflow the web Music view on portrait phones with album artwork above centred track details and playback controls.

## 0.7.3 — 30 September 2026

- Matched the web screen selector to the touchscreen hierarchy: Automatic/Sleep Now above Music/Bus Times/Home.
- Inset the Now Playing / Queue cyan indicator from the top edge to match the breathing room beneath the bottom navigation.

## 0.7.2 — 30 September 2026

- Hard-bounded the Queue scroller to the available central viewport so large queues cannot displace either fixed navigation bar.
- Disabled natural-size propagation from queue contents while retaining kinetic, scrollbar-free touch scrolling and tap-to-play rows.
- Moved the Music sub-navigation closer to the physical top edge, renamed the main Now Playing destination to Music and added breathing room inside the touchscreen brightness control.

## 0.7.1 — 30 September 2026

- Fixed the Queue viewport so it is height-bounded, touch-scrollable and does not hide the fixed bottom navigation.
- Prevented Queue's natural height from resizing the Now Playing, Bus Times and Home pages after switching views.
- Moved the Now Playing / Queue selector into the fixed top header so it no longer consumes album-art space.
- Arranged the web screen selector as Automatic/Sleep above Now Playing/Bus Times/Home, and forced admin assets to revalidate so the Home option appears immediately after updating.

## 0.7.0 — 30 September 2026

- Added a fixed, understated Now Playing / Queue selector within the Roon section while retaining the existing main navigation.
- Added a touch-scrollable, in-memory Roon queue with current-track treatment, compact metadata and tap-to-play-from-here navigation.
- Subscribe to the selected Roon zone's bounded queue as soon as it becomes available, rather than loading it on first view.
- Added a bounded thumbnail cache and background 96-pixel artwork loading so queue scrolling and GTK input remain responsive.
- Added a Roon setting to hide Queue and stop its subscription when the feature is disabled.
- Manual Bus Times, Now Playing, Home or Sleep choices now return to Automatic at the next schedule boundary; Home is also available in the web screen selector.

## 0.6.0 — 30 September 2026

- Removed full system diagnostics from the touchscreen startup path, delivered core Bus/Home/Roon state before artwork downloads, and pre-measured dynamic hidden views so their first tab switch does not pay deferred GTK layout costs.
- Added bounded startup/navigation timing traces to the system journal for evidence-based performance diagnosis without ongoing logging.
- Added a shared, persistent 10–100% hardware display-brightness control to touchscreen and web System settings; wake restores the chosen brightness rather than forcing full output.
- Added lightweight Netdata service detection and enable/start or disable/stop control using the existing fixed-action privileged broker, with no new daemon or background polling.

## 0.5.5 — 29 September 2026

- Replaced saved-brightness restoration with deterministic hardware behaviour: sleep only blanks panels that expose a power switch, while wake explicitly unblanks every detected panel and sets it to maximum hardware brightness.
- This also repairs low brightness left behind by earlier releases on the first wake after updating.

## 0.5.4 — 29 September 2026

- Made the touchscreen Roon Bridge switch persist by enabling or disabling its system service, rather than only starting or stopping the current process.
- Made touch wake force and confirm a physical backlight-on request, with a safe maximum-brightness fallback if the saved brightness is zero or invalid.
- Added stricter mobile Safari input containment and removed the non-editable Home touchscreen-layout summary.

## 0.5.3 — 29 September 2026

- Refined the mobile admin layout with a full-width final tab and Save button, constrained fields and aligned diagnostic values.
- Added web navigation between Bus Times, Now Playing and Home, with the Roon controller safely proxied through the main Pi Home address.
- Fixed View display so it preserves the public or reverse-proxied hostname instead of opening the appliance's loopback address.
- Added a compact browser Home dashboard and slightly increased spacing between touchscreen bus rows and Home controls.

## 0.5.2 — 29 September 2026

- Renamed the user-facing appliance from Pi Bus Time Display to **Pi Home**, while retaining existing repository, service, configuration and update paths for compatibility.
- Restored evenly centred arrival columns inside each bus row while retaining the subdued stop code without a separator dot.
- Corrected vertical Home controls so zero is at the bottom and 100% is at the top.
- Reworked fan, light and switch icons into a consistent rounded SVG family with grey hollow inactive and mint active states.
- Added left/right switch swipes in addition to tap-to-toggle.

## 0.5.1 — 29 September 2026

- Corrected the web sign-in focus order so username is selected before password.
- Replaced cramped touchscreen switches with clear checkbox controls and aligned the Daily Controls and Display rows.
- Left-aligned bus arrivals into consistent fixed columns and reduced the visual prominence of the stop code.
- Added purpose-drawn fan, light and switch SVGs to Home controls, with labels anchored beneath each device.
- Added vertical touch adjustment for light brightness and supported fan speeds, with debounced Home Assistant updates.

## 0.5.0 — 29 September 2026

- Redesigned touchscreen Settings with a balanced daily-controls and display layout plus fixed, equal-width actions at the bottom.
- Added touchscreen Roon Bridge and configured-bus visibility switches while retaining protected structural settings in web administration.
- Added an optional Home Assistant integration with protected URL, token and allow-listed entity configuration in a dedicated web Home section.
- Added a non-scrolling, state-aware 4×2 Home touchscreen panel for up to eight fans, lights, switches or input booleans.
- Kept Home Assistant credentials in the appliance secrets file and restricted touchscreen actions to explicitly configured, low-risk entities.

## 0.4.3 — 29 September 2026

- Added original and Touch Display 2 profile selection to the non-scrolling touchscreen Settings page.
- Added all four orientation choices with an explicit Apply & Reboot action.
- Added a compact touchscreen health summary for memory, load, temperature, Roon controller and Roon Bridge.
- Kept Wi-Fi, credentials and detailed configuration protected in web administration.

## 0.4.2 — 29 September 2026

- Corrected diagnostics that attributed the Roon controller process to the generic bus data service.
- Use systemd state as a fallback when a running component's process metrics are not visible.
- Explicitly enable and start the Roon controller during every update before readiness checks.
- Stop rebuilding unchanged GTK bus rows and re-selecting the visible page every two seconds.
- Make the Roon controller an explicit boot prerequisite of the native touchscreen service.
- Show the active Wi-Fi profile's real SSID instead of Netplan's generated connection-profile name.
- Move consistent dropdown chevrons in from the field edge and reserve appropriate text padding.

## 0.4.1 — 29 September 2026

- Removed expensive System and Wi-Fi diagnostics from the touchscreen's two-second display loop.
- Refresh configuration once per minute and System status only while touchscreen Settings is open.
- Replaced repeated Wi-Fi network listings with a lightweight active-connection query.
- Added swap use, SoC temperature and Raspberry Pi throttling state to diagnostics.

## 0.4.0 — 29 September 2026

- Added Automatic-mode Roon playback takeover with a configurable stopped-playing return delay.
- Added a configurable temporary wake timeout outside regular waking hours.
- Added adaptive two-, three- and four-service bus layouts without display scrolling.
- Added read-only live memory, load, uptime and per-component process diagnostics to System settings.
- Added selectable original Touch Display and Touch Display 2 resolution profiles with all four orientations.
- Added higher-resolution GTK scaling for Touch Display 2 while preserving the known-good original-display path.

## 0.3.0-rc.13 — 29 September 2026

- Removed the duplicate Wayland output transform that flipped the final display after the kernel had already rotated it.
- Made the kernel the sole picture-orientation authority and kept touchscreen calibration as a separate, matching libinput matrix.
- Hid the pointer directly in the native GTK display instead of disabling mouse-class input devices.

## 0.3.0-rc.12 — 29 September 2026

- Kept the last valid album cover through brief incomplete Roon metadata updates between tracks.
- Clear stale artwork only after five consecutive polls genuinely contain no artwork.

## 0.3.0-rc.11 — 29 September 2026

- URL-encoded Roon image keys so artwork containing reserved URL characters loads reliably.
- Reset the native artwork cache when playback or artwork disappears, allowing the same cover to load again when playback resumes.

## 0.3.0-rc.10 — 29 September 2026

- Made updates automatically reapply the saved display and touchscreen orientation before rebooting.

## 0.3.0-rc.9 — 29 September 2026

- Rotated touchscreen coordinates alongside the 180° display using libinput's calibration matrix.
- Suppressed non-touch pointer devices in appliance mode so Cage removes the mouse cursor.
- Strengthened physical display sleep with repeated backlight requests and the Raspberry Pi display-power fallback.

## 0.3.0-rc.8 — 29 September 2026

- Extended the display-orientation setting to the Raspberry Pi kernel console so the boot splash and GTK kiosk share the same orientation.
- Preserve the original kernel command line as `cmdline.txt.pi-bus-backup` before changing it.

## 0.3.0-rc.7 — 29 September 2026

- Added persistent appliance-mode display rotation with a simple 180° switch under System → Display.
- Added a command-line rotation recovery option and made 180° the initial appliance-mode orientation for this touchscreen mounting.

## 0.3.0-rc.6 — 29 September 2026

- Made software updates reboot automatically after successful service verification.
- Made sleep physically power down the official touchscreen backlight, while retaining touch-to-wake and the optional clock mode.
- Added a reversible Cage-based appliance mode that boots Pi Bus without loading the Raspberry Pi desktop.
- Replaced bottom navigation panels with understated active-view underlines.
- Reduced and re-centred album artwork and improved spacing around the transport controls.

## 0.3.0-rc.5 — 29 September 2026

- Distinguished the Now Playing controller from the Roon Bridge audio endpoint in web administration.
- Added clear Roon authorisation guidance and separate unavailable, unauthorised and idle states on the touchscreen.
- Refined the Now Playing split layout, artwork spacing, circular transport controls and bottom navigation emphasis.
- Made the native progress timeline touch-seekable, with debouncing and automatic disabling for non-seekable material.
- Added a Pi Bus favicon to web administration.

## 0.3.0-rc.4 — 29 September 2026

- Replaced raw command exceptions on touchscreen system actions with concise, useful failure messages while retaining full output in the service log.

## 0.3.0-rc.3 — 29 September 2026

- Made appliance updates preserve local checkout differences automatically instead of failing when an installed file has changed.
- Made installed appliances follow the supported `main` branch after the native GTK build became the primary release.

## 0.3.0-rc.2 — 29 September 2026

- Matched the native display typography to the Inter-based web administration and installed Inter automatically.
- Replaced visible main-screen utility buttons with large invisible title and clock touch targets.
- Removed page-transition animation and softened borders, status text and navigation chrome.
- Aligned and enlarged bus service and arrival figures on a shared baseline.
- Restored circular symbolic Roon transport controls and improved connected-but-idle wording.
- Added an optional completely black sleep screen while retaining tap-anywhere wake.

## 0.3.0-rc.1 — 29 September 2026

- Replaced the Chromium kiosk with a lightweight native GTK4 touchscreen.
- Added persistent Bus Times and Now Playing navigation, corner Settings and Sleep actions, and tap-anywhere wake.
- Added a restricted touchscreen settings screen with safe, one-tap software updates.
- Restored native Roon artwork, progress, playback and volume controls.
- Reorganised web administration into Schedule, Bus Stop, Roon and System sections.
- Added authenticated Roon Bridge controls, hostname, Wi-Fi and software-update actions.
- Added configurable web username/password management and optional authentication.

## 0.2.1 — 28 September 2026

- Prevented Chromium from launching before the main display service responds.
- Changed Chromium's initial background to black so startup cannot flash a white page.
- Made the updater wait for and verify both HTTP services, printing their logs on failure.

## 0.2.0 — 28 September 2026

- Replaced the bus summary panel with two much larger service rows.
- Added a proper password-manager-compatible admin login page.
- Added a persistent display shell for seamless Bus, Roon and Sleep switching.
- Added a dark, automatically recovering screen when the Roon controller is unavailable.
- Made the Roon service create its own working directory and report startup failures during updates.
- Changed Roon dependencies to immutable public HTTPS downloads.
- Added optional sleep while Roon is idle, waking automatically for playback.
- Refined Roon typography, transport icons and control shapes.

## 0.1.0 — 28 September 2026

- Initial Raspberry Pi bus display, web settings, kiosk service and Roon integration.
