# Answer formatting implementation plan

Goal: Render assistant answers with Markdown, highlighted C/C++ and LC-3 code,
and inline/display equations, preserving course selection and citations.

Use markdown-it with raw HTML disabled, KaTeX through markdown-it-texmath for
both dollar and bracket delimiters, and a restricted highlight.js language set.
Sanitize rendered HTML with DOMPurify. Keep questions and source excerpts as
literal text. Bundle all browser code, equation CSS and fonts locally; no CDN
script dependency. Preserve the existing Sites project and public audience.

- [x] Add renderer tests covering lists, paragraphs, code escaping/highlighting,
      all supported math delimiters, invalid math, unsafe HTML/URLs and code/math isolation.
- [x] Implement the renderer and connect only final assistant replies to it.
      Use real DOM integration tests to cover course switching, pending replies,
      formatted output, and literal user/source text.
- [x] Bundle browser dependencies and math fonts into same-origin static assets
      served by both development and production Worker paths. Update answer styles
      for typography, tables, inline code, code blocks and equations.
- [ ] Verify Node tests, backend regression tests and build; inspect representative
      answers in the browser, review the diff, and open a focused PR.
- [ ] Publish the website update and verify a real answer using the existing backend.

Validation: 28 frontend tests and 15 backend regression tests passed; the backend retains its existing Starlette/httpx deprecation warning. Browser fixture verified semantic Markdown, C/LC-3 highlighting, all equation delimiters and no page overflow at the default narrow viewport, with no console errors. Review found an inherited-property code-fence lookup crash; its new regression test failed first, Object.hasOwn fixed it, and the full frontend suite passed.
