import type { Monaco } from "@monaco-editor/react";
import Editor from "@monaco-editor/react";
import { Button } from "@shared-ui/components/button";
import { Download, Maximize } from "lucide-react";
import { useCallback, useState } from "react";
import { TextEditorDialog } from "@/components/TextEditorDialog";
import { useMonacoTheme } from "@/hooks/useMonacoTheme";
import { registerTurtle } from "@/language-support/turtleMonaco";
import { downloadTextFile } from "@/utils/download";
import { resolveMonacoLanguage } from "@/utils/monacoLanguage";

type TextEditorProps = {
	language: string;
	value: string;
	onChange?: (value: string) => void;
	readOnly?: boolean;
	fullscreenTitle?: string;
	fileName?: string;
	isExpandable?: boolean;
	/**
	 * The name of the editor's document. Each name keeps its own scroll and
	 * cursor position. The fullscreen view uses the name with a "fullscreen/"
	 * prefix. Without a name, the editor keeps one document for all values.
	 */
	path?: string;
};

export function TextEditor({
	language,
	value,
	onChange,
	readOnly = false,
	fullscreenTitle,
	fileName,
	isExpandable = true,
	path,
}: TextEditorProps) {
	const theme = useMonacoTheme();
	const [isFullscreen, setIsFullscreen] = useState(false);
	const monacoLanguage = resolveMonacoLanguage(language);

	let fullscreenPath: string | undefined;
	if (path !== undefined) {
		fullscreenPath = `fullscreen/${path}`;
	}

	const handleEditorBeforeMount = useCallback((monaco: Monaco) => {
		registerTurtle(monaco);
	}, []);

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

	const renderEditor = (editorPath: string | undefined) => (
		<Editor
			beforeMount={handleEditorBeforeMount}
			language={monacoLanguage}
			path={editorPath}
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

	const renderEditorWithButtons = (
		showMaximize: boolean,
		editorPath: string | undefined,
	) => (
		<div className="group relative h-full w-full overflow-hidden">
			{renderEditor(editorPath)}
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
			{renderEditorWithButtons(true, path)}

			<TextEditorDialog
				open={isFullscreen}
				onOpenChange={setIsFullscreen}
				title={fullscreenTitle || "Editor"}
			>
				{renderEditorWithButtons(false, fullscreenPath)}
			</TextEditorDialog>
		</>
	);
}
