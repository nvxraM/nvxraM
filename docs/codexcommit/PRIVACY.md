# Privacy notice

Publisher: **nvxraM**. For privacy questions, contact [freematt438@gmail.com](mailto:freematt438@gmail.com).
Notice URL: [CodexCommit privacy notice](https://github.com/nvxraM/CodexCommit/blob/main/plugin/docs/PRIVACY.md).

CodexCommit processes the tracked changes you include in the Commit tool window to prepare a commit-message draft. Selecting the Generate button sends the source patch and fixed task instructions through your local Codex CLI. No additional review or confirmation dialog opens. Check the selected changes before you use the button. The CLI communicates using its own authentication. This may send filenames, source code, comments, and any personal or secret information present in the patch to the service used by Codex.

Selected `.idea/workspace.xml` files stay checked for your Git commit.
The plugin omits their old, current, and unsaved XML contents from generation, hashes, and size calculations.
With source changes, it sends only this fixed note: "IDE workspace settings also changed. Their contents are excluded."
That note includes no workspace paths or values.
A workspace-only selection uses a fixed local draft without Codex, model detection, or account calls.
Other IDE settings and credential paths remain blocked. Workspace path, revision, selection, link, and regular-file checks still apply.
The plugin does not make your Git commit. Examine workspace settings for private data before you commit them yourself.

The plugin developer does not receive your patch, result, credentials, account details, or usage data through a developer-operated server. There is no developer telemetry endpoint. The plugin does not read or copy authentication files. Executable-path settings are stored in the IDE's normal application settings, independently of your repository. The IDE's own settings sync, local history, diagnostics, and other plugins are outside this plugin's control.

Before source generation, the plugin asks the local Codex CLI for its saved model selection or default model.
This local query does not include source text or start a Codex conversation.
The plugin uses only the reported model for generation. It does not forward other saved CLI instructions or settings.
The CLI may use its normal model metadata service when it resolves a default.

The selected patch is held in memory. Generation uses a private temporary working directory and bounded output. Non-sensitive CLI safety configuration may be written there. The plugin requests ephemeral Codex execution and removes its temporary files after completion. OS paging, crash dumps, a forced termination, malware, and CLI/provider-side storage are outside these controls; secure erasure is not promised. The generated message may subsequently be stored in IDE history or in a Git commit when you choose to commit it.

Filename and content checks reject some obvious credentials and unsupported inputs. They cannot detect all secrets, private data, licenses, or organizational restrictions. Review the complete patch and do not send data you lack permission to disclose.

The CLI may use account quota or incur charges under your chosen service. Provider processing and retention depend on your account, settings, and applicable terms. The plugin cannot promise that data never leaves your computer or that provider-side data is deleted by cancelling a request.

Read the [verification record](VERIFICATION.md) for the tests and remaining limits of each version. This notice does not imply JetBrains Marketplace approval.
