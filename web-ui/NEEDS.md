# web-ui/NEEDS.md — Cross-Agent Component & Dependency Needs

If a page agent needs a shared primitive, data field, or token modification, append a line below using the format:
`<page> | <component or field> | why it was needed`

---

claims | Generic DetailDrawer (or ClaimDetailDrawer) | Shared DetailDrawer only accepts FindingItem; built page-level composite ClaimDetailDrawer using Sheet and tokens for claim inspection.
