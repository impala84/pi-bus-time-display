# Pi Home working expectations

## Publishing completed changes

The user expects requested Pi Home changes to be delivered through the updater, not left as local edits.

- After implementing and proportionately verifying requested changes, commit the relevant changes, push to `origin/main`, and publish a GitHub release with the next appropriate semantic version and concise release notes.
- Update the application version, changelog, documented current release, and affected web asset cache versions as appropriate.
- Do not ask for publishing confirmation on every build. The user has explicitly authorised this routine workflow, including direct pushes to `main` and GitHub releases.
- Do not overwrite unrelated user changes, force-push, or publish known failing work. Report meaningful blockers or operations needing authority beyond this workflow.
- Confirm the release was published before claiming it is available through the updater. Publishing a release does not authorise remotely installing it or restarting the user's Pi.
- State verification accurately: local browser fixtures and automated tests do not prove native GTK behaviour on the actual touchscreen.
