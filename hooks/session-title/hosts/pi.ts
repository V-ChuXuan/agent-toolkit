import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const TOOL_NAME = "set_session_title";
const CORE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "session_title.py");
const PYTHON = process.env.SESSION_TITLE_PYTHON || (process.platform === "win32" ? "python" : "python3");
const CORE_TIMEOUT_MS = 5_000;
const MAX_CORE_OUTPUT = 64 * 1024;

// TypeBox accepts plain JSON Schema; avoid a runtime dependency outside the Pi package.
const TITLE_PARAMS = {
	type: "object",
	properties: {
		title: {
			type: "string",
			description: "One-line session title in the requested module | ongoing goal format.",
		},
	},
	required: ["title"],
	additionalProperties: false,
} as const;

function runCore(command: "prepare" | "validate", payload: Record<string, unknown>): Promise<any> {
	return new Promise((resolve) => {
		const child = spawn(PYTHON, ["-B", "-X", "utf8", CORE, command], {
			stdio: ["pipe", "pipe", "ignore"],
			windowsHide: true,
		});
		let stdout = "";
		let settled = false;
		let timer: ReturnType<typeof setTimeout> | undefined;

		const finish = (value: any) => {
			if (settled) {
				return;
			}
			settled = true;
			if (timer) {
				clearTimeout(timer);
			}
			if (!child.killed) {
				child.kill();
			}
			resolve(value);
		};

		timer = setTimeout(() => finish(null), CORE_TIMEOUT_MS);
		child.on("error", () => finish(null));
		child.stdout.setEncoding("utf8");
		child.stdout.on("data", (chunk: string) => {
			stdout += chunk;
			if (Buffer.byteLength(stdout, "utf8") > MAX_CORE_OUTPUT) {
				finish(null);
			}
		});
		child.on("close", (code) => {
			if (code !== 0) {
				finish(null);
				return;
			}
			try {
				finish(JSON.parse(stdout));
			} catch {
				finish(null);
			}
		});
		child.stdin.on("error", () => finish(null));
		child.stdin.end(JSON.stringify(payload));
	});
}

function taskContext(result: any): string {
	const context = result?.context ?? {};
	const terms = Array.isArray(context.domain_terms) ? context.domain_terms.join(", ") : "";
	const lines = [
		"<session-title-task>",
		`Scope kind: ${context.kind_hint ?? ""}`,
		`Scope object: ${context.object_hint ?? ""}`,
		`Relative path: ${context.relative_path ?? ""}`,
		`Format: ${context.format ?? "模块名 | 持续目标"}`,
		`Target chars: ${context.target_chars ?? 24}`,
		`Soft max chars: ${context.soft_max_chars ?? 24}`,
	];
	if (terms) {
		lines.push(`Domain terms: ${terms}`);
	}
	lines.push(`Native tool: ${TOOL_NAME}`, String(result?.instruction ?? ""), "</session-title-task>");
	return lines.join("\n");
}

function activateTitleTool(pi: ExtensionAPI): void {
	try {
		const active = pi.getActiveTools();
		if (!active.includes(TOOL_NAME)) {
			pi.setActiveTools([...active, TOOL_NAME]);
		}
	} catch {
		// Tool activation is best-effort; the title request remains a valid context hint.
	}
}

function textResult(text: string, details: Record<string, unknown>) {
	return {
		content: [{ type: "text" as const, text }],
		details,
	};
}

export default function sessionTitleExtension(pi: ExtensionAPI): void {
	pi.registerTool({
		name: TOOL_NAME,
		label: "Set Session Title",
		description:
			"Set the current session display title once, using the validated module | ongoing goal format.",
		promptSnippet: "Set the validated session display title when the session-title task requests it.",
		parameters: TITLE_PARAMS,
		defaultActive: false,
		async execute(_toolCallId, params) {
			const validation = await runCore("validate", { title: params?.title });
			if (!validation?.valid) {
				return textResult("Session title rejected; keep the existing title.", {
					status: "invalid",
					reason: validation?.reason ?? "validation_failed",
				});
			}

			try {
				if (pi.getSessionName()?.trim()) {
					return textResult("Session title unchanged because a user title already exists.", {
						status: "manual_title",
					});
				}
				pi.setSessionName(validation.title);
				if (pi.getSessionName() !== validation.title) {
					return textResult("Session title write could not be verified.", {
						status: "readback_failed",
					});
				}
			} catch {
				return textResult("Session title write failed safely.", {
					status: "write_failed",
				});
			}

			return textResult("Session title updated and read back.", {
				status: "renamed",
			});
		},
	});

	pi.on("before_agent_start", async (event, ctx) => {
		if (event.messageType !== "user") {
			return;
		}

		let currentTitle: string | undefined;
		try {
			currentTitle = pi.getSessionName();
		} catch {
			return;
		}
		if (currentTitle?.trim()) {
			return;
		}

		let sessionId: string;
		try {
			sessionId = ctx.sessionManager.getSessionId();
		} catch {
			return;
		}
		if (!sessionId) {
			return;
		}

		const result = await runCore("prepare", {
			host: "pi",
			session_id: sessionId,
			cwd: ctx.cwd,
			prompt: event.prompt,
			current_title: currentTitle ?? null,
		});
		if (result?.action !== "request_title") {
			return;
		}

		activateTitleTool(pi);
		return {
			message: {
				customType: "session-title-task",
				content: taskContext(result),
				display: false,
			},
		};
	});
}
