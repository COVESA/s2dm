import { Eye } from "lucide-react";
import { useState } from "react";
import { TextEditor } from "@/components/TextEditor";
import { TextEditorDialog } from "@/components/TextEditorDialog";
import { Button } from "@/components/ui/button";
import { selectComposedDependenciesSchema } from "@/store/deps/compose/composeSlice";
import { useAppSelector } from "@/store/hooks";

const DIALOG_TITLE = "Built Dependency Schema";

type BuiltSchemaViewerButtonProps = {
	size?: "icon" | "icon-sm";
};

export function BuiltSchemaViewerButton({
	size = "icon",
}: BuiltSchemaViewerButtonProps) {
	const [open, setOpen] = useState(false);
	const composedSchema = useAppSelector(selectComposedDependenciesSchema);
	const hasBuiltSchema = Boolean(composedSchema?.trim());

	return (
		<>
			<Button
				variant="outline"
				size={size}
				onClick={() => setOpen(true)}
				disabled={!hasBuiltSchema}
				title="View built dependency schema"
			>
				<Eye />
			</Button>
			<TextEditorDialog open={open} onOpenChange={setOpen} title={DIALOG_TITLE}>
				<TextEditor
					language="graphql"
					value={composedSchema ?? ""}
					fullscreenTitle={DIALOG_TITLE}
					fileName="built-dependencies.graphql"
					isExpandable={false}
					readOnly
				/>
			</TextEditorDialog>
		</>
	);
}
