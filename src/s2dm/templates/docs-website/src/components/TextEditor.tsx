import BrowserOnly from "@docusaurus/BrowserOnly";
import { useCallback, useState } from "react";
import { TextEditorDialog } from "@/components/TextEditorDialog";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/hooks/useTheme";
import { Download, Maximize } from "lucide-react";

type TextEditorProps = {
	language: string;
	value: string;
	onChange?: (value: string) => void;
	readOnly?: boolean;
	fullscreenTitle?: string;
	fileName?: string;
	isExpandable?: boolean;
};

function downloadTextFile(contents: string, fileName: string): void {
	const url = URL.createObjectURL(new Blob([contents], { type: "text/plain" }));
	const link = document.createElement("a");
	link.href = url;
	link.download = fileName;
	link.click();
	URL.revokeObjectURL(url);
}

export function TextEditor({
	language,
	value,
	onChange,
	readOnly = false,
	fullscreenTitle,
	fileName,
	isExpandable = true,
}: TextEditorProps) {
	const theme = useTheme() === "dark" ? "vs-dark" : "vs";
	const [isFullscreen, setIsFullscreen] = useState(false);

	const handleChange = useCallback(
		(newValue: string | undefined) => {
			if (onChange && newValue !== undefined) {
				onChange(newValue);
			}
		},
		[onChange],
	);

	const handleDownload = useCallback(() => {
		if (!fileName) {
			return;
		}
		downloadTextFile(value, fileName);
	}, [value, fileName]);

	// Monaco reaches for window as it loads, and every page here is prerendered
	// in Node first. BrowserOnly defers the require to the browser, and the
	// bundled copy is registered there too so no editor is fetched from a CDN.
	//
	// `edcore.main` and one language, not the whole package: the package entry
	// adds the TypeScript, JSON, CSS and HTML language services and every other
	// grammar, none of which a SQL box uses. Not `editor.api`, which registers
	// none of the editor's own contributions — no find, suggest, hover, folding.
	const renderEditor = () => (
		<BrowserOnly fallback={<div className="h-full w-full" />}>
			{() => {
				const { default: Editor, loader } = require("@monaco-editor/react");
				const monaco = require("monaco-editor/esm/vs/editor/edcore.main");
				require("monaco-editor/esm/vs/basic-languages/sql/sql.contribution");
				loader.config({ monaco });
				return (
					<Editor
						language={language}
						value={value}
						onChange={readOnly ? undefined : handleChange}
						theme={theme}
						options={{
							readOnly,
							contextmenu: false,
							minimap: { enabled: false },
							fontSize: 14,
							lineNumbers: "on",
							scrollBeyondLastLine: false,
						}}
					/>
				);
			}}
		</BrowserOnly>
	);

	const renderEditorWithButtons = (showMaximize: boolean) => (
		<div className="group relative h-full w-full overflow-hidden">
			{renderEditor()}
			<div className="absolute top-2 right-4 z-10 flex flex-col gap-2">
				{showMaximize && isExpandable && (
					<Button
						type="button"
						variant="outline"
						size="icon"
						className="bg-background/50 hover:bg-background/70 opacity-0 group-hover:opacity-100 transition-opacity"
						onClick={() => setIsFullscreen(true)}
						title="Fullscreen"
					>
						<Maximize className="h-4 w-4" />
					</Button>
				)}
				{fileName && value.trim() && (
					<Button
						type="button"
						variant="outline"
						size="icon"
						className="bg-background/50 hover:bg-background/70 opacity-0 group-hover:opacity-100 transition-opacity"
						onClick={handleDownload}
						title="Download"
					>
						<Download className="h-4 w-4" />
					</Button>
				)}
			</div>
		</div>
	);

	return (
		<>
			{renderEditorWithButtons(true)}

			<TextEditorDialog
				open={isFullscreen}
				onOpenChange={setIsFullscreen}
				title={fullscreenTitle || "Editor"}
			>
				{renderEditorWithButtons(false)}
			</TextEditorDialog>
		</>
	);
}
