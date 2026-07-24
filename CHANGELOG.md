# Changelog

## [2.1.0-beta.0](https://github.com/NevaMind-AI/memU/compare/v2.0.0-beta.0...v2.1.0-beta.0) (2026-07-24)


### Features

* add cloud-backed memory behind existing CLI ([988ce32](https://github.com/NevaMind-AI/memU/commit/988ce32afd7f1f4baa1f453cedb966c5cf33c65c))
* **hosts:** add a Windows Task Scheduler bridging helper ([#546](https://github.com/NevaMind-AI/memU/issues/546)) ([43488b5](https://github.com/NevaMind-AI/memU/commit/43488b5f60bf27f9cd97b4c492cd75dc73eb5fbd))
* **retrieval:** shape progressive-retrieve output for the agent ([#540](https://github.com/NevaMind-AI/memU/issues/540)) ([f9d6d69](https://github.com/NevaMind-AI/memU/commit/f9d6d69d29530b4da47a604237ddb70493d084da))


### Bug Fixes

* **commit:** update recall file description on recommit ([#548](https://github.com/NevaMind-AI/memU/issues/548)) ([59204a8](https://github.com/NevaMind-AI/memU/commit/59204a83afbef2fd11fca8d4a781dc36c0dcac9a))
* **hosts:** isolate each host's write tree so concurrent memorize can't corrupt ([#544](https://github.com/NevaMind-AI/memU/issues/544)) ([#564](https://github.com/NevaMind-AI/memU/issues/564)) ([a1a02a7](https://github.com/NevaMind-AI/memU/commit/a1a02a7b9a34bd879d5f94e56d090059f0c80980))


### Documentation

* add memU Cloud install and memory viewer ([#553](https://github.com/NevaMind-AI/memU/issues/553)) ([d37013c](https://github.com/NevaMind-AI/memU/commit/d37013c5138f286b73869d73f06af2b80addad07))
* clarify Cloud and self-hosted differences ([#557](https://github.com/NevaMind-AI/memU/issues/557)) ([60df32a](https://github.com/NevaMind-AI/memU/commit/60df32a26d95d21d5fba6e8ade23c662481c81e3))
* clarify durable memory location ([#551](https://github.com/NevaMind-AI/memU/issues/551)) ([3616ceb](https://github.com/NevaMind-AI/memU/commit/3616cebf40ad559a60753c7ea3b7ee627ee8de88))
* explain automatic skill extraction ([#562](https://github.com/NevaMind-AI/memU/issues/562)) ([48fc3ef](https://github.com/NevaMind-AI/memU/commit/48fc3ef59d3fe10d86ad6e477a9eebcc319b00c1))
* make installation the quick start ([#555](https://github.com/NevaMind-AI/memU/issues/555)) ([e7f81ae](https://github.com/NevaMind-AI/memU/commit/e7f81aefd3ea9d804af3ebee337b5c5afd91520f))
* mark memU Cloud as coming soon ([#554](https://github.com/NevaMind-AI/memU/issues/554)) ([2007b22](https://github.com/NevaMind-AI/memU/commit/2007b22606d249c1cf3c910fe66834e850bc1ff3))
* refresh README architecture diagram ([#559](https://github.com/NevaMind-AI/memU/issues/559)) ([3b803a2](https://github.com/NevaMind-AI/memU/commit/3b803a2a065ad7d430f718ee77fdee71f3c7e297))
* remove agent logos from architecture diagram ([#560](https://github.com/NevaMind-AI/memU/issues/560)) ([73f0ee9](https://github.com/NevaMind-AI/memU/commit/73f0ee974845cc964b6012d0c7b4f367b0a28107))
* simplify Quick start choices ([#558](https://github.com/NevaMind-AI/memU/issues/558)) ([f684b5b](https://github.com/NevaMind-AI/memU/commit/f684b5bbd4cd7a802b1118bed160666ca441307a))
* streamline README positioning and quick start ([#550](https://github.com/NevaMind-AI/memU/issues/550)) ([118d02f](https://github.com/NevaMind-AI/memU/commit/118d02f34c881367d225018de1bc66de18d3fcca))
* use official memU logo in README diagrams ([#565](https://github.com/NevaMind-AI/memU/issues/565)) ([2456d7d](https://github.com/NevaMind-AI/memU/commit/2456d7da4436397af07e63ba9d87007a43331a16))

## [2.0.0-beta.0](https://github.com/NevaMind-AI/memU/compare/v1.5.1...v2.0.0-beta.0) (2026-07-23)


### Features

* **blob:** ingest rich documents (PDF/Office/HTML) via MarkItDown ([#447](https://github.com/NevaMind-AI/memU/issues/447)) ([1e16341](https://github.com/NevaMind-AI/memU/commit/1e1634131f84ceb023d03cd87bcf062317abd5ba))
* Codex session-bridging pipeline and scheduled-task skill ([#477](https://github.com/NevaMind-AI/memU/issues/477)) ([1a8edb5](https://github.com/NevaMind-AI/memU/commit/1a8edb57110ebfd208b2fe1f52e3998058fed408))
* **doctor:** diagnose proxy hijacking instead of printing a bare 502 ([7c41eec](https://github.com/NevaMind-AI/memU/commit/7c41eecd53e4c13b1a5c25b01b70f484147295fb))
* **env:** config.env carries NO_PROXY; MEMU_HTTP_PROXY works from the file ([5265945](https://github.com/NevaMind-AI/memU/commit/5265945e3063529819415194e79c46b7614d6081))
* from memory item/category to tracked entry/file for workspace memorization (ADR 0006) ([#456](https://github.com/NevaMind-AI/memU/issues/456)) ([68877da](https://github.com/NevaMind-AI/memU/commit/68877da10a1a18be5c708ec1ab7eb6c45b80ae50))
* **hermes:** install retrieval as a skill ([#536](https://github.com/NevaMind-AI/memU/issues/536)) ([8766d3d](https://github.com/NevaMind-AI/memU/commit/8766d3d3903383a3d4ff38d0f0d620cdf97418ec))
* **hosts:** add Claude Code, Cursor, OpenClaw, and Hermes host adapters ([#494](https://github.com/NevaMind-AI/memU/issues/494)) ([24d1b3b](https://github.com/NevaMind-AI/memU/commit/24d1b3b4f345106f07f1262dc2756b49fb7102cf))
* **hosts:** add memu-agent, a generic adapter for any other agent ([#496](https://github.com/NevaMind-AI/memU/issues/496)) ([e46a1f0](https://github.com/NevaMind-AI/memU/commit/e46a1f04a216a80b3a38064866420c79205fbe22))
* **hosts:** agent-driven uninstall — remove-instruction, docs uninstall, per-host guides ([#509](https://github.com/NevaMind-AI/memU/issues/509)) ([f51673e](https://github.com/NevaMind-AI/memU/commit/f51673e6e80b23c570a7364b415bf61481956971))
* **hosts:** install retrieval as a skill on Codex and Claude Code ([#535](https://github.com/NevaMind-AI/memU/issues/535)) ([2ed480e](https://github.com/NevaMind-AI/memU/commit/2ed480ebe462fe4008fdb4315cf5ab9e0316dba4))
* layered, track-aware workspace memorize & retrieve ([#466](https://github.com/NevaMind-AI/memU/issues/466)) ([094e22f](https://github.com/NevaMind-AI/memU/commit/094e22f0e10e7fe71c079608407b6a01b4d67e55))
* **llm,vlm:** multi-provider LLM gateway, modular preprocessing, and VLM package ([#442](https://github.com/NevaMind-AI/memU/issues/442)) ([6f1b0bc](https://github.com/NevaMind-AI/memU/commit/6f1b0bc19d600e77abe7d6ec82d4196d1efe1516))
* **memory_fs:** workspace memorize + markdown memory file system ([#439](https://github.com/NevaMind-AI/memU/issues/439)) ([1b1ad61](https://github.com/NevaMind-AI/memU/commit/1b1ad61bdb96030f00e169b14d7864c1f6adb931))
* memu CLI, npm launcher, and agent skills for the workspace pair ([#467](https://github.com/NevaMind-AI/memU/issues/467)) ([c861974](https://github.com/NevaMind-AI/memU/commit/c8619744b13c67f7efc3322c060e6090255a8522))
* **npm:** point the launcher at the memu-cli PyPI channel ([#483](https://github.com/NevaMind-AI/memU/issues/483)) ([5056389](https://github.com/NevaMind-AI/memU/commit/505638905f279e0b2fac61572ea551f819007aa1))
* **openclaw:** install retrieval as a skill ([#537](https://github.com/NevaMind-AI/memU/issues/537)) ([3cef5ae](https://github.com/NevaMind-AI/memU/commit/3cef5ae2610ce9227de6471a63cc139ff09cf63c))
* **preprocess:** classify audio type and add an overview on ingest ([#448](https://github.com/NevaMind-AI/memU/issues/448)) ([f7601da](https://github.com/NevaMind-AI/memU/commit/f7601daf4ed89815af5c1c1c9011db6af63c1fa5))
* **vlm,preprocess:** native whole-video understanding via OpenRouter ([#450](https://github.com/NevaMind-AI/memU/issues/450)) ([1de5784](https://github.com/NevaMind-AI/memU/commit/1de57847e0ffc430cbf5d6dc17183f33d08be8fe))


### Bug Fixes

* **app:** unpack the (vectors, raw_response) tuple embed() returns ([#504](https://github.com/NevaMind-AI/memU/issues/504)) ([9b2a70c](https://github.com/NevaMind-AI/memU/commit/9b2a70ca214cd3a5b22e902cad0dc19ad07bfeb9))
* **bridging:** advance the cursor and snapshot at commit, not prepare ([#531](https://github.com/NevaMind-AI/memU/issues/531)) ([0ceaa19](https://github.com/NevaMind-AI/memU/commit/0ceaa190d92f8c7c6705db0dcfd6628581d10213))
* **ci:** sort workbuddy cli imports so make check passes ([#522](https://github.com/NevaMind-AI/memU/issues/522)) ([151298c](https://github.com/NevaMind-AI/memU/commit/151298c3c03a6b3cc9ef371d8211b469fffc2469))
* **cli:** force UTF-8 stdio so piped output survives non-UTF-8 Windows code pages ([#513](https://github.com/NevaMind-AI/memU/issues/513)) ([b521453](https://github.com/NevaMind-AI/memU/commit/b5214536c5fce628c174c9c074b9c1d0a53da2ca))
* **codex:** drop harness-injected user records from the conversation seam ([#511](https://github.com/NevaMind-AI/memU/issues/511)) ([c827157](https://github.com/NevaMind-AI/memU/commit/c827157ead066f0a859cb2f1e5deac62ffbe63a5))
* **embedding:** never route loopback embedding calls through a proxy ([#519](https://github.com/NevaMind-AI/memU/issues/519)) ([df6cfba](https://github.com/NevaMind-AI/memU/commit/df6cfba6b9741cc062b7d219af042ddddffcbb5c))
* handle multiple root-level XML elements from non-conformant LLMs ([#409](https://github.com/NevaMind-AI/memU/issues/409)) ([fed42b6](https://github.com/NevaMind-AI/memU/commit/fed42b6142ec1e9f9820e46d8899823d68de8276))
* **hermes:** escape the state.db path when building the SQLite URI ([#503](https://github.com/NevaMind-AI/memU/issues/503)) ([3135132](https://github.com/NevaMind-AI/memU/commit/313513204d87e7156d6a7d459df1bcac64469044))
* **llm/vlm:** correct OpenAI token-limit param and simplify conversation preprocess ([#449](https://github.com/NevaMind-AI/memU/issues/449)) ([ff3c2be](https://github.com/NevaMind-AI/memU/commit/ff3c2bee2ec96ebd303f3e22dae1977ff6388120))
* make lazyllm an optional dependency (fixes [#373](https://github.com/NevaMind-AI/memU/issues/373)) ([#402](https://github.com/NevaMind-AI/memU/issues/402)) ([7652982](https://github.com/NevaMind-AI/memU/commit/7652982a016b2a2426d20bc11c46491d909704d0))
* **memory_fs:** restore LLM-free skill bypass and unify synthesis paths ([#444](https://github.com/NevaMind-AI/memU/issues/444)) ([bc13bd4](https://github.com/NevaMind-AI/memU/commit/bc13bd43c6ed3d480b671736bab987434675c717))
* **openclaw:** scan only main session transcripts, not trajectory/checkpoint sidecars ([0245de9](https://github.com/NevaMind-AI/memU/commit/0245de9710f8f73a8b21361442ac3dfd6c7829c7))
* optimize category initialization to avoid unnecessary embedding ([#388](https://github.com/NevaMind-AI/memU/issues/388)) ([a92f266](https://github.com/NevaMind-AI/memU/commit/a92f2666bf94336f8c6bf950088249e611915e7d))
* remove broken memu-server entry point (fixes [#354](https://github.com/NevaMind-AI/memU/issues/354)) ([#398](https://github.com/NevaMind-AI/memU/issues/398)) ([0672b56](https://github.com/NevaMind-AI/memU/commit/0672b56725e12c35bd46061bb23ccd93690a5fbb))
* remove duplicate document text from preprocess prompt ([#420](https://github.com/NevaMind-AI/memU/issues/420)) ([44aa5ff](https://github.com/NevaMind-AI/memU/commit/44aa5ff0cbceae56ab283848e722a9d4bd8eddd0))
* remove stale memu-server script entry point (fixes [#393](https://github.com/NevaMind-AI/memU/issues/393)) ([#403](https://github.com/NevaMind-AI/memU/issues/403)) ([c5fe493](https://github.com/NevaMind-AI/memU/commit/c5fe493b0596d68479b0ce6c6d83e362ffb04e90))
* resolve SQLite embedding TypeError by using sa_column=False ([#401](https://github.com/NevaMind-AI/memU/issues/401)) ([7e198f3](https://github.com/NevaMind-AI/memU/commit/7e198f3718fa6028c809ba7d816a96541fe7e13f))
* return empty list for non-positive top_k in cosine_topk ([#423](https://github.com/NevaMind-AI/memU/issues/423)) ([39023a8](https://github.com/NevaMind-AI/memU/commit/39023a81d758eb4447ed7d88503b8d782aecaf73))
* **tests:** pin UTF-8 on test file I/O so the suite passes on non-UTF-8-locale Windows ([#501](https://github.com/NevaMind-AI/memU/issues/501)) ([dda515a](https://github.com/NevaMind-AI/memU/commit/dda515a4eb3117ff804cd7ce1ae66e03c23028b6))


### Documentation

* add ADR 0008 — trajectory as the source, hooks over API ([#476](https://github.com/NevaMind-AI/memU/issues/476)) ([ff90dac](https://github.com/NevaMind-AI/memU/commit/ff90dac6976bc920667e03d295a75d5da8626f75))
* add INSTALL-LATEST.md and register the WorkBuddy adapter ([#527](https://github.com/NevaMind-AI/memU/issues/527)) ([4871c55](https://github.com/NevaMind-AI/memU/commit/4871c558d5b84c7649d822015dab617a095d678f))
* add SKILL.md, one routing entry point for agent-driven install ([#497](https://github.com/NevaMind-AI/memU/issues/497)) ([bf7aaf3](https://github.com/NevaMind-AI/memU/commit/bf7aaf3bf95cb37f723e7a81b6d5bcdaf35a0f2e))
* add the architecture image the README references ([#492](https://github.com/NevaMind-AI/memU/issues/492)) ([c07b905](https://github.com/NevaMind-AI/memU/commit/c07b9055dc245680c67df02199d4c95cd7a9a62f))
* add under-construction notice, stabilizing ~July 15 ([#472](https://github.com/NevaMind-AI/memU/issues/472)) ([6426ff0](https://github.com/NevaMind-AI/memU/commit/6426ff02aacca12e9d4efbcfc89f53eeed2ae55b))
* ADR 0007 — drop the graph, retrieval is hybrid (embedding + BM25) ([#464](https://github.com/NevaMind-AI/memU/issues/464)) ([3dd7d5c](https://github.com/NevaMind-AI/memU/commit/3dd7d5c055fc6a3244d4c2390f7b8e6bc4321857))
* ADR 0007 — invert L1/L2 (L1 = coarse doc, L2 = item slices) ([#465](https://github.com/NevaMind-AI/memU/issues/465)) ([0afbcc5](https://github.com/NevaMind-AI/memU/commit/0afbcc550ac5b816e5ae9ad309e62adbdf4b80b4))
* ADR 0007 — replace the explicit item graph with entity linking ([#463](https://github.com/NevaMind-AI/memU/issues/463)) ([0bd3c77](https://github.com/NevaMind-AI/memU/commit/0bd3c7765ac791020941de8791ba5b7c50ecc5e0))
* ADR 0007 — three independent memory lines on a layered wiki-graph kernel ([#461](https://github.com/NevaMind-AI/memU/issues/461)) ([a6cf62e](https://github.com/NevaMind-AI/memU/commit/a6cf62e069765b7b234597e537ec170d169d751c))
* align architecture.md and READMEs with ADR 0006 data model ([#460](https://github.com/NevaMind-AI/memU/issues/460)) ([8062b91](https://github.com/NevaMind-AI/memU/commit/8062b91776e69757fd467e79e56cd72eba62c72c))
* consolidate agent skills into one memu SKILL.md, link it atop README ([#469](https://github.com/NevaMind-AI/memU/issues/469)) ([6f0ae82](https://github.com/NevaMind-AI/memU/commit/6f0ae82aaf9d1193841b8e082a2f9fed8753ed70))
* drop the API and CLI reference sections from the README ([#489](https://github.com/NevaMind-AI/memU/issues/489)) ([94a1111](https://github.com/NevaMind-AI/memU/commit/94a11117cf5684888fb7858356c51203c903e9bb))
* expand the README; rename provider var to MEMU_EMBED_PROVIDER ([#486](https://github.com/NevaMind-AI/memU/issues/486)) ([96da89b](https://github.com/NevaMind-AI/memU/commit/96da89bfe048b86516faa4b86f69b508fb4c4c3c))
* focus readme on workspace APIs ([9241f31](https://github.com/NevaMind-AI/memU/commit/9241f3112e912bd47add2fabe6dc2611a4bdac8c))
* **grok:** fix MemoryService initialization example ([#405](https://github.com/NevaMind-AI/memU/issues/405)) ([96e693a](https://github.com/NevaMind-AI/memU/commit/96e693aa09add032f67b342e21b86fa96078611b))
* highlight self-evolving skills in README and description ([#452](https://github.com/NevaMind-AI/memU/issues/452)) ([fb68d22](https://github.com/NevaMind-AI/memU/commit/fb68d22c3caa4a9b6f5cb2a57d185bb9b5e22a5f))
* **hosts:** bind the session cursor's lifecycle to the store's ([75959a6](https://github.com/NevaMind-AI/memU/commit/75959a6e72727c35929f4296c087ed00c97971bf))
* **hosts:** correct the Claude Code multi-block claim and pin it with tests ([#502](https://github.com/NevaMind-AI/memU/issues/502)) ([5995e05](https://github.com/NevaMind-AI/memU/commit/5995e05f27c7d90231468bcb062713af30813b08))
* **hosts:** default bridging schedule to hourly ([#516](https://github.com/NevaMind-AI/memU/issues/516)) ([c1046bb](https://github.com/NevaMind-AI/memU/commit/c1046bb1954c3dd7b16ced769da030d8a02c8d32))
* **hosts:** name the OS system-wide proxy as a 502 source ([#523](https://github.com/NevaMind-AI/memU/issues/523)) ([2b79803](https://github.com/NevaMind-AI/memU/commit/2b79803612872e65201a40dde95ac00541f93fae))
* **hosts:** no-key local fallback hint; default bridging schedule to cron ([#508](https://github.com/NevaMind-AI/memU/issues/508)) ([d155c48](https://github.com/NevaMind-AI/memU/commit/d155c48ac6a35465ad47848927b271f34e2dc4d0))
* **hosts:** scheduled runs drain leftover jobs first; config repairs stay at the connection layer ([9195d14](https://github.com/NevaMind-AI/memU/commit/9195d14cef2d308cff3fcb853a6274e1f0db9d31))
* **hosts:** the scheduler's PATH is not your shell's — fix and honest verify for the bridging guides ([#530](https://github.com/NevaMind-AI/memU/issues/530)) ([19302d2](https://github.com/NevaMind-AI/memU/commit/19302d24260c7b941bdfee66bba8f16b6b47c8c2))
* lead the README with the one-message agent-driven install ([#498](https://github.com/NevaMind-AI/memU/issues/498)) ([aae3d44](https://github.com/NevaMind-AI/memU/commit/aae3d44b0a4332981c4459e7da9258298bcc0fb1))
* make the workspace pair primary, mark memorize/retrieve as legacy ([#470](https://github.com/NevaMind-AI/memU/issues/470)) ([6f3c1be](https://github.com/NevaMind-AI/memU/commit/6f3c1beb36bba21a7d640b0dbdead9361a90a811))
* never fall back to legacy memorize/retrieve ([#471](https://github.com/NevaMind-AI/memU/issues/471)) ([28ee09d](https://github.com/NevaMind-AI/memU/commit/28ee09de54de5bd74f4f6bb1e0185c854ecf1053))
* pitch memU as a 500-line memory system ([#488](https://github.com/NevaMind-AI/memU/issues/488)) ([2a8f8b3](https://github.com/NevaMind-AI/memU/commit/2a8f8b3403548a8d8917a19d5ac0015adf4eab17))
* point the README at the memu-cli package ([#491](https://github.com/NevaMind-AI/memU/issues/491)) ([9ceea5b](https://github.com/NevaMind-AI/memU/commit/9ceea5b32a2694cf4ab5e5f0069b029ac13800b3))
* **readme:** readme accuracy updates ([#430](https://github.com/NevaMind-AI/memU/issues/430)) ([5f17725](https://github.com/NevaMind-AI/memU/commit/5f1772579c8d0881ec1c9ab071404aea6b3bfadc))
* **readme:** reframe intro around MEMORY.md, SKILL.md, and INDEX.md ([#434](https://github.com/NevaMind-AI/memU/issues/434)) ([ca0c755](https://github.com/NevaMind-AI/memU/commit/ca0c755dcc06874c227df811d6b7a3ca972f6be2))
* **readme:** reframe README around file-system-as-memory narrative ([#432](https://github.com/NevaMind-AI/memU/issues/432)) ([cd8150a](https://github.com/NevaMind-AI/memU/commit/cd8150ac7d68f4972d9a9e8268e3169da9b4cfc3))
* **readme:** reframe README around workspace-runtime narrative ([#438](https://github.com/NevaMind-AI/memU/issues/438)) ([7c104b1](https://github.com/NevaMind-AI/memU/commit/7c104b1eb0883437d49bea0edae3a24eea12f275))
* **readme:** sync translated READMEs to file-system-as-memory narrative ([#433](https://github.com/NevaMind-AI/memU/issues/433)) ([f4e82ce](https://github.com/NevaMind-AI/memU/commit/f4e82cec1898e34f82612ec3628f8de1faedf701))
* refine ADR 0007 with the L0/L1/L2 layer model ([#462](https://github.com/NevaMind-AI/memU/issues/462)) ([6456c35](https://github.com/NevaMind-AI/memU/commit/6456c357b22039a3b12ba2f2bc0294a8693bceb5))
* Refine OpenClaw reference and feature descriptions ([#410](https://github.com/NevaMind-AI/memU/issues/410)) ([707b80e](https://github.com/NevaMind-AI/memU/commit/707b80e5f4394b8e4aafff1ef23fd331a8b557f8))
* refine README memory filesystem positioning ([#429](https://github.com/NevaMind-AI/memU/issues/429)) ([dda0374](https://github.com/NevaMind-AI/memU/commit/dda03743b007c0863c7fe7237592f7e4a0de32b6))
* refine README positioning around personal memory as files ([#455](https://github.com/NevaMind-AI/memU/issues/455)) ([88982d3](https://github.com/NevaMind-AI/memU/commit/88982d3d22640501be09ced1876520e95d956312))
* reframe README and description around personal-information memory ([#451](https://github.com/NevaMind-AI/memU/issues/451)) ([6b5b11c](https://github.com/NevaMind-AI/memU/commit/6b5b11c0787704c119b8d2e2d3c779bd56ee66fa))
* refresh memory diagrams ([#473](https://github.com/NevaMind-AI/memU/issues/473)) ([0d8770f](https://github.com/NevaMind-AI/memU/commit/0d8770f0c9d49f3a09e6ac33ca72b34c8128a855))
* retitle around file-based memory and trim README ([#453](https://github.com/NevaMind-AI/memU/issues/453)) ([2c1cc86](https://github.com/NevaMind-AI/memU/commit/2c1cc86ba66f31ffb7c6afcd0717f7e1880c0fd0))
* rewrite README — raw data → memory → agent ([#426](https://github.com/NevaMind-AI/memU/issues/426)) ([c2a2aac](https://github.com/NevaMind-AI/memU/commit/c2a2aac52b4424583955f85f5a35776e76beb68a))
* swap the tagline to lead with Across Agents ([#490](https://github.com/NevaMind-AI/memU/issues/490)) ([6e0fc06](https://github.com/NevaMind-AI/memU/commit/6e0fc068a1e3a2212dfea52f52438b438dae88f3))
* tagline across sessions/agents/devices, lowercase memU in banner alt ([#515](https://github.com/NevaMind-AI/memU/issues/515)) ([1f4f831](https://github.com/NevaMind-AI/memU/commit/1f4f8315bc0a68a6d2c2fa8018d64e7f22e5b164))
* tighten the README intro to two sentences ([#487](https://github.com/NevaMind-AI/memU/issues/487)) ([da160f2](https://github.com/NevaMind-AI/memU/commit/da160f2155439923bfe744ac770733c1c9824cd9))


### Miscellaneous Chores

* release 2.0.0-beta.0 ([#541](https://github.com/NevaMind-AI/memU/issues/541)) ([3dc60ce](https://github.com/NevaMind-AI/memU/commit/3dc60cea094e29f86ead2fad148ea0fbeab198c3))

## [1.5.1](https://github.com/NevaMind-AI/memU/compare/v1.5.0...v1.5.1) (2026-03-23)


### Bug Fixes

* use correct interpolation in alembic url ([#390](https://github.com/NevaMind-AI/memU/issues/390)) ([fd87ceb](https://github.com/NevaMind-AI/memU/commit/fd87ceb558eaa800aeb694b045847971958f23a3))

## [1.5.0](https://github.com/NevaMind-AI/memU/compare/v1.4.0...v1.5.0) (2026-03-17)


### Features

* add non-propagate option for memory patch ([#386](https://github.com/NevaMind-AI/memU/issues/386)) ([3b67458](https://github.com/NevaMind-AI/memU/commit/3b67458c6325b4fcdaccbc34f6e0fea491b7ba96))
* **http:** add HTTP proxy support for LLM & embedding clients ([#310](https://github.com/NevaMind-AI/memU/issues/310)) ([a3d45e2](https://github.com/NevaMind-AI/memU/commit/a3d45e2f4174702fd8fd83cd13862285cd47cad9))


### Bug Fixes

* httpx base_url path discarded when endpoint starts with / ([#328](https://github.com/NevaMind-AI/memU/issues/328), [#336](https://github.com/NevaMind-AI/memU/issues/336), [#341](https://github.com/NevaMind-AI/memU/issues/341), [#329](https://github.com/NevaMind-AI/memU/issues/329)) ([#344](https://github.com/NevaMind-AI/memU/issues/344)) ([9e31ef2](https://github.com/NevaMind-AI/memU/commit/9e31ef235d46317f383613825090c52943cb55a2))


### Documentation

* add architecture explanation and adrs ([#353](https://github.com/NevaMind-AI/memU/issues/353)) ([8676a27](https://github.com/NevaMind-AI/memU/commit/8676a2721917f4e0baee6d01a9d6b95bd642be97))
* add pull request template to improve contribution quality ([#261](https://github.com/NevaMind-AI/memU/issues/261)) ([2256119](https://github.com/NevaMind-AI/memU/commit/2256119fb2d177890c7f738c926f437a355e7359))
* Update Discord link in README.md ([#377](https://github.com/NevaMind-AI/memU/issues/377)) ([163d050](https://github.com/NevaMind-AI/memU/commit/163d050299b77143226e9727f67d4826c9a69f92))
* update memU Bot section with GitHub reference and "Now open source" ([#366](https://github.com/NevaMind-AI/memU/issues/366)) ([dc6880a](https://github.com/NevaMind-AI/memU/commit/dc6880a793d40b04cd599298a110af5f0f0b9cb5))

## [1.4.0](https://github.com/NevaMind-AI/memU/compare/v1.3.0...v1.4.0) (2026-02-06)


### Features

* Add inline memory item references in category summaries ([#202](https://github.com/NevaMind-AI/memU/issues/202)) ([#205](https://github.com/NevaMind-AI/memU/issues/205)) ([5213571](https://github.com/NevaMind-AI/memU/commit/5213571b218d85784e0771f7a721eafd7da1c1ff))
* Add salience-aware memory with reinforcement tracking ([#186](https://github.com/NevaMind-AI/memU/issues/186)) ([#206](https://github.com/NevaMind-AI/memU/issues/206)) ([2bdbcce](https://github.com/NevaMind-AI/memU/commit/2bdbcce1a87ae1017d5930901fb0ae8d2924dcee))
* Add Tool Memory type with specialized metadata and statistics ([#247](https://github.com/NevaMind-AI/memU/issues/247)) ([4e8a035](https://github.com/NevaMind-AI/memU/commit/4e8a03578641afd0e07f9700629dff8d91d2b3fb))


### Bug Fixes

* add chat() API and stop misusing summarize() ([#208](https://github.com/NevaMind-AI/memU/issues/208)) ([be0a5c7](https://github.com/NevaMind-AI/memU/commit/be0a5c73250f0a21ad5e0d39b0e66e3018809e0f))
* remove unused type: ignore comment and add lazyllm mypy override ([#275](https://github.com/NevaMind-AI/memU/issues/275)) ([0e490f7](https://github.com/NevaMind-AI/memU/commit/0e490f7333feecffaef0901cccb1c9a5dbb7bafb))
* **video:** cleanup temp files on extraction failure ([#295](https://github.com/NevaMind-AI/memU/issues/295)) ([16b65e5](https://github.com/NevaMind-AI/memU/commit/16b65e54aef69dfe617835ca534c12752e06eda8))


### Documentation

* file system in readme ([#301](https://github.com/NevaMind-AI/memU/issues/301)) ([ee27d8a](https://github.com/NevaMind-AI/memU/commit/ee27d8aa5e42d249963b08d5775338080b0255f8))
* fix name ([#291](https://github.com/NevaMind-AI/memU/issues/291)) ([fd0d179](https://github.com/NevaMind-AI/memU/commit/fd0d17998f6c0c9ba5c7e91964c39ee909f2b366))
* fix readme lint ([#290](https://github.com/NevaMind-AI/memU/issues/290)) ([a7a5516](https://github.com/NevaMind-AI/memU/commit/a7a55169ecbc1579ae87dc68c5e09b1d62f07b56))
* lint error ([#287](https://github.com/NevaMind-AI/memU/issues/287)) ([7f61dc7](https://github.com/NevaMind-AI/memU/commit/7f61dc72ffbadf849f227cf314bba7ce7964761b))
* readme memubot ([#289](https://github.com/NevaMind-AI/memU/issues/289)) ([2f30798](https://github.com/NevaMind-AI/memU/commit/2f30798367e3591107e1e66a184d0dd4ad6c2f93))
* Update README.md ([#300](https://github.com/NevaMind-AI/memU/issues/300)) ([1075d7c](https://github.com/NevaMind-AI/memU/commit/1075d7c9ec3a272846c9fdb8c22ec58ff73cf6e7))

## [1.3.0](https://github.com/NevaMind-AI/memU/compare/v1.2.0...v1.3.0) (2026-01-29)


### Features

* add happened at and extra fields to memory item ([#262](https://github.com/NevaMind-AI/memU/issues/262)) ([77938e9](https://github.com/NevaMind-AI/memU/commit/77938e9c282e1c0eda11088675c35975d85c4ff0))
* add proactive example ([#268](https://github.com/NevaMind-AI/memU/issues/268)) ([d3d1de1](https://github.com/NevaMind-AI/memU/commit/d3d1de1d9b0f45d9b14479cbaa4462458b172005))
* add Sealos support agent use case (Track G) ([#255](https://github.com/NevaMind-AI/memU/issues/255)) ([8fbdf3c](https://github.com/NevaMind-AI/memU/commit/8fbdf3c301f74f2aa85604837e00bb305b8801ec))
* integrate LazyLLM to provide more llm services ([#265](https://github.com/NevaMind-AI/memU/issues/265)) ([c03f639](https://github.com/NevaMind-AI/memU/commit/c03f639677d6c897b75dfe28d0cd92d5b5270957))
* **integrations:** Add LangGraph Adapter for MemU (Track A) ([#258](https://github.com/NevaMind-AI/memU/issues/258)) ([50b5502](https://github.com/NevaMind-AI/memU/commit/50b5502ebcacd86401f98b1bb7e5a6577fab7126))
* **llm:** add Grok (xAI) integration ([#179](https://github.com/NevaMind-AI/memU/issues/179)) ([#236](https://github.com/NevaMind-AI/memU/issues/236)) ([1e16309](https://github.com/NevaMind-AI/memU/commit/1e1630948af535f8ed9d608e6c4f9d2748d4ce8e))
* Openrouter integration as backend provider ([#182](https://github.com/NevaMind-AI/memU/issues/182)) ([cba667a](https://github.com/NevaMind-AI/memU/commit/cba667a56daca5093c9b79a598c7d2ffda813756))


### Bug Fixes

* memory type & proactive example ([#272](https://github.com/NevaMind-AI/memU/issues/272)) ([710f14d](https://github.com/NevaMind-AI/memU/commit/710f14d4b171c5cde609a9dc2caf454681ab94b3))
* proactive examples ([#273](https://github.com/NevaMind-AI/memU/issues/273)) ([603ae12](https://github.com/NevaMind-AI/memU/commit/603ae122b94741bb350656086960c4e2bb868c2a))


### Documentation

* Add link to memU bot ([#276](https://github.com/NevaMind-AI/memU/issues/276)) ([2f84231](https://github.com/NevaMind-AI/memU/commit/2f842311ed592c1a45cdb9e24f7a128da97a0a39))
* multilingual readme ([#271](https://github.com/NevaMind-AI/memU/issues/271)) ([200f47a](https://github.com/NevaMind-AI/memU/commit/200f47a15ff7d05fc435abe1d2cefbb3774548fe))
* Update memU bot link to include full URL ([#277](https://github.com/NevaMind-AI/memU/issues/277)) ([6874eaf](https://github.com/NevaMind-AI/memU/commit/6874eaf278e910d07a4427dd4c06f9c4c21283ce))
* update readme ([#266](https://github.com/NevaMind-AI/memU/issues/266)) ([16ae534](https://github.com/NevaMind-AI/memU/commit/16ae534675a5e0711256a5e2147b9190fd8b2524))
* update README ([#270](https://github.com/NevaMind-AI/memU/issues/270)) ([b531d39](https://github.com/NevaMind-AI/memU/commit/b531d39e5538449b31cb212aea1deea24e12180f))

## [1.2.0](https://github.com/NevaMind-AI/memU/compare/v1.1.2...v1.2.0) (2026-01-14)


### Features

* clear memory ([#239](https://github.com/NevaMind-AI/memU/issues/239)) ([7da36da](https://github.com/NevaMind-AI/memU/commit/7da36da57d7013df213e537b1f238f5a526e69d9))
* **database:** add SQLite storage backend ([#201](https://github.com/NevaMind-AI/memU/issues/201)) ([4b899d7](https://github.com/NevaMind-AI/memU/commit/4b899d7b768fcd48b6456234800033e3b2e3173c))
* improve issue template ([#199](https://github.com/NevaMind-AI/memU/issues/199)) ([abe0f1b](https://github.com/NevaMind-AI/memU/commit/abe0f1b77d5f8294ff45c9f57f5aeb6de33977d6))
* optimize topk pick function ([#196](https://github.com/NevaMind-AI/memU/issues/196)) ([b474c54](https://github.com/NevaMind-AI/memU/commit/b474c54a7eea06ba56844d6482d5e78b3cb3f020))
* workflow step interceptor ([#240](https://github.com/NevaMind-AI/memU/issues/240)) ([bf2ac96](https://github.com/NevaMind-AI/memU/commit/bf2ac96f1cb26b196f27b543d4c3e157f408f343))


### Bug Fixes

* allow nullable resource_id in Postgres items ([#232](https://github.com/NevaMind-AI/memU/issues/232)) ([ae2ffbb](https://github.com/NevaMind-AI/memU/commit/ae2ffbb0bcd69170875a47cebf322b71a15f4bd3))
* correct coverage source to track memu package instead of tests ([#220](https://github.com/NevaMind-AI/memU/issues/220)) ([2460bbd](https://github.com/NevaMind-AI/memU/commit/2460bbd2a2c4df5b3664db81d89886b926b51031))
* correct typo in PromptBlock class label attribute ([#231](https://github.com/NevaMind-AI/memU/issues/231)) ([d69053c](https://github.com/NevaMind-AI/memU/commit/d69053cece3467dd7c8cbf0634e72447649095f7))
* default embed size ([#192](https://github.com/NevaMind-AI/memU/issues/192)) ([144fd32](https://github.com/NevaMind-AI/memU/commit/144fd32cfd6917b08f29cf56f251f239c360d2ae))
* readme partners link & github issue link ([#198](https://github.com/NevaMind-AI/memU/issues/198)) ([849f881](https://github.com/NevaMind-AI/memU/commit/849f881f004b0772f372069e40f937731c114c89))


### Documentation

* add Chinese translation of README ([#212](https://github.com/NevaMind-AI/memU/issues/212)) ([d15ecf9](https://github.com/NevaMind-AI/memU/commit/d15ecf97647d8fd9f1d2ae95008a08bbba93a44a))
* add How to Contribute section to README ([#215](https://github.com/NevaMind-AI/memU/issues/215)) ([bf44de7](https://github.com/NevaMind-AI/memU/commit/bf44de722965fd611c0dc585712eac587caa9e6c))
* **readme:** update Chinese README with fixes and improvements ([#221](https://github.com/NevaMind-AI/memU/issues/221)) ([75a8f65](https://github.com/NevaMind-AI/memU/commit/75a8f651bb4b491ab5b0363de789c0dcd0291287))

## [1.1.2](https://github.com/NevaMind-AI/memU/compare/v1.1.1...v1.1.2) (2026-01-08)


### Bug Fixes

* custom memory type default prompt ([#169](https://github.com/NevaMind-AI/memU/issues/169)) ([5a0032f](https://github.com/NevaMind-AI/memU/commit/5a0032fc0f29229524d0356d454a3f5991e04f7b))
* prompt & item fallback ([#183](https://github.com/NevaMind-AI/memU/issues/183)) ([bc95ade](https://github.com/NevaMind-AI/memU/commit/bc95adeb26789104c0bbe199e126cf05def27941))


### Documentation

* add docs folder ([#181](https://github.com/NevaMind-AI/memU/issues/181)) ([919d2ca](https://github.com/NevaMind-AI/memU/commit/919d2caef23107d539c36f30c44d4fb5aa38b324))
* fix issue template dropdown ([#167](https://github.com/NevaMind-AI/memU/issues/167)) ([14d0333](https://github.com/NevaMind-AI/memU/commit/14d03331ed14f1e593fdebbf561189a3775651be))
* issue template fix ([#165](https://github.com/NevaMind-AI/memU/issues/165)) ([5d91237](https://github.com/NevaMind-AI/memU/commit/5d912372e1bf70d7ff573cd5b92e917118048e25))

## [1.1.1](https://github.com/NevaMind-AI/memU/compare/v1.1.0...v1.1.1) (2026-01-07)


### Bug Fixes

* ensure both Linux x86_64 and ARM64 wheels are built ([#162](https://github.com/NevaMind-AI/memU/issues/162)) ([51c9ea4](https://github.com/NevaMind-AI/memU/commit/51c9ea4335a1e9eac227c79783d7aa8cca2b883b))


### Documentation

* add custom LLM and embedding configuration guide ([#160](https://github.com/NevaMind-AI/memU/issues/160)) ([29c414a](https://github.com/NevaMind-AI/memU/commit/29c414a84d1c9c2f989e2165d0b6508c3fe62862))
* add template ([#158](https://github.com/NevaMind-AI/memU/issues/158)) ([b79a78d](https://github.com/NevaMind-AI/memU/commit/b79a78d25b96e670888c18b8f09277db33803865))

## [1.1.0](https://github.com/NevaMind-AI/memU/compare/v1.0.1...v1.1.0) (2026-01-07)


### Features

* add Linux ARM64 (aarch64) build target ([#156](https://github.com/NevaMind-AI/memU/issues/156)) ([0c90fcf](https://github.com/NevaMind-AI/memU/commit/0c90fcfb19fc3e91b951f4ba7454798e4b83e42c))


### Bug Fixes

* llm client profile & wrapper ([#157](https://github.com/NevaMind-AI/memU/issues/157)) ([e55c668](https://github.com/NevaMind-AI/memU/commit/e55c66847eac3ceaf276587d58b76d953d7be9f8))


### Documentation

* remove legacy docs ([#154](https://github.com/NevaMind-AI/memU/issues/154)) ([11fda41](https://github.com/NevaMind-AI/memU/commit/11fda41dda8a5c38b790d3c2fb7053b57b16606e))

## [1.0.1](https://github.com/NevaMind-AI/memU/compare/v1.0.0...v1.0.1) (2026-01-06)


### Bug Fixes

* get embedding client ([#152](https://github.com/NevaMind-AI/memU/issues/152)) ([76716a4](https://github.com/NevaMind-AI/memU/commit/76716a4f00127a3cc21444996f32a9cf810c9282))
* Readme incomplete ([#148](https://github.com/NevaMind-AI/memU/issues/148)) ([f8bc748](https://github.com/NevaMind-AI/memU/commit/f8bc748b9ebfb652ca8a5e06edbbe7eb648ed4f6))

## [1.0.0](https://github.com/NevaMind-AI/memU/compare/v0.9.0...v1.0.0) (2026-01-05)


### ⚠ BREAKING CHANGES

* v1.0.0 ([#147](https://github.com/NevaMind-AI/memU/issues/147))

### Bug Fixes

* v1.0.0 ([#147](https://github.com/NevaMind-AI/memU/issues/147)) ([23f37ee](https://github.com/NevaMind-AI/memU/commit/23f37ee403ecaf88b48af0144e3d701c22ccfddd))


### Documentation

* add readme cloud api ([#144](https://github.com/NevaMind-AI/memU/issues/144)) ([42fd5ba](https://github.com/NevaMind-AI/memU/commit/42fd5babe6748ef54254cf114a54bdefea304f07))
* fix api doc link ([#146](https://github.com/NevaMind-AI/memU/issues/146)) ([23ce7d1](https://github.com/NevaMind-AI/memU/commit/23ce7d19b1d68f4fd0a5a5ac6b756f69fede8d09))

## [0.9.0](https://github.com/NevaMind-AI/memU/compare/v0.8.0...v0.9.0) (2026-01-04)


### Features

* add GitHub issue templates (bug report, designer feedback, feat… ([#132](https://github.com/NevaMind-AI/memU/issues/132)) ([aee22ee](https://github.com/NevaMind-AI/memU/commit/aee22ee94f275749f69367b83a02a2e819cfd001))
* add LLM wrapper and interceptors for LLM calls ([#131](https://github.com/NevaMind-AI/memU/issues/131)) ([416e102](https://github.com/NevaMind-AI/memU/commit/416e1029e7752f173c133ebc83bc42801a313059))
* patch & crud workflows ([#127](https://github.com/NevaMind-AI/memU/issues/127)) ([3cd3dc6](https://github.com/NevaMind-AI/memU/commit/3cd3dc65ae9488207ff8fb0c81e4adb0d22c0f91))


### Bug Fixes

* category summary & category user scopes ([#125](https://github.com/NevaMind-AI/memU/issues/125)) ([a24efd5](https://github.com/NevaMind-AI/memU/commit/a24efd57df2e305fa3eae8622ea889318979c2f7))
* config & resource caption ([#142](https://github.com/NevaMind-AI/memU/issues/142)) ([ea4be13](https://github.com/NevaMind-AI/memU/commit/ea4be1396c0f55b02d706819f6c2b4d5c6e68be8))
* remove duplicate and unnecessary issue templates ([#133](https://github.com/NevaMind-AI/memU/issues/133)) ([559ec14](https://github.com/NevaMind-AI/memU/commit/559ec14d2561ac09162bbb93f178e0f74cc58b23))


### Documentation

* fix README and CONTRIBUTING to match actual codebase ([#130](https://github.com/NevaMind-AI/memU/issues/130)) ([65d7ef4](https://github.com/NevaMind-AI/memU/commit/65d7ef414563395c6cfa0a75343864671c11b62d))
* modify readme.md 0102 ([#136](https://github.com/NevaMind-AI/memU/issues/136)) ([f114ee4](https://github.com/NevaMind-AI/memU/commit/f114ee46c8639b256472a8e989695b2f2215f4d4))

## [0.8.0](https://github.com/NevaMind-AI/memU/compare/v0.7.0...v0.8.0) (2025-12-24)


### Features

* add configurable batch_size for embedding API calls ([#114](https://github.com/NevaMind-AI/memU/issues/114)) ([060067a](https://github.com/NevaMind-AI/memU/commit/060067a5ebe8ad36c4ca4ad2cc6033303c3f1a36))
* add conversation created at ([#120](https://github.com/NevaMind-AI/memU/issues/120)) ([825df56](https://github.com/NevaMind-AI/memU/commit/825df5640037fa2345c3153c3df89174059551b3))
* add workflow implementation and postgres store ([#122](https://github.com/NevaMind-AI/memU/issues/122)) ([a175811](https://github.com/NevaMind-AI/memU/commit/a1758110f859f3725960d308fa0344a1056be52c))


### Bug Fixes

* example 3 output ([#117](https://github.com/NevaMind-AI/memU/issues/117)) ([65ef7c6](https://github.com/NevaMind-AI/memU/commit/65ef7c6a497047f0f86938cf77ee4602a630216b))
* postgres model definitions & database initialization ([#124](https://github.com/NevaMind-AI/memU/issues/124)) ([7d5e0cb](https://github.com/NevaMind-AI/memU/commit/7d5e0cb02837a6e2071d3c3344ef6dad613f9a43))


### Documentation

* Add memU-experiment link to README ([#119](https://github.com/NevaMind-AI/memU/issues/119)) ([2d908e1](https://github.com/NevaMind-AI/memU/commit/2d908e17ee2e15b95d4eb2f35dd09f924d57f8cf))
* clearer introduction and new agent examples ([#115](https://github.com/NevaMind-AI/memU/issues/115)) ([da27875](https://github.com/NevaMind-AI/memU/commit/da2787536d91490f7a96a0c7379abd1ad1c6d9ac))

## [0.7.0](https://github.com/NevaMind-AI/memU/compare/v0.6.0...v0.7.0) (2025-12-05)


### Features

* add user model and user context store ([#113](https://github.com/NevaMind-AI/memU/issues/113)) ([7c37fb1](https://github.com/NevaMind-AI/memU/commit/7c37fb166b0a85bf7c89d0b109cbaa882fa80064))
* add valcano model support ([#110](https://github.com/NevaMind-AI/memU/issues/110)) ([704c302](https://github.com/NevaMind-AI/memU/commit/704c3024946e8d4a1d1b13ffef33126bb68bd9c4))


### Bug Fixes

* resource caption miss problem ([#111](https://github.com/NevaMind-AI/memU/issues/111)) ([85586f5](https://github.com/NevaMind-AI/memU/commit/85586f52d6bd6355ae440ad06d8cc6779c689ce8))


### Documentation

* fix example file path ([#105](https://github.com/NevaMind-AI/memU/issues/105)) ([21aad6a](https://github.com/NevaMind-AI/memU/commit/21aad6a7f070e7666ac6a41c91980a4fa9696918))
* fix readme test case ([#107](https://github.com/NevaMind-AI/memU/issues/107)) ([228306c](https://github.com/NevaMind-AI/memU/commit/228306c897402c633f57c7aa31e8c6cd4e995d5d))
* highlight OpenAI key ([#106](https://github.com/NevaMind-AI/memU/issues/106)) ([5b6ce54](https://github.com/NevaMind-AI/memU/commit/5b6ce54def5aa7743a85bec629da65bfa9d8333b))
* highlight readme openai key ([#103](https://github.com/NevaMind-AI/memU/issues/103)) ([fc4154a](https://github.com/NevaMind-AI/memU/commit/fc4154a707220ced4359e7296218451c43cf0681))

## [0.6.0](https://github.com/NevaMind-AI/memU/compare/v0.5.0...v0.6.0) (2025-11-20)


### Features

* retrieve args change conversation_history to queries ([#98](https://github.com/NevaMind-AI/memU/issues/98)) ([6370c6e](https://github.com/NevaMind-AI/memU/commit/6370c6e968c9d0922120bf2a41e8b4206bab87cb))

## [0.5.0](https://github.com/NevaMind-AI/memU/compare/v0.4.0...v0.5.0) (2025-11-18)


### Features

* add usecase examples ([#94](https://github.com/NevaMind-AI/memU/issues/94)) ([47b5b39](https://github.com/NevaMind-AI/memU/commit/47b5b390e065ccac1cd2173fa2d6c41549e01063))

## [0.4.0](https://github.com/NevaMind-AI/memU/compare/v0.3.0...v0.4.0) (2025-11-18)


### Features

* add non-RAG retrieve solution ([#84](https://github.com/NevaMind-AI/memU/issues/84)) ([fb96e54](https://github.com/NevaMind-AI/memU/commit/fb96e5405f1c0e3477929b7d9874e624dd0453cb))


### Bug Fixes

* correct binary name after making a release ([#91](https://github.com/NevaMind-AI/memU/issues/91)) ([0fa721a](https://github.com/NevaMind-AI/memU/commit/0fa721aaae294c6f230221af11084a0a6c1f478d))


### Documentation

* fix several words in README ([#89](https://github.com/NevaMind-AI/memU/issues/89)) ([1e3baf9](https://github.com/NevaMind-AI/memU/commit/1e3baf92d5a08ec51a7eda3249bbd4b40530f56c))
* revise README for clarity and roadmap inclusion ([#86](https://github.com/NevaMind-AI/memU/issues/86)) ([2235b09](https://github.com/NevaMind-AI/memU/commit/2235b099acc7e92ac52b2613fa731f85259d58fd))
* update images and refine punctuation in README ([#88](https://github.com/NevaMind-AI/memU/issues/88)) ([cc375e8](https://github.com/NevaMind-AI/memU/commit/cc375e89a9b49bda0b7057eee696d74c4c1d9cee))

## [0.3.0](https://github.com/NevaMind-AI/memU/compare/v0.2.2...v0.3.0) (2025-11-17)


### Features

* initialize the memorize and retrieve workflows with the new 3-layer architecture ([#81](https://github.com/NevaMind-AI/memU/issues/81)) ([4a2e86c](https://github.com/NevaMind-AI/memU/commit/4a2e86c0e8bc3e50c82c4fde33d07ad741c8a65e))


### Documentation

* add German translation for README ([f6d6ab1](https://github.com/NevaMind-AI/memU/commit/f6d6ab1a51b76bd4312542422aebac89410b8da9))
* add German translation for README ([76c3fc4](https://github.com/NevaMind-AI/memU/commit/76c3fc4227a8e349fbcf1e5bfec29d68e984ff7a))
