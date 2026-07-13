import type { Monaco } from "@monaco-editor/react";
import Editor from "@monaco-editor/react";
import { Download, Maximize } from "lucide-react";
import { useCallback, useState } from "react";
import { TextEditorDialog } from "@/components/TextEditorDialog";
import { Button } from "@/components/ui/button";
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
};

export function TextEditor({
	language,
	value,
	onChange,
	readOnly = false,
	fullscreenTitle,
	fileName,
	isExpandable = true,
}: TextEditorProps) {
	const theme = useMonacoTheme();
	const [isFullscreen, setIsFullscreen] = useState(false);
	const monacoLanguage = resolveMonacoLanguage(language);

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

	const renderEditor = () => (
		<Editor
			beforeMount={handleEditorBeforeMount}
			language={monacoLanguage}
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
