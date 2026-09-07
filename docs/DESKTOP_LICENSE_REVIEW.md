# Desktop distribution license review / 桌面发行许可检查

Status on 2026-09-08: **pending owner decision; v1.2.1 binaries are not a public release yet**.

ScholarNova's own code retains its existing MIT license. This does not relicense bundled third-party components. In particular, the PDF implementation depends on `pymupdf==1.26.3` in `requirements-lock.txt`. PyMuPDF and MuPDF have open-source AGPL and commercial licensing options; see the [official license explanation](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright).

The desktop package bundles a Python runtime and PDF libraries, rather than asking end users to install those dependencies separately. Do not describe the complete binary bundle as MIT-only or assume that an MIT source repository resolves all dependency obligations. No commercial PyMuPDF license has been verified for this release.

## Decision needed / 需要确认的路线

- Continue open-source distribution: review the combined distribution's applicable terms, include license notices and the required corresponding source/build information, retaining existing authorship notices.
- Preserve a permissive-only dependency direction: replace the PDF dependency and regression-test text, tables, rendering and image analysis before shipping the replacement.
- Use a commercial license: the owner supplies and verifies an appropriate authorization; the agent does not purchase one or assume it exists.

这是发行前检查记录，不是已经完成的法律合规认证。应用功能修复、用户数据及源代码原有许可证均不因这个待选项而被擅自变更。

## Release gate / 发布闸门

Manual desktop builds can still run for validation. A version-tag build must fail until repository variable `DESKTOP_LICENSE_REVIEWED` is `true`. Set it only after recording the selected licensing route and completing its required notices/source distribution or dependency replacement—not simply to bypass the check. Keep the review evidence in version control and recheck whenever bundled dependencies change.

Windows commercial code signing and Apple notarization are separate from dependency licensing. Passing build/startup tests proves neither legal clearance nor platform signing.
