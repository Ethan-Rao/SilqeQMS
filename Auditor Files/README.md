# Auditor Files

This folder is intentionally empty. It is the mount point the auditor portal reads from
(`AUDITOR_FILES_ROOT`, defaulting to this path).

## The 2026 external audit set has been archived

The audit is closed, so its 683 documents (~649 MB) were removed from the repository on
2026-08-10 and archived to:

```
C:\Users\Ethan\OneDrive\Desktop\Silq Auditor Portal Archive 2026\
```

That copy is backed up by OneDrive and retains the original folder structure. A permanent
record of exactly which documents the auditor was shown is committed at
`docs/AUDITOR_PORTAL_2026_FILE_MANIFEST.csv` (682 rows: folder, filename, size, last
modified). The portal's own access log is preserved in the `auditor_access_events` table.

None of the archived documents were unique to the portal — they were copies assembled for
the audit. The controlled originals remain in the eQMS document libraries and in the
top-level QMS folders (`QM Documents/`, `DCOs/`, `DHF/`, `Suppliers/`, and so on).

## Do not simply drop files here for the next audit

Portal documents used to be committed to git so they would be baked into the Docker image.
That put ~649 MB into every clone and slowed every build, which is why the files are now
git-ignored and Docker-ignored.

Reusing the portal requires reworking it to read documents from DigitalOcean Spaces, the way
the `admin_docs` libraries already do. Until that work lands, adding files here will not
serve them in production. See `docs/SYSTEM_OVERVIEW.md`.
