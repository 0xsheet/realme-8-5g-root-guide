# Third-party components

This repository contains its own orchestration code and documentation. Vendor firmware,
Download Agents, APKs, binaries and private phone dumps are not committed or attached to releases.
`fetch-tools` retrieves upstream assets into ignored `local/tools/`.

| Component | Pinned source | License / provenance |
|---|---|---|
| Magisk | topjohnwu/Magisk v30.7 | GPL-3.0; official project release; preserve upstream notices |
| Penumbra / Antumbra | shomykohai/penumbra v2.0.0 | AGPL-3.0-or-later; official project release |
| MTKClient | 7cb40e727727dfe3faa065eefb29b16ed29bbdf1 | GPLv3; source and loaders remain in its own downloaded tree |
| Oppo preloader patcher | Shocked-Cat commit ecf8e2c6f967706e6ab55c4774141abb5d78d12f | AGPL-3.0; downloaded and invoked separately |
| Platform-Tools | Android Developers, 36.0.0 Linux archive | Android SDK terms and bundled NOTICE; see upstream download terms |
| OPLUS MT6833 2025 DA stages | GeekFlashTool resources commit 566ab99bc2502f8d655c971bb1e411d3e74929e0 | Third-party resource distribution; no redistribution license is assumed here |

The MIT license applies only to this repository's original code/documentation; it does not
relicense downloaded components. Source URLs and file checksums are in `assets.lock.json`.
No claim is made that the GeekFlashTool DA distribution is an official realme download.
