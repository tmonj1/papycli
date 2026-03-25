# Changelog

## [0.13.1](https://github.com/tmonj1/papycli/compare/v0.13.0...v0.13.1) (2026-03-25)


### Documentation

* add GitHub Pages documentation site with MkDocs Material ([7220f4e](https://github.com/tmonj1/papycli/commit/7220f4e9bfe2f4d2ea213f49670b69ac9349129f))
* GitHub Pages ドキュメントサイトの追加 ([#139](https://github.com/tmonj1/papycli/issues/139)) ([7220f4e](https://github.com/tmonj1/papycli/commit/7220f4e9bfe2f4d2ea213f49670b69ac9349129f))
* README および design_doc.md を最新の実装に追従させる ([#137](https://github.com/tmonj1/papycli/issues/137)) ([58712a2](https://github.com/tmonj1/papycli/commit/58712a28b25159bc74ee9652eeb0b452e8e2ea25))

## [0.13.0](https://github.com/tmonj1/papycli/compare/v0.12.2...v0.13.0) (2026-03-24)


### Features

* ResponseContext に schema プロパティを追加する ([#134](https://github.com/tmonj1/papycli/issues/134)) ([684b5c4](https://github.com/tmonj1/papycli/commit/684b5c415b0d937ce4d063381e4328ab78e0b896))

## [0.12.2](https://github.com/tmonj1/papycli/compare/v0.12.1...v0.12.2) (2026-03-22)


### Bug Fixes

* **test:** unittest の PETSTORE_PATH のディレクトリ階層を修正 ([40c9a7c](https://github.com/tmonj1/papycli/commit/40c9a7ceb6bf6d9b84b44d6b4493142e1faee7c9))
* **test:** unittest の PETSTORE_PATH のディレクトリ階層を修正 ([e38d220](https://github.com/tmonj1/papycli/commit/e38d220fbc48989407ff23ddc508fa2cf7d1e20f)), closes [#129](https://github.com/tmonj1/papycli/issues/129)

## [0.12.1](https://github.com/tmonj1/papycli/compare/v0.12.0...v0.12.1) (2026-03-21)


### Bug Fixes

* **ci:** --http-status を終了コード判定に置き換え ([784e77e](https://github.com/tmonj1/papycli/commit/784e77ebbbff2f5652b0eb156cc54ccd023b82a3))
* **ci:** PRへの追加コミット時にCopilot再レビューが実行されない問題を修正 ([f9ecfaf](https://github.com/tmonj1/papycli/commit/f9ecfaf76f6cd2d7c838ea2e17a0006d8ed2c4cb))
* **ci:** PRへの追加コミット時にCopilot再レビューが実行されない問題を修正 ([2bc69ab](https://github.com/tmonj1/papycli/commit/2bc69ab2554e1963a8b419accd2c998605116ec6)), closes [#121](https://github.com/tmonj1/papycli/issues/121)
* **ci:** コラボレーター確認ステップを追加 ([140a974](https://github.com/tmonj1/papycli/commit/140a974dbffbecf87812c6f44608c13e77d21a2b))
* papycli spec のヘルプテキストをユーザー向けに改善 ([1eb7efc](https://github.com/tmonj1/papycli/commit/1eb7efca444a961d7cbe7df7654ce0df42f629a2))
* papycli spec のヘルプテキストをユーザー向けに改善 ([#124](https://github.com/tmonj1/papycli/issues/124)) ([ff64f44](https://github.com/tmonj1/papycli/commit/ff64f440f4f2079fdf6266b6ef3d22a2e8925fcf))


### Documentation

* README にユニットテストと統合テストの実行方法を追加する ([917d3dc](https://github.com/tmonj1/papycli/commit/917d3dc76f5a3681375c9e47ebfcbdb525fc7f61))
* README にユニットテストと統合テストの実行方法を追加する ([b4e6100](https://github.com/tmonj1/papycli/commit/b4e61005779c5885dfa11e442834c1ad77982b65)), closes [#127](https://github.com/tmonj1/papycli/issues/127)

## [0.12.0](https://github.com/tmonj1/papycli/compare/v0.11.0...v0.12.0) (2026-03-19)


### Features

* RequestContext に spec 属性を追加してAPIオペレーション仕様を格納する ([d259f14](https://github.com/tmonj1/papycli/commit/d259f1408e8e2baaacfb5f727cb9391ffddb5f19))
* RequestContext に spec 属性を追加してAPIオペレーション仕様を格納する ([#113](https://github.com/tmonj1/papycli/issues/113)) ([230231e](https://github.com/tmonj1/papycli/commit/230231eae044a78cd40b9b5b2ec4837972681783))


### Bug Fixes

* spec フィールドの deepcopy によるリーク防止と is→== テスト修正 ([6289572](https://github.com/tmonj1/papycli/commit/628957251eb6d4e7f696b13bef2a689f90550fee))
* spec を apply_response_filters の request_body パターンで復元・保護 ([2629db6](https://github.com/tmonj1/papycli/commit/2629db6a0714c7ae8bdd624cfa3d35fdfe3a6a4b))

## [0.11.0](https://github.com/tmonj1/papycli/compare/v0.10.1...v0.11.0) (2026-03-18)


### Features

* config alias サブコマンドの追加 ([01931fd](https://github.com/tmonj1/papycli/commit/01931fd16fc1b5d932ed7f756b637fba3bf27be9))
* config alias サブコマンドの追加 ([#110](https://github.com/tmonj1/papycli/issues/110)) ([2ae48a3](https://github.com/tmonj1/papycli/commit/2ae48a3317c3a0686375d5172e4dfd118f306779))

## [0.10.1](https://github.com/tmonj1/papycli/compare/v0.10.0...v0.10.1) (2026-03-17)


### Bug Fixes

* release-please.yml に publish ジョブを追加して PyPI 公開を修正 ([a77cc0f](https://github.com/tmonj1/papycli/commit/a77cc0fbf7ee498cc7fcd4b6f9096c5a9be19746))
* release-please.yml に publish ジョブを追加して PyPI 公開を修正 ([#105](https://github.com/tmonj1/papycli/issues/105)) ([9ffc692](https://github.com/tmonj1/papycli/commit/9ffc692f1c9f5e9e0cdef974129f70a2284c4af1))
* タグ形式を papycli-vX.Y.Z から vX.Y.Z に変更 ([802dc53](https://github.com/tmonj1/papycli/commit/802dc53b92ff753721b7109bb40fbc79182df18e))

## [0.10.0](https://github.com/tmonj1/papycli/compare/papycli-v0.9.0...papycli-v0.10.0) (2026-03-17)


### Features

* --check オプションの追加（必須パラメータ・型チェック、警告のみ） ([8e27fc2](https://github.com/tmonj1/papycli/commit/8e27fc293d028779516c142ac43a283b791ea567))
* --check-strict オプションの追加（チェック失敗時はリクエスト送信しない） ([edb49b5](https://github.com/tmonj1/papycli/commit/edb49b59319c21cbfdc0c7596dc5eb44461049f2))
* --response-check にステータスコード照合機能を追加 ([dbdcbca](https://github.com/tmonj1/papycli/commit/dbdcbcaf93f618ca31edab6e48ad559198bf80aa))
* add config remove subcommand ([321ba6f](https://github.com/tmonj1/papycli/commit/321ba6f6e6ad95c161174b0bdeff95775c9b6075))
* add GitHub Actions release workflow ([2f153d4](https://github.com/tmonj1/papycli/commit/2f153d4151c0688995682b6efa2a308071c2e402))
* add request filter plugin mechanism via entry point group ([34a6557](https://github.com/tmonj1/papycli/commit/34a6557dc0a49c406ffc274bb1fe96968bede192)), closes [#46](https://github.com/tmonj1/papycli/issues/46)
* **api:** --response-check オプションでレスポンスを OpenAPI スキーマに照合する ([9e759f9](https://github.com/tmonj1/papycli/commit/9e759f9d8f7460124ffc1fff90261ea2384a36a2))
* **api:** --response-check オプションでレスポンスを OpenAPI スキーマに照合する ([7b1edae](https://github.com/tmonj1/papycli/commit/7b1edaeaa714134139ff96a20e749a60c731083a)), closes [#77](https://github.com/tmonj1/papycli/issues/77)
* bash completion fallback to file paths after config add ([abb03a6](https://github.com/tmonj1/papycli/commit/abb03a683ce6e695c260c176a8d2e72c7b4fe806))
* bash completion fallback to file paths after config add ([a1d5721](https://github.com/tmonj1/papycli/commit/a1d5721d2bbf7146ab333d4a1056a38e662333e2))
* **check:** add --check option to method commands ([8478d9f](https://github.com/tmonj1/papycli/commit/8478d9fe0064107a73833d72d3d83d1a0b883033))
* **checker:** add request validation module for --check option ([0525903](https://github.com/tmonj1/papycli/commit/05259030ab5d8aaadff703740f394b90bd3aec05))
* **ci:** generate AI release notes via GitHub Models on release ([fb3be43](https://github.com/tmonj1/papycli/commit/fb3be43221a2b2f306e62cd693c1e8986cc9f483)), closes [#39](https://github.com/tmonj1/papycli/issues/39)
* **ci:** GitHub Release に AI 生成リリースノートを追加する ([046405b](https://github.com/tmonj1/papycli/commit/046405bcb1873f05b4619001c30193ccb6f299b3))
* complete API names for config remove / config use ([c552b51](https://github.com/tmonj1/papycli/commit/c552b51c99ed18ea07a7f4af9a99a5f396c4ff75)), closes [#43](https://github.com/tmonj1/papycli/issues/43)
* **completion:** add tab completion for spec command ([f501753](https://github.com/tmonj1/papycli/commit/f50175397704bdf18af29509d8645d9abfb83ffa))
* **completion:** add tab completion for summary command ([20a363a](https://github.com/tmonj1/papycli/commit/20a363a8c01a186ee7fd530fd5d96cfb9fc6dae1))
* **completion:** add tab completion for summary command ([3913d81](https://github.com/tmonj1/papycli/commit/3913d819d0875e6d5cb23ef9fa8ee42c66950e84)), closes [#29](https://github.com/tmonj1/papycli/issues/29)
* **completion:** exclude already-used param names from -p/-q candidates ([98c9595](https://github.com/tmonj1/papycli/commit/98c95956e81880dc297c5b16c9826f8c3a875c9e))
* **completion:** exclude already-used param names from -p/-q candidates ([bc3ad90](https://github.com/tmonj1/papycli/commit/bc3ad9011f507aa5b4711872ec1c2060291d0c0f)), closes [#67](https://github.com/tmonj1/papycli/issues/67)
* config remove / config use のタブ補完で登録済み API 名を候補表示する ([a1d006e](https://github.com/tmonj1/papycli/commit/a1d006e3d6d51ba668fd74f056ce5262d7759788))
* **examples:** add request filter plugin example (papycli-debug-filter) ([ab9aa4b](https://github.com/tmonj1/papycli/commit/ab9aa4b3b5a9a733f4ca4e84e247470f46730bac)), closes [#53](https://github.com/tmonj1/papycli/issues/53)
* **examples:** add response filter plugin example (papycli-debug-response-filter) ([50f4479](https://github.com/tmonj1/papycli/commit/50f4479c9e63011a7f9e8c87eadfcb711920c5bc))
* **examples:** add response filter plugin example (papycli-debug-response-filter) ([890e18e](https://github.com/tmonj1/papycli/commit/890e18e635c24910d8ac15b67087179f17128d9d)), closes [#57](https://github.com/tmonj1/papycli/issues/57)
* **examples:** リクエストフィルタープラグインの実装例を追加する ([4538d64](https://github.com/tmonj1/papycli/commit/4538d64066374349e7849e46b6703020c9c2d377))
* GitHub Actions release workflow (GitHub Release + PyPI) ([91cc915](https://github.com/tmonj1/papycli/commit/91cc9159064977e69a5de43212f780889a16115a))
* hide -q/-p/-d in completion when endpoint has no matching params ([4dab346](https://github.com/tmonj1/papycli/commit/4dab346da9376503b43210bf8ba2309df36e50e9))
* hide -q/-p/-d options when endpoint has no matching parameters ([3497cdb](https://github.com/tmonj1/papycli/commit/3497cdb975f6a2b6f2e71cfd942babd8ea5195e6))
* hide HTTP status line by default, add --verbose / -v flag ([04a255c](https://github.com/tmonj1/papycli/commit/04a255c6e086bb9d29eb9bb9252cc0e5fc38c194))
* hide HTTP status line by default, add --verbose / -v flag ([dcb31b5](https://github.com/tmonj1/papycli/commit/dcb31b517b652e147fcbb2afe36df53e35033228)), closes [#1](https://github.com/tmonj1/papycli/issues/1)
* i18n — English by default, Japanese when locale is ja ([08c6b5b](https://github.com/tmonj1/papycli/commit/08c6b5b989a49074d41787a13bba1ff2933d7142))
* i18n — English by default, Japanese when locale is ja ([b0edeeb](https://github.com/tmonj1/papycli/commit/b0edeeb1057a5b1d03c2bef223b7c47e56d688a4))
* **M1:** project scaffolding with CLI skeleton ([b7bbf58](https://github.com/tmonj1/papycli/commit/b7bbf583ad49a708fdd6a0afd379d7c8ac176ac2))
* **M2:** add config module with conf file read/write ([dab02d2](https://github.com/tmonj1/papycli/commit/dab02d287041cece36fb4816494a99ff375e67d8))
* **M2:** add init_cmd for spec conversion and apidef persistence ([8d8cb6c](https://github.com/tmonj1/papycli/commit/8d8cb6c3ab3949ff9ab992ba2c3dd29dc53d172b))
* **M2:** add spec_loader with $ref resolution and apidef conversion ([d68de1b](https://github.com/tmonj1/papycli/commit/d68de1bcfd7c9b169bededf3aa668c417573a844))
* **M2:** wire --init / --use / --conf commands in CLI ([0097b22](https://github.com/tmonj1/papycli/commit/0097b220ec4ae3d0478ad42b7af07533188c39e0))
* **M3:** add --check-strict option (abort request on validation failure) ([147c645](https://github.com/tmonj1/papycli/commit/147c645655c6d7af25f5ec502ce8663f115503be)), closes [#33](https://github.com/tmonj1/papycli/issues/33)
* **M3:** add api_call with path matching, param building, HTTP execution ([50af5c5](https://github.com/tmonj1/papycli/commit/50af5c5e7c9ff6b9d5af7de1720586cc11fded8f))
* **M3:** add config log command and request/response logging ([65c01d2](https://github.com/tmonj1/papycli/commit/65c01d24e5356595e2953e47ac28620d2f84d08e))
* **M3:** add config log command and request/response logging ([b728385](https://github.com/tmonj1/papycli/commit/b728385f8eb7ff06f5c681a2483bc166032caa62)), closes [#45](https://github.com/tmonj1/papycli/issues/45)
* **M3:** add config remove subcommand ([e4e288a](https://github.com/tmonj1/papycli/commit/e4e288aee0ac9de89e45af419e39558a358a159b)), closes [#10](https://github.com/tmonj1/papycli/issues/10)
* **M3:** rename config init to config add ([6dc49f2](https://github.com/tmonj1/papycli/commit/6dc49f23493fbe9598bd9c9a4a6c1735acac0969)), closes [#9](https://github.com/tmonj1/papycli/issues/9)
* **M3:** rename config show to config list ([bf8a355](https://github.com/tmonj1/papycli/commit/bf8a3558b6fd150307ef2bf8b16cfa965bce4503)), closes [#11](https://github.com/tmonj1/papycli/issues/11)
* **M3:** wire get/post/put/patch/delete commands in CLI ([d4e98ed](https://github.com/tmonj1/papycli/commit/d4e98edec6fe3c7d9646cf6ee3ef187d22d7bb22))
* **M4:** add summary module for endpoint listing ([e9aec2b](https://github.com/tmonj1/papycli/commit/e9aec2bde7231e60d15e524b6324ffa6c8042bbf))
* **M4:** wire summary command and --summary flag on method commands ([6df88e8](https://github.com/tmonj1/papycli/commit/6df88e8f2809c588c7b4b8815589c3f9ab3fcba8))
* **M5:** add completion module with context-aware suggestions ([6587bbd](https://github.com/tmonj1/papycli/commit/6587bbdc5571e44a53242db1677d1dc10a0c3985))
* **M5:** wire completion-script and _complete commands in CLI ([0581c14](https://github.com/tmonj1/papycli/commit/0581c14ca20691594dbc9ab6ca2175b41cc2ddd3))
* **M8:** add response filter plugin mechanism ([b5e6e48](https://github.com/tmonj1/papycli/commit/b5e6e48455b14b5f42fe373a1699ce8b3b265ebe))
* **M8:** add response filter plugin mechanism ([8c4b88e](https://github.com/tmonj1/papycli/commit/8c4b88e395fd0e1bff5a25b3c33ae8fef39b3177)), closes [#55](https://github.com/tmonj1/papycli/issues/55)
* rename config init to config add ([84c446e](https://github.com/tmonj1/papycli/commit/84c446e1b8b0ad09c4b6622e391087fe29e08ae7))
* rename config show to config list ([2a3013d](https://github.com/tmonj1/papycli/commit/2a3013d9b054329ed646a5477ac0510ffb5e090d))
* **response_checker:** --response-check にステータスコード照合機能を追加 ([06b2192](https://github.com/tmonj1/papycli/commit/06b219240878a480d15bffe80e7aec9578bf56c4)), closes [#79](https://github.com/tmonj1/papycli/issues/79)
* ResponseContext にリクエストボディフィールドを追加 ([a9d97f1](https://github.com/tmonj1/papycli/commit/a9d97f1a26468341bc0eae04a16420328ec1f4d1))
* ResponseContext にリクエストボディフィールドを追加 ([#83](https://github.com/tmonj1/papycli/issues/83)) ([0016634](https://github.com/tmonj1/papycli/commit/0016634a2c5c4041787adc33439ec7783274fa83))
* spec サブコマンドの追加 ([8aeb77b](https://github.com/tmonj1/papycli/commit/8aeb77b90829d7d583659c4878a5fff381f58b3b))
* **spec:** add --full option to output full OpenAPI spec ([e1a8493](https://github.com/tmonj1/papycli/commit/e1a849345e2642457a4d347db3789b1b4a379eee))
* **spec:** add --full option to output full OpenAPI spec ([3625142](https://github.com/tmonj1/papycli/commit/3625142e383aaef9adebe5e72394a1619e936641)), closes [#69](https://github.com/tmonj1/papycli/issues/69)
* **spec:** add spec subcommand to display raw apidef ([845c22a](https://github.com/tmonj1/papycli/commit/845c22ae6c70fb72c3e06b6293719bdc9e54f4a3))
* **spec:** allow --full and RESOURCE to be combined ([521b175](https://github.com/tmonj1/papycli/commit/521b1752ddbfbbd57b5c4ad43434f372785cafa3))
* **spec:** allow --full and RESOURCE to be combined ([510237d](https://github.com/tmonj1/papycli/commit/510237df77cd20adb52d30147b8f9afe6862079c)), closes [#73](https://github.com/tmonj1/papycli/issues/73)
* **spec:** include referenced schemas in spec --full &lt;RESOURCE&gt; output ([557ae3a](https://github.com/tmonj1/papycli/commit/557ae3a6621485a0eaef218491668175395cc3dd)), closes [#75](https://github.com/tmonj1/papycli/issues/75)
* **spec:** spec --full &lt;RESOURCE&gt; で参照スキーマを components.schemas に付加する ([23e96f9](https://github.com/tmonj1/papycli/commit/23e96f92b62a5e7382d3f0f41a6829f19efb57a0))
* tab completion for -q and -p parameter names and enum values ([39b9601](https://github.com/tmonj1/papycli/commit/39b960186bdbb3cc978b71095eddea0a20df5ce6))
* zsh completion fallback to file paths after config add ([84f9e50](https://github.com/tmonj1/papycli/commit/84f9e5028fcfb36fab1d2e0299c9cbfb7c0f4755))
* zsh completion fallback to file paths after config add ([08b9716](https://github.com/tmonj1/papycli/commit/08b9716902059a01084b881f521426cc72c2a1a3))
* エントリポイントグループによるリクエストフィルタープラグイン機構を追加 ([e262e21](https://github.com/tmonj1/papycli/commit/e262e218240f28a0aab1960ada8032d4a1bc35e8))
* リクエストフィルター適用後の値もログに出力する ([dfd1769](https://github.com/tmonj1/papycli/commit/dfd1769b5fd05fac9eb5935aa05c059706106835))
* リクエストフィルター適用後の値もログに出力する ([d23e79e](https://github.com/tmonj1/papycli/commit/d23e79e899ce1e70f2bc9beb732104a78543b91e)), closes [#63](https://github.com/tmonj1/papycli/issues/63)
* リソースパスのインラインクエリ文字列をサポート ([269e3f6](https://github.com/tmonj1/papycli/commit/269e3f6f9c00549c88afc78b570b3fcf5bd24fb4))
* リソースパスのインラインクエリ文字列をサポート ([eea8c41](https://github.com/tmonj1/papycli/commit/eea8c41f535c60821f8164b4cfc9f9cd5750e5a4)), closes [#61](https://github.com/tmonj1/papycli/issues/61)
* レスポンスフィルターが None を返した場合に出力とチェーンを中断する ([35d4d40](https://github.com/tmonj1/papycli/commit/35d4d4075ecb34274a50f3aefb4f4c09b11892c0))
* レスポンスフィルターが None を返した場合に出力とチェーンを中断する ([#84](https://github.com/tmonj1/papycli/issues/84)) ([5e6bead](https://github.com/tmonj1/papycli/commit/5e6beadf8a61ffd6182166bfe8616fd1a968d1f2))
* 必須パラメータを先頭に表示し * を付ける（-p / -q 補完） ([243f244](https://github.com/tmonj1/papycli/commit/243f2442187464c11a00524cc82dbbaec484564c))
* 必須パラメータを先頭に表示し * を付ける（-p / -q 補完） ([49a3389](https://github.com/tmonj1/papycli/commit/49a33899ba6e99c21199b7913dd6943b66f77f34)), closes [#93](https://github.com/tmonj1/papycli/issues/93)


### Bug Fixes

* -p オプションで integer / boolean 型の値を正しく JSON 変換する ([de7fcb8](https://github.com/tmonj1/papycli/commit/de7fcb872320d0df654aa951fdbd78781751d8b5))
* || true を 422 専用ハンドリングに置き換える ([cb4a28d](https://github.com/tmonj1/papycli/commit/cb4a28d984423e9beca4ac19b9b932e61159084e))
* 422 エラーの無視条件を「already」メッセージとの組み合わせに絞る ([b9283a0](https://github.com/tmonj1/papycli/commit/b9283a0cd9719f099b8e2497d700a862d4c550d1))
* add helpful hint to config remove empty-registry error ([29332cd](https://github.com/tmonj1/papycli/commit/29332cd94f7c11676fe7901417d1ee7f4374f019))
* address PR [#35](https://github.com/tmonj1/papycli/issues/35) review comments ([dd0e780](https://github.com/tmonj1/papycli/commit/dd0e7805f6fa16510a6f152df9ae7bb52200c92d))
* address review comments — verbose completion and status for errors/empty body ([fc2c0d9](https://github.com/tmonj1/papycli/commit/fc2c0d956ebfd22a842b69a35a031da8c04c8bb0))
* address review comments on config add rename ([5b4f512](https://github.com/tmonj1/papycli/commit/5b4f5124fa3fe84c8a9717388752e29a5db8189f))
* address review comments on config remove ([c0dcc63](https://github.com/tmonj1/papycli/commit/c0dcc63287fb9c571a9347f76551d1ae5fe19087))
* also catch ValueError in body rewrite; always replace Content-Type charset ([8c7389d](https://github.com/tmonj1/papycli/commit/8c7389d9fdb80613ae4100a3e05467a40ef561a3))
* call_api 戻り値型変更に伴う mypy 型エラーを修正 ([aaaa919](https://github.com/tmonj1/papycli/commit/aaaa91939ecfb4134bdf110d7573fe40d02ba66a))
* change RequestContext.query_params to list[tuple[str,str]] to preserve order ([4e6d7bc](https://github.com/tmonj1/papycli/commit/4e6d7bc793a76dfe952d81a0d8bae421928c3779))
* **checker:** address PR review comments ([32bd27b](https://github.com/tmonj1/papycli/commit/32bd27ba0394d18e8009a53a8493f4945532dfe6))
* **checker:** remove --check flag name from warning messages ([0b281f5](https://github.com/tmonj1/papycli/commit/0b281f562b5b500b39a17b262343b5220ad54feb))
* **ci:** address release workflow review comments ([f155dfa](https://github.com/tmonj1/papycli/commit/f155dfa5bfbeed42161d5082ad94f7570ae98091))
* **ci:** enforce Features → Bug Fixes → Maintenance section order ([ba849fb](https://github.com/tmonj1/papycli/commit/ba849fb74dccb38f73f0e8302e6e4a28cb7a5350)), closes [#41](https://github.com/tmonj1/papycli/issues/41)
* **ci:** use --max-count instead of head to avoid SIGPIPE under pipefail ([a2534bf](https://github.com/tmonj1/papycli/commit/a2534bf2035092f991f2bc655684da1ec50797a6))
* **ci:** リリースノートの章の順番を Features → Bug Fixes → Maintenance に固定する ([e4abe87](https://github.com/tmonj1/papycli/commit/e4abe876066b28e400aa2161bdaee36394f511d1))
* coerce -p integer/boolean/number values to correct JSON types ([176fa6b](https://github.com/tmonj1/papycli/commit/176fa6bbdc7dd2780a8228e413bc87f7ed96c6ed)), closes [#44](https://github.com/tmonj1/papycli/issues/44)
* **completion:** force LF-only output in _complete to fix Windows CRLF issue ([51bb803](https://github.com/tmonj1/papycli/commit/51bb803c8a82a0a6a6517cb225771f077cf5b1e6))
* **completion:** force LF-only output in _complete to fix Windows CRLF issue ([f98682a](https://github.com/tmonj1/papycli/commit/f98682add6b378ac2c36b1bc8cc539c1a9517ed6)), closes [#27](https://github.com/tmonj1/papycli/issues/27)
* **completion:** guard against IndexError and remove duplicate test ([6cadc65](https://github.com/tmonj1/papycli/commit/6cadc651b5c35ebcd18f376bd1d7d8dc7010b1e9))
* **completion:** pass words[:current] to _used_param_names to avoid excluding the name being typed ([31ad6f0](https://github.com/tmonj1/papycli/commit/31ad6f02e26927583a73c44b6ad3dd082a50c4f2))
* **completion:** preserve option ordering with filter-based approach ([67d62ba](https://github.com/tmonj1/papycli/commit/67d62baa2ecb0881f541a4e7b34966ce65309a42))
* **completion:** skip empty/flag tokens in _used_param_names; add test for incomplete value ([ca2a6f8](https://github.com/tmonj1/papycli/commit/ca2a6f8da0b51f3a9b5e68baea1506acdfb4df80))
* **completion:** use click binary stream and respect stdout encoding ([2ea4f61](https://github.com/tmonj1/papycli/commit/2ea4f6191a2b27719a7c77292d0dce759f3f9f71))
* concurrency で同一 PR の実行を直列化して TOCTOU を防ぐ ([67d954d](https://github.com/tmonj1/papycli/commit/67d954d037b083113cde1075989f9b810319e17b))
* **config-log:** address review feedback (3 issues) ([095d8d5](https://github.com/tmonj1/papycli/commit/095d8d512ba77b9dae7657073283df386a3e0357))
* **config-log:** address review feedback (5 issues) ([e5a0536](https://github.com/tmonj1/papycli/commit/e5a05363e72ab3d2d92d7133b96b9e851745bd79))
* **config-log:** make _write_log fully best-effort and align timestamp docs ([eaf93d7](https://github.com/tmonj1/papycli/commit/eaf93d7c3105546668ffd2b6a600a2e7375ebb05))
* **config-log:** validate logfile type and add error handling to config log ([ec55661](https://github.com/tmonj1/papycli/commit/ec55661c713af2ebbb65dc618ac64df0413986d0))
* **config:** validate get_default_api() return type ([9c23fda](https://github.com/tmonj1/papycli/commit/9c23fda8516d1bcab5975c1bb8ef0888311c3ac9))
* deep-copy ctx before each filter to prevent leaked in-place mutations ([9d6e897](https://github.com/tmonj1/papycli/commit/9d6e89758dcd4de2861357b3b136b1a1c3b5f68f))
* **examples:** fix pyproject description and handle non-serializable body ([4bfa79a](https://github.com/tmonj1/papycli/commit/4bfa79ac037190cbdc515d578d2be4cd9e690731))
* **examples:** output debug filter to stderr; add production warning ([e321bbe](https://github.com/tmonj1/papycli/commit/e321bbefcc3d7d06ed4be1f6c3da55b17b9feea4))
* **examples:** print response headers in debug response filter ([67b3910](https://github.com/tmonj1/papycli/commit/67b39103ef4b5472df99ab8899b810d9451eb876))
* filter resource completion candidates by HTTP method ([d23c94d](https://github.com/tmonj1/papycli/commit/d23c94d514f1ffc2af4bebb1810ec1bb751c7dfa))
* filter resource completion candidates by HTTP method ([ba874b7](https://github.com/tmonj1/papycli/commit/ba874b7f0ae20a00759cb0d0a16a8c7e7a698ad3))
* filtered セクションの直列化失敗時もログエントリ全体を書き込む ([4172783](https://github.com/tmonj1/papycli/commit/4172783653f9cff2843722a214950b065a330d4a))
* filters が空の場合は早期リターンして deepcopy を省略 ([#83](https://github.com/tmonj1/papycli/issues/83)) ([c4ee682](https://github.com/tmonj1/papycli/commit/c4ee6827e2fcaa055bb0cc3c85b11e48210d7b4c))
* guard against reserved name 'default' in config init and use ([dcdd613](https://github.com/tmonj1/papycli/commit/dcdd6134e9be7f7efd7475a6a558b10e52f92eb3))
* guard words[2] access with len check; clarify get_completions docstring ([75af1df](https://github.com/tmonj1/papycli/commit/75af1dfa1e21931028dc3a9d0279766c7e325b52))
* handle TypeError in body rewrite, update Content-Type charset, fix reason in docs ([4b0cf76](https://github.com/tmonj1/papycli/commit/4b0cf76572c9699ae5da7581439456ad753179eb))
* hermetic integration tests; Content-Type based on body type for rewrites ([09cf927](https://github.com/tmonj1/papycli/commit/09cf9279309f2799dde121f7b7e79e908798c384))
* **i18n:** align Japanese help text for conf command with actual behaviour ([830ba23](https://github.com/tmonj1/papycli/commit/830ba23e56ede9cc4bba20849efdf8600e55ff37))
* JsonValue を TypeAlias で明示的に型エイリアス宣言 ([#83](https://github.com/tmonj1/papycli/issues/83)) ([a067dcc](https://github.com/tmonj1/papycli/commit/a067dcc94ab39df6173d0084a54098f5a88a3a83))
* **logging:** apply review feedback round 5 ([635b833](https://github.com/tmonj1/papycli/commit/635b8333a924c74f2e60e966bdeac64ed3ec0a1c))
* move reserved-name check before init_api() to avoid partial writes ([df7505a](https://github.com/tmonj1/papycli/commit/df7505a411007e90e5b340fbcbee91db29c1d29d))
* name* がそのまま CLI に渡る問題を修正・rstrip を removesuffix に統一・-q テスト追加 ([224ea77](https://github.com/tmonj1/papycli/commit/224ea7707f97911fd249bfa230dffcb5d7b5170f))
* original_request_body を deepcopy で保持 ([#83](https://github.com/tmonj1/papycli/issues/83)) ([c8b5739](https://github.com/tmonj1/papycli/commit/c8b57394cd03396097882f9a92834ef1aacf222e))
* PR [#62](https://github.com/tmonj1/papycli/issues/62) レビュー指摘への対応 ([e78f93b](https://github.com/tmonj1/papycli/commit/e78f93bf00b7d4383d4c3152df7c9805b5cb1415))
* PR [#64](https://github.com/tmonj1/papycli/issues/64) レビュー指摘への対応 ([772eb51](https://github.com/tmonj1/papycli/commit/772eb51769b9eafad9b55b72f50a9159b74730db))
* PR [#64](https://github.com/tmonj1/papycli/issues/64) レビュー指摘への対応（第2弾） ([6126750](https://github.com/tmonj1/papycli/commit/612675005bc9b5079ff23510c91ea0e4cd81bf85))
* preserve extra Content-Type params when updating charset; fix brittle test bytes ([03a74db](https://github.com/tmonj1/papycli/commit/03a74db43d1b5fd96a8b74270b778c7379bff8bb))
* pull_request_target に切り替えてフォーク PR でも書き込み権限を確保する ([2f2be88](https://github.com/tmonj1/papycli/commit/2f2be88bb8b462a11d88eae7001d008343bef08e))
* README.ja.md の -q 説明から句点を削除して表記を統一する ([4cda141](https://github.com/tmonj1/papycli/commit/4cda141173d06e68dfbc13f02df58c5498bc1cab))
* reject reserved key 'default' in `papycli config use` ([164c00d](https://github.com/tmonj1/papycli/commit/164c00d7a5b1c335f1db865c75c1a20a44a9d995))
* release-please PR作成に必要なリポジトリ設定をコメントに追記 ([59c0b43](https://github.com/tmonj1/papycli/commit/59c0b43e442bbc0d95f07e9ce6338e1be8875418))
* release-please PR作成に必要なリポジトリ設定をコメントに追記 ([#102](https://github.com/tmonj1/papycli/issues/102)) ([42b29f6](https://github.com/tmonj1/papycli/commit/42b29f68c23530575a1956a9770c1a3f370e8692))
* remove → add で Copilot レビューを確実に再起動する ([5447122](https://github.com/tmonj1/papycli/commit/544712211a783f553c411ae0b22e40bbc164aa30))
* remove・add 両ステップで stderr をキャプチャして特定エラーのみ無視する ([a25e86a](https://github.com/tmonj1/papycli/commit/a25e86ac7dc3d53c1118308e7c86886dac5e6fa8))
* request_body の deepcopy をループ後に常に適用 ([#83](https://github.com/tmonj1/papycli/issues/83)) ([9df988f](https://github.com/tmonj1/papycli/commit/9df988fd3818730b49f5d393c42adc76aeaf921f))
* request_body の不変性を apply_response_filters() で強制 ([#83](https://github.com/tmonj1/papycli/issues/83)) ([45c79f0](https://github.com/tmonj1/papycli/commit/45c79f0079291d99a0e853b2f6777bd3f1593af6))
* **request_filter:** validate callable before registering loaded filter ([a45acbb](https://github.com/tmonj1/papycli/commit/a45acbbe6a0ff34ef03d39ec5c2269823a489339))
* **response_checker,api_call:** paths型ガード追加・do_response_check契約を明示化 ([c1038ba](https://github.com/tmonj1/papycli/commit/c1038babca18940ae500ff0638297c8a551d2ab7))
* **response_checker,tests:** エラーラベル修正・docstring修正・重複テスト削除 ([7e87844](https://github.com/tmonj1/papycli/commit/7e8784416d770f5f9edc5471282bf33852dd85db))
* **response_checker:** スキーマ形式不正時のクラッシュを防ぐ型ガードを追加 ([828c2b3](https://github.com/tmonj1/papycli/commit/828c2b3b02ed7451c1a1e8d1194a3237c1ae4929))
* **response_checker:** ステータスコード照合のキー正規化・空dict対応 ([2af5c6d](https://github.com/tmonj1/papycli/commit/2af5c6d7421b20dc983131cc5277fbe3aa68a6b0))
* **response_checker:** 不正なスキーマ形式・二重conf読み込みを修正 ([223776b](https://github.com/tmonj1/papycli/commit/223776b12254f3002d71ba055a5a760f910c8bdd))
* **response-check:** +json事前パース対応・$ref解決エラーの安全処理 ([5a62774](https://github.com/tmonj1/papycli/commit/5a627748f8c0bcda5461c824749066360235750e))
* **response-check:** nullのenum検証・+jsonメディアタイプ対応 ([276fbfd](https://github.com/tmonj1/papycli/commit/276fbfdd5ed160890cc0eb40be3418ac42fe77a8))
* **response-check:** null型違反検出・事前パースをfilterのみに限定 ([0594593](https://github.com/tmonj1/papycli/commit/0594593378b7b0ac686d5295ce8410529ecb3beb))
* **response-check:** Path Item $ref解決・レンジ指定小文字対応 ([8c09d3c](https://github.com/tmonj1/papycli/commit/8c09d3c42e6fbda0ff6b2d23b045d4383c3c6f77))
* **response-check:** type 省略・list 型対応とテストの stderr 検証を修正 ([b4233d8](https://github.com/tmonj1/papycli/commit/b4233d874942df9069ac8882c288abc7473a6f85))
* **response-check:** type省略スキーマでの型違反検出・テスト明確化 ([6143990](https://github.com/tmonj1/papycli/commit/6143990224deb0c7770b046e78eefee12f0da054))
* **response-check:** union 型のオブジェクト/配列検証・ルートパス補正・spec 読み込み遅延 ([41ddda0](https://github.com/tmonj1/papycli/commit/41ddda0d290924d762648bcd92c5737e066b9cc1))
* **response-check:** スキーマ確認後にボディパース・テストのstderr互換性向上 ([bec0e55](https://github.com/tmonj1/papycli/commit/bec0e557b7aa44c0f534e78e64b4af7b49f963c4))
* **response-check:** 条件付きボディパース・JSON解析失敗の伝播 ([8c8e67c](https://github.com/tmonj1/papycli/commit/8c8e67c7a43421ebb570cd017ef26fb45c9bc136))
* **response-check:** 範囲ステータス対応・多重パース防止・補完追加・テスト統一 ([973fa35](https://github.com/tmonj1/papycli/commit/973fa3533704122ce597f09af3af37bd2b7bf4fc))
* ResponseFilterFunc の型を ResponseContext | None を返せる形に修正 ([fcaa0a6](https://github.com/tmonj1/papycli/commit/fcaa0a63dedafc11fdfe8963dacb60ac37a39d51))
* show help for `papycli config` with no subcommand; fix docstring ([7c3db15](https://github.com/tmonj1/papycli/commit/7c3db155f8e96d90d6fb90a9a0f23ca4aa5cdad6))
* skip response filter overhead when no filters; set encoding; log pre-filter resp; fix noop test ([3bf8c99](https://github.com/tmonj1/papycli/commit/3bf8c997a7c38ee7215054395322a4b1fd15c331))
* **spec:** _visited を collect_schema_refs の内部変数化し破壊的変更を排除 ([823b46e](https://github.com/tmonj1/papycli/commit/823b46e88ce4665a533639da14dcfcaf60e163c1))
* **spec:** address review comments for --full option ([8812e0a](https://github.com/tmonj1/papycli/commit/8812e0a09ca7bc78fbcf49254c234f3359fb3128))
* **spec:** components/schemas が null の場合の AttributeError を防御 ([bf3fe00](https://github.com/tmonj1/papycli/commit/bf3fe00ecd754057accd6c1304b35c02c53b363d))
* **spec:** delete .spec.json on config remove; clarify --full help text and README ([e60845f](https://github.com/tmonj1/papycli/commit/e60845f5cdeed80d14a0430c4f9e9ffca3799952))
* **spec:** アンエスケープ処理を共通化し非スキーマ内部 ref も走査するよう修正 ([789ae82](https://github.com/tmonj1/papycli/commit/789ae824b6708184f457535b81a9b59f4196d176))
* **spec:** サブパス ref の誤収集と JSON Pointer エスケープ未考慮を修正 ([6034f50](https://github.com/tmonj1/papycli/commit/6034f50e41ae1200fa6fe9869a767a01f4774b9f))
* synchronize 後も Copilot レビューを確実に再リクエストする ([2eb5e68](https://github.com/tmonj1/papycli/commit/2eb5e681c3bd99963407787e13f5cdc611286366))
* synchronize 後も Copilot レビューを確実に再リクエストする ([269c083](https://github.com/tmonj1/papycli/commit/269c0835f373ef2de41097781439d1e339d0eabf)), closes [#91](https://github.com/tmonj1/papycli/issues/91)
* **tests:** correct PETSTORE_PATH in test_init_cmd.py and test_spec_loader.py ([6660839](https://github.com/tmonj1/papycli/commit/66608390897c609a2e66160de9c55e8cc2bc481d))
* **tests:** correct PETSTORE_PATH to examples/petstore/petstore-oas3.json ([051f7d0](https://github.com/tmonj1/papycli/commit/051f7d0a699b2fd861d986dc321975a23290f476))
* **tests:** import順修正・未使用import削除・MagicMockをcastで型付け ([5900356](https://github.com/tmonj1/papycli/commit/590035647380c923a59c8522387f8615e2c77b7a))
* update Content-Length on body rewrite; case-insensitive Content-Type handling ([8deefd6](https://github.com/tmonj1/papycli/commit/8deefd64d12f52087e8d159f428c8d9523110ef3))
* update error messages and docs to use new `papycli config init` command ([51b077c](https://github.com/tmonj1/papycli/commit/51b077cd9c0861a6d5c674950afaf4504b8627f0))
* update error messages in config.py to use config add ([4c0c674](https://github.com/tmonj1/papycli/commit/4c0c674f40c3162551b9283c43f02d6f06ff9285))
* use equality check for body diff and reflect status/reason/headers from response filters ([059b989](https://github.com/tmonj1/papycli/commit/059b9897371694ba3fb1c0f84fc3fdb7334b7405))
* validate filter return type, widen body type, document query_params ordering ([54c3d5e](https://github.com/tmonj1/papycli/commit/54c3d5ecdc06211f394e718756ff2b029e00c2fd))
* エラー判定を HTTP 422 + 特定メッセージの組み合わせに絞る ([6747b49](https://github.com/tmonj1/papycli/commit/6747b49fa9714dc82f78cba5ade9a74a5d0dcad3))
* レビュー依頼済みの場合は --add-reviewer をスキップして冪等にする ([c672fcf](https://github.com/tmonj1/papycli/commit/c672fcf11fd2dc3b877c501a6d7f272679ff18c0))
* 全フィルター失敗時も request_body を deepcopy 済み値で確保 ([#83](https://github.com/tmonj1/papycli/issues/83)) ([f614f90](https://github.com/tmonj1/papycli/commit/f614f9035adebd69322f43fc833070da66490d24))


### Performance Improvements

* **request_filter:** optimize apply_filters snapshot to avoid full deepcopy ([0861ce0](https://github.com/tmonj1/papycli/commit/0861ce0faf25fb64090c2d8b076a391adb4fca69))


### Documentation

* --response-check と --full オプションをドキュメントに追加 ([38d1af5](https://github.com/tmonj1/papycli/commit/38d1af5d91e42d5d776f8b3fd9e5f82615edaf93))
* --response-check と --full をドキュメントに追加 ([#81](https://github.com/tmonj1/papycli/issues/81)) ([59ebdbb](https://github.com/tmonj1/papycli/commit/59ebdbb45ffa23e2ccfdc17b85500ccc86c1cf02))
* add Git repository workflow guidelines to CLAUDE.md ([d71e8b3](https://github.com/tmonj1/papycli/commit/d71e8b3bc951818c96d176df3f81d23328a4fd7b))
* add README.md and CLAUDE.md ([92dc55a](https://github.com/tmonj1/papycli/commit/92dc55ad1fbad68a940386e29412ffebdad85983))
* **examples:** add README.md to response filter plugin example ([e7812b8](https://github.com/tmonj1/papycli/commit/e7812b817f364440fa5452ecebc696d083d34677))
* **examples:** add README.md to response filter plugin example ([1185f45](https://github.com/tmonj1/papycli/commit/1185f458edbe28553cb7a7722d391bd4df9cd53e)), closes [#59](https://github.com/tmonj1/papycli/issues/59)
* fix command syntax and example filenames in README and CLAUDE.md ([88f02a5](https://github.com/tmonj1/papycli/commit/88f02a51499509196d99a41f9cc8cc9998f50a65))
* Git Bash での MSYS_NO_PATHCONV=1 設定を README に追記する ([a604432](https://github.com/tmonj1/papycli/commit/a604432c60f5be581315c685602c5e049a349662))
* Git Bash での MSYS_NO_PATHCONV=1 設定を README に追記する ([1a35757](https://github.com/tmonj1/papycli/commit/1a357579126f3a38ddb5912e1f9c767f06a13b25)), closes [#65](https://github.com/tmonj1/papycli/issues/65)
* remove xapicli references, treat papycli as standalone project ([55a775f](https://github.com/tmonj1/papycli/commit/55a775f6f1dd03e15aaa62083963d6c10bc4da13))
* translate README to English, keep Japanese version as README.ja.md ([afeb098](https://github.com/tmonj1/papycli/commit/afeb098a583d727fb0b8f318ac46d9c21de7d9b0))
* update CLAUDE.md, design_doc.md, README for issues [#9](https://github.com/tmonj1/papycli/issues/9)-[#12](https://github.com/tmonj1/papycli/issues/12) ([865fa18](https://github.com/tmonj1/papycli/commit/865fa188527a7b6206b5e30d8274f40c62d7ab14))
* update CLAUDE.md, design_doc.md, README for issues [#9](https://github.com/tmonj1/papycli/issues/9)-[#12](https://github.com/tmonj1/papycli/issues/12) changes ([69f525d](https://github.com/tmonj1/papycli/commit/69f525d7b8aa7bc215cafe3df254846946635ce1))
* update docs to reflect changes since v0.5.3 ([c4171eb](https://github.com/tmonj1/papycli/commit/c4171eb2ee29782a4949b3e132f0da840edac5de)), closes [#51](https://github.com/tmonj1/papycli/issues/51)
* update docs to reflect post-v0.5.2 features ([8c43b17](https://github.com/tmonj1/papycli/commit/8c43b179f35636e2a6bbae247fd949325674d1cd)), closes [#37](https://github.com/tmonj1/papycli/issues/37)
* v0.5.2 以降の機能追加をドキュメントに反映する ([d92e787](https://github.com/tmonj1/papycli/commit/d92e78714edd11b338c632f95131be05919d5283))
* v0.5.3以降の変更をCLAUDE.md・README・design_doc.mdに反映する ([a38ff97](https://github.com/tmonj1/papycli/commit/a38ff97321de1aea64a0c06a79d343e18e072818))
* v0.8.0 以降の変更をドキュメントに反映する（v0.9.0 リリース前） ([d4ec024](https://github.com/tmonj1/papycli/commit/d4ec0243d6ac3e660468df051248a44f2de8969d))
* v0.8.0 以降の変更をドキュメントに反映する（v0.9.0 リリース前） ([2a5e556](https://github.com/tmonj1/papycli/commit/2a5e5566893c50ed899a709ba0b3baab5b7bde8d)), closes [#98](https://github.com/tmonj1/papycli/issues/98)
* レスポンスフィルターの None 返却によるレスポンス抑制をドキュメントに反映 ([1aa5a75](https://github.com/tmonj1/papycli/commit/1aa5a7516376e643ad899a131c5bff3227ec5629))

## Changelog

All notable changes to this project will be documented in this file.

This file is auto-generated by [release-please](https://github.com/googleapis/release-please).
