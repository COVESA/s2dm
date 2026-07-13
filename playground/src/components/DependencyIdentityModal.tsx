import { Eye, EyeOff } from "lucide-react";
import { useEffect, useState } from "react";
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
import type {
	DependencyIdentityDraft,
	DependencyIdentityEditableField,
} from "@/types/dependencyIdentity";

type DependencyIdentityModalProps = {
	open: boolean;
	mode: "add" | "edit";
	identity: DependencyIdentityDraft;
	onOpenChange: (open: boolean) => void;
	onSave: (identity: DependencyIdentityDraft) => void;
};

type FieldConfig = {
	field: DependencyIdentityEditableField;
	label: string;
	placeholder: string;
	required?: boolean;
	type?: string;
};

const FIELDS: FieldConfig[] = [
	{ field: "host", label: "Host", placeholder: "github.com", required: true },
	{ field: "scope", label: "Scope", placeholder: "owner/repository" },
	{
		field: "token",
		label: "Token",
		placeholder: "Personal access token",
		required: true,
		type: "password",
	},
];

function validateIdentity(identity: DependencyIdentityDraft): string | null {
	if (!identity.host.trim()) {
		return "Host is required.";
	}

	if (!identity.token.trim()) {
		return "Token is required.";
	}

	return null;
}

export function DependencyIdentityModal({
	open,
	mode,
	identity,
	onOpenChange,
	onSave,
}: DependencyIdentityModalProps) {
	const [draft, setDraft] = useState(identity);
	const [error, setError] = useState("");
	const [showToken, setShowToken] = useState(false);

	useEffect(() => {
		if (!open) {
			return;
		}

		setDraft(identity);
		setError("");
		setShowToken(false);
	}, [identity, open]);

	const title = mode === "add" ? "Add Identity" : "Edit Identity";
	const description =
		mode === "add"
			? "Create a new identity entry and add it to the list."
			: "Edit the selected identity entry.";
	const submitLabel = mode === "add" ? "Add" : "Save";

	const handleFieldChange = (
		field: DependencyIdentityEditableField,
		value: string,
	) => {
		setDraft((currentDraft) => ({
			...currentDraft,
			[field]: value,
		}));
		setError("");
	};

	const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
		event.preventDefault();

		const validationError = validateIdentity(draft);
		if (validationError) {
			setError(validationError);
			return;
		}

		onSave(draft);
	};

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="flex max-h-[90vh] w-[90vw] max-w-2xl flex-col sm:max-w-2xl">
				<DialogHeader>
					<DialogTitle>{title}</DialogTitle>
					<DialogDescription>{description}</DialogDescription>
				</DialogHeader>

				{error && (
					<div className="rounded border border-destructive bg-destructive/10 p-2 text-sm text-destructive">
						{error}
					</div>
				)}

				<form onSubmit={handleSubmit}>
					<div className="space-y-4 py-1">
						{FIELDS.map(({ field, label, placeholder, required, type }) => {
							const inputId = `identity-${field}-${draft.id}`;
							const isSecret = type === "password";
							const effectiveType = isSecret && showToken ? "text" : type;
							return (
								<div key={field} className="space-y-2">
									<FormLabel htmlFor={inputId} showRequired={required}>
										{label}
									</FormLabel>
									<div className="relative">
										<Input
											id={inputId}
											type={effectiveType}
											value={draft[field]}
											onChange={(event) =>
												handleFieldChange(field, event.target.value)
											}
											placeholder={placeholder}
											className={isSecret ? "pr-9" : undefined}
										/>
										{isSecret && (
											<button
												type="button"
												onClick={() => setShowToken((current) => !current)}
												aria-label={
													showToken ? `Hide ${label}` : `Show ${label}`
												}
												aria-pressed={showToken}
												className="absolute inset-y-0 right-0 flex items-center px-2 text-muted-foreground hover:text-foreground"
											>
												{showToken ? (
													<EyeOff className="h-4 w-4" />
												) : (
													<Eye className="h-4 w-4" />
												)}
											</button>
										)}
									</div>
								</div>
							);
						})}
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
