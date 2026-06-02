"""Lambda authentication checks.

Every Lambda's first line of logic is `verify(event, context, expected_source)`.
Sources: `webhook:<provider>`, `cognito:presignup`, `cognito:postconfirmation`,
`eventbridge:<rule>`. Raises `Unauthorized` on mismatch.

See `.claude/rules/security.md` § "Lambda auth — explicit per type".
"""
