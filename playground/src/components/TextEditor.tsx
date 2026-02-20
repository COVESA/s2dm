import type { Monaco } from "@monaco-editor/react";
import Editor from "@monaco-editor/react";
import { Download, Maximize } from "lucide-react";
import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
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
};

export function TextEditor({
	language,
	value,
	onChange,
	readOnly = false,
	fullscreenTitle,
	fileName,
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
				{showMaximize && (
					<Button
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

			<Dialog
				open={isFullscreen}
				onOpenChange={(open) => !open && setIsFullscreen(false)}
			>
				<DialogContent className="w-[90vw] h-[90vh] max-w-none sm:max-w-none flex flex-col p-0">
					<DialogHeader className="px-6 py-4 border-b shrink-0">
						<DialogTitle>{fullscreenTitle || "Editor"}</DialogTitle>
					</DialogHeader>
					<div className="flex-1 overflow-hidden">
						{renderEditorWithButtons(false)}
					</div>
				</DialogContent>
			</Dialog>
		</>
	);
}
