# Changelog

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
