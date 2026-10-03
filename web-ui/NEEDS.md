# web-ui/NEEDS.md — Cross-Agent Component & Dependency Needs

If a page agent needs a shared primitive, data field, or token modification, append a line below using the format:
`<page> | <component or field> | why it was needed`

---

tunnels | CandidateSet in src/api/types.ts | In golden.mock.json and tui/models.py, CandidateSet has 'surviving' (not 'survivors'), 'universe_size: number' (not 'universe: string[]'), and 'field' is optional. Types should allow both variants.
claims | Generic DetailDrawer (or ClaimDetailDrawer) | Shared DetailDrawer only accepts FindingItem; built page-level composite ClaimDetailDrawer using Sheet and tokens for claim inspection.
