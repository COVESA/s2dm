import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { isValidUrl } from "@/utils/validation";

type AddUrlDialogProps = {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	onAdd: (url: string) => void;
};

export function AddUrlDialog({ open, onOpenChange, onAdd }: AddUrlDialogProps) {
	const [urlInput, setUrlInput] = useState("");
	const [urlError, setUrlError] = useState("");

	useEffect(() => {
		if (open) {
			setUrlInput("");
			setUrlError("");
		}
	}, [open]);

	const handleConfirm = useCallback(() => {
		const trimmed = urlInput.trim();
		if (!trimmed) {
			setUrlError("URL is required");
			return;
		}

		if (!isValidUrl(urlInput)) {
			setUrlError("Please enter a valid URL");
			return;
		}

		onAdd(urlInput);
		onOpenChange(false);
	}, [urlInput, onAdd, onOpenChange]);

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent>
				<DialogHeader>
					<DialogTitle>Add Schema URL</DialogTitle>
					<DialogDescription>
						Enter the URL of a GraphQL schema to add to your file list.
					</DialogDescription>
				</DialogHeader>
				<div className="grid gap-4 py-4">
					<div className="grid gap-2">
						<Label htmlFor="schema-url">Schema URL</Label>
						<Input
							id="schema-url"
							placeholder="https://example.com/schema.graphql"
							value={urlInput}
							onChange={(e) => {
								setUrlInput(e.target.value);
								setUrlError("");
							}}
							onKeyDown={(e) => {
								if (e.key === "Enter") {
									handleConfirm();
								}
							}}
						/>
						{urlError && <p className="text-sm text-destructive">{urlError}</p>}
					</div>
				</div>
				<DialogFooter>
					<Button variant="outline" onClick={() => onOpenChange(false)}>
						Cancel
					</Button>
					<Button onClick={handleConfirm}>Add URL</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
