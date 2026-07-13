import { useEffect, useState } from "react";
import { TextEditor } from "@/components/TextEditor";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { FormLabel } from "@/components/ui/form-label";
import { Input } from "@/components/ui/input";
import {
	DEPENDENCY_NAME_PATTERN,
	type DependencyDraft,
	type DependencyEditableField,
} from "@/types/dependency";

type DependencyModalProps = {
	open: boolean;
	mode: "add" | "edit";
	dependency: DependencyDraft;
	onOpenChange: (open: boolean) => void;
	onSave: (dependency: DependencyDraft) => void;
};

type DependencyInputField = Exclude<
	DependencyEditableField,
	"selectionContent"
>;

type FieldConfig = {
	field: DependencyInputField;
	label: string;
	placeholder: string;
	required?: boolean;
	fullWidth?: boolean;
};

const FIELDS: FieldConfig[] = [
	{
		field: "name",
		label: "Name",
		placeholder: "Dependency name",
		required: true,
	},
	{
		field: "version",
		label: "Version",
		placeholder: "1.0.0",
		required: true,
	},
	{
		field: "source",
		label: "Source",
		placeholder: "https://github.com/owner/repository",
		required: true,
		fullWidth: true,
	},
	{
		field: "artifact",
		label: "Artifact",
		placeholder: "schema.graphql",
		required: true,
		fullWidth: true,
	},
];

function getDependencyLabel(
	dependency: DependencyDraft,
	mode: "add" | "edit",
): string {
	if (mode === "add") {
		return "New Dependency";
	}

	return `${dependency.name} ${dependency.version}`;
}

function validateDependency(dependency: DependencyDraft): string | null {
	if (!dependency.name.trim()) {
		return "Name is required.";
	}

	if (!DEPENDENCY_NAME_PATTERN.test(dependency.name.trim())) {
		return "Name must start and end with a letter or digit and may contain only letters, digits, '.', '_', or '-'.";
	}

	if (!dependency.version.trim()) {
		return "Version is required.";
	}

	if (!dependency.source.trim()) {
		return "Source is required.";
	}

	if (!dependency.artifact.trim()) {
		return "Artifact is required.";
	}

	return null;
}

export function DependencyModal({
	open,
	mode,
	dependency,
	onOpenChange,
	onSave,
}: DependencyModalProps) {
	const [draft, setDraft] = useState(dependency);
	const [error, setError] = useState("");

	useEffect(() => {
		if (!open) {
			return;
		}

		setDraft(dependency);
		setError("");
	}, [dependency, open]);

	const dependencyLabel = getDependencyLabel(draft, mode);
	const title = mode === "add" ? "Add Dependency" : "Edit Dependency";
	const description =
		mode === "add"
			? "Create a new dependency entry and add it to the list."
			: "Edit the selected dependency entry.";
	const submitLabel = mode === "add" ? "Add" : "Save";

	const handleFieldChange = (field: DependencyInputField, value: string) => {
		setDraft((currentDraft) => ({
			...currentDraft,
			[field]: value,
		}));
		setError("");
	};

	const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
		event.preventDefault();

		const validationError = validateDependency(draft);
		if (validationError) {
			setError(validationError);
			return;
		}

		onSave(draft);
	};

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="flex max-h-[90vh] w-[90vw] max-w-3xl flex-col sm:max-w-3xl">
				<DialogHeader>
					<DialogTitle>{title}</DialogTitle>
					<DialogDescription>{description}</DialogDescription>
				</DialogHeader>

				{error && (
					<div className="rounded border border-destructive bg-destructive/10 p-2 text-sm text-destructive">
						{dependencyLabel}: {error}
					</div>
				)}

				<form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
					<div className="min-h-0 flex-1 overflow-y-auto pr-1">
						<div className="space-y-4">
							<div className="grid gap-4 md:grid-cols-2">
								{FIELDS.map(
									({ field, label, placeholder, required, fullWidth }) => {
										const inputId = `dependency-${field}-${draft.id}`;
										return (
											<div
												key={field}
												className={
													fullWidth ? "space-y-2 md:col-span-2" : "space-y-2"
												}
											>
												<FormLabel htmlFor={inputId} showRequired={required}>
													{label}
												</FormLabel>
												<Input
													id={inputId}
													value={draft[field]}
													onChange={(event) =>
														handleFieldChange(field, event.target.value)
													}
													placeholder={placeholder}
												/>
											</div>
										);
									},
								)}
							</div>

							<div className="space-y-2">
								<FormLabel>Selection</FormLabel>
								<div className="h-48 overflow-hidden rounded-md border">
									<TextEditor
										language="graphql"
										value={draft.selectionContent ?? ""}
										fullscreenTitle={`${dependencyLabel} Selection`}
										fileName={`${draft.name || "dependency"}-selection.graphql`}
										readOnly
									/>
								</div>
							</div>
						</div>
					</div>

					<DialogFooter className="mt-6">
						<Button
							type="button"
							variant="outline"
							onClick={() => onOpenChange(false)}
						>
							Cancel
						</Button>
						<Button type="submit">{submitLabel}</Button>
					</DialogFooter>
				</form>
			</DialogContent>
		</Dialog>
	);
}
