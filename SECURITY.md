# Security

Initial supported line: 0.1.x, best effort. No external security audit has been performed.

The checker runs locally and has no network client. It never modifies input files and creates output files exclusively. HTML reports escape input text. Treat report IDs and field names as potentially sensitive; do not publish unreviewed reports.

This is not an untrusted-file sandbox: large files may exhaust memory or take excessive time. Run only on files you trust within your available resources. URL checks validate syntax, not destination safety or authenticity.

After publication, use the repository's GitHub private vulnerability reporting feature if enabled. The release checklist asks the maintainer to enable it. If unavailable, open a minimal issue asking for a private contact without posting an exploit or sensitive data. Never include real credentials or personal records.
