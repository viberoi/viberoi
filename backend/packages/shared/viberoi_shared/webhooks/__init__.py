"""Webhook HMAC verification per provider.

`verify(provider, headers, raw_body)` — raises `Unauthorized` on mismatch.
Always pass RAW bytes (HMAC is byte-exact); never the parsed JSON.

Providers: github, gitlab, bitbucket, azure_devops, jira, linear.
Each provider has its own signing scheme and header; the dispatcher
selects the right verifier.
"""
