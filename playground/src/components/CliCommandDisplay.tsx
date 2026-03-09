import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { selectExporterByEndpoint } from "@/store/capabilities/capabilitiesSlice";
import { selectExportFormat, selectExportResult } from "@/store/export/exportSlice";
import { useAppSelector } from "@/store/hooks";
import { selectSourceFiles } from "@/store/schema/schemaSlice";
import { selectSelectionQuery } from "@/store/selection/selectionSlice";
import { buildCliCommand, buildComposeCommand } from "@/utils/buildCliCommand";

type CliCommandDisplayProps =
	| { type: "export"; selectedExporterEndpoint: string }
	| { type: "compose" };

export function CliCommandDisplay(props: CliCommandDisplayProps) {
	const [copied, setCopied] = useState(false);
	const schemas = useAppSelector(selectSourceFiles);
	const selectionQuery = useAppSelector(selectSelectionQuery);
	const exporter = useAppSelector((state) =>
		props.type === "export"
			? selectExporterByEndpoint(state, props.selectedExporterEndpoint)
			: null,
	);
	const exportResult = useAppSelector((state) => {
		if (!exporter) {
			return "";
		}

		return selectExportResult(state, exporter.endpoint);
	});
	const exportFormat = useAppSelector((state) => {
		if (!exporter) {
			return "text";
		}

		return selectExportFormat(state, exporter.endpoint);
	});

	let command: string | null = null;

	if (props.type === "export") {
		if (!exporter) {
			return null;
		}
		const outputFormat = exportResult ? exportFormat : undefined;
		command = buildCliCommand(exporter, schemas, selectionQuery, outputFormat);
	} else if (props.type === "compose") {
		command = buildComposeCommand(schemas);
	}

	const handleCopy = async () => {
		try {
			await navigator.clipboard.writeText(command || "");
			setCopied(true);
			setTimeout(() => setCopied(false), 2000);
		} catch {
			const textarea = document.createElement("textarea");
			textarea.value = command || "";
			textarea.style.position = "fixed";
			textarea.style.opacity = "0";
			document.body.appendChild(textarea);
			textarea.select();
			document.execCommand("copy");
			document.body.removeChild(textarea);
			setCopied(true);
			setTimeout(() => setCopied(false), 2000);
		}
	};

	let buttonIcon: React.ReactNode;
	if (copied) {
		buttonIcon = <Check className="h-4 w-4 text-green-600" />;
	} else {
		buttonIcon = <Copy className="h-4 w-4" />;
	}

	return (
		<div className="space-y-2">
			{command && (
				<div className="flex gap-2 items-center">
					<pre className="font-mono text-sm bg-muted p-3 rounded-md overflow-x-auto flex-1">
						{command}
					</pre>
					<Button
						variant="ghost"
						size="icon"
						onClick={handleCopy}
						title={copied ? "Copied!" : "Copy command"}
					>
						{buttonIcon}
					</Button>
				</div>
			)}
			<a
				href="https://covesa.github.io/s2dm/docs/tools/command-line-interface-cli/"
				target="_blank"
				rel="noopener noreferrer"
				className="text-sm text-muted-foreground hover:text-foreground inline-block"
			>
				Learn more about CLI commands →
			</a>
		</div>
	);
}
